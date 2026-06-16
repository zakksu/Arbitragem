"""ProfitDLL path discovery for Windows setup wizard and dev.py."""

from __future__ import annotations

import os
import sys
from pathlib import Path

DLL_NAMES = ("ProfitDLL.dll", "ProfitDLL64.dll", "Profit.dll")


def _windows_search_roots() -> list[Path]:
    roots: list[Path] = []
    for env_key in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA", "APPDATA"):
        val = os.environ.get(env_key)
        if val:
            roots.append(Path(val))
    roots.extend(
        [
            Path(r"C:\Nelogica"),
            Path(r"C:\Program Files\Nelogica"),
            Path(r"C:\Program Files (x86)\Nelogica"),
        ]
    )
    seen: set[str] = set()
    out: list[Path] = []
    for root in roots:
        key = str(root).lower()
        if key not in seen and root.exists():
            seen.add(key)
            out.append(root)
    return out


def _registry_hint() -> Path | None:
    if sys.platform != "win32":
        return None
    try:
        import winreg

        for hive, subkey in (
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Nelogica\Profit"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Nelogica\Profit"),
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\WOW6432Node\Nelogica\Profit"),
        ):
            try:
                with winreg.OpenKey(hive, subkey) as key:
                    for name in ("InstallPath", "Path", "ProfitPath"):
                        try:
                            val, _ = winreg.QueryValueEx(key, name)
                            p = Path(str(val))
                            if p.exists():
                                return p
                        except OSError:
                            continue
            except OSError:
                continue
    except ImportError:
        pass
    return None


def find_profit_dll_candidates(*, max_depth: int = 4) -> list[Path]:
    """Return unique ProfitDLL paths, best match first."""
    found: list[Path] = []
    seen: set[str] = set()

    def add(path: Path) -> None:
        resolved = path.resolve()
        key = str(resolved).lower()
        if key not in seen and resolved.is_file():
            seen.add(key)
            found.append(resolved)

    hint = _registry_hint()
    if hint:
        for name in DLL_NAMES:
            direct = hint / name
            if direct.is_file():
                add(direct)
        for name in DLL_NAMES:
            for match in hint.rglob(name):
                add(match)

    for root in _windows_search_roots():
        for name in DLL_NAMES:
            direct = root / "Profit" / name
            if direct.is_file():
                add(direct)
        try:
            for depth, (dirpath, dirnames, filenames) in enumerate(os.walk(root)):
                if depth > max_depth:
                    dirnames.clear()
                    continue
                for name in DLL_NAMES:
                    if name in filenames:
                        add(Path(dirpath) / name)
        except OSError:
            continue

    configured = os.environ.get("PROFIT_DLL_PATH", "").strip()
    if configured:
        p = Path(configured)
        if p.is_file():
            add(p)

    return found


def detect_profit_dll() -> dict:
    """Structured detect result for API + CLI."""
    candidates = find_profit_dll_candidates()
    return {
        "found": bool(candidates),
        "count": len(candidates),
        "candidates": [str(p) for p in candidates],
        "recommended": str(candidates[0]) if candidates else None,
        "platform": sys.platform,
    }


def env_line_for_best_match() -> str | None:
    result = detect_profit_dll()
    if result["recommended"]:
        return f"PROFIT_DLL_PATH={result['recommended']}"
    return None
