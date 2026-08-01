#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DOCS = path.join(ROOT, 'docs');
const EXCLUDED_DIRS = new Set(['templates', 'handoffs', 'assets']);

const LAYERS = {
  foundation: {
    idPattern: /^FOUNDATION-\d+/i,
    headerRequired: ['Versao', 'Status'],
  },
  domain: {
    idPattern: /^(DOMAIN|ENT|VO|DSVC|EVT|BR)-\d+/i,
    headerRequired: ['Versão', 'Status'],
  },
  product: {
    idPattern: /^(EPIC|FEAT|US)-\d+/i,
    headerRequired: ['Status'],
  },
  decisions: {
    idPattern: /^ADR-\d+/i,
    headerRequired: ['Status'],
  },
  architecture: {
    idPattern: null,
    headerRequired: ['Versão', 'Status'],
  },
};

const DOMAIN_TEMPLATES = {
  aggregates: 'templates/aggregate-template.md',
  entities: 'templates/entity-template.md',
  'value-objects': 'templates/value-object-template.md',
  services: 'templates/domain-service-template.md',
  events: 'templates/domain-event-template.md',
  rules: 'templates/business-rule-template.md',
};

const PRODUCT_TEMPLATES = {
  EPIC: 'templates/epic-template.md',
  FEAT: 'templates/feature-template.md',
  US: 'templates/user-story-template.md',
};

const results = { errors: [], warnings: [], ok: [] };

const rel = (p) => path.relative(ROOT, p).replace(/\\/g, '/');
const norm = (s) => s.replace(/\s+/g, ' ').trim();
const strip = (s) => s.normalize('NFD').replace(/[\u0300-\u036f]/g, '');

function walk(dir) {
  const out = [];
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      out.push(...walk(p));
    } else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) {
      out.push(p);
    }
  }
  return out;
}

