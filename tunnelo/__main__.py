import asyncio

import typer

from .hosts import HostConfig, connect_host, load_config


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

    async def run_tunnels():
        async with asyncio.TaskGroup() as tg:
            for host_config in all_hosts:
                tg.create_task(connect_host(host_config))

    try:
        asyncio.run(run_tunnels())
    except KeyboardInterrupt:
        print("\nInterrupted - shutting down gracefully...")
    except ExceptionGroup as eg:
        # Handle task cancellation during shutdown
        if all(isinstance(e, asyncio.CancelledError) for e in eg.exceptions):
            print("Shutdown complete")
        else:
            typer.echo(f"Error running tunnels: {eg}")
            raise typer.Exit(code=1)


if __name__ == "__main__":
    typer.run(_main)
