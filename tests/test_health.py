"""Unit tests for fleetwatcher health observer (no network, no sc.exe)."""

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from fleetwatcher_mcp.health import (  # noqa: E402
    classify,
    parse_fleet_config,
    remediation,
    service_candidates,
)


def test_classify_healthy():
    assert classify(listening=True, http_ok=True, http_status=200, expected="x", claimed_by=["x"]) == "healthy"


def test_classify_dead():
    assert classify(listening=False, http_ok=None, http_status=None, expected="x", claimed_by=["x"]) == "dead"


def test_classify_unbound():
    assert classify(listening=False, http_ok=None, http_status=None, expected=None, claimed_by=["x"]) == "unbound"


def test_classify_hung():
    assert (
        classify(listening=True, http_ok=False, http_status=None, expected="x", claimed_by=["x"])
        == "listening-but-hung"
    )


def test_classify_conflict():
    assert (
        classify(listening=True, http_ok=True, http_status=200, expected="a", claimed_by=["a", "b"])
        == "conflict"
    )


def test_parse_fleet_config():
    with tempfile.TemporaryDirectory() as d:
        cfg = (
            "@{\n    Name = 'demo-mcp'\n    BackendPort = 10999\n"
            "    HealthPath = '/api/health'\n}\n"
        )
        with open(os.path.join(d, "fleet-start.config.ps1"), "w", encoding="utf-8") as f:
            f.write(cfg)
        out = parse_fleet_config(d)
        assert out["backend_port"] == 10999
        assert out["health_path"] == "/api/health"
        assert out["config_name"] == "demo-mcp"


def test_parse_fleet_config_missing():
    with tempfile.TemporaryDirectory() as d:
        assert parse_fleet_config(d) == {}


def test_service_candidates_order():
    cands = service_candidates("demo")
    assert cands[0] == "demo"
    assert "demo-mcp" in cands


def test_remediation_mentions_sc_and_pid():
    s = remediation("demo", 10999)
    assert "sc.exe stop demo" in s
    assert "10999" in s
    assert "taskkill" not in s.lower() or "never taskkill" in s.lower()
