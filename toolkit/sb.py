#!/usr/bin/env python3
"""Punto d'ingresso del toolkit Second Brain: python3 sb.py <comando> [opzioni]."""
import os
import sys

if sys.version_info < (3, 9):
    sys.stderr.write("sb: serve Python 3.9 o superiore\n")
    sys.exit(2)

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sb_core.cli import main  # noqa: E402

if __name__ == "__main__":
    sys.exit(main())
