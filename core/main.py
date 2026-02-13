#!/usr/bin/env python3
"""QTMoS core CLI entrypoint.

Minimal bootstrap: keep dependencies optional so the core can run in a fresh env.
"""

try:
    from dotenv import load_dotenv  # type: ignore

    load_dotenv()
except ModuleNotFoundError:
    # Optional dependency; continue without .env support.
    pass

from pathlib import Path
import sys
import os
import subprocess
import socket


def _init_line_editing(history_name: str = ".qtmos_history"):
    """Enable arrow-key history/editing where possible.

    - Linux/macOS: readline
    - Windows: works if pyreadline3 provides readline
    """
    try:
        import readline  # type: ignore
    except Exception:
        return

    hist_file = str(Path.home() / history_name)
    try:
        readline.parse_and_bind("tab: complete")
        # Enable arrow history search if supported
        readline.parse_and_bind('"\\e[A": history-search-backward')
        readline.parse_and_bind('"\\e[B": history-search-forward')
    except Exception:
        pass

    try:
        readline.read_history_file(hist_file)
    except Exception:
        pass

    import atexit

    def _save_hist():
        try:
            readline.set_history_length(2000)
            readline.write_history_file(hist_file)
        except Exception:
            pass

    atexit.register(_save_hist)

# -------------------------------------------------
# Ensure project root is on sys.path
# -------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# -------------------------------------------------
# Ensure we are running inside the expected venv
# -------------------------------------------------

def _ensure_expected_venv():
    """If the user has a preferred venv, re-exec into it automatically.

    Dave wants ~/qtmos-venv activated before *anything* runs.

    Behavior:
      - If already in a venv (VIRTUAL_ENV set), do nothing.
      - Else, if ~/qtmos-venv/bin/python exists, exec into it.
      - Can override via QTM_VENV=/path/to/venv
      - Can disable via QTM_AUTO_VENV=0
    """

    if os.getenv("QTM_AUTO_VENV", "1") != "1":
        return

    # If we're already using a venv python, don't rely on VIRTUAL_ENV.
    # (VIRTUAL_ENV is only set when you "activate"; direct execution may not set it.)

    venv = os.getenv("QTM_VENV")
    if venv:
        venv_path = Path(venv).expanduser()
    else:
        venv_path = Path.home() / "qtmos-venv"

    py = venv_path / "bin" / "python"
    if not py.exists():
        return

    try:
        # Detect venv by prefix (more reliable than executable path, which may be a shared symlink).
        if Path(getattr(sys, "prefix", "")).resolve() == venv_path.resolve():
            return
    except Exception:
        pass

    # If another venv is active, still prefer the expected QTMoS venv by default.
    # Set QTM_RESPECT_ACTIVE_VENV=1 to keep the currently-activated venv.
    if os.getenv("VIRTUAL_ENV") and os.getenv("QTM_RESPECT_ACTIVE_VENV", "0") == "1":
        return

    # IDLE doesn't behave well with execv() (it just restarts the shell).
    if "idlelib" in sys.modules:
        print(f"[VENV]: please run with: {py} -m core")
        return

    # Re-exec using venv python, preserving args
    os.execv(str(py), [str(py), *sys.argv])

# -------------------------------------------------
# Minimal dependency checks (local-only)
# -------------------------------------------------

def _ensure_numpy_for_qtmos(*, quiet: bool = False):
    """QTMoS boot currently depends on numpy (qtmos_storage.py).

    If running inside a venv, we can auto-install it.
    This may download packages from PyPI.

    quiet=True suppresses informational prints (used for one-shot mode).
    """
    try:
        import numpy  # noqa: F401
        return
    except ModuleNotFoundError:
        pass

    in_venv = bool(os.getenv("VIRTUAL_ENV"))
    auto = os.getenv("QTM_AUTO_INSTALL_DEPS", "1") == "1"

    if not (in_venv and auto):
        if not quiet:
            print("[DEPS]: numpy missing (needed for QTMoS).")
            print("[DEPS]: Fix: python -m pip install numpy")
        return

    if not quiet:
        print("[DEPS]: numpy missing; auto-installing into current venv...")
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "numpy"], check=False)
    except Exception as e:
        if not quiet:
            print("[DEPS ERROR]: failed to auto-install numpy:", e)


def _port_open(host: str, port: int, timeout_s: float = 0.25) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout_s):
            return True
    except OSError:
        return False


def _start_background(
    cmd: list[str], *, cwd: str | None, log_path: Path, label: str, quiet: bool = False
):
    log_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        lf = open(log_path, "ab", buffering=0)
    except Exception:
        lf = subprocess.DEVNULL

    try:
        subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=lf,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        )
        if not quiet:
            print(f"[{label}]: started ({' '.join(cmd)})")
    except FileNotFoundError:
        if not quiet:
            print(f"[{label} ERROR]: command not found: {cmd[0]}")
    except Exception as e:
        if not quiet:
            print(f"[{label} ERROR]: failed to start: {e}")


