#!/usr/bin/env node
'use strict';

/**
 * Testes da família Identifiers (SPEC-002 CB-008).
 *
 *     node scripts/tests/test-identifiers.js
 *
 * Sem framework — assert e execução direta, como em test-validator.js: o
 * validador roda no pre-commit e não deve arrastar dependências.
 */

const assert = require('assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { execFileSync } = require('child_process');
const { pathToFileURL } = require('url');

const {
  verificarIdentificadores,
  carregarRegistry,
  validarDefinicaoSchema,
  validarJsonSchema,
  coletarIds,
  idDoTitulo,
  carregarBaselineGit,
  validarHistorico,
  REGISTRY_REL,
} = require('../identifier-check.js');

const RAIZ = path.resolve(__dirname, '..', '..');

const casos = [];
const teste = (nome, fn) => casos.push({ nome, fn });

/**
 * Monta um repositório mínimo em diretório temporário: um Registry e os
 * documentos informados. Permite exercitar cada regra isoladamente, sem
 * depender do estado do repositório real.
 */
function repoTemporario(registry, documentos) {
  const base = fs.mkdtempSync(path.join(os.tmpdir(), 'idcheck-'));
  const dirReg = path.join(base, path.dirname(REGISTRY_REL));
  fs.mkdirSync(dirReg, { recursive: true });
  const registryCompleto = {
    $schema: './identifier-registry.schema.json',
    versao: 'test',
    atualizadoEm: '2026-08-10',
    normativo: true,
    ...registry,
  };
  fs.writeFileSync(path.join(base, REGISTRY_REL), JSON.stringify(registryCompleto, null, 2));
  fs.copyFileSync(
    path.join(RAIZ, 'docs', 'governance', 'registry', 'identifier-registry.schema.json'),
    path.join(dirReg, 'identifier-registry.schema.json')
  );
  for (const [rel, conteudo] of Object.entries(documentos)) {
    const abs = path.join(base, rel);
    fs.mkdirSync(path.dirname(abs), { recursive: true });
    fs.writeFileSync(abs, conteudo);
  }
  return base;
}

function rodar(registry, documentos) {
  const base = repoTemporario(registry, documentos);
  const res = { errors: [], warnings: [], ok: [] };
  try {
    verificarIdentificadores({ root: base, results: res, baseline: null });
  } finally {
    fs.rmSync(base, { recursive: true, force: true });
  }
  return res;
}

function assertSemErros(res) {
  assert.strictEqual(res.errors.length, 0, res.errors.join('\n'));
}

function git(root, args) {
  return execFileSync('git', args, { cwd: root, encoding: 'utf8' }).trim();
}

function iniciarGit(root) {
  git(root, ['init']);
  git(root, ['config', 'user.email', 'identifier-tests@example.invalid']);
  git(root, ['config', 'user.name', 'Identifier Tests']);
}

function commitTudo(root, mensagem) {
  git(root, ['add', '.']);
  git(root, ['commit', '-m', mensagem]);
  return git(root, ['rev-parse', 'HEAD']);
}

const NS_BASE = {
  namespaces: {
    ADR: {
      prefixo: 'ADR', nome: 'Architectural Decision Record', classe: 'DOCUMENT',
      governadoPor: 'AMP-001', regraNumeracao: 'AMP', status: 'ACTIVE',
      validador: 'docs:validate/identifiers',
    },
    TASK: {
      prefixo: 'TASK', nome: 'Unidade operacional', classe: 'OPERATIONAL',
      governadoPor: 'git', regraNumeracao: 'max+1', status: 'ACTIVE',
      validador: 'docs:validate/identifiers',
    },
    DECISION: {
      prefixo: 'DECISION', nome: 'Nomenclatura anterior a ADR', classe: 'DOCUMENT',
      governadoPor: '—', regraNumeracao: 'nao emitir', status: 'LEGACY',
      sucessor: 'ADR', validador: 'docs:validate/identifiers',
    },
    US: {
      prefixo: 'US', nome: 'User Story', classe: 'DOCUMENT',
      governadoPor: 'sequencial', regraNumeracao: 'ultimo + 1', status: 'ACTIVE',
      ultimo: 0, validador: 'docs:validate/identifiers',
    },
  },
};

// --- Unidades ---------------------------------------------------------------

teste('coletarIds agrupa por namespace', () => {
  const ids = coletarIds('Ver ADR-018 e ADR-002, além de TASK-097.');
  assert.deepStrictEqual([...ids.get('ADR')].sort(), ['ADR-002', 'ADR-018']);
  assert.deepStrictEqual([...ids.get('TASK')], ['TASK-097']);
});

teste('coletarIds ignora siglas técnicas que casam a gramática', () => {
  const ids = coletarIds('Codificado em UTF-8 conforme RFC-123.');
  assert.ok(!ids.has('UTF'), 'UTF-8 não é identificador de governança');
  assert.ok(!ids.has('RFC'));
});

teste('idDoTitulo lê o ID emitido pelo documento', () => {
  assert.deepStrictEqual(idDoTitulo('# ADR-018: Identidade externa\n\ntexto'), {
    ns: 'ADR', numero: 18, id: 'ADR-018',
  });
});

teste('idDoTitulo devolve null quando o H1 não traz ID', () => {
  assert.strictEqual(idDoTitulo('# Relatório de alinhamento\n\ntexto'), null);
});

teste('carregarRegistry devolve null quando o arquivo não existe', () => {
  assert.strictEqual(carregarRegistry(os.tmpdir()), null);
});

// --- CB-002: namespace inexistente ------------------------------------------

teste('CB-002: namespace ausente do Registry é ERRO (regra 5.2)', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nVer XPTO-001.' });
  assert.ok(
    res.errors.some((e) => e.includes('XPTO') && e.includes('ausente do Registry')),
    'esperava erro de namespace desconhecido, obtive:\n' + res.errors.join('\n')
  );
});

