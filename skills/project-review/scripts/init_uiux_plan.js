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

function timestampLabel() {
  const d = new Date();
  const y = d.getFullYear();
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  const hh = String(d.getHours()).padStart(2, "0");
  const mm = String(d.getMinutes()).padStart(2, "0");
  const ss = String(d.getSeconds()).padStart(2, "0");
  return `${y}${m}${day}-${hh}${mm}${ss}`;
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function main() {
  const args = parseArgs(process.argv);
  const runId = args["run-id"] || timestampLabel();
  const outDir = args["out-dir"] || path.resolve("out", "project-review", "ui-ux", runId);

  const templateDir = path.resolve(__dirname, "..", "assets", "templates");
  if (!fs.existsSync(templateDir)) {
    throw new Error(`template dir not found: ${templateDir}`);
  }

  ensureDir(outDir);
  const files = fs
    .readdirSync(templateDir)
    .filter((name) => name.toLowerCase().endsWith(".csv"));

  for (const file of files) {
    const src = path.join(templateDir, file);
    const dst = path.join(outDir, file);
    const raw = fs.readFileSync(src, "utf8");
    const hydrated = raw.replaceAll("<run_id>", runId);
    fs.writeFileSync(dst, hydrated, "utf8");
  }

  const reportScriptPath = path.resolve(__dirname, "generate_uiux_report.js");
  const readme = [
    "# UI-UX Review Run",
    "",
    `- run_id: ${runId}`,
    `- generated_at: ${new Date().toISOString()}`,
    "",
    "## Next",
    "",
    "1. Fill 01_scope.csv 02_coverage_matrix.csv 03_test_cases.csv.",
    "2. Execute test cases and update 04_execution_log.csv row by row.",
    "3. Sync failures into 05_bug_list.csv.",
    "4. Update 06_summary.csv.",
    "5. Generate report with command below:",
    "",
    `${process.execPath} ${reportScriptPath} --execution-csv ${path.join(outDir, "04_execution_log.csv")} --bugs-csv ${path.join(outDir, "05_bug_list.csv")} --output ${path.join(outDir, `ui-ux-review-report-${runId}.md`)} --title \"UI/UX 定向验证报告\" --run-id ${runId}`,
    "",
  ].join("\n");

  fs.writeFileSync(path.join(outDir, "README.md"), readme, "utf8");
  console.log(`initialized ui-ux review plan: ${outDir}`);
}

try {
  main();
} catch (err) {
  console.error(`[init_uiux_plan] ${err.message}`);
  process.exit(1);
}
