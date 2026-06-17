"""LOW_RAM_MODE — config flag, ops budget, and scanner cache behavior."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest

from src.config import get_settings
from src.services.ops_panel import build_ops_panel
from src.services.resource_profile import get_resource_profile

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def low_ram_env(monkeypatch):
    monkeypatch.setenv("LOW_RAM_MODE", "true")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_low_ram_mode_env_flag(low_ram_env):
    assert get_settings().low_ram_mode is True
    assert get_settings().low_ram_enabled is True


def test_effective_ram_budget_capped(low_ram_env, monkeypatch):
    monkeypatch.setenv("RAM_BUDGET_MB", "1200")
    get_settings.cache_clear()
    prof = get_resource_profile()
    assert prof.effective_ram_budget_mb == 500


def test_scanner_skips_universe_cache(low_ram_env, monkeypatch):
    monkeypatch.setenv("SCANNER_MODE", "filipe_core14")
    get_settings.cache_clear()
    import src.services.scanner as scanner_mod
    from src.services.scanner import _avg_volume_map

    scanner_mod._UNIVERSE_MAP = None
    prof = get_resource_profile()
    assert prof.scanner_universe_cache is False
    m1 = _avg_volume_map()
    m2 = _avg_volume_map()
    assert m1 == m2
    assert scanner_mod._UNIVERSE_MAP is None


def test_ops_panel_uses_effective_budget(low_ram_env, monkeypatch):
    monkeypatch.setenv("RAM_BUDGET_MB", "1200")
    get_settings.cache_clear()
    panel = build_ops_panel()
    assert panel["ram_budget_mb"] == 500
    assert panel["resource_profile"]["low_ram_mode"] is True


def test_dev_script_exists():
    dev = ROOT / "scripts" / "dev.py"
    assert dev.exists()


def test_bench_memory_script_runs():
    script = ROOT / "scripts" / "bench_memory.py"
    if not script.exists():
        pytest.skip("bench_memory.py missing")
    result = subprocess.run(
        [sys.executable, str(script), "--low-ram", "--json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, result.stderr
    assert "tracemalloc_peak_kb" in result.stdout
