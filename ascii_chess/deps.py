from __future__ import annotations

import os
import platform
import shutil
import sys
import subprocess
from dataclasses import dataclass
from typing import Optional


@dataclass
class DependencyStatus:
    python_chess_ok: bool
    stockfish_path: Optional[str]


def ensure_python_chess(auto_install: bool = True) -> bool:
    try:
        import chess  # noqa: F401
        return True
    except ModuleNotFoundError:
        if not auto_install:
            return False
        return _attempt_install_python_chess()


def _attempt_install_python_chess() -> bool:
    python_executable = sys.executable
    if not python_executable:
        return False
    result = subprocess.run(
        [python_executable, "-m", "pip", "install", "python-chess"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        return False
    try:
        import chess  # noqa: F401
    except ModuleNotFoundError:
        return False
    return True


def locate_stockfish(explicit_path: Optional[str]) -> Optional[str]:
    if explicit_path:
        resolved = _resolve_candidate(explicit_path)
        if resolved:
            return resolved
        return None

    discovered = shutil.which("stockfish")
    if discovered:
        return discovered

    for candidate in _bundled_candidates():
        resolved = _resolve_candidate(candidate)
        if resolved:
            return resolved
    return None


def _resolve_candidate(path: str) -> Optional[str]:
    expanded = os.path.abspath(os.path.expanduser(path))
    if os.path.isdir(expanded):
        return _find_executable_in_dir(expanded)
    if os.path.isfile(expanded):
        if _is_executable(expanded):
            return expanded
        # Allow `.exe` even if `os.X_OK` is False on Windows filesystems.
        if expanded.lower().endswith(".exe") and sys.platform.startswith("win"):
            return expanded
    located = shutil.which(expanded)
    if located:
        return located
    return None


def _find_executable_in_dir(directory: str) -> Optional[str]:
    for entry in sorted(os.listdir(directory)):
        full = os.path.join(directory, entry)
        if os.path.isdir(full):
            nested = _find_executable_in_dir(full)
            if nested:
                return nested
            continue
        if "stockfish" in entry.lower() and _is_executable(full):
            return full
        if "stockfish" in entry.lower() and sys.platform.startswith("win") and entry.lower().endswith(".exe"):
            return full
    return None


def _is_executable(path: str) -> bool:
    return os.access(path, os.X_OK)


def _bundled_candidates() -> list[str]:
    system = platform.system().lower()
    base_dir = os.path.join(os.path.dirname(__file__), "..", "engines")
    base_dir = os.path.abspath(base_dir)

    mapping = {
        "darwin": ["stockfish-macos"],
        "windows": ["stockfish-windows", "stockfish-windows.exe", "stockfish.exe"],
        "win32": ["stockfish-windows", "stockfish-windows.exe", "stockfish.exe"],
    }

    names = mapping.get(system, [])
    return [os.path.join(base_dir, name) for name in names]


def collect_dependency_status(engine_path: Optional[str], auto_install: bool = True) -> DependencyStatus:
    python_chess_ok = ensure_python_chess(auto_install=auto_install)
    stockfish_path = locate_stockfish(engine_path)
    return DependencyStatus(
        python_chess_ok=python_chess_ok,
        stockfish_path=stockfish_path,
    )