function sectionsOf(file) {
  const set = new Set();
  for (const line of fs.readFileSync(file, 'utf8').split(/\r?\n/)) {
    const m = line.match(/^#{1,2}\s+\d+(?:\.\d+)?\.\s+(.+?)\s*$/);
    if (m) set.add(norm(m[1]));
  }
  return set;
}

function idOf(lines) {
  for (const line of lines) {
    const m = line.match(/^#\s+((?:FOUNDATION|DOMAIN|ENT|VO|DSVC|EVT|BR|EPIC|FEAT|US|ADR)-\d+)\b/i);
    if (m) return m[1];
  }
  return null;
}

function hasSection(lines, re) {
  return lines.some((l) => re.test(l));
}

function templateFor(layerName, id, file) {
  if (layerName === 'foundation') return 'templates/foundation-template.md';
  if (layerName === 'decisions') return 'templates/adr-template.md';
  if (layerName === 'domain') {
    const sub = path.basename(path.dirname(file));
    return DOMAIN_TEMPLATES[sub] || null;
  }
  if (layerName === 'product') {
    const m = id && id.match(/^(EPIC|FEAT|US)-/i);
    return m ? PRODUCT_TEMPLATES[m[1].toUpperCase()] : null;
  }
  return null;
}

function validateDoc(file, layerName, layer) {
  const txt = fs.readFileSync(file, 'utf8');
  const lines = txt.split(/\r?\n/);
  const id = idOf(lines);
  const rp = rel(file);

  if (layer.idPattern) {
    if (!id) {
      results.errors.push(`${rp}: ID obrigatório ausente — padrão esperado: ${layer.idPattern}`);
    } else if (!layer.idPattern.test(id)) {
      results.errors.push(`${rp}: ID inválido "${id}" — padrão esperado: ${layer.idPattern}`);
    }
  }

  for (const h of layer.headerRequired || []) {
    if (!lines.some((l) => strip(l).includes(`**${strip(h)}:**`))) {
      results.errors.push(`${rp}: campo de cabeçalho "${h}" ausente`);
    }
  }

  if (!hasSection(lines, /^#{1,2}\s+(\d+\.\s+)?hist[óo]rico\s+de\s+vers[õo]es/i)) {
    results.errors.push(`${rp}: seção "Histórico de Versões" ausente`);
  }

  const tpl = templateFor(layerName, id, file);
  if (tpl) {
    const tplPath = path.join(DOCS, tpl);
    if (!fs.existsSync(tplPath)) {
      results.warnings.push(`${rp}: template ${tpl} não encontrado — checagem de seções ignorada`);
    } else {
      const tplSections = sectionsOf(tplPath);
      const docSections = sectionsOf(file);
      const extra = [...docSections].filter((s) => !tplSections.has(s));
      if (extra.length) {
        results.errors.push(`${rp}: seções fora do template (${tpl}): ${extra.join(', ')}`);
      }
    }
  }

  results.ok.push(`${rp} — ${id || 'sem ID'}`);
}

function brokenLinks(file) {
  const txt = fs.readFileSync(file, 'utf8');
  const re = /\]\(([^)]+)\)/g;
  let m;
  while ((m = re.exec(txt))) {
    const target = m[1].trim();
    if (/^[a-zA-Z][a-zA-Z0-9+.-]*:/.test(target)) continue;
    if (target.startsWith('#')) continue;
    const clean = target.split('#')[0];
    if (!clean) continue;
    const resolved = path.resolve(path.dirname(file), clean);
    if (!fs.existsSync(resolved)) {
      results.errors.push(`${rel(file)}: link quebrado -> ${target}`);
    }
  }
}

function main() {
  const knownIds = new Map();

  for (const layerName of Object.keys(LAYERS)) {
    const dir = path.join(DOCS, layerName);
    if (!fs.existsSync(dir)) continue;
    const files = walk(dir).sort();
    for (const f of files) {
      const id = idOf(fs.readFileSync(f, 'utf8').split(/\r?\n/));
      if (id) {
        const key = id.toUpperCase();
        if (knownIds.has(key)) {
          results.errors.push(`ID duplicado ${id} em ${rel(f)} (também em ${knownIds.get(key)})`);
        } else {
          knownIds.set(key, rel(f));
        }
      }
      validateDoc(f, layerName, LAYERS[layerName]);
    }
  }

  const knownSet = new Set(knownIds.keys());

  for (const entry of fs.readdirSync(DOCS, { withFileTypes: true })) {
    if (!entry.isDirectory() || EXCLUDED_DIRS.has(entry.name)) continue;
    for (const f of walk(path.join(DOCS, entry.name))) {
      brokenLinks(f);
    }
  }

  for (const layerName of ['product']) {
    const dir = path.join(DOCS, layerName);
    if (!fs.existsSync(dir)) continue;
    for (const f of walk(dir)) {
      const txt = fs.readFileSync(f, 'utf8');
      const id = idOf(txt.split(/\r?\n/));
      const re = /(?:FOUNDATION|EPIC|FEAT|US|DOMAIN|ENT|VO|DSVC|EVT|BR|ADR)-\d{2,}/g;
      const seen = new Set();
      let m;
      while ((m = re.exec(txt))) {
        const ref = m[0].toUpperCase();
        if (!id || ref === id.toUpperCase()) continue;
        if (seen.has(ref)) continue;
        seen.add(ref);
        if (!knownSet.has(ref)) {
          results.warnings.push(`${rel(f)}: referência cruzada para ID desconhecido ${m[0]} (pode ser planejamento futuro)`);
        }
      }
    }
  }

  const print = results.ok.length + results.warnings.length + results.errors.length > 0;
  console.log('docs:validate — Validação da documentação');
  console.log('='.repeat(50));
  for (const m of [...results.ok].sort()) console.log(`  [OK]    ${m}`);
  for (const m of [...results.warnings].sort()) console.log(`  [AVISO] ${m}`);
  for (const m of [...results.errors].sort()) console.log(`  [ERRO]  ${m}`);
  console.log('='.repeat(50));
  console.log(`Resumo: ${results.ok.length} verificação(ões) OK, ${results.warnings.length} aviso(s), ${results.errors.length} erro(s).`);
  if (!print) console.log('  (nenhum documento encontrado para validar)');

  process.exit(results.errors.length ? 1 : 0);
}

main();
