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

After installation, the `tunnelo` command will be available directly in your terminal (no need to use `poetry run`).

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
    teleport:
      tsh_host: my-cluster-host
      tsh_ssh_jump_args: ["-J", "jump.example.com"]  # optional
    remote_kube_client: dlmaster
    namespace: default  # optional
    context: my-cluster  # optional
    sudo: false  # optional, can be true or username string
    kubectl_args: ["--kubeconfig", "/path/to/config"]  # optional
    ssh_args: ["-i", "~/.ssh/id_rsa"]  # optional
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

## Templating

Tunnelo supports Jinja2 templating for dynamic configuration generation. This is useful for creating reusable configurations with variable values.

### Template Files

Template files should use the `.yaml.j2` extension and can contain Jinja2 template syntax:

```yaml
hosts:
  - mode: ssh
    hostname: {{ hostname }}
    mounts:
      {% for port in ports %}
      - "{{ port }}:80"
      {% endfor %}
    ssh_args: {{ ssh_args | default([]) }}
```

### Template Variables

You can pass variables to templates in several ways:

**Via CLI flags:**
```bash
tunnelo -t config.yaml.j2 -v hostname=example.com -v port=8080
```

**Via variable file:**
```yaml
# vars.yaml
hostname: example.com
ports: [8080, 8443]
ssh_args: ["-i", "~/.ssh/id_rsa"]
```

```bash
tunnelo -t config.yaml.j2 -vf vars.yaml
```

**Via JSON file:**
```json
{
  "hostname": "example.com",
  "ports": [8080, 8443],
  "ssh_args": ["-i", "~/.ssh/id_rsa"]
}
```

```bash
tunnelo -t config.yaml.j2 -vf vars.json
```

## Usage

After installation, the `tunnelo` command is available directly in your terminal.

### Regular Configuration Files

Run tunnels from one or more configuration files:

```bash
tunnelo config1.yaml config2.yaml
```

### Template Files

Use Jinja2 templates for dynamic configurations:

```bash
# With template variables
tunnelo -t config.yaml.j2 -v hostname=example.com -v port=8080

# With variable file
tunnelo -t config.yaml.j2 -vf vars.yaml

# With JSON variable file
tunnelo -t config.yaml.j2 -vf vars.json
```

### Mixed Usage

You can combine regular config files and templates:

```bash
tunnelo config1.yaml -t template.yaml.j2 -v var=value config2.yaml
```