teste('CB-002: namespace registrado não gera erro', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nVer TASK-097.' });
  assertSemErros(res);
});

// --- CB-003: emissão em namespace LEGACY ------------------------------------

teste('CB-003: emitir novo ID em namespace LEGACY é ERRO (regra 5.3)', () => {
  const res = rodar(NS_BASE, { 'docs/nova.md': '# DECISION-002: nova decisão\n\ntexto' });
  assert.ok(
    res.errors.some((e) => e.includes('DECISION-002') && e.includes('LEGACY')),
    'esperava erro de emissão em LEGACY, obtive:\n' + res.errors.join('\n')
  );
});

teste('CB-003: o erro aponta o namespace sucessor', () => {
  const res = rodar(NS_BASE, { 'docs/nova.md': '# DECISION-002: nova\n\ntexto' });
  assert.ok(res.errors.some((e) => e.includes('ADR')), 'a mensagem deve indicar o sucessor');
});

// --- CB-004: qualificador não é colisão (AC-003) ----------------------------

teste('CB-004: TASK-092 e TASK-092-A convivem sem erro', () => {
  const res = rodar(NS_BASE, {
    'docs/x.md': '# ADR-018: ok\n\nVer TASK-092, TASK-092-A e TASK-092-B.',
  });
  assertSemErros(res);
});

teste('CB-004: o qualificador não vira namespace novo', () => {
  const ids = coletarIds('TASK-049-fix concluída');
  assert.deepStrictEqual([...ids.keys()], ['TASK']);
  assert.deepStrictEqual([...ids.get('TASK')], ['TASK-049-fix']);
});

// --- CB-005: LEGACY referenciado é aviso ------------------------------------

teste('CB-005: citar DECISION-001 existente gera AVISO, não erro', () => {
  const res = rodar(NS_BASE, {
    'docs/x.md': '# ADR-018: ok\n\nRegistro oficial da DECISION-001 — stack.',
  });
  assertSemErros(res);
  assert.ok(
    res.warnings.some((w) => w.includes('LEGACY') && w.includes('DECISION')),
    'esperava aviso de LEGACY referenciado'
  );
});

// --- Regras 5.4, 5.6, 5.7 ---------------------------------------------------

teste('regra 5.4: número com menos de 3 dígitos gera aviso', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nVer ADR-1 antiga.' });
  assert.ok(res.warnings.some((w) => w.includes('gramática') && w.includes('ADR-1')));
});

teste('regra 5.4: padrão glob (DOMAIN-02*) não é tratado como identificador', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      DOMAIN: {
        prefixo: 'DOMAIN', nome: 'Dominio', classe: 'DOCUMENT',
        governadoPor: 'sequencial', regraNumeracao: 'ultimo + 1', status: 'ACTIVE',
        ultimo: 0,
        validador: 'docs:validate/identifiers',
      },
    },
  };
  const res = rodar(registry, { 'docs/x.md': '# ADR-018: ok\n\nArquivos `DOMAIN-02*.md`.' });
  assertSemErros(res);
  assert.ok(
    !res.warnings.some((w) => w.includes('gramática')),
    'glob não deve gerar aviso de gramática: ' + res.warnings.join('\n')
  );
});

