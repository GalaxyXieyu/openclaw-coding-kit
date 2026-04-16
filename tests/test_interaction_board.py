from __future__ import annotations

import json
import sys
import tempfile
import unittest
from base64 import b64decode
from contextlib import redirect_stdout
import io
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
    extract_nextjs_manifest,
    hydrate_manifest_cards,
    main,
    query_manifest_nodes,
    render_drawio_board,
    render_html_board,
    render_playwright_spec,
    scaffold_manifest_scenarios,
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

    def _build_web_repo(self, root: Path) -> None:
        write(root / "apps/admin/app/page.tsx", "import { redirect } from 'next/navigation';\nexport default function HomePage() { redirect('/dashboard'); }\n")
        write(
            root / "apps/admin/middleware.ts",
            """import { NextRequest, NextResponse } from 'next/server';

export function middleware(request: NextRequest) {
  if (!request.nextUrl.pathname.startsWith('/dashboard')) {
    return NextResponse.next();
  }

  return NextResponse.redirect(new URL('/login', request.url));
}
""",
        )
        write(
            root / "apps/admin/components/dashboard/nav-config.ts",
            """export const dashboardNavGroups = [
  {
    id: 'data',
    title: { zh: '数据', en: 'Data' },
    items: [{ href: '/dashboard', label: { zh: '数据', en: 'Data' } }],
  },
  {
    id: 'users',
    title: { zh: '用户', en: 'Users' },
    items: [{ href: '/dashboard/tenant-management', label: { zh: '用户', en: 'Users' } }],
  },
];
""",
        )
        write(
            root / "apps/admin/components/dashboard/dashboard-top-tabs.tsx",
            """const TAB_ITEMS = [
  { href: '/dashboard', label: { zh: '数据', en: 'Data' } },
  { href: '/dashboard/settings/pricing', label: { zh: '设置', en: 'Settings' } },
];
""",
        )
        write(
            root / "apps/admin/components/dashboard/dashboard-commerce-tabs.tsx",
            """const TAB_ITEMS = [
  { href: '/dashboard/commerce/catalog', label: { zh: '商品目录', en: 'Catalog' } },
  { href: '/dashboard/commerce/orders', label: { zh: '订单管理', en: 'Orders' } },
];
""",
        )
        write(
            root / "apps/admin/components/dashboard/dashboard-settings-tabs.tsx",
            """const TAB_ITEMS = [
  { href: '/dashboard/settings/pricing', label: { zh: '套餐定价', en: 'Pricing' } },
  { href: '/dashboard/settings/platform-branding', label: { zh: '平台品牌', en: 'Platform Branding' } },
];
""",
        )
        write(
            root / "apps/admin/lib/locales/dashboard-pages.ts",
            """export const DASHBOARD_OVERVIEW_MESSAGES = {
  zh: { title: '数据' },
  en: { title: 'Data' },
} as const;

export const TENANT_MANAGEMENT_MESSAGES = {
  zh: { title: '平台用户' },
  en: { title: 'Platform Users' },
} as const;
""",
        )
        write(
            root / "apps/admin/lib/locales/settings-pages.ts",
            """export const PRICING_SETTINGS_MESSAGES = {
  zh: { title: '套餐定价' },
  en: { title: 'Pricing' },
} as const;
""",
        )
        write(
            root / "apps/admin/app/login/page.tsx",
            """'use client';
export default function LoginPage() {
  return <main><h1>后台登录</h1><span>密码登录</span></main>;
}
""",
        )
        write(
            root / "apps/admin/app/dashboard/layout.tsx",
            """import { redirect } from 'next/navigation';
export default function DashboardLayout({ children }) {
  redirect('/login?redirect=/dashboard');
  return children;
}
""",
        )
        write(
            root / "apps/admin/app/dashboard/page.tsx",
            """import { DASHBOARD_OVERVIEW_MESSAGES } from '@/lib/locales/dashboard-pages';
export default function DashboardPage() {
  return <section><h2>平台概况</h2><a href="/dashboard/tenant-management">进入用户工作台</a></section>;
}
""",
        )
        write(
            root / "apps/admin/app/dashboard/tenant-management/page.tsx",
            """import { TENANT_MANAGEMENT_MESSAGES } from '@/lib/locales/dashboard-pages';
export default function TenantPage() {
  return <form><input id="tenant-governance-search" /><button>搜索</button></form>;
}
""",
        )
        write(root / "apps/admin/app/dashboard/settings/page.tsx", "import { redirect } from 'next/navigation';\nexport default function SettingsPage() { redirect('/dashboard/settings/pricing'); }\n")
        write(root / "apps/admin/app/dashboard/settings/pricing/page.tsx", "import { PRICING_SETTINGS_MESSAGES } from '@/lib/locales/settings-pages';\nexport default function PricingPage() { return <div>套餐定价</div>; }\n")
        write(root / "apps/admin/app/dashboard/settings/platform-branding/page.tsx", "export default function BrandingPage() { return <div>平台品牌</div>; }\n")
        write(root / "apps/admin/app/dashboard/commerce/page.tsx", "import { redirect } from 'next/navigation';\nexport default function CommercePage() { redirect('/dashboard/commerce/catalog'); }\n")
        write(root / "apps/admin/app/dashboard/commerce/catalog/page.tsx", "export default function CatalogPage() { return <div>商品目录</div>; }\n")
        write(
            root / "apps/admin/features/commerce/community/community-editor-page-client.tsx",
            """export function CommunityEditorPageClient() {
  return <form className="commerce-editor-form"><input /></form>;
}
""",
        )
        write(
            root / "apps/admin/app/dashboard/commerce/community/new/page.tsx",
            """import { CommunityEditorPageClient } from '@/features/commerce/community/community-editor-page-client';
export default function CommunityPage() { return <CommunityEditorPageClient />; }
""",
        )
        write(root / "apps/admin/app/dashboard/commerce/orders/page.tsx", "export default function OrdersPage() { return <div>订单管理</div>; }\n")

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

    def test_extract_nextjs_manifest_builds_route_inventory_and_edges(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir)
            self._build_web_repo(repo_root)
            manifest = extract_nextjs_manifest(
                repo_root,
                app_dir="apps/admin",
                app_kind="web-admin",
                app_name="Admin",
            )

            node_ids = {node["node_id"] for node in manifest["nodes"]}
            self.assertIn("admin-login", node_ids)
            self.assertIn("admin-dashboard", node_ids)
            self.assertIn("admin-dashboard-settings-pricing", node_ids)
            self.assertIn("admin-dashboard-commerce-catalog", node_ids)

            dashboard = next(node for node in manifest["nodes"] if node["node_id"] == "admin-dashboard")
            login = next(node for node in manifest["nodes"] if node["node_id"] == "admin-login")
            pricing = next(node for node in manifest["nodes"] if node["node_id"] == "admin-dashboard-settings-pricing")
            self.assertEqual("数据", dashboard["title"])
            self.assertEqual("后台登录", login["title"])
            self.assertEqual("套餐定价", pricing["title"])

            edge_pairs = {(edge["from"], edge["to"], edge["kind"]) for edge in manifest["edges"]}
            self.assertIn(("admin-root", "admin-dashboard", "redirect"), edge_pairs)
            self.assertIn(("admin-dashboard", "admin-login", "redirect"), edge_pairs)
            self.assertIn(("admin-dashboard-settings", "admin-dashboard-settings-pricing", "redirect"), edge_pairs)
            self.assertIn(("admin-dashboard", "admin-dashboard-tenant-management", "navigateTo"), edge_pairs)

    def test_scaffold_manifest_scenarios_writes_one_file_per_node(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            scenario_root = Path(tmp_dir) / "board" / "scenarios"
            self._build_web_repo(repo_root)
            manifest = extract_nextjs_manifest(repo_root, app_dir="apps/admin", app_kind="web-admin", app_name="Admin")

            report = scaffold_manifest_scenarios(
                manifest,
                scenario_root,
                base_url="https://admin.example.com",
                auth_surface="admin",
                auth_profile="prod-admin",
                scenario_prefix="prod-admin",
                write_specs=True,
                force=True,
            )

            self.assertEqual(len(manifest["nodes"]), report["scenario_count"])
            login_scenario = json.loads((scenario_root / "prod-admin-admin-login.json").read_text(encoding="utf-8"))
            dashboard_scenario = json.loads((scenario_root / "prod-admin-admin-dashboard.json").read_text(encoding="utf-8"))
            tenant_scenario = json.loads((scenario_root / "prod-admin-admin-dashboard-tenant-management.json").read_text(encoding="utf-8"))
            community_new_scenario = json.loads((scenario_root / "prod-admin-admin-dashboard-commerce-community-new.json").read_text(encoding="utf-8"))
            self.assertEqual("admin-login", login_scenario["entry_node_id"])
            self.assertEqual("admin-login", dashboard_scenario["entry_node_id"])
            self.assertEqual("/dashboard", dashboard_scenario["steps"][0]["target"])
            self.assertEqual("selector", tenant_scenario["assertions"][0]["type"])
            self.assertEqual("#tenant-governance-search", tenant_scenario["assertions"][0]["selector"])
            self.assertEqual("selector", community_new_scenario["assertions"][0]["type"])
            self.assertEqual("form.commerce-editor-form", community_new_scenario["assertions"][0]["selector"])
            self.assertTrue((scenario_root / "prod-admin-admin-dashboard.spec.ts").exists())

    def test_query_node_prefers_exact_node_id_over_longer_contains_match(self) -> None:
        manifest = {
            "nodes": [
                {
                    "node_id": "admin-dashboard",
                    "route_key": "AdminDashboard",
                    "title": "数据",
                    "route": "dashboard",
                    "status": "registered",
                    "group": "admin",
                    "package": "main",
                    "screen_component": "apps/admin/app/dashboard/page.tsx",
                    "page_file": "apps/admin/app/dashboard/page.tsx",
                    "config_file": "",
                    "aliases": ["admin-dashboard", "dashboard"],
                    "source_refs": [],
                    "regions": [],
                    "board_meta": {},
                    "card": {"images": [], "primary_image": {}, "scenario_refs": []},
                },
                {
                    "node_id": "admin-dashboard-guiquan-management",
                    "route_key": "AdminDashboardGuiquanManagement",
                    "title": "Guiquan Management",
                    "route": "dashboard/guiquan-management",
                    "status": "registered",
                    "group": "admin",
                    "package": "main",
                    "screen_component": "apps/admin/app/dashboard/guiquan-management/page.tsx",
                    "page_file": "apps/admin/app/dashboard/guiquan-management/page.tsx",
                    "config_file": "",
                    "aliases": ["admin-dashboard-guiquan-management"],
                    "source_refs": [],
                    "regions": [],
                    "board_meta": {},
                    "card": {"images": [], "primary_image": {}, "scenario_refs": []},
                },
            ]
        }

        matches = query_manifest_nodes(manifest, "admin-dashboard", limit=1)
        self.assertEqual("admin-dashboard", matches[0]["node_id"])

    def test_hydrate_manifest_cards_projects_target_scenarios_and_hides_entry_noise(self) -> None:
        manifest = {
            "nodes": [
                {
                    "node_id": "admin-login",
                    "route_key": "AdminLogin",
                    "title": "后台登录",
                    "route": "login",
                    "status": "registered",
                    "group": "entry",
                    "package": "main",
                    "screen_component": "apps/admin/app/login/page.tsx",
                    "page_file": "apps/admin/app/login/page.tsx",
                    "config_file": "",
                    "aliases": ["admin-login"],
                    "source_refs": [],
                    "regions": [],
                    "screenshot_refs": [],
                    "board_meta": {
                        "scenario_refs": [
                            {
                                "scenario_id": "login-self",
                                "script_path": "scenarios/login-self.spec.ts",
                                "scenario_path": "/tmp/scenarios/login-self.json",
                                "capture_output": "../screenshots/login-self.png",
                                "engine": "web-playwright-cli",
                                "role": "entry",
                            },
                            {
                                "scenario_id": "login-self",
                                "script_path": "scenarios/login-self.spec.ts",
                                "scenario_path": "/tmp/scenarios/login-self.json",
                                "capture_output": "../screenshots/login-self.png",
                                "engine": "web-playwright-cli",
                                "role": "target",
                            },
                            {
                                "scenario_id": "dashboard",
                                "script_path": "scenarios/dashboard.spec.ts",
                                "scenario_path": "/tmp/scenarios/dashboard.json",
                                "capture_output": "../screenshots/dashboard.png",
                                "engine": "web-playwright-cli",
                                "role": "entry",
                            },
                        ]
                    },
                }
            ],
            "edges": [],
            "conflicts": [],
        }

        hydrated = hydrate_manifest_cards(manifest)
        login = hydrated["nodes"][0]
        self.assertEqual(1, len(login["card"]["scenario_refs"]))
        self.assertEqual("login-self", login["card"]["scenario_refs"][0]["scenario_id"])
        self.assertEqual("target", login["card"]["scenario_refs"][0]["role"])
        self.assertEqual(2, len(login["card"]["scenario_refs_all"]))
        self.assertEqual(1, login["card"]["scenario_ref_stats"]["hidden_count"])

    def test_hydrate_manifest_cards_inherits_redirect_target_image(self) -> None:
        manifest = {
            "nodes": [
                {
                    "node_id": "admin-dashboard",
                    "route_key": "AdminDashboard",
                    "title": "数据",
                    "route": "dashboard",
                    "status": "registered",
                    "group": "admin",
                    "package": "main",
                    "screen_component": "apps/admin/app/dashboard/page.tsx",
                    "page_file": "apps/admin/app/dashboard/page.tsx",
                    "config_file": "",
                    "aliases": ["admin-dashboard"],
                    "source_refs": [],
                    "regions": [],
                    "screenshot_refs": [
                        {
                            "label": "scenario:dashboard",
                            "path": "screenshots/prod-admin-admin-dashboard.png",
                            "exists": True,
                            "absolute_path": "/tmp/screenshots/prod-admin-admin-dashboard.png",
                            "source_path": "/tmp/screenshots/prod-admin-admin-dashboard.png",
                            "matched_by": "scenario:target",
                        }
                    ],
                    "board_meta": {},
                },
                {
                    "node_id": "admin-root",
                    "route_key": "AdminRoot",
                    "title": "后台根入口",
                    "route": "",
                    "status": "registered",
                    "group": "entry",
                    "package": "main",
                    "screen_component": "apps/admin/app/page.tsx",
                    "page_file": "apps/admin/app/page.tsx",
                    "config_file": "",
                    "aliases": ["admin-root"],
                    "source_refs": [],
                    "regions": [],
                    "screenshot_refs": [],
                    "board_meta": {
                        "route_mode": "redirect",
                        "redirect_target": "/dashboard",
                    },
                },
            ],
            "edges": [],
            "conflicts": [],
        }

        hydrated = hydrate_manifest_cards(manifest)
        redirect_node = next(node for node in hydrated["nodes"] if node["node_id"] == "admin-root")
        self.assertTrue(redirect_node["card"]["primary_image"]["exists"])
        self.assertEqual(
            "screenshots/prod-admin-admin-dashboard.png",
            redirect_node["card"]["primary_image"]["relative_path"],
        )
        self.assertEqual(
            "redirect:admin-dashboard",
            redirect_node["card"]["primary_image"]["matched_by"],
        )

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
            self.assertIn("code_entry", product["card"])
            self.assertIn("code_anchors", product["card"])
            self.assertIn("primary_image", product["card"])
            self.assertTrue(product["card"]["primary_image"]["absolute_path"].endswith("screenshots/products.png"))

    def test_build_manual_board_hydrates_scenarios_and_skips_missing_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            board_dir = Path(tmp_dir) / "board"
            scenarios_dir = board_dir / "scenarios"
            seed_manifest = board_dir / "board.seed.json"
            screenshot_path = board_dir / "screenshots" / "prod-admin-dashboard-auth.png"

            write(
                seed_manifest,
                json.dumps(
                    {
                        "schema_version": "1.0",
                        "generated_at": "2026-04-15T17:00:00+08:00",
                        "project": {"name": "Admin Board", "repo_root": "/tmp/repo", "app_kind": "web-admin"},
                        "sources": {},
                        "summary": {},
                        "nodes": [
                            {
                                "node_id": "admin-login",
                                "route_key": "adminLogin",
                                "title": "后台登录",
                                "route": "login",
                                "aliases": ["login", "admin-login"],
                                "package": "main",
                                "group": "entry",
                                "status": "registered",
                                "screen_component": "apps/admin/app/login/page.tsx",
                                "page_file": "apps/admin/app/login/page.tsx",
                                "config_file": "",
                                "regions": ["账号/手机号", "密码登录"],
                                "screenshot_refs": [{"label": "planned", "path": "screenshots/admin-login.png", "exists": False}],
                                "source_refs": [{"path": "/tmp/repo/apps/admin/app/login/page.tsx", "line": 147}],
                            },
                            {
                                "node_id": "admin-dashboard",
                                "route_key": "adminDashboard",
                                "title": "平台概况",
                                "route": "dashboard",
                                "aliases": ["dashboard", "admin-dashboard"],
                                "package": "main",
                                "group": "admin",
                                "status": "registered",
                                "screen_component": "apps/admin/app/dashboard/page.tsx",
                                "page_file": "apps/admin/app/dashboard/page.tsx",
                                "config_file": "",
                                "regions": ["平台概况", "营收概览"],
                                "screenshot_refs": [{"label": "planned", "path": "screenshots/admin-dashboard.png", "exists": False}],
                                "source_refs": [{"path": "/tmp/repo/apps/admin/app/dashboard/page.tsx", "line": 127}],
                            },
                        ],
                        "edges": [],
                        "conflicts": [],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            write(
                scenarios_dir / "prod-admin-dashboard.json",
                json.dumps(
                    {
                        "scenario_id": "prod-admin-dashboard",
                        "engine": "web-playwright-cli",
                        "entry_node_id": "admin-login",
                        "target_node_id": "admin-dashboard",
                        "capture": {"output": "../screenshots/prod-admin-dashboard-auth.png"},
                        "steps": [{"action": "open", "target": "/dashboard"}],
                        "assertions": [{"type": "text", "value": "平台概况"}],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            write(
                scenarios_dir / "prod-web-home.json",
                json.dumps(
                    {
                        "scenario_id": "prod-web-home",
                        "engine": "web-playwright-cli",
                        "entry_node_id": "web-home",
                        "target_node_id": "web-home",
                        "capture": {"output": "../screenshots/prod-web-home.png"},
                        "steps": [{"action": "open", "target": "/"}],
                        "assertions": [{"type": "text", "value": "首页"}],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
            )
            write_binary(
                screenshot_path,
                b64decode(
                    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9sX6b08AAAAASUVORK5CYII="
                ),
            )

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "build-manual-board",
                        "--manifest",
                        str(seed_manifest),
                        "--out-dir",
                        str(board_dir),
                        "--scenario-dir",
                        str(scenarios_dir),
                        "--skip-missing-scenarios",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertTrue(Path(payload["manifest"]).exists())
            built_manifest = json.loads((board_dir / "board.manifest.json").read_text(encoding="utf-8"))
            inventory_text = (board_dir / "inventory.md").read_text(encoding="utf-8")
            dashboard = next(node for node in built_manifest["nodes"] if node["node_id"] == "admin-dashboard")
            self.assertEqual("scenario:prod-admin-dashboard", dashboard["card"]["primary_image"]["label"])
            self.assertEqual("screenshots/prod-admin-dashboard-auth.png", dashboard["card"]["primary_image"]["relative_path"])
            self.assertEqual("apps/admin/app/dashboard/page.tsx", dashboard["card"]["code_entry"]["screen_component"])
            self.assertEqual(1, built_manifest["summary"]["nodes_with_screenshots"])
            self.assertIn("scenario:prod-admin-dashboard", inventory_text)
            self.assertNotIn("| 已注册 | 平台概况 | `dashboard` | admin | main | planned |", inventory_text)
            self.assertEqual(
                [
                    {
                        "scenario_id": "prod-web-home",
                        "node_ref": "web-home",
                        "role": "target",
                    },
                    {
                        "scenario_id": "prod-web-home",
                        "node_ref": "web-home",
                        "role": "entry",
                    },
                ],
                built_manifest["sources"]["skipped_scenarios"],
            )

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
            self.assertEqual(1, hydrated["summary"]["nodes_with_screenshots"])
            self.assertEqual(1, hydrated["summary"]["attached_screenshot_count"])

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

    def test_query_node_returns_code_paths_and_images(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            board_root = Path(tmp_dir) / "board"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            write(board_root / "screenshots" / "compare" / "products.png", "products-image")

            products = next(node for node in manifest["nodes"] if node["node_id"] == "products")
            products["screenshot_refs"] = [
                {
                    "label": "compare",
                    "path": "screenshots/compare/products.png",
                    "exists": True,
                    "source_path": str(board_root / "screenshots" / "compare" / "products.png"),
                    "matched_by": "route-tail",
                }
            ]

            hydrated = hydrate_manifest_cards(manifest, board_root)
            matches = query_manifest_nodes(hydrated, "宠物档案", limit=1)

            self.assertEqual(1, len(matches))
            match = matches[0]
            self.assertEqual("products", match["node_id"])
            self.assertEqual("apps/miniapp/src/features/product/list/screen.tsx", match["code"]["screen_component"])
            self.assertEqual("apps/miniapp/src/pages/products/index.tsx", match["code"]["page_file"])
            self.assertEqual("screenshots/compare/products.png", match["images"]["primary"]["relative_path"])
            self.assertEqual(1, match["images"]["existing_version_count"])

            manifest_path = board_root / "board.manifest.json"
            write(manifest_path, json.dumps(hydrated, ensure_ascii=False, indent=2))
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "query-node",
                        "--manifest",
                        str(manifest_path),
                        "--query",
                        "products",
                        "--limit",
                        "1",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertEqual(1, payload["match_count"])
            self.assertEqual("products", payload["matches"][0]["node_id"])
            self.assertEqual("screenshots/compare/products.png", payload["matches"][0]["images"]["primary"]["relative_path"])

    def test_query_node_without_query_lists_all_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            board_root = Path(tmp_dir) / "board"
            self._build_repo(repo_root)
            manifest = hydrate_manifest_cards(extract_miniapp_manifest(repo_root), board_root)
            manifest_path = board_root / "board.manifest.json"
            write(manifest_path, json.dumps(manifest, ensure_ascii=False, indent=2))

            matches = query_manifest_nodes(manifest, "", limit=0)
            self.assertEqual(len(manifest["nodes"]), len(matches))
            self.assertEqual(manifest["nodes"][0]["node_id"], matches[0]["node_id"])
            self.assertEqual(["list:all"], matches[0]["match_reasons"])

            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "query-node",
                        "--manifest",
                        str(manifest_path),
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertEqual(len(manifest["nodes"]), payload["match_count"])
            self.assertEqual(manifest["nodes"][0]["node_id"], payload["matches"][0]["node_id"])

    def test_query_node_compact_mode_keeps_code_and_image_paths_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            board_root = Path(tmp_dir) / "board"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            write(board_root / "screenshots" / "compare" / "products.png", "products-image")

            products = next(node for node in manifest["nodes"] if node["node_id"] == "products")
            products["screenshot_refs"] = [
                {
                    "label": "compare",
                    "path": "screenshots/compare/products.png",
                    "exists": True,
                    "source_path": str(board_root / "screenshots" / "compare" / "products.png"),
                    "matched_by": "route-tail",
                    "image_mean": 123.4,
                    "image_stddev": 22.2,
                }
            ]

            hydrated = hydrate_manifest_cards(manifest, board_root)
            matches = query_manifest_nodes(hydrated, "products", limit=1, compact=True)

            self.assertEqual(1, len(matches))
            match = matches[0]
            self.assertEqual("apps/miniapp/src/pages/products/index.tsx", match["code"]["page_file"])
            self.assertNotIn("source_refs", match["code"])
            self.assertEqual("screenshots/compare/products.png", match["images"]["primary"]["relative_path"])
            self.assertNotIn("source_path", match["images"]["primary"])
            self.assertNotIn("image_mean", match["images"]["versions"][0])

            manifest_path = board_root / "board.manifest.json"
            write(manifest_path, json.dumps(hydrated, ensure_ascii=False, indent=2))
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "query-node",
                        "--manifest",
                        str(manifest_path),
                        "--query",
                        "products",
                        "--limit",
                        "1",
                        "--compact",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertTrue(payload["compact"])
            self.assertEqual("products", payload["matches"][0]["node_id"])
            self.assertNotIn("source_refs", payload["matches"][0]["code"])
            self.assertEqual(
                "screenshots/compare/products.png",
                payload["matches"][0]["images"]["versions"][0]["relative_path"],
            )

    def test_query_node_paths_only_mode_keeps_only_lookup_paths(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            board_root = Path(tmp_dir) / "board"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            write(board_root / "screenshots" / "compare" / "products.png", "products-image")

            products = next(node for node in manifest["nodes"] if node["node_id"] == "products")
            products["screenshot_refs"] = [
                {
                    "label": "compare",
                    "path": "screenshots/compare/products.png",
                    "exists": True,
                    "source_path": str(board_root / "screenshots" / "compare" / "products.png"),
                    "matched_by": "route-tail",
                    "image_mean": 123.4,
                    "image_stddev": 22.2,
                }
            ]

            hydrated = hydrate_manifest_cards(manifest, board_root)
            matches = query_manifest_nodes(hydrated, "products", limit=1, paths_only=True)

            self.assertEqual(1, len(matches))
            match = matches[0]
            self.assertEqual("products", match["node_id"])
            self.assertEqual("apps/miniapp/src/pages/products/index.tsx", match["code"]["page_file"])
            self.assertNotIn("route_key", match)
            self.assertNotIn("match_score", match)
            self.assertNotIn("regions", match)
            self.assertEqual("screenshots/compare/products.png", match["images"]["primary"]["relative_path"])
            self.assertNotIn("version_count", match["images"])
            self.assertNotIn("source_path", match["images"]["versions"][0])

            manifest_path = board_root / "board.manifest.json"
            write(manifest_path, json.dumps(hydrated, ensure_ascii=False, indent=2))
            stdout = io.StringIO()
            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "query-node",
                        "--manifest",
                        str(manifest_path),
                        "--query",
                        "products",
                        "--limit",
                        "1",
                        "--paths-only",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(0, exit_code)
            self.assertTrue(payload["paths_only"])
            self.assertEqual("products", payload["matches"][0]["node_id"])
            self.assertNotIn("compact", payload["matches"][0])
            self.assertNotIn("regions", payload["matches"][0])
            self.assertEqual(
                "screenshots/compare/products.png",
                payload["matches"][0]["images"]["primary"]["relative_path"],
            )

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

    def test_attach_scenarios_can_skip_missing_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            repo_root = Path(tmp_dir) / "repo"
            self._build_repo(repo_root)
            manifest = extract_miniapp_manifest(repo_root)
            bindings = [
                {
                    "scenario_id": "products-to-detail",
                    "scenario_path": str(Path(tmp_dir) / "products-to-detail.json"),
                    "script_path": "products-to-detail.spec.ts",
                    "script_absolute_path": str(Path(tmp_dir) / "products-to-detail.spec.ts"),
                    "capture_output": "../screenshots/scenario/products-to-detail.png",
                    "engine": "miniapp-devtools",
                    "target": {},
                    "assertions": [],
                    "node_ref": "productdetail",
                    "role": "target",
                },
                {
                    "scenario_id": "missing-admin-flow",
                    "scenario_path": str(Path(tmp_dir) / "missing-admin-flow.json"),
                    "script_path": "missing-admin-flow.spec.ts",
                    "script_absolute_path": str(Path(tmp_dir) / "missing-admin-flow.spec.ts"),
                    "capture_output": "../screenshots/scenario/missing-admin-flow.png",
                    "engine": "web-playwright-cli",
                    "target": {},
                    "assertions": [],
                    "node_ref": "admin-dashboard",
                    "role": "target",
                },
            ]

            merged = hydrate_manifest_cards(attach_scenarios(manifest, bindings, skip_missing_nodes=True))
            detail = next(node for node in merged["nodes"] if node["node_id"] == "productdetail")

            self.assertEqual(["products-to-detail"], [ref["scenario_id"] for ref in detail["card"]["scenario_refs"]])
            self.assertEqual(
                [
                    {
                        "scenario_id": "missing-admin-flow",
                        "node_ref": "admin-dashboard",
                        "role": "target",
                    }
                ],
                merged["sources"]["skipped_scenarios"],
            )


if __name__ == "__main__":
    unittest.main()
