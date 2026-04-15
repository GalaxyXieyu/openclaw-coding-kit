from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "project-review" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from main_digest_builder import build_main_digest_payload


class ProjectReviewMainDigestTest(unittest.TestCase):
    def test_build_main_digest_supports_main_target_schema(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            repo = tmp_root / "repo"
            (repo / ".pm").mkdir(parents=True)
            (repo / ".pm" / "current-context.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "项目一"},
                        "open_tasks": [{"summary": "[T1] 主Agent主动节律与知识闭环"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = {
                "main_target": {
                    "alias": "main",
                    "channel": "feishu",
                    "chat_id": "oc_main_target",
                    "chat_name": "宇宇(main agent)",
                },
                "sources": [{"project_name": "项目一", "repo_root": str(repo)}],
            }

            with patch(
                "main_digest_builder.collect_recent_commits",
                return_value=[{"hash": "a1", "authored_at": "2026-04-14T10:00:00+08:00", "subject": "Fix PM completion due sync"}],
            ):
                payload = build_main_digest_payload(config, since="7 days ago", now_iso="2026-04-14T21:30:00+08:00")

            self.assertEqual("oc_main_target", payload["channel_id"])
            self.assertEqual("main", payload["meta"]["main_target_alias"])
            self.assertEqual("feishu", payload["meta"]["main_target_channel"])
            self.assertEqual("宇宇(main agent)", payload["meta"]["main_chat_name"])

    def test_build_main_digest_skips_disabled_source(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            repo = tmp_root / "repo"
            (repo / ".pm").mkdir(parents=True)
            (repo / ".pm" / "current-context.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "项目一"},
                        "open_tasks": [{"summary": "[T1] 主Agent主动节律与知识闭环"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = {
                "main_target": {"chat_id": "oc_main"},
                "sources": [{"project_name": "项目一", "repo_root": str(repo), "enabled": False}],
            }

            with patch(
                "main_digest_builder.collect_recent_commits",
                return_value=[{"hash": "a1", "authored_at": "2026-04-14T10:00:00+08:00", "subject": "Fix PM completion due sync"}],
            ):
                with self.assertRaisesRegex(ValueError, "no active projects"):
                    build_main_digest_payload(config, since="7 days ago", now_iso="2026-04-14T21:30:00+08:00")

    def test_build_main_digest_uses_recent_sources_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            repo_one = tmp_root / "repo-one"
            repo_two = tmp_root / "repo-two"
            repo_one.mkdir()
            repo_two.mkdir()
            (repo_one / ".pm").mkdir()
            (repo_two / ".pm").mkdir()

            (repo_one / ".pm" / "current-context.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "项目一"},
                        "open_tasks": [{"summary": "[T1] 主Agent主动节律与知识闭环"}],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (repo_two / ".pm" / "project-scan.json").write_text(
                json.dumps(
                    {
                        "gsd": {
                            "summaries": {
                                "project": "### Active\n- [ ] 支持消费 Java 后端已上传附件的元数据或文件引用，并提供文件预览下载与失败状态反馈\n- [ ] 建立问题项输出契约\n"
                            }
                        }
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = {
                "main_chat_id": "oc_main",
                "main_project_name": "全部项目",
                "sources": [
                    {"project_name": "项目一", "repo_root": str(repo_one)},
                    {"project_name": "项目二", "repo_root": str(repo_two)},
                ],
            }

            def fake_commits(repo_root: str, since: str, until: str | None = None) -> list[dict[str, str]]:
                if Path(repo_root) == repo_one:
                    return [{"hash": "a1", "authored_at": "2026-04-14T10:00:00+08:00", "subject": "Fix PM completion due sync"}]
                if Path(repo_root) == repo_two:
                    return []
                return []

            with patch("main_digest_builder.collect_recent_commits", side_effect=fake_commits):
                payload = build_main_digest_payload(
                    config,
                    since="7 days ago",
                    now_iso="2026-04-14T21:30:00+08:00",
                )

            self.assertEqual("oc_main", payload["channel_id"])
            self.assertEqual(1, len(payload["project_summaries"]))
            first = payload["project_summaries"][0]
            self.assertEqual("项目一", first["project"])
            self.assertIn("PM完成时间同步", first["done"])
            self.assertIn("主Agent主动节律", first["pending"])
            self.assertEqual("main-weekly-2026-W16", payload["period_key"])

    def test_build_main_digest_uses_review_state_when_available(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            repo = tmp_root / "repo"
            (repo / ".pm").mkdir(parents=True)
            (repo / ".pm" / "project-review-state.json").write_text(
                json.dumps(
                    {
                        "reviews": [
                            {
                                "trigger_kind": "weekly",
                                "updated_at": "2026-04-14T20:00:00+08:00",
                                "bundle": {
                                    "projects": [
                                        {
                                            "done": "支付回调",
                                            "pending": "真机联调",
                                            "next_step": "跑一元下单",
                                        },
                                        {
                                            "done": "市场挂牌",
                                            "pending": "成交回归",
                                            "next_step": "补成交验收",
                                        },
                                    ]
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = {
                "main_chat_id": "oc_main",
                "sources": [{"project_name": "项目二", "repo_root": str(repo)}],
            }

            with patch(
                "main_digest_builder.collect_recent_commits",
                return_value=[{"hash": "a1", "authored_at": "2026-04-14T10:00:00+08:00", "subject": "feat: whatever"}],
            ):
                payload = build_main_digest_payload(config, since="7 days ago", now_iso="2026-04-14T21:30:00+08:00")

            summary = payload["project_summaries"][0]
            self.assertEqual("支付回调、市场挂牌", summary["done"])
            self.assertEqual("真机联调、成交回归", summary["pending"])
            self.assertEqual("跑一元下单、补成交验收", summary["next_step"])

    def test_build_main_digest_ignores_aggregate_review_drafts_in_source_repo(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_root = Path(tmp_dir)
            repo = tmp_root / "repo"
            (repo / ".pm").mkdir(parents=True)
            (repo / ".pm" / "current-context.json").write_text(
                json.dumps(
                    {
                        "project": {"name": "PM工具链"},
                        "open_tasks": [
                            {"summary": "[T1] 设计主Agent主动节律与知识闭环"},
                            {"summary": "[T2] interaction-board sample"},
                        ],
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (repo / ".pm" / "project-review-state.json").write_text(
                json.dumps(
                    {
                        "reviews": [
                            {
                                "trigger_kind": "weekly",
                                "updated_at": "2026-04-14T22:08:45+08:00",
                                "project_name": "全部项目",
                                "dedupe_key": "weekly:全部项目:oc_main:main-weekly-2026-W16",
                                "source_payload": {
                                    "project_name": "全部项目",
                                    "period_key": "main-weekly-2026-W16",
                                },
                                "bundle": {
                                    "project": {"name": "全部项目"},
                                    "projects": [
                                        {
                                            "done": "被污染摘要",
                                            "pending": "错误待办",
                                            "next_step": "错误下一步",
                                        }
                                    ],
                                },
                            }
                        ]
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            config = {
                "main_chat_id": "oc_main",
                "sources": [{"project_name": "PM工具链", "repo_root": str(repo)}],
            }

            with patch(
                "main_digest_builder.collect_recent_commits",
                return_value=[{"hash": "a1", "authored_at": "2026-04-14T10:00:00+08:00", "subject": "Fix PM completion due sync"}],
            ):
                payload = build_main_digest_payload(config, since="7 days ago", now_iso="2026-04-14T21:30:00+08:00")

            summary = payload["project_summaries"][0]
            self.assertEqual("PM工具链", summary["project"])
            self.assertIn("PM完成时间同步", summary["done"])
            self.assertIn("主Agent主动节律", summary["pending"])
            self.assertEqual("交互看板样例", summary["next_step"])
            self.assertNotIn("被污染摘要", summary["done"])


if __name__ == "__main__":
    unittest.main()
