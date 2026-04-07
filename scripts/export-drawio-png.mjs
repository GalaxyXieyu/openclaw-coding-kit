import fs from "node:fs";
import os from "node:os";
import path from "node:path";
import { execFileSync } from "node:child_process";

const repoRoot = "/Volumes/DATABASE/code/learn/openclaw-pm-coder-kit";
const input = path.join(repoRoot, "diagrams", "pm-coder-bridge-architecture.drawio");
const svgOutput = path.join(repoRoot, "diagrams", "pm-coder-bridge-architecture.drawio.svg");
const pngOutput = path.join(repoRoot, "diagrams", "pm-coder-bridge-architecture.drawio.png");

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), "drawio-export-"));

function ensurePackageJson() {
  const packageJson = {
    private: true,
    type: "module",
  };
  fs.writeFileSync(path.join(tempDir, "package.json"), JSON.stringify(packageJson, null, 2));
}

function installDeps() {
  execFileSync(
    "npm",
    ["install", "@markdown-viewer/drawio2svg", "@markdown-viewer/text-measure", "@xmldom/xmldom", "sharp", "tsx", "gui", "coroutine"],
    { cwd: tempDir, stdio: "inherit" },
  );

  const indexNodePath = path.join(
    tempDir,
    "node_modules",
    "@markdown-viewer",
    "text-measure",
    "lib",
    "index.node.ts",
  );

  fs.writeFileSync(
    indexNodePath,
    [
      "export * from './index.ts';",
      "",
      "// Patched in temporary export environment:",
      "// disable automatic WebView provider bootstrap for upstream Node.js runtime.",
      "",
    ].join("\n"),
    "utf8",
  );
}

function writeWorkerScript() {
  const worker = `
import fs from "node:fs";
import sharp from "sharp";
import { DOMParser } from "@xmldom/xmldom";
import { convert } from "./node_modules/@markdown-viewer/drawio2svg/lib/convert.ts";
import { setTextMeasureProvider } from "./node_modules/@markdown-viewer/text-measure/lib/measure.ts";

globalThis.DOMParser = DOMParser;

function stripHtml(text) {
  return String(text || "").replace(/<[^>]*>/g, "");
}

setTextMeasureProvider({
  measureText(text, fontSize, _fontFamily, fontWeight = "normal") {
    const plain = stripHtml(text);
    let units = 0;
    for (const ch of plain) {
      units += /[\\u4e00-\\u9fff\\u3400-\\u4dbf\\uf900-\\ufaff]/.test(ch) ? 1 : 0.58;
    }
    const weightFactor = (fontWeight === "bold" || String(fontWeight) === "700") ? 1.06 : 1;
    return { width: Math.max(units * fontSize * weightFactor, 1), height: Math.max(fontSize * 1.25, 1) };
  },
  measureTextLayout(text, fontSize, fontFamily, fontWeight = "normal", fontStyle = "normal", containerWidth, isHtml = false) {
    const single = this.measureText(text, fontSize, fontFamily, fontWeight, fontStyle, isHtml);
    const lineHeight = Math.max(fontSize * 1.25, 1);
    if (!containerWidth || single.width <= containerWidth) {
      return { width: single.width, height: lineHeight, lineCount: 1, lineHeight };
    }
    const lineCount = Math.max(1, Math.ceil(single.width / containerWidth));
    return { width: Math.min(single.width, containerWidth), height: lineCount * lineHeight, lineCount, lineHeight };
  }
});

const input = ${JSON.stringify(input)};
const svgOutput = ${JSON.stringify(svgOutput)};
const pngOutput = ${JSON.stringify(pngOutput)};

const xml = fs.readFileSync(input, "utf8");
const svg = convert(xml, {
  padding: 16,
  scale: 1,
  backgroundColor: "#ffffff",
  fontFamily: "PingFang SC, Arial",
});

fs.writeFileSync(svgOutput, svg, "utf8");
await sharp(Buffer.from(svg)).png().toFile(pngOutput);
console.log(pngOutput);
`;

  fs.writeFileSync(path.join(tempDir, "worker.mjs"), worker, "utf8");
}

ensurePackageJson();
installDeps();
writeWorkerScript();
execFileSync("npx", ["tsx", "worker.mjs"], { cwd: tempDir, stdio: "inherit" });
