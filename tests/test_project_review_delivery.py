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

from review_delivery import send_review_card
from review_orchestrator import ingest_review_results, prepare_review
from review_state_store import load_state, update_review_status


class ProjectReviewDeliveryTest(unittest.TestCase):
    def test_send_review_card_updates_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "weekly",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "project_summaries": [
                        {
                            "project": "小程序",
                            "done": "登录页",
                            "pending": "支付联调",
                            "next_step": "补测试",
                            "status": "推进中",
                        }
                    ],
                    "tasks": {"completed": [{"id": "T1"}], "active": [{"id": "T2"}]},
                },
                state_path=state_path,
                now_iso="2026-04-14T20:00:00+08:00",
            )

            bridge_output = {
                "action": "send",
                "channel": "feishu",
                "payload": {
                    "ok": True,
                    "messageId": "om_demo",
                    "chatId": "oc_demo",
                },
            }

            with patch("review_delivery.subprocess.run") as mocked_run:
                mocked_run.return_value.returncode = 0
                mocked_run.return_value.stdout = json.dumps(bridge_output, ensure_ascii=False)
                mocked_run.return_value.stderr = ""
                result = send_review_card(
                    prepared["review_id"],
                    state_path=state_path,
                    now_iso="2026-04-14T20:10:00+08:00",
                )

            self.assertTrue(result["ok"])
            self.assertEqual("om_demo", result["delivery"]["message_id"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("sent", stored["status"])
            self.assertEqual("om_demo", stored["delivery"]["message_id"])
            self.assertEqual(3, len(stored["history"]))

    def test_send_review_card_dry_run_returns_card_without_state_change(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "weekly",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "project_summaries": [
                        {
                            "project": "小程序",
                            "done": "登录页",
                            "pending": "支付联调",
                            "next_step": "补测试",
                            "status": "推进中",
                        }
                    ],
                },
                state_path=state_path,
                now_iso="2026-04-14T20:00:00+08:00",
            )

            result = send_review_card(
                prepared["review_id"],
                state_path=state_path,
                dry_run=True,
            )

            self.assertIn("header", result["card"])
            self.assertIn("--card", result["command_preview"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("drafted", stored["status"])
            self.assertEqual({}, stored["delivery"])

    def test_send_review_card_falls_back_to_lark_bridge_user_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "weekly",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "project_summaries": [
                        {
                            "project": "小程序",
                            "done": "登录页",
                            "pending": "支付联调",
                            "next_step": "补测试",
                            "status": "推进中",
                        }
                    ],
                },
                state_path=state_path,
                now_iso="2026-04-14T20:00:00+08:00",
            )

            def fake_run(*args, **kwargs):
                cmd = args[0]
                response = type("Completed", (), {})()
                if cmd[0] == "openclaw":
                    response.returncode = 1
                    response.stdout = ""
                    response.stderr = "Error: Card send failed: Bot/User can NOT be out of the chat."
                    return response
                response.returncode = 0
                response.stdout = json.dumps(
                    {
                        "ok": True,
                        "details": {
                            "message_id": "om_bridge",
                            "chat_id": "oc_demo",
                        },
                    },
                    ensure_ascii=False,
                )
                response.stderr = ""
                return response

            with patch("review_delivery.subprocess.run", side_effect=fake_run):
                with patch("review_delivery._resolve_bridge_script", return_value=Path("/tmp/fake-bridge.py")):
                    result = send_review_card(
                        prepared["review_id"],
                        state_path=state_path,
                        now_iso="2026-04-14T20:10:00+08:00",
                    )

            self.assertTrue(result["ok"])
            self.assertEqual("om_bridge", result["delivery"]["message_id"])
            self.assertEqual("openclaw-lark.feishu_im_user_message.send", result["delivery"]["tool"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("sent", stored["status"])
            self.assertEqual("om_bridge", stored["delivery"]["message_id"])

    def test_send_review_card_falls_back_to_pm_user_token_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "weekly",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "project_summaries": [
                        {
                            "project": "小程序",
                            "done": "登录页",
                            "pending": "支付联调",
                            "next_step": "补测试",
                            "status": "推进中",
                        }
                    ],
                },
                state_path=state_path,
                now_iso="2026-04-14T20:00:00+08:00",
            )

            with patch(
                "review_delivery._invoke_openclaw_send",
                side_effect=RuntimeError("Card send failed: Bot/User can NOT be out of the chat."),
            ):
                with patch(
                    "review_delivery._invoke_lark_bridge_user_send",
                    side_effect=RuntimeError("need_user_authorization"),
                ):
                    with patch(
                        "review_delivery._invoke_pm_user_token_send",
                        return_value={
                            "tool": "pm.user_token.im.message.create",
                            "chat_id": "oc_demo",
                            "message_id": "om_pm",
                        },
                    ):
                        result = send_review_card(
                            prepared["review_id"],
                            state_path=state_path,
                            now_iso="2026-04-14T20:10:00+08:00",
                        )

            self.assertTrue(result["ok"])
            self.assertEqual("om_pm", result["delivery"]["message_id"])
            self.assertEqual("pm.user_token.im.message.create", result["delivery"]["tool"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("sent", stored["status"])
            self.assertEqual("om_pm", stored["delivery"]["message_id"])

    def test_send_review_card_force_resend_uses_fresh_uuid_for_pm_send(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "weekly",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "project_summaries": [
                        {
                            "project": "小程序",
                            "done": "登录页",
                            "pending": "支付联调",
                            "next_step": "补测试",
                            "status": "推进中",
                        }
                    ],
                },
                state_path=state_path,
                now_iso="2026-04-14T20:00:00+08:00",
            )
            update_review_status(
                state_path,
                prepared["review_id"],
                status="sent",
                updated_at="2026-04-14T20:05:00+08:00",
                extra={
                    "delivery": {
                        "tool": "pm.user_token.im.message.create",
                        "chat_id": "oc_demo",
                        "message_id": "om_existing",
                        "sent_at": "2026-04-14T20:05:00+08:00",
                    }
                },
            )

            captured: dict[str, str] = {}

            def fake_pm_send(*, chat_id, card, delivery_uuid):
                captured["uuid"] = delivery_uuid
                return {
                    "tool": "pm.user_token.im.message.create",
                    "chat_id": chat_id,
                    "message_id": "om_pm_force",
                    "uuid": delivery_uuid,
                }

            fake_uuid = type("FakeUuid", (), {"hex": "1234567890abcdef1234567890abcdef"})()

            with patch(
                "review_delivery._invoke_openclaw_send",
                side_effect=RuntimeError("Card send failed: Bot/User can NOT be out of the chat."),
            ):
                with patch(
                    "review_delivery._invoke_lark_bridge_user_send",
                    side_effect=RuntimeError("need_user_authorization"),
                ):
                    with patch("review_delivery._invoke_pm_user_token_send", side_effect=fake_pm_send):
                        with patch("review_delivery.uuid.uuid4", return_value=fake_uuid):
                            result = send_review_card(
                                prepared["review_id"],
                                state_path=state_path,
                                now_iso="2026-04-14T20:10:00+08:00",
                                force=True,
                            )

            self.assertTrue(result["ok"])
            self.assertEqual(
                f"project-review-{prepared['review_id']}-1234567890",
                captured["uuid"],
            )
            self.assertEqual(captured["uuid"], result["delivery"]["uuid"])
            stored = load_state(state_path)["reviews"][0]
            self.assertEqual("om_pm_force", stored["delivery"]["message_id"])
            self.assertEqual(captured["uuid"], stored["delivery"]["uuid"])

    def test_send_review_card_blocks_incomplete_code_health_review(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            state_path = Path(tmp_dir) / "project-review-state.json"
            prepared = prepare_review(
                {
                    "trigger_kind": "code-health",
                    "project_name": "主项目群",
                    "channel_id": "oc_demo",
                    "changed_files": ["src/api/home.ts"],
                    "commits": [{"hash": "abc123", "subject": "fix api"}],
                },
                state_path=state_path,
                now_iso="2026-04-14T20:00:00+08:00",
            )

            with self.assertRaisesRegex(RuntimeError, "还没完成"):
                send_review_card(
                    prepared["review_id"],
                    state_path=state_path,
                    now_iso="2026-04-14T20:10:00+08:00",
                )

            ingest_review_results(
                prepared["review_id"],
                {
                    "code-review": {
                        "lane": "code-review",
                        "summary": "发现订单状态问题",
                        "findings": [],
                        "docs_flags": [],
                        "next_actions": ["先补状态回写"],
                    },
                    "docs-review": {
                        "lane": "docs-review",
                        "summary": "文档要补",
                        "findings": [],
                        "docs_flags": [],
                        "next_actions": ["再补业务说明"],
                    },
                },
                state_path=state_path,
                now_iso="2026-04-14T20:20:00+08:00",
            )

            with patch("review_delivery.subprocess.run") as mocked_run:
                mocked_run.return_value.returncode = 0
                mocked_run.return_value.stdout = json.dumps(
                    {
                        "action": "send",
                        "channel": "feishu",
                        "payload": {
                            "ok": True,
                            "messageId": "om_ready",
                            "chatId": "oc_demo",
                        },
                    },
                    ensure_ascii=False,
                )
                mocked_run.return_value.stderr = ""
                result = send_review_card(
                    prepared["review_id"],
                    state_path=state_path,
                    now_iso="2026-04-14T20:30:00+08:00",
                )

            self.assertEqual("om_ready", result["delivery"]["message_id"])


if __name__ == "__main__":
    unittest.main()
