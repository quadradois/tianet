#!/usr/bin/env node
'use strict';

const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..');
const DOCS = path.join(ROOT, 'docs');

// Pastas que não precisam de validação estruturada (apenas links quebrados).
const FREE_DIRS = new Set(['templates', 'assets', 'ux']);

// Camadas reconhecidas. Cada camada pode ter subcategorias.
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
    idPattern: /^(PRODUCT|EPIC|FEAT(?:URE)?|US)-\d+/i,
    headerRequired: ['Status'],
  },
  architecture: {
    subcategories: {
      adrs: {
        idPattern: /^ADR-\d+/i,
        headerRequired: ['Status'],
      },
      amp: {
        idPattern: null,
        headerRequired: ['Versão', 'Status'],
      },
      reviews: {
        idPattern: null,
        headerRequired: ['Versão', 'Status'],
      },
    },
  },
  implementation: {
    idPattern: /^PLAN-\d+/i,
    headerRequired: [],
  },
  governance: {
    idPattern: null,
    headerRequired: [],
  },
  audits: {
    idPattern: null,
    headerRequired: [],
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
  FEATURE: 'templates/feature-template.md',
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
    const m = line.match(/^#\s+((?:FOUNDATION|DOMAIN|ENT|VO|DSVC|EVT|BR|PRODUCT|EPIC|FEAT(?:URE)?|US|ADR|PLAN)-\d+)\b/i);
    if (m) return m[1];
  }
  return null;
}

function hasSection(lines, re) {
  return lines.some((l) => re.test(l));
}

function skipIdRegistration(file) {
  const rp = rel(file);
  return rp.startsWith('docs/audits/discoveries/') || rp.startsWith('docs/implementation/backlogs/');
}

function skipHistorySection(layerName) {
  return layerName === 'governance' || layerName === 'audits';
}

function templateFor(layerName, subcategory, id, file) {
  if (layerName === 'foundation') return 'templates/foundation-template.md';
  if (layerName === 'architecture' && subcategory === 'adrs') return 'templates/adr-template.md';
  if (layerName === 'domain') {
    const sub = path.basename(path.dirname(file));
    return DOMAIN_TEMPLATES[sub] || null;
  }
  if (layerName === 'product') {
    const m = id && id.match(/^(EPIC|FEAT(?:URE)?|US)-/i);
    return m ? PRODUCT_TEMPLATES[m[1].toUpperCase()] : null;
  }
  return null;
}

function validateDoc(file, layerName, subcategory, layer) {
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

  if (!skipHistorySection(layerName) && !hasSection(lines, /^#{1,2}\s+(\d+\.\s+)?hist[óo]rico\s+de\s+vers[õo]es/i)) {
    results.errors.push(`${rp}: seção "Histórico de Versões" ausente`);
  }

  const isMaterialized = lines.some((l) => /^\*\*Status:\*\*\s*Aprovado\s*$/i.test(strip(l)));
  const tpl = templateFor(layerName, subcategory, id, file);
  if (tpl && !isMaterialized) {
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

function getLayer(file) {
  const parts = rel(file).split('/');
  // parts[0] === 'docs'
  const layerName = parts[1];
  if (!LAYERS[layerName]) return null;

  const layer = LAYERS[layerName];
  if (layer.subcategories) {
    const subcategory = parts[2];
    if (layer.subcategories[subcategory]) {
      return { layerName, subcategory, layer: layer.subcategories[subcategory] };
    }
  }
  return { layerName, subcategory: null, layer };
}

function main() {
  const knownIds = new Map();

  // Validar documentos estruturados.
  for (const layerName of Object.keys(LAYERS)) {
    const dir = path.join(DOCS, layerName);
    if (!fs.existsSync(dir)) continue;
    const files = walk(dir).sort();
    for (const f of files) {
      const info = getLayer(f);
      if (!info) continue;

      const id = idOf(fs.readFileSync(f, 'utf8').split(/\r?\n/));
      if (id && !skipIdRegistration(f)) {
        const key = id.toUpperCase();
        if (knownIds.has(key)) {
          results.errors.push(`ID duplicado ${id} em ${rel(f)} (também em ${knownIds.get(key)})`);
        } else {
          knownIds.set(key, rel(f));
        }
      }
      validateDoc(f, info.layerName, info.subcategory, info.layer);
    }
  }

  const knownSet = new Set(knownIds.keys());

  // Verificar links quebrados em toda a documentação (exceto templates/assets/ux).
  for (const entry of fs.readdirSync(DOCS, { withFileTypes: true })) {
    if (!entry.isDirectory() || FREE_DIRS.has(entry.name)) continue;
    for (const f of walk(path.join(DOCS, entry.name))) {
      brokenLinks(f);
    }
  }

  // Verificar referências cruzadas em product, implementation, audits e governance.
  const crossRefLayers = ['product', 'implementation', 'audits', 'governance'];
  for (const layerName of crossRefLayers) {
    const dir = path.join(DOCS, layerName);
    if (!fs.existsSync(dir)) continue;
    for (const f of walk(dir)) {
      const txt = fs.readFileSync(f, 'utf8');
      const id = idOf(txt.split(/\r?\n/));
      const re = /(?:FOUNDATION|PRODUCT|EPIC|FEAT(?:URE)?|US|DOMAIN|ENT|VO|DSVC|EVT|BR|ADR|PLAN)-\d{2,}/g;
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

  // Validações de higiene da migração.
  if (fs.existsSync(path.join(DOCS, 'handoffs', 'HANDOFF-VIGENTE.md'))) {
    results.errors.push('docs/handoffs/HANDOFF-VIGENTE.md ainda existe (deve ser removido do repo)');
  }
  if (fs.existsSync(path.join(DOCS, 'implementationplans'))) {
    results.errors.push('docs/implementationplans/ ainda existe (deve ser removido)');
  }
  if (fs.existsSync(path.join(DOCS, 'implementation', 'plansPLAN-002-epic-001-tenant-management.md'))) {
    results.errors.push('docs/implementation/plansPLAN-002-epic-001-tenant-management.md ainda existe (deve ser removido)');
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
