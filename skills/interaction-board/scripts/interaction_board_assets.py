from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"


@lru_cache(maxsize=1)
def load_board_assets() -> tuple[str, str, str]:
    template = (ASSET_DIR / "board_template.html").read_text(encoding="utf-8")
    styles_dir = ASSET_DIR / "styles"
    if styles_dir.exists():
        css = "\n\n".join(
            path.read_text(encoding="utf-8").rstrip()
            for path in sorted(styles_dir.glob("*.css"))
        )
    else:
        css = (ASSET_DIR / "board.css").read_text(encoding="utf-8")
    js = (ASSET_DIR / "board.js").read_text(encoding="utf-8")
    return template, css, js