teste('regra 5.6: namespace registrado e não usado gera aviso', () => {
  const res = rodar(NS_BASE, { 'docs/x.md': '# ADR-018: ok\n\nsem outras citações' });
  assert.ok(res.warnings.some((w) => w.includes('nenhum documento utiliza')));
});

teste('regra 5.7: buraco na sequência de namespace sequencial gera aviso', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      US: { ...NS_BASE.namespaces.US, ultimo: 3 },
    },
  };
  const res = rodar(registry, {
    'docs/a.md': '# US-001: primeira\n\ntexto',
    'docs/c.md': '# US-003: terceira\n\ntexto',
  });
  assertSemErros(res);
  assert.ok(
    res.warnings.some((w) => w.includes('US') && w.includes('002')),
    'esperava aviso do número 002 ausente'
  );
});

teste('regra 5.7 não se aplica a namespace governado pelo Git', () => {
  const res = rodar(NS_BASE, {
    'docs/a.md': '# TASK-001: primeira\n\ntexto',
    'docs/c.md': '# TASK-099: nonagésima nona\n\ntexto',
  });
  assert.ok(
    !res.warnings.some((w) => w.startsWith('TASK:') && w.includes('ausente na sequência')),
    'TASK é governada pelo Git (DA-098-001), não pela sequência de documentos'
  );
});

teste('regra 5.8: ultimo abaixo do maior ID emitido gera erro', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      US: { ...NS_BASE.namespaces.US, ultimo: 1 },
    },
  };
  const res = rodar(registry, { 'docs/us.md': '# US-002: segunda\n\ntexto' });
  assert.ok(
    res.errors.some(
      (e) => e.includes('US') && e.includes('ultimo=001') && e.includes('vivo=002')
    ),
    'esperava erro de contador defasado, obtive:\n' + res.errors.join('\n')
  );
});

teste('regra 5.8: ultimo ausente em namespace sequencial gera erro', () => {
  const us = { ...NS_BASE.namespaces.US };
  delete us.ultimo;
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      US: us,
    },
  };
  const res = rodar(registry, { 'docs/us.md': '# US-002: segunda\n\ntexto' });
  assert.ok(
    res.errors.some(
      (e) => e.includes('US') && e.includes('ultimo=ausente') && e.includes('inteiro nao negativo')
    ),
    'esperava erro de contador ausente, obtive:\n' + res.errors.join('\n')
  );
});

teste('regra 5.8: ultimo nao inteiro em namespace sequencial gera erro', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      US: { ...NS_BASE.namespaces.US, ultimo: '2' },
    },
  };
  const res = rodar(registry, { 'docs/us.md': '# US-002: segunda\n\ntexto' });
  assert.ok(
    res.errors.some(
      (e) => e.includes('US') && e.includes('ultimo="2"') && e.includes('inteiro nao negativo')
    ),
    'esperava erro de contador nao inteiro, obtive:\n' + res.errors.join('\n')
  );
});

teste('regra 5.8: ultimo negativo em namespace sequencial gera erro', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      US: { ...NS_BASE.namespaces.US, ultimo: -1 },
    },
  };
  const res = rodar(registry, {});
  assert.ok(
    res.errors.some(
      (e) => e.includes('US') && e.includes('ultimo=-1') && e.includes('inteiro nao negativo')
    ),
    'esperava erro de contador negativo, obtive:\n' + res.errors.join('\n')
  );
});

teste('regra 5.8: ultimo acima do maior ID vivo preserva emissao historica', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      US: { ...NS_BASE.namespaces.US, ultimo: 3 },
    },
  };
  const res = rodar(registry, { 'docs/us.md': '# US-002: segunda\n\ntexto' });
  assertSemErros(res);
  assert.strictEqual(registry.namespaces.US.ultimo + 1, 4, 'a proxima emissao nao recicla US-003');
});

teste('regra 5.9: exclusao preserva ultimo e nao gera erro', () => {
  const atual = new Map([
    ['US', [{ numero: 1 }, { numero: 2 }]],
  ]);
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: { US: { governadoPor: 'sequencial', ultimo: 3 } },
    emitidosPorNs: atual,
    baseline: {
      registry: { namespaces: { US: { governadoPor: 'sequencial', ultimo: 3 } } },
      emitidosPorNs: { US: [1, 2, 3] },
    },
    results: res,
  });
  assertSemErros(res);
});

