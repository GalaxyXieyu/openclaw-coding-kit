from __future__ import annotations

import json
import sys
import tempfile
import unittest
from base64 import b64decode
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parents[1] / "skills" / "interaction-board" / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from interaction_board import (
    apply_board_overlay,
    attach_scenarios,
    attach_screenshots,
    build_sample,
    collect_scenario_bindings,
    extract_miniapp_manifest,
    hydrate_manifest_cards,
    render_drawio_board,
    render_html_board,
    render_playwright_spec,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def write_binary(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


class InteractionBoardTest(unittest.TestCase):
    def _build_repo(self, root: Path) -> None:
        write(
            root / "apps/miniapp/src/runtime/page-paths.ts",
            """export const MINIAPP_PAGE_PATHS = {
  workspaceEntry: '/pages/workspace-entry/index',
  home: '/pages/products/index',
  products: '/pages/products/index',
  productDetail: '/subpackages/workspace/pages/product-detail/index',
  candidateOnly: '/subpackages/workspace/pages/candidate-only/index',
} as const;
""",
        )
        write(
            root / "apps/miniapp/src/runtime/routes.ts",
            """const ROUTE_MAP = {
  'products': MINIAPP_PAGE_PATHS.products,
  'product-detail': MINIAPP_PAGE_PATHS.productDetail,
};
""",
        )
        write(
            root / "apps/miniapp/src/app.config.ts",
            """const pageOrder = [
  MINIAPP_PAGE_PATHS.workspaceEntry,
  MINIAPP_PAGE_PATHS.products,
];
const subPackages = [
  {
    root: 'subpackages/workspace',
    pages: ['pages/product-detail/index'],
  },
];
""",
        )
        write(root / "apps/miniapp/src/pages/workspace-entry/index.tsx", "export { default } from '@/features/workspace-entry/screen';\n")
        write(root / "apps/miniapp/src/pages/workspace-entry/index.config.ts", "export default definePageConfig({ navigationBarTitleText: '选择空间' });\n")
        write(root / "apps/miniapp/src/pages/products/index.tsx", "export { default } from '@/features/product/list/screen';\n")
        write(root / "apps/miniapp/src/pages/products/index.config.ts", "export default definePageConfig({ navigationBarTitleText: '宠物档案' });\n")
        write(root / "apps/miniapp/src/subpackages/workspace/pages/product-detail/index.tsx", "export { default } from '@/features/product/detail/screen';\n")
        write(root / "apps/miniapp/src/subpackages/workspace/pages/product-detail/index.config.ts", "export default definePageConfig({ navigationBarTitleText: '宠物详情' });\n")
        write(root / "apps/miniapp/src/subpackages/workspace/pages/candidate-only/index.tsx", "export { default } from '@/features/product/candidate/screen';\n")
        write(root / "apps/miniapp/src/subpackages/workspace/pages/candidate-only/index.config.ts", "export default definePageConfig({ navigationBarTitleText: '候选页' });\n")
        write(
            root / "apps/miniapp/src/features/product/list/screen.tsx",
            """import { openProductDetail } from './controller';

export default function Screen() {
  void openProductDetail();
  return null;
}
""",
        )
        write(
            root / "apps/miniapp/src/features/product/list/controller.ts",
            """import { MINIAPP_PAGE_PATHS } from '@/runtime';

export function openProductDetail() {
  return `${MINIAPP_PAGE_PATHS.productDetail}?from=products`;
}
""",
        )
        write(root / "apps/miniapp/src/features/product/detail/screen.tsx", "export default function Screen() { return null; }\n")
        write(root / "apps/miniapp/src/features/workspace-entry/screen.tsx", "export default function Screen() { return null; }\n")
        write(root / "docs/miniapp-runbook.md", "| /pages/products/index | 产品列表 |\n| /pages/login/index | 登录 |\n")

    def test_extract_miniapp_manifest_detects_candidate_and_doc_drift(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)

            self.assertEqual(3, manifest["summary"]["registered_count"])
            self.assertEqual(1, manifest["summary"]["candidate_count"])
            self.assertEqual(2, manifest["summary"]["conflict_count"])
            candidate = next(node for node in manifest["nodes"] if node["route_key"] == "candidateOnly")
            self.assertEqual("candidate", candidate["status"])
            self.assertTrue(any(edge["to"] == "productdetail" for edge in manifest["edges"]))
            kinds = sorted(conflict["kind"] for conflict in manifest["conflicts"])
            self.assertEqual(["doc_only_route", "route_constant_unregistered"], kinds)

    def test_render_outputs_include_expected_strings(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            html_output = render_html_board(manifest, title="Demo Board")
            drawio_output = render_drawio_board(manifest, title="Demo Board")

            self.assertIn("Demo Board", html_output)
            self.assertIn('id="board-data"', html_output)
            self.assertIn('id="nodeModal"', html_output)
            self.assertIn("<mxfile", drawio_output)
            self.assertIn("候选页", drawio_output)

    def test_attach_screenshots_copies_assets_and_renders_gallery(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            self._build_repo(repo_root)
            out_dir = Path(tmp_dir) / "out"
            manifest = extract_miniapp_manifest(repo_root)

            explicit_root = Path(tmp_dir) / "manual-ui"
            heuristic_root = Path(tmp_dir) / "smoke"
            write(explicit_root / "products.png", "products-image")
            write(
                explicit_root / "routes.json",
                json.dumps(
                    [
                        {
                            "slug": "products",
                            "url": "http://127.0.0.1:10086/#/pages/products/index",
                            "screenshot": str(explicit_root / "products.png"),
                        }
                    ],
                    ensure_ascii=False,
                ),
            )
            write(heuristic_root / "product-detail-preview.png", "detail-image")

            manifest = attach_screenshots(
                manifest,
                [f"compare={explicit_root}", f"smoke={heuristic_root}"],
                out_dir,
            )

            products = next(node for node in manifest["nodes"] if node["route_key"] == "products")
            product_detail = next(node for node in manifest["nodes"] if node["route_key"] == "productDetail")
            candidate = next(node for node in manifest["nodes"] if node["route_key"] == "candidateOnly")

            self.assertEqual("screenshots/compare/products.png", products["screenshot_refs"][0]["path"])
            self.assertEqual("screenshots/smoke/productdetail.png", product_detail["screenshot_refs"][0]["path"])
            self.assertTrue(products["screenshot_refs"][0]["exists"])
            self.assertTrue(product_detail["screenshot_refs"][0]["exists"])
            self.assertFalse(candidate["screenshot_refs"][0]["exists"])
            self.assertTrue((out_dir / "screenshots" / "compare" / "products.png").exists())
            self.assertTrue((out_dir / "screenshots" / "smoke" / "productdetail.png").exists())
            self.assertEqual(2, manifest["summary"]["nodes_with_screenshots"])
            self.assertEqual(2, manifest["summary"]["attached_screenshot_count"])

            html_output = render_html_board(manifest, title="Screenshot Board")
            self.assertIn("screenshots/compare/products.png", html_output)
            self.assertIn("产品画布", html_output)
            self.assertIn("Screenshot Board", html_output)

    def test_build_sample_writes_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            self._build_repo(repo_root)
            out_dir = Path(tmp_dir) / "out"
            outputs = build_sample(repo_root, out_dir, title="Sample Board")

            self.assertTrue(Path(outputs["manifest"]).exists())
            self.assertTrue(Path(outputs["drawio"]).exists())
            self.assertTrue(Path(outputs["html"]).exists())
            self.assertTrue(Path(outputs["inventory"]).exists())
            self.assertTrue((out_dir / "screenshots" / "README.md").exists())

            payload = json.loads((out_dir / "board.manifest.json").read_text(encoding="utf-8"))
            self.assertEqual("1.0", payload["schema_version"])
            product = next(node for node in payload["nodes"] if node["node_id"] == "products")
            self.assertIn("card", product)
            self.assertIn("primary_image", product["card"])
            self.assertTrue(product["card"]["primary_image"]["absolute_path"].endswith("screenshots/products.png"))

    def test_apply_board_overlay_adds_draft_card_and_link(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            overlay = {
                "cards": [
                    {
                        "node_id": "ai-share-flow",
                        "title": "分享漏斗草图",
                        "group": "products",
                        "status": "draft",
                        "extends": "products",
                        "note": "用于 AI 先补一版分享闭环页面。",
                        "tags": ["ai", "prototype"],
                        "scenario_refs": ["scenarios/products-to-detail.spec.ts"],
                    }
                ],
                "links": [
                    {
                        "from": "products",
                        "to": "ai-share-flow",
                        "kind": "prototype",
                        "trigger": "overlay:share-funnel",
                        "label": "补一条 AI 草图路径",
                    }
                ],
                "card_patches": [
                    {
                        "match": "products",
                        "note": "产品主列表，后续要和分享草图联动。",
                    }
                ],
            }

            merged = hydrate_manifest_cards(apply_board_overlay(manifest, overlay, "board.overlay.json"))

            draft = next(node for node in merged["nodes"] if node["node_id"] == "ai-share-flow")
            products = next(node for node in merged["nodes"] if node["node_id"] == "products")
            self.assertEqual("draft", draft["status"])
            self.assertEqual("overlay/ai-share-flow", draft["route"])
            self.assertEqual("用于 AI 先补一版分享闭环页面。", draft["board_meta"]["note"])
            self.assertEqual(
                [
                    {
                        "scenario_id": "products-to-detail",
                        "script_path": "scenarios/products-to-detail.spec.ts",
                        "script_absolute_path": "",
                        "scenario_path": "",
                        "capture_output": "",
                        "engine": "",
                        "target": {},
                        "assertions": [],
                        "role": "manual",
                    }
                ],
                draft["card"]["scenario_refs"],
            )
            self.assertEqual(1, merged["summary"]["draft_count"])
            self.assertIn("board.overlay.json", merged["sources"]["board_overlay"])
            self.assertTrue(any(edge["to"] == "ai-share-flow" and edge["kind"] == "prototype" for edge in merged["edges"]))
            self.assertEqual("产品主列表，后续要和分享草图联动。", products["board_meta"]["note"])

            html_output = render_html_board(merged, title="Overlay Board")
            self.assertIn("AI 草图", html_output)
            self.assertIn("待截图节点", html_output)

    def test_hydrate_manifest_cards_uses_scenario_capture_for_missing_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            board_root = Path(tmp_dir) / "board"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            scenario_path = board_root / "scenarios" / "products-to-detail.json"
            capture_path = board_root / "screenshots" / "scenario" / "products-to-detail.png"
            write(
                scenario_path,
                json.dumps(
                    {
                        "scenario_id": "products-to-detail",
                        "engine": "miniapp-devtools",
                        "entry_node_id": "products",
                        "target_node_id": "productdetail",
                        "capture": {"output": "../screenshots/scenario/products-to-detail.png"},
                        "steps": [],
                        "assertions": [],
                    },
                    ensure_ascii=False,
                ),
            )
            write_binary(
                capture_path,
                b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sX6b08AAAAASUVORK5CYII="
                ),
            )

            bindings = collect_scenario_bindings(board_root / "scenarios")
            merged = attach_scenarios(manifest, bindings)
            hydrated = hydrate_manifest_cards(merged, board_root)
            detail = next(node for node in hydrated["nodes"] if node["node_id"] == "productdetail")

            self.assertEqual("scenario:products-to-detail", detail["card"]["primary_image"]["label"])
            self.assertEqual("screenshots/scenario/products-to-detail.png", detail["card"]["primary_image"]["relative_path"])
            self.assertTrue(detail["card"]["primary_image"]["exists"])

    def test_render_playwright_spec_from_scenario(self) -> None:
        scenario = {
            "scenario_id": "products-to-detail",
            "engine": "web-playwright-cli",
            "target": {"base_url": "http://127.0.0.1:3000"},
            "context": {
                "notes": "需要先注入 workspace 上下文。",
                "storage": [{"key": "workspace", "value": {"id": "w1"}}],
            },
            "steps": [
                {"action": "open", "target": "/pages/products/index"},
                {"action": "tap", "selector": "[data-testid='product-card']"},
            ],
            "assertions": [
                {"type": "path", "value": "/subpackages/workspace/pages/product-detail/index"},
                {"type": "text", "value": "宠物详情"},
            ],
            "capture": {"output": "out/product-detail.png"},
        }
        spec = render_playwright_spec(scenario)
        self.assertIn('test("products-to-detail"', spec)
        self.assertIn("page.addInitScript", spec)
        self.assertIn("page.goto", spec)
        self.assertIn("page.screenshot", spec)
        self.assertIn("page.getByText", spec)

    def test_attach_scenarios_binds_target_and_entry_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            scenarios_dir = Path(tmp_dir) / "scenarios"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            write(
                scenarios_dir / "board.overlay.example.json",
                json.dumps(
                    {
                        "cards": [{"node_id": "ai-share-flow", "title": "草图"}],
                        "links": [{"from": "products", "to": "productdetail"}],
                    },
                    ensure_ascii=False,
                ),
            )
            write(
                scenarios_dir / "products-to-detail.json",
                json.dumps(
                    {
                        "scenario_id": "products-to-detail",
                        "engine": "miniapp-devtools",
                        "entry_node_id": "products",
                        "target_node_id": "productdetail",
                        "target": {"target_name": "workspace-default"},
                        "capture": {"output": "screenshots/scenario/productdetail.png"},
                        "assertions": [{"type": "path", "value": "subpackages/workspace/pages/product-detail/index"}],
                        "steps": [],
                    },
                    ensure_ascii=False,
                ),
            )

            bindings = collect_scenario_bindings(scenarios_dir)
            self.assertEqual(2, len(bindings))

            merged = hydrate_manifest_cards(attach_scenarios(manifest, bindings))
            products = next(node for node in merged["nodes"] if node["node_id"] == "products")
            detail = next(node for node in merged["nodes"] if node["node_id"] == "productdetail")

            self.assertEqual(2, merged["summary"]["attached_scenario_count"])
            self.assertEqual(2, merged["summary"]["nodes_with_scenarios"])
            self.assertEqual("entry", products["card"]["scenario_refs"][0]["role"])
            self.assertEqual("target", detail["card"]["scenario_refs"][0]["role"])
            self.assertIn("products-to-detail", detail["card"]["scenario_refs"][0]["scenario_id"])
            self.assertEqual("miniapp-devtools", detail["card"]["scenario_refs"][0]["engine"])
            self.assertEqual("workspace-default", detail["card"]["scenario_refs"][0]["target"]["target_name"])
            self.assertEqual("", detail["card"]["scenario_refs"][0]["script_path"])

    def test_attach_scenarios_can_replace_existing_refs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            scenarios_dir = Path(tmp_dir) / "scenarios"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)

            products = next(node for node in manifest["nodes"] if node["node_id"] == "products")
            products["board_meta"] = {
                "scenario_refs": [
                    {
                        "scenario_id": "legacy-products-flow",
                        "script_path": "",
                        "script_absolute_path": "",
                        "scenario_path": "",
                        "capture_output": "",
                        "engine": "miniapp-devtools",
                        "target": {},
                        "assertions": [],
                        "role": "entry",
                    }
                ]
            }

            write(
                scenarios_dir / "products-to-me-tab.json",
                json.dumps(
                    {
                        "scenario_id": "products-to-me-tab",
                        "engine": "miniapp-devtools",
                        "entry_node_id": "products",
                        "target_node_id": "workspaceentry",
                        "capture": {"output": "../screenshots/scenario/products-to-me-tab.png"},
                        "assertions": [{"type": "path", "value": "pages/workspace-entry/index"}],
                        "steps": [],
                    },
                    ensure_ascii=False,
                ),
            )

            bindings = collect_scenario_bindings(scenarios_dir)
            merged = hydrate_manifest_cards(attach_scenarios(manifest, bindings, replace_existing=True))
            products = next(node for node in merged["nodes"] if node["node_id"] == "products")

            self.assertEqual(
                ["products-to-me-tab"],
                [ref["scenario_id"] for ref in products["card"]["scenario_refs"]],
            )


if __name__ == "__main__":
    unittest.main()
