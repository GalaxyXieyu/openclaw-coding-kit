#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

INTERACTION_BOARD_SCRIPTS = Path(__file__).resolve().parents[2] / "interaction-board" / "scripts"
if str(INTERACTION_BOARD_SCRIPTS) not in sys.path:
    sys.path.insert(0, str(INTERACTION_BOARD_SCRIPTS))

from interaction_board import main


if __name__ == "__main__":
    main()
