#!/usr/bin/env node

const fs = require("fs");
const path = require("path");

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const token = argv[i];
    if (!token.startsWith("--")) continue;
    const key = token.slice(2);
    const next = argv[i + 1];
    if (!next || next.startsWith("--")) {
      args[key] = "true";
      continue;
    }
    args[key] = next;
    i += 1;
  }
  return args;
}

function normalizeKey(key) {
  return (key || "")
    .replace(/^\uFEFF/, "")
    .toLowerCase()
    .replace(/[\s\-_()[\]{}]/g, "");
}

function parseCsv(content) {
  const rows = [];
  let row = [];
  let field = "";
  let inQuotes = false;

  for (let i = 0; i < content.length; i += 1) {
    const ch = content[i];
    const next = content[i + 1];

    if (inQuotes) {
      if (ch === '"') {
        if (next === '"') {
          field += '"';
          i += 1;
        } else {
          inQuotes = false;
        }
      } else {
        field += ch;
      }
      continue;
    }

    if (ch === '"') {
      inQuotes = true;
      continue;
    }

    if (ch === ",") {
      row.push(field);
      field = "";
      continue;
    }

    if (ch === "\r") continue;

    if (ch === "\n") {
      row.push(field);
      rows.push(row);
      row = [];
      field = "";
      continue;
    }

    field += ch;
  }

  if (field.length > 0 || row.length > 0) {
    row.push(field);
    rows.push(row);
  }

  if (rows.length === 0) return { headers: [], records: [] };

  const headers = rows[0].map((h) => h.replace(/^\uFEFF/, "").trim());
  const records = rows.slice(1).map((cells) => {
    const rec = {};
    headers.forEach((h, idx) => {
      rec[h] = (cells[idx] || "").trim();
    });
    return rec;
  });
  return { headers, records };
}

function detectHeader(headers, candidates) {
  const normalized = headers.map((h) => ({ raw: h, norm: normalizeKey(h) }));
  for (const c of candidates.map(normalizeKey)) {
    const exact = normalized.find((x) => x.norm === c);
    if (exact) return exact.raw;
  }
  for (const c of candidates.map(normalizeKey)) {
    const partial = normalized.find((x) => x.norm.includes(c));
    if (partial) return partial.raw;
  }
  return null;
}

function normalizeResult(raw) {
  const val = (raw || "").trim().toUpperCase();
  if (!val) return "NOT_RUN";
  if (["P", "PASS", "PASSED", "通过"].includes(val)) return "PASS";
  if (["F", "FAIL", "FAILED", "失败"].includes(val)) return "FAIL";
  if (["BLOCKED", "阻塞"].includes(val)) return "BLOCKED";
  if (["NOT_RUN", "NOTRUN", "未执行", "未跑"].includes(val)) return "NOT_RUN";
  return val;
}

function normalizePriority(raw) {
  const val = (raw || "").toUpperCase().trim();
  if (!val) return "";
  if (val.startsWith("P0")) return "P0";
  if (val.startsWith("P1")) return "P1";
  if (val.startsWith("P2")) return "P2";
  if (val.startsWith("P3")) return "P3";
  return val;
}

function toRate(numerator, denominator) {
  if (denominator <= 0) return 1;
  return numerator / denominator;
}

function pct(rate) {
  return `${(rate * 100).toFixed(1)}%`;
}

function safe(v) {
  return (v || "").replace(/\|/g, "\\|");
}

