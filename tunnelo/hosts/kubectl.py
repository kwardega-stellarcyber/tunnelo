import asyncio
from typing import Literal


from .common import KubectlBase


class KubectlHostConfig(KubectlBase):
    mode: Literal["kubectl"]


async def open_kubectl_tunnel(
    *,
    context: str | None,
    namespace: str | None,
    resource: str,
    src_port: int,
    dst_port: int,
) -> None:
    command = ["kubectl", "port-forward"]
    tunnel_name = f"{resource}:{src_port}->{dst_port}"

    if context:
        command.extend(["--context", context])
    if namespace:
        command.extend(["--namespace", namespace])

    command.extend([resource, f"{src_port}:{dst_port}"])

    while True:
        print(f"[{tunnel_name}] `{' '.join(command)}`")
        process = await asyncio.create_subprocess_exec(*command)
        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            break
        except Exception as e:
            print(f"[{tunnel_name}] Error: {e}")
        finally:
            await asyncio.sleep(1)


async def connect_kubectl_host(kubectl_config: KubectlHostConfig) -> None:
    async with asyncio.TaskGroup() as tg:
        for resource in kubectl_config.resources:
            for port in resource.ports:
                tg.create_task(
                    open_kubectl_tunnel(
                        context=kubectl_config.context,
                        namespace=kubectl_config.namespace,
                        resource=resource.resource,
                        src_port=port.src_port,
                        dst_port=port.dst_port,
                    )
                )
