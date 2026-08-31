#!/usr/bin/env node
'use strict';

// Guardrail da ADR-003 — escopo single-tenant do v1.
//
// Existe porque a decisao "um Credor, um Tenant, um usuario" viveu meses apenas
// num handoff, enquanto o FOUNDATION-006 dizia, com status Aprovado, que a
// plataforma atendia varios Credores simultaneamente. Toda sessao que lia o
// canonico reabria a questao, e o fundador precisou repetir a mesma decisao
// varias vezes.
//
// Este teste verifica que a decisao continua declarada nos tres documentos que
// governam o tema, e que a afirmacao de escopo multi-tenant nao reaparece em
// documento canonico.
//
// A distincao que este guardrail respeita:
//   - multi-tenant como MECANISMO (escopo por tenant_id, barrar acesso
//     cross-tenant) -> correto, permanece, NAO e verificado aqui;
//   - multi-tenant como ESCOPO DE PRODUTO (atender varios Credores) -> revogado.

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8').replace(/\r\n/g, '\n');

const FILES = {
  adr: 'docs/architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md',
  foundation: 'docs/foundation/FOUNDATION-006-arquitetura-multi-tenant.md',
  amp: 'docs/architecture/amp/AMP-001-architecture-master-plan.md',
};

// Diretorios canonicos: onde escopo de produto e declarado. `audits/` e
// `handoffs/` ficam de fora de proposito — sao registro historico, e devem
// poder descrever o que se pensava na epoca.
const DIRETORIOS_CANONICOS = [
  'docs/foundation',
  'docs/architecture',
  'docs/product',
  'docs/implementation/plans',
  'docs/implementation/backlogs',
];

// A afirmacao de escopo, nao o mecanismo. Hoje ha zero ocorrencias no repo.
const AFIRMACAO_DE_ESCOPO =
  /(m[uú]ltipl[oa]s|v[aá]rios|diversos)\s+(credores|organiza[cç][oõ]es|empresas|clientes)\s+de\s+forma\s+simult/i;

const docs = Object.fromEntries(Object.entries(FILES).map(([k, rel]) => [k, read(rel)]));

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

function listarMarkdown(dir) {
  const absoluto = path.join(ROOT, dir);
  if (!fs.existsSync(absoluto)) return [];
  const saida = [];
  for (const entrada of fs.readdirSync(absoluto, { withFileTypes: true })) {
    const rel = `${dir}/${entrada.name}`;
    if (entrada.isDirectory()) saida.push(...listarMarkdown(rel));
    else if (entrada.name.endsWith('.md')) saida.push(rel);
  }
  return saida;
}

test('ADR-003 existe, esta Aceita e declara o escopo single-tenant', () => {
  assert.match(docs.adr, /\*\*Status:\*\*\s*Aceito/);
  assert.match(docs.adr, /um Credor.*um Tenant.*um usu[aá]rio/i);
});

test('ADR-003 preserva tenant_id como invariante estrutural', () => {
  // Sem isto, alguem le "nao e multi-tenant" e comeca a apagar coluna.
  assert.ok(
    /N[AÃ]O (remove|faz)/i.test(docs.adr) && /tenant_id/.test(docs.adr),
    'a ADR precisa dizer explicitamente que tenant_id permanece',
  );
});

test('FOUNDATION-006 declara escopo suspenso e aponta para a ADR-003', () => {
  assert.match(docs.foundation, /SUSPENSO no v1/i);
  assert.ok(
    docs.foundation.includes('ADR-003-escopo-single-tenant-do-v1.md'),
    'FOUNDATION-006 deve linkar a ADR que o suspendeu',
  );
});

test('AMP-001 marca a reserva ADR-003 como emitida', () => {
  assert.match(docs.amp, /~~\*\*ADR-003\*\*~~/);
  assert.match(docs.amp, /\*\*EMITIDA em 31\/08\/2026\*\*/);
});

test('AMP-001 nao trata multi-tenant como roadmap nem como divida a pagar', () => {
  assert.ok(
    !/^- Crit[eé]rios para ADR-003 \(evolu[cç][aã]o do multi-tenant\) definidos/m.test(docs.amp),
    'o marco de roadmap da ADR-003 deve ter saido',
  );
  assert.ok(
    !/^\| Multi-tenant N[ií]vel 1 \| MVP valida/m.test(docs.amp),
    '"Multi-tenant Nivel 1" nao pode seguir listado como divida a pagar',
  );
});

test('nenhum documento canonico afirma escopo multi-tenant de produto', () => {
  const infratores = [];
  for (const dir of DIRETORIOS_CANONICOS) {
    for (const rel of listarMarkdown(dir)) {
      // A propria ADR-003 cita a afirmacao que revoga, na tabela de contexto.
      // Citar para revogar e o trabalho dela, nao uma reincidencia.
      if (rel === FILES.adr) continue;
      const conteudo = read(rel);
      for (const [i, linha] of conteudo.split('\n').entries()) {
        // A nota da propria ADR-003 cita a afirmacao para revoga-la.
        if (/ADR-003|SUSPENSO|revogad|deixou de ser/i.test(linha)) continue;
        if (AFIRMACAO_DE_ESCOPO.test(linha)) infratores.push(`${rel}:${i + 1}: ${linha.trim()}`);
      }
    }
  }
  assert.strictEqual(
    infratores.length,
    0,
    `escopo multi-tenant reafirmado em documento canonico (ver ADR-003):\n${infratores.join('\n')}`,
  );
});

function run() {
  let failures = 0;
  console.log('test-adr-003-single-tenant');
  console.log('='.repeat(50));
  for (const item of cases) {
    try {
      item.fn();
      console.log(`  [PASS] ${item.name}`);
    } catch (error) {
      failures += 1;
      console.log(`  [FAIL] ${item.name}`);
      console.log(`         ${error.message}`);
    }
  }
  console.log('='.repeat(50));
  console.log(`Resumo: ${cases.length - failures}/${cases.length} teste(s) passaram.`);
  return failures;
}

if (require.main === module) process.exit(run() ? 1 : 0);

module.exports = { FILES, docs, run };
