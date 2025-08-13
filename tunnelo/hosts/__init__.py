import yaml
from pydantic import RootModel

from .ssh import SSHHostConfig, connect_ssh_host
from .kubectl import KubectlHostConfig, connect_kubectl_host
from .tunneled_kubectl import TunneledKubectlHostConfig, connect_tunneled_kubectl_host


HostConfig = RootModel[SSHHostConfig | KubectlHostConfig | TunneledKubectlHostConfig]
ConfigFile = RootModel[list[HostConfig]]


__all__ = [
    "HostConfig",
    "SSHHostConfig",
    "KubectlHostConfig",
    "TunneledKubectlHostConfig",
    "connect_host",
    "load_config",
]


async def connect_host(config: HostConfig) -> None:
    host_config = config.root
    match host_config.mode:
        case "ssh":
            await connect_ssh_host(host_config)
        case "kubectl":
            await connect_kubectl_host(host_config)
        case "tunneled_kubectl":
            await connect_tunneled_kubectl_host(host_config)
        case _:  # type: ignore
            raise ValueError(f"Unsupported mode: {host_config.mode}")


def load_config(file_path: str) -> list[HostConfig]:
    with open(file_path, "r") as file:
        config = yaml.safe_load(file)

    config_file = ConfigFile.model_validate(config.get("hosts", []))
    return config_file.root
