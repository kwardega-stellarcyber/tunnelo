import asyncio
import yaml
import json
from pathlib import Path
from typing import Annotated, Any

import typer

from .hosts import HostConfig, ConfigFile, connect_host, load_config
from .templating import load_template_config


def _main(
    config_files: Annotated[
        list[str] | None,
        typer.Option(
            "-c",
            "--config",
            help="Configuration files to load",
        ),
    ] = None,
    template: Annotated[
        str | None,
        typer.Option(
            "-t",
            "--template",
            help="Template file to render instead of loading config files directly",
        ),
    ] = None,
    template_vars: Annotated[
        str | None,
        typer.Option(
            "-vf",
            "--template-vars",
            help="JSON or YAML file containing template variables",
        ),
    ] = None,
    template_var: Annotated[
        list[str],
        typer.Option(
            "-v",
            "--template-var",
            help="Template variable in key=value format (can be used multiple times)",
        ),
    ] = [],
):
    if not config_files and not template:
        typer.echo("At least one configuration file or template is required")
        raise typer.Exit(code=1)

    # Prepare template variables
    template_variables: dict[str, Any] = {}

    # Load variables from file if provided
    if template_vars:
        try:
            vars_path = Path(template_vars)
            match vars_path.suffix.lower():
                case ".json":
                    with Path(vars_path).open() as f:
                        template_values = json.load(f)
                case ".yaml":
                    with Path(vars_path).open() as f:
                        template_values = yaml.safe_load(f)
                case _:
                    typer.echo(
                        f"Unsupported template variable file type: {vars_path.suffix}"
                    )
                    raise ValueError(
                        f"Unsupported template variable file type: {vars_path.suffix}"
                    )
            if not isinstance(template_values, dict):
                raise ValueError(
                    f"Template variables must be a dictionary: {template_values}"
                )
            template_variables |= template_values
        except Exception as e:
            typer.echo(f"Error loading template variables from {template_vars}: {e}")
            raise typer.Exit(code=1)

    # Add variables from CLI flags
    for var in template_var:
        if "=" not in var:
            typer.echo(f"Template variable must be in key=value format: {var}")
            raise typer.Exit(code=1)
        key, value = var.split("=", 1)
        template_variables[key] = value

    # Load all configurations
    all_hosts: list[HostConfig] = []

    if template:
        # Load from template
        try:
            config_data = load_template_config(template, template_variables)
            config_file = ConfigFile.model_validate(config_data.get("hosts", []))
            all_hosts.extend(config_file.root)
        except Exception as e:
            typer.echo(f"Error loading template {template}: {e}")
            raise typer.Exit(code=1)
    # Load from regular config files
    for config_file in config_files or []:
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


def main():
    typer.run(_main)


if __name__ == "__main__":
    main()
