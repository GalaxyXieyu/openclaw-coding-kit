#!/usr/bin/env python3
"""Compatibility wrapper for the main review builder entrypoint."""

from __future__ import annotations

import sys

from main_digest_builder import main


if __name__ == "__main__":
    sys.exit(main())
