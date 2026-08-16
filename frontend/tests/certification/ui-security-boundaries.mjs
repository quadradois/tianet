import assert from "node:assert/strict";
import crypto from "node:crypto";
import { existsSync, readdirSync, readFileSync } from "node:fs";
import { resolve, relative } from "node:path";
import { fileURLToPath } from "node:url";

const repositoryRoot = fileURLToPath(new URL("../../../", import.meta.url));
const frontendRoot = resolve(repositoryRoot, "frontend");

function walk(directory, predicate = () => true) {
  if (!existsSync(directory)) return [];
  const found = [];
  const pending = [directory];
  while (pending.length) {
    const current = pending.pop();
    for (const entry of readdirSync(current, { withFileTypes: true })) {
      const absolute = resolve(current, entry.name);
      if (entry.isDirectory()) {
        pending.push(absolute);
      } else if (predicate(absolute)) {
        found.push(absolute);
      }
    }
  }
  return found.sort();
}

function readText(absolute) {
  return readFileSync(absolute, "utf8").replace(/\r\n/g, "\n");
}

function failOnPattern(files, patterns, context) {
  const violations = [];
  for (const absolute of files) {
    const source = readText(absolute);
    for (const [label, pattern] of patterns) {
      if (pattern.test(source)) {
        violations.push(`${relative(repositoryRoot, absolute).replace(/\\/g, "/")}: ${label}`);
      }
    }
  }
  assert.deepEqual(violations, [], `${context}:\n${violations.join("\n")}`);
}

function readPngDimensions(absolute) {
  const bytes = readFileSync(absolute);
  assert.equal(bytes.toString("ascii", 1, 4), "PNG", `${absolute}: assinatura PNG`);
  return { width: bytes.readUInt32BE(16), height: bytes.readUInt32BE(20), bytes };
}

function certifyVisualEvidence() {
  const evidenceRoot = resolve(repositoryRoot, "docs/audits/evidence");
  const reportRoot = resolve(repositoryRoot, "docs/audits/reports");
  const reports = walk(reportRoot, (absolute) => absolute.endsWith(".md")).map(readText).join("\n");
  const pngs = walk(evidenceRoot, (absolute) => /frontend-mvp-imp-.*\.png$/.test(absolute.replace(/\\/g, "/")));

  assert.equal(pngs.length, 50, "IMP-302 espera 50 PNGs de evidencia frontend");
  for (const absolute of pngs) {
    const relativePath = relative(repositoryRoot, absolute).replace(/\\/g, "/");
    const { width, height, bytes } = readPngDimensions(absolute);
    if (relativePath.includes("desktop")) {
      assert.ok(width >= 1440, `${relativePath}: largura desktop cobre viewport`);
      assert.ok(height >= 900, `${relativePath}: altura desktop cobre viewport`);
    }
    if (relativePath.includes("mobile")) {
      assert.ok(width >= 390, `${relativePath}: largura mobile cobre viewport`);
      assert.ok(height >= 844, `${relativePath}: altura mobile cobre viewport`);
    }
    const sha = crypto.createHash("sha256").update(bytes).digest("hex");
    assert.ok(reports.includes(sha), `${relativePath}: SHA vigente ausente dos relatorios`);
  }
}

function certifyPublicBundle() {
  const staticRoot = resolve(frontendRoot, ".next/static");
  assert.ok(existsSync(staticRoot), ".next/static ausente; execute npm run build antes de test:certification");
  const bundleFiles = walk(staticRoot, (absolute) => /\.(?:js|css|html|txt|map)$/.test(absolute));
  const secretPatterns = [
    ["access_token", /access_token/i],
    ["refresh_token", /refresh_token/i],
    ["FRONTEND_BACKEND_URL", /FRONTEND_BACKEND_URL/],
    ["FRONTEND_SESSION_KEY", /FRONTEND_SESSION_KEY/],
    ["Authorization", /\bAuthorization\b/],
    ["Bearer", /\bBearer\b/],
    ["localStorage", /\blocalStorage\b/],
    ["sessionStorage", /\bsessionStorage\b/],
    ["document.cookie", /document\.cookie/],
  ];
  failOnPattern(bundleFiles, secretPatterns, "bundle publico nao pode conter tokens, segredos ou storage sensivel");
}

function certifyClientBoundaries() {
  const sourceFiles = walk(resolve(frontendRoot, "src"), (absolute) => /\.(?:ts|tsx|js|jsx|css)$/.test(absolute));
  const clientFiles = sourceFiles.filter((absolute) => readText(absolute).includes('"use client"') || readText(absolute).includes("'use client'"));
  assert.ok(clientFiles.length >= 1, "certificacao deve observar Client Components reais");
  const clientForbidden = [
    ["FRONTEND_BACKEND_URL", /FRONTEND_BACKEND_URL/],
    ["Authorization", /\bAuthorization\b/],
    ["Bearer", /\bBearer\b/],
    ["access_token", /access_token/i],
    ["refresh_token", /refresh_token/i],
    ["localStorage", /\blocalStorage\b/],
    ["sessionStorage", /\bsessionStorage\b/],
    ["document.cookie", /document\.cookie/],
    ["direct backend fetch", /fetch\(\s*["'](?:https?:\/\/|\/(?:credit|iam|platform)\b)/],
  ];
  failOnPattern(clientFiles, clientForbidden, "Client Components nao podem acessar backend direto nem material sensivel");
}

function certifyWebInterfaceGuidelines() {
  // Web Interface Guidelines: controles nativos, foco visivel, sem zoom lock,
  // sem handlers em elementos nao interativos, sem transicao universal.
  const files = walk(resolve(frontendRoot, "src"), (absolute) => /\.(?:tsx|css)$/.test(absolute));
  const guidelinePatterns = [
    ["transition: all", /transition\s*:\s*all\b/i],
    ["outline-none", /\boutline-none\b|outline\s*:\s*none\b/i],
    ["<div onClick", /<div[^>]*\bonClick=/i],
    ["<span onClick", /<span[^>]*\bonClick=/i],
    ["user-scalable=no", /user-scalable\s*=\s*no/i],
    ["maximum-scale=1", /maximum-scale\s*=\s*1/i],
    ["autoFocus", /\bautoFocus\b/],
    ["img sem alt", /<img\b(?![^>]*\balt=)/i],
  ];
  failOnPattern(files, guidelinePatterns, "Web Interface Guidelines violadas");
}

function certifyNoFinancialEngineParallel() {
  const files = walk(resolve(frontendRoot, "src"), (absolute) =>
    /\.(?:ts|tsx)$/.test(absolute) && !absolute.replace(/\\/g, "/").endsWith("openapi.generated.ts")
  );
  const financePattern = [
    ["reduce financeiro", /\.reduce\(/],
    ["parseFloat financeiro", /parseFloat\(/],
    ["parseInt financeiro", /parseInt\(/],
    ["toFixed financeiro", /toFixed\(/],
    ["soma de valor financeiro", /\+\s*(?:principal|juros|mora|multa|saldo|valor)|(?:principal|juros|mora|multa|saldo|valor)\s*\+/i],
  ];
  failOnPattern(files, financePattern, "frontend nao pode implementar Motor/calculo financeiro paralelo");
}

certifyVisualEvidence();
certifyPublicBundle();
certifyClientBoundaries();
certifyWebInterfaceGuidelines();
certifyNoFinancialEngineParallel();

console.log("IMP-302 certification: 50 PNGs, bundle publico, Client Components, Web Interface Guidelines e anti-calculo verificados.");