teste('regra 5.9: proxima emissao apos exclusao usa ultimo + 1', () => {
  const atual = new Map([
    ['US', [{ numero: 1 }, { numero: 2 }, { numero: 4 }]],
  ]);
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: { US: { governadoPor: 'sequencial', ultimo: 4 } },
    emitidosPorNs: atual,
    baseline: {
      registry: { namespaces: { US: { governadoPor: 'sequencial', ultimo: 3 } } },
      emitidosPorNs: { US: [1, 2] },
      historicosPorNs: { US: [1, 2, 3] },
    },
    results: res,
  });
  assertSemErros(res);
});

teste('regra 5.9: recriar ID removido gera erro de reciclagem', () => {
  const atual = new Map([
    ['US', [{ numero: 1 }, { numero: 2 }, { numero: 3 }]],
  ]);
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: { US: { governadoPor: 'sequencial', ultimo: 3 } },
    emitidosPorNs: atual,
    baseline: {
      registry: { namespaces: { US: { governadoPor: 'sequencial', ultimo: 3 } } },
      emitidosPorNs: { US: [1, 2] },
      historicosPorNs: { US: [1, 2, 3] },
    },
    results: res,
  });
  assert.ok(res.errors.some((e) => e.includes('003') && e.includes('faixa historica')));
});

teste('regra 5.9: reduzir ultimo contra baseline gera erro', () => {
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: { US: { governadoPor: 'sequencial', ultimo: 2 } },
    emitidosPorNs: new Map([['US', [{ numero: 1 }, { numero: 2 }]]]),
    baseline: {
      registry: { namespaces: { US: { governadoPor: 'sequencial', ultimo: 3 } } },
      emitidosPorNs: { US: [1, 2] },
    },
    results: res,
  });
  assert.ok(res.errors.some((e) => e.includes('reduziu') && e.includes('baseline=003')));
});

teste('regra 5.9: materializar numero reservado e permitido', () => {
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: { EPIC: { governadoPor: 'sequencial', ultimo: 7 } },
    emitidosPorNs: new Map([['EPIC', [{ numero: 7 }]]]),
    baseline: {
      registry: { namespaces: { EPIC: { governadoPor: 'sequencial', ultimo: 7 } } },
      emitidosPorNs: { EPIC: [] },
      historicosPorNs: { EPIC: [1, 2, 3, 4, 5, 6] },
    },
    results: res,
  });
  assertSemErros(res);
});

teste('regra 5.9: remover namespace sequencial da baseline gera erro', () => {
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: {},
    emitidosPorNs: new Map(),
    baseline: {
      registry: { namespaces: { US: { governadoPor: 'sequencial', ultimo: 3 } } },
      emitidosPorNs: { US: [1, 2, 3] },
    },
    results: res,
  });
  assert.ok(res.errors.some((erro) => erro.includes('US') && erro.includes('removido')));
});

teste('regra 5.9: trocar governanca sequencial da baseline gera erro', () => {
  const res = { errors: [], warnings: [], ok: [] };
  validarHistorico({
    ns: { US: { governadoPor: 'git' } },
    emitidosPorNs: new Map(),
    baseline: {
      registry: { namespaces: { US: { governadoPor: 'sequencial', ultimo: 3 } } },
      emitidosPorNs: { US: [1, 2, 3] },
    },
    results: res,
  });
  assert.ok(res.errors.some((erro) => erro.includes('US') && erro.includes('governanca mudou')));
});

teste('regra 5.9: baseline Git indisponivel falha fechado', () => {
  assert.throws(
    () => carregarBaselineGit(RAIZ, 'ref-que-nao-existe-para-o-teste'),
    /baseline Git .* indisponivel/
  );
});

teste('regra 5.9: erro de baseline percorre o validador completo', () => {
  const anterior = process.env.IDENTIFIER_BASE_REF;
  process.env.IDENTIFIER_BASE_REF = 'ref-que-nao-existe-no-validador';
  const res = { errors: [], warnings: [], ok: [] };
  try {
    verificarIdentificadores({ root: RAIZ, results: res });
  } finally {
    if (anterior === undefined) delete process.env.IDENTIFIER_BASE_REF;
    else process.env.IDENTIFIER_BASE_REF = anterior;
  }
  assert.ok(res.errors.some((erro) => erro.includes('baseline Git') && erro.includes('indisponivel')));
});

