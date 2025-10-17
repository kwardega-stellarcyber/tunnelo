import asyncio
import contextlib
import re
from typing import Literal

from pydantic import BaseModel, Field

from .common import KubectlBase, ssh_user_config_flags


class TeleportConfig(BaseModel):
    tsh_host: str
    tsh_ssh_jump_args: list[str] | None = Field(default=None)


class TunneledKubectlHostConfig(KubectlBase):
    mode: Literal["tunneled_kubectl"]
    teleport: TeleportConfig | None = Field(default=None)
    remote_kube_client: str
    ssh_args: list[str] | None = Field(default=None)


async def open_tunneled_kubectl_tunnel(
    *,
    teleport: TeleportConfig | None,
    remote_kube_client: str,
    ssh_args: list[str] | None = None,
    context: str | None,
    namespace: str | None,
    resource: str,
    src_port: int,
    dst_port: int,
    kubectl_args: list[str] | None = None,
    kubectl_sudo: bool | str = False,
) -> None:
    """
    Creates a tunneled kubectl port-forward in two steps:
    1. Start kubectl port-forward on remote node with dynamic port
    2. Create SSH tunnel to the dynamically assigned port
    """
    # Build base connection command with SSH config if needed

    # Step 1: Start kubectl port-forward and capture the dynamic port
    kubectl_cmd = [
        *(("tsh", "ssh", teleport.tsh_host, "exec") if teleport else ()),
        "ssh",
        "-tt",
        *(
            ssh_user_config_flags()
            if not teleport
            else (teleport.tsh_ssh_jump_args or ())
        ),
        *(ssh_args or ()),
        remote_kube_client,
        "exec",
        *(
            (
                "sudo",
                "-i",
                *(("-u", kubectl_sudo) if isinstance(kubectl_sudo, str) else ()),
            )
            if kubectl_sudo
            else ()
        ),
        "kubectl",
        *(kubectl_args or ()),
        "port-forward",
        "--address=0.0.0.0",
        *(("--context", context) if context else ()),
        *(("--namespace", namespace) if namespace else ()),
        resource,
        f"0:{dst_port}",
    ]

    tunnel_name = f"{resource}:{src_port}->{dst_port}"

    while True:
        kubectl_process = None
        tunnel_process = None
        dynamic_port = None
        try:
            print(
                f"[{tunnel_name}] Starting kubectl port-forward: `{' '.join(kubectl_cmd)}`",
                flush=True,
            )

            # Start kubectl port-forward process
            kubectl_process = await asyncio.create_subprocess_exec(
                *kubectl_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                stdin=asyncio.subprocess.DEVNULL,
            )

            # Read output to find the dynamically assigned port
            async def read_kubectl_output():
                if kubectl_process is None or kubectl_process.stdout is None:
                    return None
                while True:
                    line = await kubectl_process.stdout.readline()
                    if not line:
                        break

                    line_str = line.decode().strip()
                    print(f"[{tunnel_name}] kubectl: {line_str}", flush=True)

                    # Look for "Forwarding from 0.0.0.0:XXXX -> YYYY"
                    port_match = re.search(
                        r"Forwarding from 0\.0\.0\.0:(\d+)", line_str
                    )
                    if port_match:
                        dynamic_port = int(port_match.group(1))
                        print(
                            f"[{tunnel_name}] Found dynamic port: {dynamic_port}",
                            flush=True,
                        )
                        return dynamic_port
                return None

            # Wait for dynamic port with timeout
            try:
                dynamic_port = await asyncio.wait_for(read_kubectl_output(), timeout=10)
            except asyncio.TimeoutError:
                print(
                    f"[{tunnel_name}] Timeout waiting for dynamic port from kubectl output",
                    flush=True,
                )
                kubectl_process.terminate()
                await kubectl_process.wait()
                continue

            if not dynamic_port:
                print(
                    f"[{tunnel_name}] Failed to detect dynamic port from kubectl output",
                    flush=True,
                )
                kubectl_process.terminate()
                await kubectl_process.wait()
                continue

            # Step 2: Create SSH tunnel to the dynamic port
            tunnel_cmd = [
                *(("tsh",) if teleport else ()),
                "ssh",
                *(ssh_user_config_flags() if not teleport else ()),
                *(ssh_args or ()),
                "-L",
                f"{src_port}:{remote_kube_client if teleport else 'localhost'}:{dynamic_port}",
                "-N",
                teleport.tsh_host if teleport else remote_kube_client,
            ]

            print(
                f"[{tunnel_name}] Starting SSH tunnel: `{' '.join(tunnel_cmd)}`",
                flush=True,
            )
            tunnel_process = await asyncio.create_subprocess_exec(
                *tunnel_cmd,
            )
            futs = {
                asyncio.create_task(kubectl_process.wait()): kubectl_process,
                asyncio.create_task(tunnel_process.wait()): tunnel_process,
            }

            # Wait for either process to complete
            _, pending = await asyncio.wait(
                futs.keys(), return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                futs[task].terminate()
                await task

        except asyncio.CancelledError:
            print(f"[{tunnel_name}] Cancelling tunneled kubectl", flush=True)
            with contextlib.suppress(ProcessLookupError):
                if kubectl_process is not None:
                    kubectl_process.terminate()
                    await kubectl_process.wait()
                if tunnel_process is not None:
                    tunnel_process.terminate()
                    await tunnel_process.wait()
            break
        except Exception as e:
            print(f"[{tunnel_name}] Error in tunneled kubectl: {e}", flush=True)
        finally:
            await asyncio.sleep(1)


async def connect_tunneled_kubectl_host(config: TunneledKubectlHostConfig) -> None:
    async with asyncio.TaskGroup() as tg:
        for resource in config.resources:
            for port in resource.ports:
                tg.create_task(
                    open_tunneled_kubectl_tunnel(
                        teleport=config.teleport,
                        remote_kube_client=config.remote_kube_client,
                        ssh_args=config.ssh_args,
                        context=config.context,
                        namespace=config.namespace,
                        resource=resource.resource,
                        src_port=port.src_port,
                        dst_port=port.dst_port,
                        kubectl_args=config.kubectl_args,
                        kubectl_sudo=config.sudo,
                    )
                )
