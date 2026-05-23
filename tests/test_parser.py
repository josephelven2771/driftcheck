"""Tests for driftcheck.parser module."""

import textwrap
from pathlib import Path

import pytest

from driftcheck.parser import ParseError, extract_service_definitions, load_yaml


# ---------------------------------------------------------------------------
# load_yaml
# ---------------------------------------------------------------------------

def test_load_yaml_returns_dict(tmp_path: Path) -> None:
    f = tmp_path / "infra.yml"
    f.write_text("image: nginx\nport: 80\n")
    result = load_yaml(f)
    assert result == {"image": "nginx", "port": 80}


def test_load_yaml_empty_file_returns_empty_dict(tmp_path: Path) -> None:
    f = tmp_path / "empty.yml"
    f.write_text("")
    assert load_yaml(f) == {}


def test_load_yaml_file_not_found_raises(tmp_path: Path) -> None:
    with pytest.raises(ParseError, match="File not found"):
        load_yaml(tmp_path / "missing.yml")


def test_load_yaml_invalid_yaml_raises(tmp_path: Path) -> None:
    f = tmp_path / "bad.yml"
    f.write_text("key: [unclosed")
    with pytest.raises(ParseError, match="YAML parse error"):
        load_yaml(f)


def test_load_yaml_non_mapping_raises(tmp_path: Path) -> None:
    f = tmp_path / "list.yml"
    f.write_text("- item1\n- item2\n")
    with pytest.raises(ParseError, match="Expected a YAML mapping"):
        load_yaml(f)


# ---------------------------------------------------------------------------
# extract_service_definitions
# ---------------------------------------------------------------------------

SAMPLE_COMPOSE: dict = {
    "version": "3.9",
    "services": {
        "web": {"image": "nginx:latest", "ports": ["80:80"]},
        "db": {"image": "postgres:15", "environment": {"POSTGRES_DB": "app"}},
    },
}


def test_extract_service_definitions_returns_services() -> None:
    result = extract_service_definitions(SAMPLE_COMPOSE)
    assert set(result.keys()) == {"web", "db"}
    assert result["web"]["image"] == "nginx:latest"


def test_extract_service_definitions_no_services_key() -> None:
    assert extract_service_definitions({"version": "3.9"}) == {}


def test_extract_service_definitions_null_service_treated_as_empty() -> None:
    raw = {"services": {"bare": None}}
    result = extract_service_definitions(raw)
    assert result == {"bare": {}}


def test_extract_service_definitions_bad_services_type_raises() -> None:
    with pytest.raises(ParseError, match="'services' must be a mapping"):
        extract_service_definitions({"services": ["web", "db"]})


def test_extract_service_definitions_bad_service_config_raises() -> None:
    with pytest.raises(ParseError, match="Service 'web' config must be a mapping"):
        extract_service_definitions({"services": {"web": "nginx"}})
