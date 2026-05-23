"""Fetches live service state from running infrastructure."""

from __future__ import annotations

import subprocess
import json
from typing import Any


class FetchError(Exception):
    """Raised when fetching live service state fails."""


def fetch_docker_service_state(service_name: str) -> dict[str, Any]:
    """Return live state for a Docker container by name.

    Args:
        service_name: The name of the Docker container to inspect.

    Returns:
        A dict with normalised fields: image, ports, env, labels.

    Raises:
        FetchError: If the container is not found or Docker is unavailable.
    """
    try:
        result = subprocess.run(
            ["docker", "inspect", service_name],
            capture_output=True,
            text=True,
            timeout=10,
        )
    except FileNotFoundError:
        raise FetchError("Docker executable not found. Is Docker installed?")
    except subprocess.TimeoutExpired:
        raise FetchError(f"Timed out inspecting container '{service_name}'.")

    if result.returncode != 0:
        raise FetchError(
            f"Container '{service_name}' not found or Docker error: "
            f"{result.stderr.strip()}"
        )

    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise FetchError(f"Failed to parse Docker inspect output: {exc}") from exc

    if not raw:
        raise FetchError(f"No data returned for container '{service_name}'.")

    return _normalise_docker_state(raw[0])


def _normalise_docker_state(raw: dict[str, Any]) -> dict[str, Any]:
    """Normalise raw docker inspect output into a consistent schema."""
    config = raw.get("Config", {})
    host_config = raw.get("HostConfig", {})
    network_settings = raw.get("NetworkSettings", {})

    # Normalise environment variables into a dict
    env_list: list[str] = config.get("Env") or []
    env: dict[str, str] = {}
    for entry in env_list:
        if "=" in entry:
            key, _, value = entry.partition("=")
            env[key] = value

    # Normalise port bindings into list of "host:container" strings
    port_bindings: dict[str, Any] = host_config.get("PortBindings") or {}
    ports: list[str] = []
    for container_port, bindings in port_bindings.items():
        if bindings:
            for binding in bindings:
                host_port = binding.get("HostPort", "")
                ports.append(f"{host_port}:{container_port.split('/')[0]}")

    return {
        "image": config.get("Image", ""),
        "ports": ports,
        "env": env,
        "labels": config.get("Labels") or {},
        "restart_policy": host_config.get("RestartPolicy", {}).get("Name", ""),
    }
