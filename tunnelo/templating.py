"""Template processing utilities for Tunnelo configurations."""

import yaml
from jinja2 import Environment, TemplateError
from typing import Any, Never


def raise_filter(v: str) -> Never:
    raise TemplateError(v)


_env = Environment()
_env.filters["raise"] = raise_filter


def render_template(template_content: str, variables: dict[str, Any]) -> str:
    """
    Render a Jinja2 template with the provided variables.

    Args:
        template_content: The template content as a string
        variables: Dictionary of variables to use in template rendering

    Returns:
        Rendered template as a string

    Raises:
        TemplateError: If template rendering fails
    """
    template = _env.from_string(template_content)
    return template.render(**variables)


def load_template_config(
    template_path: str, variables: dict[str, Any]
) -> dict[str, Any]:
    """
    Load and render a template configuration file.

    Args:
        template_path: Path to the template file
        variables: Variables to use for template rendering

    Returns:
        Parsed YAML configuration as a dictionary

    Raises:
        FileNotFoundError: If template file doesn't exist
        TemplateError: If template rendering fails
        yaml.YAMLError: If rendered content is not valid YAML
    """
    with open(template_path, "r") as f:
        template_content = f.read()

    rendered_content = render_template(template_content, variables)
    return yaml.safe_load(rendered_content)
