"""
Bootstrap helpers shared by manage.py, WSGI, and ASGI.

Centralizes sys.path setup so ``apps.*`` imports resolve consistently
in development, tests, and production entrypoints.
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def setup_path() -> Path:
    """Insert the repository root on sys.path if it is not already there."""
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    return PROJECT_ROOT
