import asyncio
import os
from dataclasses import dataclass
from typing import Literal

import typer
import yaml


@dataclass
class TunnelMount:
    src_port: int
    dst_port: int


@dataclass
class KubectlResource:
    resource: str
    ports: list[TunnelMount]


@dataclass
class HostConfig:
    mode: Literal["ssh", "kubectl"]
    mounts: list[TunnelMount]  # For SSH mode
    resources: list[KubectlResource] | None = None  # For kubectl mode
    # SSH specific
    hostname: str | None = None
    ssh_args: list[str] | None = None
    # Kubectl specific
    context: str | None = None
    namespace: str | None = None


async def open_ssh_tunnel(
    *,
    host: str,
    src_port: int,
    dst_port: int,
    extra_args: list[str] | None = None,
) -> None:
    command = ["ssh", "-L", f"{src_port}:localhost:{dst_port}", "-N", host]
    if extra_args:
        command.extend(extra_args)

    ssh_config_path = os.path.expanduser("~/.ssh/config")
    if os.path.exists(ssh_config_path):
        command.insert(1, "-F")
        command.insert(2, ssh_config_path)

    while True:
        print(command)
        process = await asyncio.create_subprocess_exec(*command)
        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            break
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await asyncio.sleep(1)


async def open_kubectl_tunnel(
    *,
    context: str | None,
    namespace: str | None,
    resource: str,
    src_port: int,
    dst_port: int,
) -> None:
    command = ["kubectl", "port-forward"]
    
    if context:
        command.extend(["--context", context])
    if namespace:
        command.extend(["--namespace", namespace])
    
    command.extend([resource, f"{src_port}:{dst_port}"])

    while True:
        print(command)
        process = await asyncio.create_subprocess_exec(*command)
        try:
            await process.wait()
        except asyncio.CancelledError:
            process.terminate()
            await process.wait()
            break
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await asyncio.sleep(1)


def load_config(file_path: str) -> list[HostConfig]:
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)

    hosts = []
    for host_config in config.get("hosts", []):
        if host_config["mode"] == "ssh":
            mounts = []
            for mount in host_config.get("mounts", []):
                src_port, dst_port = map(int, mount.split(":"))
                mounts.append(TunnelMount(src_port=src_port, dst_port=dst_port))
            
            host = HostConfig(
                mode="ssh",
                mounts=mounts,
                hostname=host_config["hostname"],
                ssh_args=host_config.get("ssh_args"),
            )
        else:  # kubectl mode
            resources = []
            for resource in host_config.get("resources", []):
                ports = []
                for port in resource.get("ports", []):
                    src_port, dst_port = map(int, port.split(":"))
                    ports.append(TunnelMount(src_port=src_port, dst_port=dst_port))
                resources.append(KubectlResource(resource=resource["resource"], ports=ports))
            
            host = HostConfig(
                mode="kubectl",
                mounts=[],  # Not used in kubectl mode
                resources=resources,
                context=host_config.get("context"),
                namespace=host_config.get("namespace"),
            )
        hosts.append(host)
    
    return hosts


def _main(
    config_files: list[str] = typer.Argument(
        ...,
        help="One or more configuration files to load",
    ),
):
    if not config_files:
        typer.echo("At least one configuration file is required")
        raise typer.Exit(code=1)

    # Load all configurations
    all_hosts: list[HostConfig] = []
    for config_file in config_files:
        try:
            hosts = load_config(config_file)
            all_hosts.extend(hosts)
        except Exception as e:
            typer.echo(f"Error loading config file {config_file}: {e}")
            raise typer.Exit(code=1)

    if not all_hosts:
        typer.echo("No valid host configurations found in any of the provided files")
        raise typer.Exit(code=1)

    loop = asyncio.new_event_loop()
    tasks = []

    for host_config in all_hosts:
        if host_config.mode == "ssh":
            if not host_config.hostname:
                typer.echo(f"Hostname required for SSH mode in host {host_config}")
                raise typer.Exit(code=1)
            for mount in host_config.mounts:
                task = loop.create_task(
                    open_ssh_tunnel(
                        host=host_config.hostname,
                        src_port=mount.src_port,
                        dst_port=mount.dst_port,
                        extra_args=host_config.ssh_args,
                    )
                )
                tasks.append(task)
        elif host_config.mode == "kubectl":
            if not host_config.resources:
                typer.echo(f"Resources required for kubectl mode in host {host_config}")
                raise typer.Exit(code=1)
            for resource in host_config.resources:
                for port in resource.ports:
                    task = loop.create_task(
                        open_kubectl_tunnel(
                            context=host_config.context,
                            namespace=host_config.namespace,
                            resource=resource.resource,
                            src_port=port.src_port,
                            dst_port=port.dst_port,
                        )
                    )
                    tasks.append(task)
        else:
            typer.echo(f"Invalid mode: {host_config.mode}")
            raise typer.Exit(code=1)

    try:
        loop.run_until_complete(asyncio.gather(*tasks))
    except KeyboardInterrupt:
        print("Interrupted")
        for task in tasks:
            task.cancel()
    finally:
        loop.run_until_complete(asyncio.gather(*tasks))
        loop.close()


def main():
    typer.run(_main)


if __name__ == "__main__":
    main()
