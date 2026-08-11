#!/usr/bin/env node
'use strict';

const assert = require('assert');
const fs = require('fs');
const path = require('path');

const ROOT = path.resolve(__dirname, '..', '..');
const read = (rel) => fs.readFileSync(path.join(ROOT, rel), 'utf8');

const FILES = {
  discovery: 'docs/audits/discoveries/EPIC-007-operacao-diaria-discovery.md',
  epic: 'docs/product/credit/epics/EPIC-007-operacao-diaria.md',
  product005: 'docs/product/credit/capabilities/PRODUCT-005-administrar-cobrancas.md',
  product006: 'docs/product/credit/capabilities/PRODUCT-006-administrar-agenda.md',
  product007: 'docs/product/credit/capabilities/PRODUCT-007-administrar-comunicacao.md',
  product008: 'docs/product/credit/capabilities/PRODUCT-008-administrar-relatorios.md',
  feature028: 'docs/product/credit/features/FEATURE-028-gerir-cobranca-manual.md',
  feature029: 'docs/product/credit/features/FEATURE-029-administrar-agenda-operacional.md',
  feature030: 'docs/product/credit/features/FEATURE-030-registrar-comunicacao-manual.md',
  feature031: 'docs/product/credit/features/FEATURE-031-consultar-relatorios-operacionais.md',
  us075: 'docs/product/credit/user-stories/US-075-consultar-fila-de-cobranca.md',
  us076: 'docs/product/credit/user-stories/US-076-registrar-acao-de-cobranca.md',
  us077: 'docs/product/credit/user-stories/US-077-registrar-promessa-de-pagamento.md',
  us078: 'docs/product/credit/user-stories/US-078-acompanhar-promessa-de-pagamento.md',
  us079: 'docs/product/credit/user-stories/US-079-consultar-agenda-operacional.md',
  us080: 'docs/product/credit/user-stories/US-080-criar-compromisso-e-lembrete.md',
  us081: 'docs/product/credit/user-stories/US-081-manter-compromisso-de-agenda.md',
  us082: 'docs/product/credit/user-stories/US-082-registrar-comunicacao-manual.md',
  us083: 'docs/product/credit/user-stories/US-083-consultar-historico-de-comunicacao.md',
  us084: 'docs/product/credit/user-stories/US-084-consultar-resumo-da-carteira.md',
  us085: 'docs/product/credit/user-stories/US-085-consultar-vencimentos-e-inadimplencia.md',
  us086: 'docs/product/credit/user-stories/US-086-consultar-pagamentos-e-operacoes-encerradas.md',
  us087: 'docs/product/credit/user-stories/US-087-consultar-fluxo-previsto-e-realizado.md',
  us088: 'docs/product/credit/user-stories/US-088-impedir-calculo-financeiro-fora-do-motor-na-operacao-diaria.md',
};

const docs = Object.fromEntries(Object.entries(FILES).map(([key, rel]) => [key, read(rel)]));

