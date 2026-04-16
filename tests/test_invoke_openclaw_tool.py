from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path


SCRIPT_DIR = (
    Path(__file__).resolve().parents[1]
    / "skills"
    / "openclaw-lark-bridge"
    / "scripts"
)
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from invoke_openclaw_tool import build_dry_run_preview, build_parser, prepare_gateway_request


class InvokeOpenClawToolTest(unittest.TestCase):
    def test_prepare_gateway_request_mirrors_action_and_redacts_auth_in_preview(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "openclaw.json"
            config_path.write_text(
                json.dumps(
                    {
                        "gateway": {
                            "port": 19001,
                            "auth": {"token": "secret-token"},
                        }
                    }
                ),
                encoding="utf-8",
            )
            parser = build_parser()
            args = parser.parse_args(
                [
                    "--tool",
                    "feishu_task_task",
                    "--action",
                    "comment",
                    "--config",
                    str(config_path),
                    "--message-channel",
                    "feishu",
                    "--header",
                    "X-Test=value",
                ]
            )

            resolved_path, gateway_url, body, headers, extra_headers, action_mirrored = prepare_gateway_request(args)
            preview = build_dry_run_preview(
                config_path=resolved_path,
                gateway_url=gateway_url,
                headers=headers,
                body=body,
                args=args,
                extra_headers=extra_headers,
                action_mirrored=action_mirrored,
            )

            self.assertEqual(resolved_path, config_path)
            self.assertEqual(gateway_url, "http://127.0.0.1:19001")
            self.assertTrue(action_mirrored)
            self.assertEqual(body["args"]["action"], "comment")
            self.assertEqual(headers["Authorization"], "Bearer secret-token")
            self.assertEqual(preview["headers"]["Authorization"], "<redacted>")
            self.assertEqual(preview["request"]["headers"]["message_channel"], "feishu")
            self.assertEqual(preview["request"]["headers"]["extra"]["X-Test"], "value")


if __name__ == "__main__":
    unittest.main()
