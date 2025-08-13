import asyncio
import os
from typing import Literal

from pydantic import BaseModel, Field

from .common import TunnelMountString


class SSHHostConfig(BaseModel):
    mode: Literal["ssh"]
    mounts: list[TunnelMountString]
    hostname: str
    ssh_args: list[str] | None = Field(default=None)


async def open_ssh_tunnel(
    *,
    host: str,
    src_port: int,
    dst_port: int,
    extra_args: list[str] | None = None,
) -> None:
    command = ["ssh", "-L", f"{src_port}:localhost:{dst_port}", "-N", host]
    tunnel_name = f"{host}:{src_port}->{dst_port}"
    if extra_args:
        command.extend(extra_args)

    ssh_config_path = os.path.expanduser("~/.ssh/config")
    if os.path.exists(ssh_config_path):
        command.insert(1, "-F")
        command.insert(2, ssh_config_path)

    while True:
        print(f"[{tunnel_name}] `{' '.join(command)}`")
        process = await asyncio.create_subprocess_exec(
            *command,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.STDOUT,
            stdin=asyncio.subprocess.DEVNULL,
        )
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


async def connect_ssh_host(ssh_config: SSHHostConfig) -> None:
    async with asyncio.TaskGroup() as tg:
        for mount in ssh_config.mounts:
            tg.create_task(
                open_ssh_tunnel(
                    host=ssh_config.hostname,
                    src_port=mount.src_port,
                    dst_port=mount.dst_port,
                    extra_args=ssh_config.ssh_args,
                )
            )