def _bg_python_executable() -> str:
    """Pick python executable for background helpers.

    Priority:
      1) QTM_BG_PYTHON (explicit override)
      2) expected QTMoS venv python (QTM_VENV or ~/qtmos-venv)
      3) current interpreter (sys.executable)
    """
    forced = os.getenv("QTM_BG_PYTHON")
    if forced:
        return forced

    venv = os.getenv("QTM_VENV")
    venv_path = Path(venv).expanduser() if venv else (Path.home() / "qtmos-venv")
    py = venv_path / "bin" / "python"
    if py.exists():
        return str(py)

    return sys.executable


def _ensure_background_services(*, quiet: bool = False):
    """Best-effort: start local helper services if they aren't already running.

    Controlled by env:
      QTM_AUTO_START_SERVERS=1 (default) / 0

    quiet=True suppresses informational prints (used for one-shot mode).
    """

    if os.getenv("QTM_AUTO_START_SERVERS", "1") != "1":
        return

    # ---- Ollama ----
    if not _port_open("127.0.0.1", 11434):
        _start_background(
            ["ollama", "serve"],
            cwd=None,
            log_path=PROJECT_ROOT / "runtime" / "logs" / "ollama-serve.log",
            label="OLLAMA",
            quiet=quiet,
        )

    # ---- MCP server (FastAPI/uvicorn) ----
    # Allow override via MCP_ROOT; otherwise auto-discover a directory containing mcp_server.py
    mcp_root = os.getenv("MCP_ROOT")
    if not mcp_root:
        # 1) Walk upward from this file and pick first directory containing mcp_server.py
        try:
            for p in Path(__file__).resolve().parents:
                if (p / "mcp_server.py").exists():
                    mcp_root = str(p)
                    break
        except Exception:
            pass

    if not mcp_root:
        candidates = []
        try:
            candidates.append(str(Path(__file__).resolve().parents[5]))
        except Exception:
            pass
        # Common migrated locations (WSL + Windows mounts)
        candidates += [
            str(Path.home() / "Desktop" / "UniProjects"),
            str(Path.home() / "Documents" / "UniProjects"),
            "/mnt/c/Users/Dave/Desktop/UniProjects",
            "/mnt/c/Users/Dave/Documents/UniProjects",
            "/mnt/c/Users/Dave/Desktop/Projects",
            # NVMe mounts used on Linux/WSL
            "/mnt/nvme/Users/Dave/Desktop/UniProjects",
            "/mnt/nvme/Users/Dave/Desktop/QTMoSV1dev",
        ]

        for c in candidates:
            try:
                if c and (Path(c) / "mcp_server.py").exists():
                    mcp_root = c
                    break
            except Exception:
                continue

    if not _port_open("127.0.0.1", 8000):
        _start_background(
            [_bg_python_executable(), "-m", "uvicorn", "mcp_server:app", "--host", "127.0.0.1", "--port", "8000"],
            cwd=mcp_root,
            log_path=PROJECT_ROOT / "runtime" / "logs" / "mcp-server.log",
            label="MCP",
            quiet=quiet,
        )


# -------------------------------------------------
# Core system imports
# -------------------------------------------------

from core.cognitive_system import CognitiveSystem
from utils.printhelp import print_help

# -------------------------------------------------
# Collective cognition imports (safe, unused for now)
# -------------------------------------------------

from collective.collective_review import merge_points, reinforce_points
from collective.collective_points import Point

# -------------------------------------------------
# MAIN ENTRY
# -------------------------------------------------

def main(argv: list[str] | None = None):
    """Entry point.

    Interactive (default): prints help/banner, prompts for commands.
    One-shot: --once "<command>" executes exactly one command and exits.

    One-shot requirements:
      - no prompt
      - no banner/help
      - output only the command result
    """

    import argparse
    import contextlib
    import io

    if argv is None:
        argv = sys.argv[1:]

    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--once",
        metavar="CMD",
        help='Execute a single command and exit (e.g. --once "claw status --json")',
    )

    args, _unknown = parser.parse_known_args(argv)

    once_cmd = args.once

    if once_cmd:
        # One-shot mode: suppress all non-command output.
        # (Preflight + system init can print; we hide it.)
        buf_out = io.StringIO()
        buf_err = io.StringIO()
        with contextlib.redirect_stdout(buf_out), contextlib.redirect_stderr(buf_err):
            _ensure_expected_venv()
            _ensure_numpy_for_qtmos(quiet=True)
            _ensure_background_services(quiet=True)
            system = CognitiveSystem()

        try:
            system.handle_command(once_cmd.strip())
            return
        except SystemExit:
            return
        except Exception as e:
            # Errors should be visible to the caller.
            print(f"[ONCE ERROR]: {e}")
            raise

    # Interactive mode (unchanged behavior)
    _ensure_expected_venv()

    _ensure_numpy_for_qtmos()
    _ensure_background_services()
    _init_line_editing()

    system = CognitiveSystem()
    print_help()
    print("[MAIN]: System online.")

    while True:
        try:
            line = input("> ").strip()
            if not line:
                continue

            if line in ("exit", "quit"):
                print("[MAIN]: Shutdown.")
                break

            system.handle_command(line)

        except KeyboardInterrupt:
            print("\n[MAIN]: Interrupted.")
            break
        except Exception as e:
            print("[MAIN ERROR]:", e)


if __name__ == "__main__":
    main()
