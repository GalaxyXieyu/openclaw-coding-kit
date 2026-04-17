#!/usr/bin/env python3
"""Explicit card-sending entrypoint for nightly project reviews."""

from __future__ import annotations

import sys

from nightly_auto_review import main


if __name__ == "__main__":
    sys.exit(main())
