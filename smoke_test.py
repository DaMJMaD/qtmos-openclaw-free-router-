"""Minimal non-interactive smoke test for QTMoS core.

Local-only; avoids network calls and avoids requiring optional dependencies.

Usage:
  python3 smoke_test.py

Exit codes:
  0 = OK
  1 = failed to import / initialize core
"""

from __future__ import annotations

import sys


def main() -> int:
    try:
        # Import the primary AI logic.
        from core.cognitive_system import CognitiveSystem

        system = CognitiveSystem()

        # Basic runtime sanity: exercise a cheap command.
        system.command_state()

        # Confirm object shape at least exists.
        assert hasattr(system, "handle_command")
        return 0

    except Exception as e:
        print("[SMOKE_TEST ERROR]:", repr(e))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
