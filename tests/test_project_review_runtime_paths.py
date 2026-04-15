from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from review_runtime_paths import resolve_main_review_config_path, resolve_main_review_state_path


class ProjectReviewRuntimePathsTest(unittest.TestCase):
    def test_resolve_main_review_paths_prefer_openclaw_runtime_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "openclaw.json").write_text("{}", encoding="utf-8")
            runtime_dir = root / "project-review"
            runtime_dir.mkdir()
            config_path = runtime_dir / "main_review_sources.json"
            config_path.write_text("{}", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                resolved_config = resolve_main_review_config_path(start=root)
                resolved_state = resolve_main_review_state_path(config_path=resolved_config, start=root)

            self.assertEqual(config_path.resolve(), resolved_config)
            self.assertEqual((runtime_dir / "project-review-state.json").resolve(), resolved_state.resolve())

    def test_resolve_main_review_state_uses_openclaw_runtime_even_without_config_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "openclaw.json").write_text("{}", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                resolved_state = resolve_main_review_state_path(start=root)

            self.assertEqual((root / "project-review" / "project-review-state.json").resolve(), resolved_state.resolve())

    def test_env_config_override_wins(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            explicit_path = root / "custom-main-review.json"
            explicit_path.write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, {"PROJECT_REVIEW_MAIN_REVIEW_CONFIG": str(explicit_path)}, clear=False):
                resolved_config = resolve_main_review_config_path(start=root)
            self.assertEqual(explicit_path.resolve(), resolved_config.resolve())

    def test_openclaw_config_path_env_is_supported(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            state_dir = root / ".openclaw"
            state_dir.mkdir()
            (state_dir / "openclaw.json").write_text("{}", encoding="utf-8")
            runtime_dir = state_dir / "project-review"
            runtime_dir.mkdir()
            config_path = runtime_dir / "main_review_sources.json"
            config_path.write_text("{}", encoding="utf-8")
            with patch.dict(os.environ, {"OPENCLAW_CONFIG_PATH": str(state_dir / "openclaw.json")}, clear=False):
                resolved_config = resolve_main_review_config_path(start=root)
            self.assertEqual(config_path.resolve(), resolved_config.resolve())

    def test_explicit_config_path_keeps_state_beside_config(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            (root / "openclaw.json").write_text("{}", encoding="utf-8")
            explicit_dir = root / "custom-review"
            explicit_dir.mkdir()
            explicit_config = explicit_dir / "main_review_sources.json"
            explicit_config.write_text("{}", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True):
                resolved_state = resolve_main_review_state_path(config_path=explicit_config, start=root)

            self.assertEqual((explicit_dir / "project-review-state.json").resolve(), resolved_state.resolve())


if __name__ == "__main__":
    unittest.main()
