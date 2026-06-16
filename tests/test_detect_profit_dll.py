"""ProfitDLL detection stub tests (no real DLL required)."""

import json
import subprocess
import sys
from pathlib import Path

from src.integrations.profit_dll_detect import detect_profit_dll, find_profit_dll_candidates


def test_detect_returns_structure():
    result = detect_profit_dll()
    assert "found" in result
    assert "candidates" in result
    assert "platform" in result


def test_find_candidates_with_env(tmp_path, monkeypatch):
    fake_dll = tmp_path / "ProfitDLL.dll"
    fake_dll.write_bytes(b"fake")
    monkeypatch.setenv("PROFIT_DLL_PATH", str(fake_dll))
    candidates = find_profit_dll_candidates()
    assert str(fake_dll.resolve()) in [str(Path(c).resolve()) for c in candidates]


def test_cli_json_exit_code(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.delenv("PROFIT_DLL_PATH", raising=False)
    proc = subprocess.run(
        [sys.executable, str(root / "scripts" / "detect_profit_dll.py"), "--json"],
        cwd=root,
        capture_output=True,
        text=True,
        timeout=30,
    )
    data = json.loads(proc.stdout)
    assert isinstance(data["found"], bool)
    assert proc.returncode in (0, 2)