teste('regra 5.9: historia da baseline nao inclui a branch candidata', () => {
  const registry = {
    namespaces: {
      EPIC: {
        prefixo: 'EPIC', nome: 'Epic', classe: 'DOCUMENT', governadoPor: 'sequencial',
        regraNumeracao: 'ultimo + 1', ultimo: 7, status: 'ACTIVE',
        validador: 'docs:validate/identifiers',
      },
    },
  };
  const root = repoTemporario(registry, { 'docs/README.md': '# Documentacao\n' });
  try {
    iniciarGit(root);
    const baseRef = commitTudo(root, 'baseline reserva EPIC-007');
    fs.writeFileSync(path.join(root, 'docs', 'EPIC-007.md'), '# EPIC-007 - Candidato\n');
    commitTudo(root, 'branch candidata materializa EPIC-007');

    const res = { errors: [], warnings: [], ok: [] };
    verificarIdentificadores({
      root,
      results: res,
      baseline: carregarBaselineGit(root, baseRef),
    });
    assertSemErros(res);
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

teste('regra 5.9: Git detecta ID emitido, removido e reintroduzido', () => {
  const registry = {
    namespaces: {
      US: {
        prefixo: 'US', nome: 'User Story', classe: 'DOCUMENT', governadoPor: 'sequencial',
        regraNumeracao: 'ultimo + 1', ultimo: 3, status: 'ACTIVE',
        validador: 'docs:validate/identifiers',
      },
    },
  };
  const root = repoTemporario(registry, { 'docs/US-003.md': '# US-003 - Emitida\n' });
  try {
    iniciarGit(root);
    commitTudo(root, 'emite US-003');
    fs.unlinkSync(path.join(root, 'docs', 'US-003.md'));
    const baseRef = commitTudo(root, 'remove US-003 preservando contador');
    fs.writeFileSync(path.join(root, 'docs', 'US-003.md'), '# US-003 - Reciclada\n');

    const res = { errors: [], warnings: [], ok: [] };
    verificarIdentificadores({
      root,
      results: res,
      baseline: carregarBaselineGit(root, baseRef),
    });
    assert.ok(res.errors.some((erro) => erro.includes('003') && erro.includes('faixa historica')));
  } finally {
    fs.rmSync(root, { recursive: true, force: true });
  }
});

teste('regra 5.9: repositorio raso falha fechado', () => {
  const registry = {
    namespaces: {
      US: {
        prefixo: 'US', nome: 'User Story', classe: 'DOCUMENT', governadoPor: 'sequencial',
        regraNumeracao: 'ultimo + 1', ultimo: 1, status: 'ACTIVE',
        validador: 'docs:validate/identifiers',
      },
    },
  };
  const source = repoTemporario(registry, { 'docs/US-001.md': '# US-001 - Primeira\n' });
  const parent = fs.mkdtempSync(path.join(os.tmpdir(), 'idcheck-shallow-'));
  const clone = path.join(parent, 'repo');
  try {
    iniciarGit(source);
    commitTudo(source, 'primeira emissao');
    fs.appendFileSync(path.join(source, 'docs', 'US-001.md'), '\nAtualizacao.\n');
    commitTudo(source, 'segunda revisao');
    execFileSync('git', ['clone', '--depth', '1', pathToFileURL(source).href, clone], {
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    assert.throws(() => carregarBaselineGit(clone, 'HEAD'), /historico Git raso/);
  } finally {
    fs.rmSync(source, { recursive: true, force: true });
    fs.rmSync(parent, { recursive: true, force: true });
  }
});

teste('regra 5.8 não se aplica a namespace governado pelo Git ou AMP', () => {
  const registry = {
    namespaces: {
      ...NS_BASE.namespaces,
      TASK: { ...NS_BASE.namespaces.TASK, ultimo: 1 },
      ADR: { ...NS_BASE.namespaces.ADR, ultimo: 1 },
    },
  };
  const res = rodar(registry, {
    'docs/task.md': '# TASK-999: tarefa\n\ntexto',
    'docs/adr.md': '# ADR-999: decisao\n\ntexto',
  });
  assert.ok(
    !res.errors.some((e) => e.includes('abaixo do maior ID')),
    'TASK e ADR usam fontes externas de governanca'
  );
});

// --- Registry real ----------------------------------------------------------

teste('CB-001/CB-006: o Registry real declara os campos normativos', () => {
  const reg = carregarRegistry(RAIZ);
  assert.ok(reg && !reg.__erro, 'Registry deve existir e ser JSON válido');
  const obrigatorios = ['prefixo', 'nome', 'classe', 'governadoPor', 'regraNumeracao', 'status', 'validador'];
  for (const [nome, cfg] of Object.entries(reg.namespaces)) {
    for (const campo of obrigatorios) {
      assert.ok(campo in cfg, `namespace ${nome} não declara "${campo}" (DA-098-005)`);
    }
  }
  for (const [nome, cfg] of Object.entries(reg.namespaces)) {
    if (cfg.governadoPor !== 'sequencial') continue;
    assert.ok(
      Number.isInteger(cfg.ultimo) && cfg.ultimo >= 0,
      `namespace sequencial ${nome} deve declarar ultimo inteiro nao negativo (DA-098-008)`
    );
  }
  assert.ok(Object.keys(reg.namespaces).length >= 24, 'esperava ao menos os 24 namespaces inventariados');
});

teste('o Registry real referencia um JSON Schema valido e atende ao contrato', () => {
  const reg = carregarRegistry(RAIZ);
  const schemaRel = path.join('docs', 'governance', 'registry', reg.$schema.replace('./', ''));
  const schemaAbs = path.join(RAIZ, schemaRel);
  assert.ok(fs.existsSync(schemaAbs), `schema ausente: ${schemaRel}`);
  const schema = JSON.parse(fs.readFileSync(schemaAbs, 'utf8'));
  assert.deepStrictEqual(validarDefinicaoSchema(schema), []);
  assert.deepStrictEqual(validarJsonSchema(reg, schema), []);

  const registryInvalido = JSON.parse(JSON.stringify(reg));
  registryInvalido.namespaces.US.classe = 'CLASSE_INVALIDA';
  assert.ok(validarJsonSchema(registryInvalido, schema).some((erro) => erro.includes('enum')));

  const registrySemSchema = JSON.parse(JSON.stringify(reg));
  delete registrySemSchema.$schema;
  assert.ok(validarJsonSchema(registrySemSchema, schema).some((erro) => erro.includes('$schema')));

  const registryComDataImpossivel = JSON.parse(JSON.stringify(reg));
  registryComDataImpossivel.atualizadoEm = '2026-99-99';
  assert.ok(validarJsonSchema(registryComDataImpossivel, schema).some((erro) => erro.includes('format')));

  assert.ok(validarDefinicaoSchema({ type: 'tipo-inexistente' }).length > 0);
  assert.ok(validarDefinicaoSchema({ enum: [] }).length > 0);
  assert.ok(validarDefinicaoSchema({ required: ['x', 'x'] }).length > 0);
  assert.ok(validarDefinicaoSchema({ $schema: 42 }).length > 0);
});

teste('o Registry real marca TASK como governada pelo Git (DA-098-001)', () => {
  const reg = carregarRegistry(RAIZ);
  assert.strictEqual(reg.namespaces.TASK.governadoPor, 'git');
});

teste('o Registry real delega ADR ao AMP-001 (DA-098-002)', () => {
  const reg = carregarRegistry(RAIZ);
  assert.strictEqual(reg.namespaces.ADR.governadoPor, 'AMP-001');
  assert.ok(!('ultimo' in reg.namespaces.ADR), 'o Registry não deve manter contador de ADR');
});

teste('o Registry real marca DECISION como LEGACY (DA-098-004)', () => {
  const reg = carregarRegistry(RAIZ);
  assert.strictEqual(reg.namespaces.DECISION.status, 'LEGACY');
  assert.strictEqual(reg.namespaces.DECISION.sucessor, 'ADR');
});

teste('CB-007: o repositório real passa sem erros de identificador', () => {
  const res = { errors: [], warnings: [], ok: [] };
  verificarIdentificadores({ root: RAIZ, results: res });
  assert.strictEqual(res.errors.length, 0, 'erros no repositório real:\n' + res.errors.join('\n'));
});

// --- Execução ---------------------------------------------------------------

let falhas = 0;
console.log('test-identifiers — SPEC-002');
console.log('='.repeat(50));
for (const { nome, fn } of casos) {
  try {
    fn();
    console.log(`  [PASS] ${nome}`);
  } catch (e) {
    falhas++;
    console.log(`  [FAIL] ${nome}`);
    console.log(`         ${e.message.split('\n').join('\n         ')}`);
  }
}
console.log('='.repeat(50));
console.log(`Resumo: ${casos.length - falhas}/${casos.length} teste(s) passaram.`);
process.exit(falhas ? 1 : 0);
