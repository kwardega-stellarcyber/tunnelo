from functools import cache
import os
from typing import Annotated

from pydantic import BaseModel, BeforeValidator, Field


class TunnelMount(BaseModel):
    src_port: int
    dst_port: int

    @staticmethod
    def from_str(s: str) -> "TunnelMount":
        src_port, dst_port = map(int, s.split(":"))
        return TunnelMount(src_port=src_port, dst_port=dst_port)


TunnelMountString = Annotated[TunnelMount, BeforeValidator(TunnelMount.from_str)]


class KubectlResource(BaseModel):
    resource: str
    ports: list[TunnelMountString]


class KubectlBase(BaseModel):
    resources: list[KubectlResource]
    context: str | None = Field(default=None)
    namespace: str | None = Field(default=None)
    kubectl_args: list[str] | None = Field(default=None)
    sudo: bool | str = Field(default=False)


@cache
def ssh_user_config_flags() -> tuple[str, ...]:
    ssh_config_path = os.path.expanduser("~/.ssh/config")
    if os.path.exists(ssh_config_path):
        return ("-F", ssh_config_path)
    return ()