function main() {
  const args = parseArgs(process.argv);
  const executionCsv = args["execution-csv"];
  const bugsCsv = args["bugs-csv"];
  const outputPath = args["output"];
  const title = args["title"] || "UI/UX 定向验证报告";
  const project = args["project"] || "unknown-project";
  const runId = args["run-id"] || "unknown-run";
  const p0Threshold = Number(args["p0-threshold"] || "1");
  const p1Threshold = Number(args["p1-threshold"] || "0.9");

  if (!executionCsv || !outputPath) {
    throw new Error(
      "usage: --execution-csv <path> --output <path> [--bugs-csv <path>] [--title <title>] [--project <name>] [--run-id <id>]"
    );
  }

  const executionRaw = fs.readFileSync(executionCsv, "utf8");
  const parsed = parseCsv(executionRaw);
  if (parsed.headers.length === 0) {
    throw new Error(`execution csv has no header: ${executionCsv}`);
  }

  const caseIdKey = detectHeader(parsed.headers, ["case_id", "caseid", "用例id"]) || parsed.headers[0];
  const priorityKey = detectHeader(parsed.headers, ["priority", "优先级"]) || "";
  const resultKey = detectHeader(parsed.headers, ["result", "结果"]) || "";
  const failureTypeKey = detectHeader(parsed.headers, ["failure_type", "失败分类", "分类"]) || "";
  const evidenceKey = detectHeader(parsed.headers, ["evidence_path", "证据路径"]) || "";
  const screenshotKey = detectHeader(parsed.headers, ["screenshot_path", "截图路径"]) || evidenceKey;
  const defectKey = detectHeader(parsed.headers, ["defect_id", "缺陷id", "缺陷"]) || "";
  const actualKey = detectHeader(parsed.headers, ["actual_result", "实际结果"]) || "";
  const notesKey = detectHeader(parsed.headers, ["notes", "备注"]) || "";

  const cases = parsed.records.map((r) => ({
    caseId: r[caseIdKey] || "",
    priority: normalizePriority(priorityKey ? r[priorityKey] : ""),
    result: normalizeResult(resultKey ? r[resultKey] : ""),
    failureType: failureTypeKey ? r[failureTypeKey] : "",
    evidencePath: evidenceKey ? r[evidenceKey] : "",
    screenshotPath: screenshotKey ? r[screenshotKey] : "",
    defectId: defectKey ? r[defectKey] : "",
    actualResult: actualKey ? r[actualKey] : "",
    notes: notesKey ? r[notesKey] : "",
  }));

  const total = cases.length;
  const passCases = cases.filter((c) => c.result === "PASS").length;
  const failCases = cases.filter((c) => c.result === "FAIL").length;
  const blockedCases = cases.filter((c) => c.result === "BLOCKED").length;
  const notRunCases = cases.filter((c) => c.result === "NOT_RUN").length;

  const p0Cases = cases.filter((c) => c.priority === "P0");
  const p1Cases = cases.filter((c) => c.priority === "P1");
  const p0PassRate = toRate(
    p0Cases.filter((c) => c.result === "PASS").length,
    p0Cases.length
  );
  const p1PassRate = toRate(
    p1Cases.filter((c) => c.result === "PASS").length,
    p1Cases.length
  );
  const gateResult = p0PassRate >= p0Threshold && p1PassRate >= p1Threshold ? "PASS" : "FAIL";

  let bugRows = [];
  if (bugsCsv && fs.existsSync(bugsCsv)) {
    bugRows = parseCsv(fs.readFileSync(bugsCsv, "utf8")).records;
  }

  const failedOrBlocked = cases.filter((c) => c.result === "FAIL" || c.result === "BLOCKED");

  const lines = [];
  lines.push(`# ${title}`);
  lines.push("");
  lines.push(`- 项目: \`${project}\``);
  lines.push(`- run_id: \`${runId}\``);
  lines.push(`- 生成时间: \`${new Date().toISOString()}\``);
  lines.push("");

  lines.push("## 1. 执行汇总");
  lines.push("");
  lines.push("| 指标 | 数值 |");
  lines.push("|---|---|");
  lines.push(`| 总用例数 | ${total} |`);
  lines.push(`| PASS | ${passCases} |`);
  lines.push(`| FAIL | ${failCases} |`);
  lines.push(`| BLOCKED | ${blockedCases} |`);
  lines.push(`| NOT_RUN | ${notRunCases} |`);
  lines.push(`| P0 通过率 | ${pct(p0PassRate)} |`);
  lines.push(`| P1 通过率 | ${pct(p1PassRate)} |`);
  lines.push(`| Gate 结论 | **${gateResult}** |`);
  lines.push("");

  lines.push("## 2. 问题清单（失败/阻塞）");
  lines.push("");
  if (failedOrBlocked.length === 0) {
    lines.push("- 无失败或阻塞用例。");
    lines.push("");
  } else {
    for (const item of failedOrBlocked) {
      lines.push(`### ${item.caseId || "(unknown case)"} [${item.priority || "-"}]`);
      lines.push(`- 结果: ${item.result}`);
      lines.push(`- 分类: ${item.failureType || "-"}`);
      lines.push(`- 缺陷ID: ${item.defectId || "-"}`);
      if (item.actualResult) lines.push(`- 实际结果: ${item.actualResult}`);
      if (item.notes) lines.push(`- 备注: ${item.notes}`);
      if (item.evidencePath) lines.push(`- 证据: \`${item.evidencePath}\``);
      if (item.screenshotPath) {
        lines.push("");
        lines.push(`![${item.caseId || "screenshot"}](${item.screenshotPath})`);
      }
      lines.push("");
    }
  }

  lines.push("## 3. 缺陷表");
  lines.push("");
  if (bugRows.length === 0) {
    lines.push("- 未提供缺陷表，或缺陷表为空。");
    lines.push("");
  } else {
    const bugHeaders = Object.keys(bugRows[0]);
    lines.push(`| ${bugHeaders.map(safe).join(" | ")} |`);
    lines.push(`| ${bugHeaders.map(() => "---").join(" | ")} |`);
    for (const row of bugRows) {
      lines.push(`| ${bugHeaders.map((h) => safe(row[h])).join(" | ")} |`);
    }
    lines.push("");
  }

  lines.push("## 4. 全量用例结果");
  lines.push("");
  lines.push("| case_id | priority | result | failure_type | defect_id | screenshot |");
  lines.push("|---|---|---|---|---|---|");
  for (const c of cases) {
    const shot = c.screenshotPath ? `[image](${c.screenshotPath})` : "";
    lines.push(`| ${safe(c.caseId)} | ${safe(c.priority)} | ${safe(c.result)} | ${safe(c.failureType)} | ${safe(c.defectId)} | ${shot} |`);
  }
  lines.push("");

  fs.mkdirSync(path.dirname(outputPath), { recursive: true });
  fs.writeFileSync(outputPath, lines.join("\n"), "utf8");
  console.log(`ui-ux report generated: ${outputPath}`);
}

try {
  main();
} catch (err) {
  console.error(`[generate_uiux_report] ${err.message}`);
  process.exit(1);
}
