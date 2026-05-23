"""Parser for infrastructure definition files (e.g., docker-compose, systemd units)."""

import yaml
from pathlib import Path
from typing import Any


class ParseError(Exception):
    """Raised when an infrastructure definition file cannot be parsed."""
    pass


def load_yaml(path: str | Path) -> dict[str, Any]:
    """Load and parse a YAML infrastructure definition file.

    Args:
        path: Path to the YAML file.

    Returns:
        Parsed contents as a dictionary.

    Raises:
        ParseError: If the file is missing, unreadable, or contains invalid YAML.
    """
    file_path = Path(path)

    if not file_path.exists():
        raise ParseError(f"File not found: {file_path}")

    if not file_path.is_file():
        raise ParseError(f"Path is not a file: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except yaml.YAMLError as exc:
        raise ParseError(f"YAML parse error in {file_path}: {exc}") from exc
    except OSError as exc:
        raise ParseError(f"Cannot read file {file_path}: {exc}") from exc

    if data is None:
        return {}

    if not isinstance(data, dict):
        raise ParseError(
            f"Expected a YAML mapping at the top level, got {type(data).__name__}"
        )

    return data


def extract_service_definitions(raw: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Extract per-service configuration blocks from a parsed docker-compose-style dict.

    Args:
        raw: Top-level parsed YAML dictionary.

    Returns:
        Mapping of service name -> service config dict.

    Raises:
        ParseError: If the 'services' key is present but malformed.
    """
    services_raw = raw.get("services")

    if services_raw is None:
        return {}

    if not isinstance(services_raw, dict):
        raise ParseError(
            f"'services' must be a mapping, got {type(services_raw).__name__}"
        )

    result: dict[str, dict[str, Any]] = {}
    for name, config in services_raw.items():
        if config is None:
            config = {}
        if not isinstance(config, dict):
            raise ParseError(
                f"Service '{name}' config must be a mapping, got {type(config).__name__}"
            )
        result[name] = config

    return result
