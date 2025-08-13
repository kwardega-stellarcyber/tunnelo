# Tunnelo

A flexible tunnel management tool that supports SSH, kubectl, and tunneled kubectl port forwarding. Tunnelo allows you to manage multiple tunnels across different hosts and contexts through a simple YAML configuration.

## Features

- Support for SSH, kubectl, and tunneled kubectl port forwarding
- Multiple hosts per configuration
- Multiple resources and ports per host
- Automatic tunnel restart on failure

## Installation

```bash
poetry install
```

## Configuration

Tunnelo uses YAML configuration files to define tunnels. You can specify multiple configuration files when running the tool.

### SSH Mode Example

```yaml
hosts:
  - mode: ssh
    hostname: example.com
    mounts:
      - "8080:80"
      - "8443:443"
    ssh_args: ["-i", "~/.ssh/id_rsa"]
```

### Kubectl Mode Example

```yaml
hosts:
  - mode: kubectl
    context: my-cluster
    namespace: default
    resources:
      - resource: service/my-service
        ports:
          - "8080:80"
          - "8443:443"
      - resource: deployment/my-deployment
        ports:
          - "9090:80"
```

### Tunneled Kubectl Mode Example

For scenarios where you need to connect through an intermediate host to run kubectl port-forward on a remote node:

```yaml
hosts:
  - mode: tunneled_kubectl
    cluster: my-cluster
    node: dlmaster  # optional, defaults to "dlmaster"
    namespace: default  # optional
    connection_command: ["tsh", "ssh"]  # optional, defaults to ["tsh", "ssh"]
    resources:
      - resource: service/my-service
        ports:
          - "8080:80"
          - "8443:443"
      - resource: deployment/my-deployment
        ports:
          - "9090:80"
```

This mode creates a two-step tunnel:
1. SSH to the cluster host and run kubectl port-forward with a dynamic port
2. Create an SSH tunnel from your local machine to the dynamically assigned port

## Usage

Run tunnels from one or more configuration files:

```bash
poetry run tunnelo config1.yaml config2.yaml
```
