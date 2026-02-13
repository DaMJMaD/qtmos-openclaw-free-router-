"""Allow running QTMoS core as: python -m core

Keeps core/main.py as the canonical entrypoint.
"""

from .main import main

if __name__ == "__main__":
    main()
