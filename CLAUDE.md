# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Tunnelo is a Python CLI tool for managing SSH and kubectl port forwarding tunnels. It uses asyncio for concurrent tunnel management and supports YAML configuration files for defining multiple tunnel endpoints.

## Development Commands

### Installation and Dependencies
```bash
poetry install
```

### Running the Application
```bash
poetry run tunnelo config1.yaml config2.yaml
```

### Linting and Type Checking
```bash
poetry run ruff check .
poetry run pyright .
```

### Testing
```bash
# Run tests (if any exist in tests/ directory)
poetry run pytest
```

## Code Architecture

### Core Components

- **Main Entry Point**: `tunnelo/__main__.py` - CLI entry point that imports from hosts module
- **Hosts Module**: `tunnelo/hosts/` - Modular host configuration system:
  - `common.py`: Shared models (`TunnelMount`, `TunnelMountString`)
  - `ssh.py`: SSH-specific configuration (`SSHHostConfig`) and tunnel functions
  - `kubectl.py`: Kubectl-specific configuration (`KubectlHostConfig`, `KubectlResource`) and tunnel functions
  - `tunneled_kubectl.py`: Tunneled kubectl configuration (`TunneledKubectlHostConfig`) and two-step tunnel functions
  - `__init__.py`: Public API with `connect_host()` dispatcher and `load_config()`

### Key Functions

- `load_config()` (in `hosts/`): Parses YAML configuration files using pydantic validation
- `connect_host()` (in `hosts/`): Dispatches to appropriate host connector based on mode
- `connect_ssh_host()` (in `hosts/ssh.py`): Creates persistent SSH tunnels with auto-restart
- `connect_kubectl_host()` (in `hosts/kubectl.py`): Creates persistent kubectl tunnels with auto-restart
- `connect_tunneled_kubectl_host()` (in `hosts/tunneled_kubectl.py`): Creates persistent two-step tunneled kubectl connections
- `_main()` (in `__main__.py`): CLI entry point using Typer, orchestrates asyncio task management

### Configuration System

The tool supports three tunnel modes:
- **SSH Mode**: Direct SSH port forwarding to remote hosts
- **Kubectl Mode**: Kubernetes port forwarding to services/deployments
- **Tunneled Kubectl Mode**: Two-step tunneling through SSH to run kubectl port-forward on remote nodes

Configuration files are YAML-based and can specify multiple hosts with different modes. Each host can have multiple port mappings or resources.

### Async Architecture

Uses asyncio for concurrent tunnel management:
- Each tunnel runs in its own async task
- Automatic restart on tunnel failure (1-second delay)
- Graceful shutdown on KeyboardInterrupt
- All tunnels run concurrently within a single event loop

## Project Structure

- `tunnelo/__main__.py` - CLI entry point
- `tunnelo/hosts/` - Host configuration module
  - `__init__.py` - Public API with `connect_host()` and `load_config()`
  - `common.py` - Shared models and types
  - `ssh.py` - SSH host configuration and tunnel functions
  - `kubectl.py` - Kubectl host configuration and tunnel functions
  - `tunneled_kubectl.py` - Tunneled kubectl host configuration and two-step tunnel functions
- `configs/` - Example YAML configuration files for different environments
- `tests/` - Test directory (minimal setup)
- `pyproject.toml` - Poetry configuration with dependencies and dev tools

## Dependencies

- **typer**: CLI framework
- **pyyaml**: YAML configuration parsing
- **pydantic**: Data validation and configuration models
- **pyright**: Type checking (dev)
- **ruff**: Linting and formatting (dev)