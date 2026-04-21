from __future__ import annotations

from functools import lru_cache
from pathlib import Path

ASSET_DIR = Path(__file__).resolve().parents[1] / "assets"
SCRIPT_DIR = ASSET_DIR / "scripts"
LEGACY_JS_FILES = ("board_helpers.js", "board.js")


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
    script_paths = sorted(path for path in SCRIPT_DIR.glob("*.js") if path.is_file()) if SCRIPT_DIR.exists() else []
    if script_paths:
        js_paths = [*script_paths, ASSET_DIR / "board.js"]
    else:
        js_paths = [ASSET_DIR / filename for filename in LEGACY_JS_FILES]
    js = "\n\n".join(path.read_text(encoding="utf-8").rstrip() for path in js_paths)
    return template, css, js