function unidades(doc) {
  const resultado = [];
  let atual = '';
  const flush = () => {
    if (atual.trim()) resultado.push(atual.replace(/\s+/g, ' ').trim());
    atual = '';
  };
  for (const raw of doc.replace(/\r/g, '').split('\n')) {
    const linha = raw.trim();
    if (!linha) {
      flush();
      continue;
    }
    if (/^(#{1,6}\s|---$|- |\|)/.test(linha)) flush();
    atual = atual ? `${atual} ${linha}` : linha;
    if (/^\|/.test(linha)) flush();
  }
  flush();
  return resultado;
}

function assertTexto(doc, texto, contexto) {
  assert.ok(doc.includes(texto), `${contexto}: contrato ausente: ${texto}`);
}

function assertUnidade(doc, fragmentos, contexto) {
  const encontrada = unidades(doc).some((unidade) => fragmentos.every((item) => unidade.includes(item)));
  assert.ok(encontrada, `${contexto}: fragmentos fora da mesma clausula: ${fragmentos.join(' + ')}`);
}

function assertSemUnidade(doc, fragmentos, contexto) {
  const encontrada = unidades(doc).some((unidade) => fragmentos.every((item) => unidade.includes(item)));
  assert.ok(!encontrada, `${contexto}: contradicao encontrada: ${fragmentos.join(' + ')}`);
}

function mutar(base, chave, origem, destino) {
  assert.ok(base[chave].includes(origem), `fixture de mutacao ausente em ${chave}: ${origem}`);
  return { ...base, [chave]: base[chave].replace(origem, destino) };
}

const contracts = {
  hierarchy(source) {
    assert.strictEqual(Object.keys(source).length, 24, 'a matriz deve conter 24 artefatos');
    for (const [key, rel] of Object.entries(FILES)) {
      const esperado = key === 'discovery' ? 'EPIC-007' : path.basename(rel).match(/^[A-Z]+-\d{3}/)[0];
      assert.ok(source[key].startsWith(`# ${esperado}`), `${rel}: H1 nao declara ${esperado}`);
    }
    for (const product of ['product005', 'product006', 'product007', 'product008']) {
      assertTexto(source[product], 'EPIC-007', product);
    }
    const rastreio = {
      feature028: 'PRODUCT-005', feature029: 'PRODUCT-006',
      feature030: 'PRODUCT-007', feature031: 'PRODUCT-008',
      us075: 'FEATURE-028', us076: 'FEATURE-028', us077: 'FEATURE-028', us078: 'FEATURE-028',
      us079: 'FEATURE-029', us080: 'FEATURE-029', us081: 'FEATURE-029',
      us082: 'FEATURE-030', us083: 'FEATURE-030',
      us084: 'FEATURE-031', us085: 'FEATURE-031', us086: 'FEATURE-031',
      us087: 'FEATURE-031', us088: 'FEATURE-031',
    };
    for (const [key, parent] of Object.entries(rastreio)) assertTexto(source[key], parent, key);
    const filhos = {
      epic: ['FEATURE-028', 'FEATURE-029', 'FEATURE-030', 'FEATURE-031'],
      feature028: ['US-075', 'US-076', 'US-077', 'US-078'],
      feature029: ['US-079', 'US-080', 'US-081'],
      feature030: ['US-082', 'US-083'],
      feature031: ['US-084', 'US-085', 'US-086', 'US-087', 'US-088'],
    };
    for (const [parent, children] of Object.entries(filhos)) {
      for (const child of children) assertTexto(source[parent], child, `${parent} -> ${child}`);
    }
  },

  temporal(source) {
    for (const key of ['discovery', 'epic', 'product005', 'product006', 'feature028', 'feature029', 'us075', 'us079', 'product008', 'feature031', 'us084', 'us085']) {
      assertTexto(source[key], 'SituacaoParcelaNaDataV1', key);
    }
    assertUnidade(source.discovery, ['Motor', 'data_referencia', 'futura', 'vencida', 'regularizada', 'cancelada'], 'projecao temporal');
    assertUnidade(source.us075, ['data_referencia', 'SituacaoParcelaNaDataV1'], 'US-075');
    assertUnidade(source.us079, ['vencimento_financeiro', 'SituacaoParcelaNaDataV1'], 'US-079');
    assertUnidade(source.us085, ['regularizada_em', 'Motor'], 'US-085');
  },

  upstream(source) {
    assertUnidade(source.discovery, ['PagamentoEstornadoV1', 'service do Motor'], 'produtor do estorno');
    for (const campo of ['pagamento_id', 'estorno_id', 'apropriacoes', 'valor_efeito_realizado_assinado']) {
      assertTexto(source.discovery, campo, 'PagamentoEstornadoV1');
    }
    assertUnidade(source.discovery, ['mesma Unit of Work', 'reverte efeitos financeiros', 'fato idempotente'], 'publicacao do estorno');
    assertTexto(source.discovery, 'EncerramentoOperacaoV1', 'contrato de encerramento');
    assertUnidade(source.discovery, ['Quitacao e renegociacao', 'Motor'], 'origem financeira');
    assertUnidade(source.discovery, ['Encerramento administrativo', 'Contratos'], 'origem administrativa');
    assertUnidade(
      source.discovery,
      ['dependencias bloqueantes', 'SituacaoParcelaNaDataV1', 'PagamentoEstornadoV1', 'valor_efeito_realizado_assinado', 'EncerramentoOperacaoV1'],
      'dependencias upstream do PLAN'
    );
    assertUnidade(source.discovery, ['Estes contratos ainda nao existem no backend', 'nao podem ser simulados'], 'honestidade upstream');
  },

  reports(source) {
    for (const key of ['discovery', 'product008', 'feature031', 'us084', 'us086', 'us087']) {
      assertTexto(source[key], 'valor_efeito_realizado_assinado', key);
    }
    assertUnidade(source.us086, ['Pagamentos brutos', 'estornos', 'liquido', 'separadamente'], 'US-086');
    assertUnidade(source.us087, ['realizado', 'valor_efeito_realizado_assinado', 'Motor'], 'US-087');
    assertUnidade(source.feature031, ['encerramentos', 'Contratos'], 'FEATURE-031');
  },

  promise(source) {
    const rows = [
      '| criacao | registro valido | `pendente` | operador; data futura e valor positivo |',
      '| `pendente` | informacao manual | `pagamento_informado` | operador; antes do fim da data; nao confirma Pagamento |',
      '| `pendente` ou `pagamento_informado` | apropriacoes elegiveis atingem o valor | `cumprida` | sistema; Pagamentos oficiais dentro da janela |',
      '| `pendente` ou `pagamento_informado` | fim da data sem valor suficiente | `descumprida` | sistema ou operador; justificativa obrigatoria quando manual |',
      '| `descumprida` | Pagamento oficial retroativo recebido dentro da janela | `cumprida` | sistema; preserva a correcao historica |',
      '| `cumprida` | estorno reduz a soma antes do limite | `pendente` | sistema; emite invalidacao |',
      '| `cumprida` | estorno reduz a soma depois do limite | `descumprida` | sistema; emite invalidacao |',
      '| `cumprida` | estorno mantem soma suficiente | `cumprida` | sistema; nao emite invalidacao |',
    ];
    for (const row of rows) assertTexto(source.discovery, row, 'DA-718');
    for (const key of ['discovery', 'epic', 'product005', 'feature028', 'us078']) {
      assertTexto(source[key], 'ApropriarPagamentoPromessa', key);
      assertTexto(source[key], 'Scheduler', key);
    }
    assertUnidade(source.discovery, ['ReavaliarPromessaPagamento', 'PagamentoEstornadoV1', 'promessa vencida'], 'gatilhos DA-718');
    assertUnidade(source.us078, ['ReavaliarPromessaPagamento', 'PagamentoEstornadoV1', 'promessa vencida'], 'gatilhos US-078');
    assertUnidade(source.discovery, ['no maximo uma transicao', 'por promessa afetada'], 'limite por promessa');
    assertUnidade(source.us078, ['PromessaPagamentoCumprimentoInvalidado', 'estado anterior', '`cumprida`'], 'invalidacao condicional');
    assertUnidade(source.us078, ['nao e emitido', 'continuar `cumprida`', 'nunca esteve cumprida'], 'nao invalidacao');
  },

  references(source) {
    assertUnidade(source.us076, ['Emprestimo obrigatorio', 'deriva Devedor', 'Parcela', 'mesmo Emprestimo'], 'US-076');
    assertUnidade(source.us077, ['Emprestimo', 'deriva Devedor', 'Parcela', 'mesmo Emprestimo'], 'US-077');
    assertUnidade(source.us080, ['mesma cadeia Tenant, Carteira', 'contrato/ACL'], 'US-080');
    assertUnidade(source.product007, ['Cobranca', 'contratos conformistas/ACL'], 'PRODUCT-007');
    assertUnidade(source.feature030, ['Cobranca', 'contrato/ACL'], 'FEATURE-030');
    assertUnidade(source.us082, ['Emprestimo ou Cobranca', 'Devedor, Tenant e Carteira'], 'US-082');
    assertTexto(source.us083, 'PRODUCT-005', 'US-083');
  },

  agenda(source) {
    assertUnidade(source.product006, ['SituacaoParcelaNaDataV1', 'vencimento financeiro', 'somente leitura'], 'PRODUCT-006');
    assertUnidade(source.us079, ['vencimento_financeiro', 'SituacaoParcelaNaDataV1'], 'US-079');
    for (const key of ['feature029', 'us081']) {
      assertTexto(source[key], 'reagendado', key);
      assertTexto(source[key], 'concluido', key);
      assertTexto(source[key], 'cancelado', key);
    }
    assertUnidade(source.us081, ['item concluido ou cancelado', 'nao reabre'], 'US-081');
    assertUnidade(source.us081, ['nunca retorna ao estado aberto', 'cria outro item'], 'US-081 regra de nao reabertura');
    assertSemUnidade(source.us081, ['retorna ao estado aberto', 'sem nova decisao'], 'US-081 sem excecao de reabertura');
  },

  http(source) {
    const completos = {
      us075: ['malformado', 'cross-tenant', 'incompat'],
      us076: ['malformado', 'cross-tenant', 'payload diferente'],
      us077: ['malformado', 'cross-tenant', 'incompat'],
      us078: ['malformado', 'cross-tenant', 'transicao invalida'],
      us079: ['malformado', 'cross-tenant', 'incompat'],
      us080: ['malformado', 'cross-tenant', 'cadeias diferentes'],
      us081: ['malformado', 'cross-tenant', 'transicao invalida'],
      us082: ['malformado', 'cross-tenant', 'incompat'],
      us083: ['malformado', 'cross-tenant', 'cadeias diferentes'],
    };
    for (const [key, [bad, missing, conflict]] of Object.entries(completos)) {
      assertUnidade(source[key], [bad, '`400`'], `${key} 400`);
      assertUnidade(source[key], [missing, '`404`'], `${key} 404`);
      assertUnidade(source[key], [conflict, '`409`'], `${key} 409`);
      assertSemUnidade(source[key], [bad, '`404`'], `${key} nao troca 400/404`);
    }
    for (const key of ['us084', 'us085', 'us086', 'us087']) {
      assertUnidade(source[key], ['malformado', '`400`'], `${key} 400`);
      assertUnidade(source[key], ['cross-tenant', '`404`'], `${key} 404`);
      assertUnidade(source[key], ['`409`', 'nao se aplica'], `${key} 409 N/A`);
    }
    assertUnidade(source.us083, ['recurso inexistente', 'cross-tenant', '`404`'], 'US-083 causas de 404');
    for (const key of ['feature028', 'feature029', 'feature030']) {
      assertUnidade(source[key], ['malformado', '`400`'], `${key} 400`);
      assertUnidade(source[key], ['cross-tenant', '`404`'], `${key} 404`);
      assertUnidade(source[key], ['`409`'], `${key} 409`);
    }
    assertUnidade(source.feature031, ['malformado', '`400`'], 'FEATURE-031 400');
    assertUnidade(source.feature031, ['cross-tenant', '`404`', '`409`', 'nao se aplica'], 'FEATURE-031 leitura');
    for (const key of ['us077', 'us080', 'us082']) {
      assertUnidade(source[key], ['chave idempotente', 'payload', 'diferente', '`409`'], `${key} conflito idempotente`);
    }
  },

  guardrail(source) {
    for (const key of ['discovery', 'product008', 'feature031', 'us088']) {
      assertUnidade(source[key], ['`count`', '`sum`', '`group`', 'permitid'], `${key} agregacoes permitidas`);
    }
    assertUnidade(source.product008, ['juros', 'mora', 'amortizacao', 'arredondamento', 'proibido'], 'PRODUCT-008 formulas proibidas');
    assertUnidade(source.feature031, ['guardrails permitem agregacoes', 'falham diante de juros', 'amortizacao', 'arredondamento'], 'FEATURE-031 guardrail');
    assertUnidade(source.us088, ['falha diante', 'juros', 'mora', 'amortizacao', 'arredondamento'], 'US-088 formulas proibidas');
    assertSemUnidade(source.us088, ['juros', 'permitid'], 'US-088 nao permite juros');
  },
};

const cases = [];
const test = (name, fn) => cases.push({ name, fn });

test('matriz completa e rastreabilidade dos 24 artefatos', () => contracts.hierarchy(docs));
test('Motor materializa situacao temporal as-of-date sem Scheduler', () => contracts.temporal(docs));
test('contratos upstream definem estorno e encerramento', () => contracts.upstream(docs));
test('relatorios usam efeitos assinados e origens oficiais', () => contracts.reports(docs));
test('promessa possui tabela exata, gatilhos e invalidacao condicional', () => contracts.promise(docs));
test('referencias usam cadeia canonica e ACL', () => contracts.references(docs));
test('Agenda inclui vencimentos e ciclo de vida completo', () => contracts.agenda(docs));
test('contrato HTTP preserva causas de 400, 404 e 409', () => contracts.http(docs));
test('guardrail permite agregacao e proibe formula financeira', () => contracts.guardrail(docs));

test('mutacao: troca de 400 por 404 e rejeitada', () => {
  let altered = mutar(docs, 'us080', 'malformado retorna `400`', 'malformado retorna `404`');
  altered = mutar(altered, 'us080', 'cross-tenant retorna `404`', 'cross-tenant retorna `400`');
  assert.throws(() => contracts.http(altered));
});

test('mutacao: destino incorreto na DA-718 e rejeitado', () => {
  const altered = mutar(
    docs,
    'discovery',
    '| `cumprida` | estorno reduz a soma antes do limite | `pendente` |',
    '| `cumprida` | estorno reduz a soma antes do limite | `cumprida` |'
  );
  assert.throws(() => contracts.promise(altered));
});

test('mutacao: cumprimento por apropriacao com destino incorreto e rejeitado', () => {
  const altered = mutar(
    docs,
    'discovery',
    '| `pendente` ou `pagamento_informado` | apropriacoes elegiveis atingem o valor | `cumprida` |',
    '| `pendente` ou `pagamento_informado` | apropriacoes elegiveis atingem o valor | `descumprida` |'
  );
  assert.throws(() => contracts.promise(altered));
});

test('mutacao: invalidacao incondicional e rejeitada', () => {
  const altered = mutar(docs, 'us078', 'nao e emitido se continuar `cumprida`', 'e emitido se continuar `cumprida`');
  assert.throws(() => contracts.promise(altered));
});

test('mutacao: remocao de gatilho sincronico e rejeitada', () => {
  const altered = mutar(docs, 'us078', 'ReavaliarPromessaPagamento', 'ReavaliacaoSemContrato');
  assert.throws(() => contracts.promise(altered));
});

test('mutacao: produtor de estorno fora do Motor e rejeitado', () => {
  const altered = mutar(docs, 'discovery', 'service do Motor', 'service de Cobranca');
  assert.throws(() => contracts.upstream(altered));
});

test('mutacao: contratos upstream declarados existentes e rejeitada', () => {
  const altered = mutar(docs, 'discovery', 'Estes contratos ainda nao existem no backend', 'Estes contratos ja existem no backend');
  assert.throws(() => contracts.upstream(altered));
});

test('mutacao: formula financeira permitida fora do Motor e rejeitada', () => {
  const altered = mutar(docs, 'feature031', 'falham diante de juros', 'permitem juros');
  assert.throws(() => contracts.guardrail(altered));
});

test('mutacao: Feature removida do Epic e rejeitada', () => {
  const altered = mutar(docs, 'epic', 'FEATURE-030 - Registrar Comunicacao Manual', 'FEATURE-999 - Ausente');
  assert.throws(() => contracts.hierarchy(altered));
});

test('mutacao: Product de Relatorios autoriza juros e rejeitada', () => {
  const altered = mutar(docs, 'product008', 'fora do Motor e proibido', 'fora do Motor e permitido');
  assert.throws(() => contracts.guardrail(altered));
});

test('mutacao: US-083 omite recurso inexistente no 404 e rejeitada', () => {
  const altered = mutar(docs, 'us083', 'recurso inexistente ou cross-tenant', 'recurso cross-tenant');
  assert.throws(() => contracts.http(altered));
});

function run() {
  let failures = 0;
  console.log('test-epic-007-contracts');
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

module.exports = { FILES, contracts, docs, run, unidades };
