'use strict';

/**
 * Família Identifiers do docs:validate (SPEC-002, DA-098-007).
 *
 * O Registry (docs/governance/registry/identifier-registry.json) é documento
 * NORMATIVO (DA-098-006): é ele quem diz quais namespaces existem, quem os
 * governa e quais estão em fim de vida. Este módulo confronta o repositório
 * contra ele.
 *
 * Origem: o comando AC-001 foi emitido sob `DA-001`, prefixo que já pertencia a
 * Design Assumption. Não havia registro do que estava emitido, então nada
 * detectou a colisão — a regra 5.2 abaixo é exatamente esse detector.
 *
 * Fora de escopo por decisão da Arquitetura:
 *  - contador de TASK (DA-098-001: governado pelo Git, não pelo Registry);
 *  - reservas de ADR (DA-098-002: governadas pelo AMP-001).
 * Validá-los aqui recriaria as duas fontes de verdade que as decisões unificaram.
 */

const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');
const Ajv2020 = require('ajv/dist/2020');
const addFormats = require('ajv-formats');

const REGISTRY_REL = 'docs/governance/registry/identifier-registry.json';
const REGISTRY_SCHEMA_REL = 'docs/governance/registry/identifier-registry.schema.json';

/** Gramática oficial (AC-003): NAMESPACE-NNN[-QUALIFICADOR]. */
const RE_ID = /\b([A-Z]{2,12})-(\d{1,4})(-[A-Za-z]+)?\b/g;

/**
 * Prefixos que casam a gramática mas não são identificadores de governança.
 * Sem esta lista, siglas técnicas em prosa viram falso erro de namespace.
 */
const NAO_IDENTIFICADORES = new Set([
  'UTF', 'ISO', 'RFC', 'HTTP', 'SHA', 'MD', 'ADR2', 'PT', 'BR2',
  'CPF', 'CNPJ', 'SQL', 'API', 'URL', 'UUID', 'JSON', 'YAML',
]);

const escaparRegex = (s) => s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

function carregarRegistry(root) {
  const abs = path.join(root, REGISTRY_REL);
  if (!fs.existsSync(abs)) return null;
  try {
    return JSON.parse(fs.readFileSync(abs, 'utf8'));
  } catch (e) {
    return { __erro: e.message };
  }
}

function criarValidadorSchema() {
  const ajv = new Ajv2020({ allErrors: true, strict: true });
  addFormats(ajv);
  return ajv;
}

function validarDefinicaoSchema(schema) {
  try {
    criarValidadorSchema().compile(schema);
    return [];
  } catch (error) {
    return [error instanceof Error ? error.message : String(error)];
  }
}

function validarJsonSchema(valor, schema) {
  let validate;
  try {
    validate = criarValidadorSchema().compile(schema);
  } catch (error) {
    return [`schema invalido: ${error instanceof Error ? error.message : String(error)}`];
  }
  if (validate(valor)) return [];
  return (validate.errors || []).map((erro) => {
    const local = erro.instancePath || '$';
    return `${local}: ${erro.keyword}: ${erro.message || 'violacao do schema'}`;
  });
}

function validarRegistryContraSchema(root, registry, results) {
  const schemaAbs = path.resolve(root, REGISTRY_SCHEMA_REL);
  if (!fs.existsSync(schemaAbs)) {
    results.errors.push(`[IDENTIFIERS] schema ausente: ${path.relative(root, schemaAbs)}`);
    return;
  }
  let schema;
  try {
    schema = JSON.parse(fs.readFileSync(schemaAbs, 'utf8'));
  } catch (error) {
    results.errors.push(`[IDENTIFIERS] schema JSON invalido: ${error.message}`);
    return;
  }
  const errosSchema = validarDefinicaoSchema(schema);
  const errosRegistry = errosSchema.length ? [] : validarJsonSchema(registry, schema);
  for (const erro of [...errosSchema, ...errosRegistry]) {
    results.errors.push(`[IDENTIFIERS] schema/Registry: ${erro}`);
  }
}

function walk(dir) {
  const out = [];
  if (!fs.existsSync(dir)) return out;
  for (const entry of fs.readdirSync(dir, { withFileTypes: true })) {
    const p = path.join(dir, entry.name);
    if (entry.isDirectory()) out.push(...walk(p));
    else if (entry.isFile() && entry.name.toLowerCase().endsWith('.md')) out.push(p);
  }
  return out;
}

/**
 * Coleta os identificadores citados em um texto.
 * Retorna Map<namespace, Set<idCompleto>>.
 */
function coletarIds(texto) {
  const achados = new Map();
  let m;
  RE_ID.lastIndex = 0;
  while ((m = RE_ID.exec(texto))) {
    const ns = m[1];
    if (NAO_IDENTIFICADORES.has(ns)) continue;
    if (!achados.has(ns)) achados.set(ns, new Set());
    achados.get(ns).add(m[0]);
  }
  return achados;
}

/** Identificador declarado no título H1 do documento — é o ID "emitido" por ele. */
function idDoTitulo(texto) {
  for (const linha of texto.split(/\r?\n/)) {
    const m = linha.match(/^#\s+([A-Z]{2,12})-(\d{1,4})(-[A-Za-z]+)?\b/);
    if (m) return { ns: m[1], numero: parseInt(m[2], 10), id: m[0].replace(/^#\s+/, '') };
    if (/^#\s+/.test(linha)) return null; // primeiro H1 não traz ID
  }
  return null;
}

function carregarBaselineGit(root, ref = process.env.IDENTIFIER_BASE_REF || 'HEAD') {
  try {
    const shallow = execFileSync('git', ['rev-parse', '--is-shallow-repository'], {
      cwd: root,
      encoding: 'utf8',
      stdio: ['ignore', 'pipe', 'ignore'],
    }).trim();
    if (shallow === 'true') throw new Error('historico Git raso; execute fetch --unshallow');
    const registry = JSON.parse(
      execFileSync('git', ['show', `${ref}:${REGISTRY_REL}`], {
        cwd: root,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      })
    );
    let titulos = '';
    try {
      titulos = execFileSync('git', ['grep', '-n', '^# ', ref, '--', 'docs'], {
        cwd: root,
        encoding: 'utf8',
        stdio: ['ignore', 'pipe', 'ignore'],
      });
    } catch (error) {
      if (!error || error.status !== 1) throw error;
    }
    const emitidosPorNs = {};
    for (const linha of titulos.split(/\r?\n/)) {
      const m = linha.match(/^[^:]+:(.+?):\d+:(# .+)$/);
      if (!m) continue;
      const titulo = idDoTitulo(m[2]);
      if (!titulo) continue;
      if (!emitidosPorNs[titulo.ns]) emitidosPorNs[titulo.ns] = [];
      emitidosPorNs[titulo.ns].push(titulo.numero);
    }
    const historicosPorNs = {};
    const historico = execFileSync('git', ['log', ref, '-p', '--format=', '--', 'docs'], {
      cwd: root,
      encoding: 'utf8',
      maxBuffer: 20 * 1024 * 1024,
      stdio: ['ignore', 'pipe', 'ignore'],
    });
    for (const linha of historico.split(/\r?\n/)) {
      if (!/^[+-]# /.test(linha)) continue;
      const titulo = idDoTitulo(linha.slice(1));
      if (!titulo) continue;
      if (!historicosPorNs[titulo.ns]) historicosPorNs[titulo.ns] = [];
      historicosPorNs[titulo.ns].push(titulo.numero);
    }
    return { ref, registry, emitidosPorNs, historicosPorNs };
  } catch (error) {
    const detalhe = error instanceof Error ? error.message : String(error);
    throw new Error(`baseline Git "${ref}" indisponivel: ${detalhe}`);
  }
}

function validarHistorico({ ns, emitidosPorNs, baseline, results }) {
  if (!baseline || !baseline.registry) return;
  const baselineNs = baseline.registry.namespaces || {};
  const baselineEmitidos = baseline.emitidosPorNs || {};
  const historicos = baseline.historicosPorNs || baselineEmitidos;

  for (const [prefixo, baseCfg] of Object.entries(baselineNs)) {
    if (baseCfg.governadoPor !== 'sequencial') continue;
    const cfg = ns[prefixo];
    if (!cfg) {
      results.errors.push(
        `${prefixo}: namespace sequencial da baseline foi removido do Registry ` +
          `(SPEC-002 §5.9)`
      );
    } else if (cfg.governadoPor !== 'sequencial') {
      results.errors.push(
        `${prefixo}: governanca mudou de sequencial para ${cfg.governadoPor || 'ausente'} ` +
          `sem migracao historica explicita (SPEC-002 §5.9)`
      );
    }
  }

  for (const [prefixo, cfg] of Object.entries(ns)) {
    if (cfg.governadoPor !== 'sequencial') continue;
    const baseCfg = baselineNs[prefixo];
    if (!baseCfg || baseCfg.governadoPor !== 'sequencial') continue;
    if (!Number.isInteger(cfg.ultimo) || !Number.isInteger(baseCfg.ultimo)) continue;

    if (cfg.ultimo < baseCfg.ultimo) {
      results.errors.push(
        `${prefixo}: ultimo=${String(cfg.ultimo).padStart(3, '0')} reduziu o marcador ` +
          `historico da baseline=${String(baseCfg.ultimo).padStart(3, '0')} ` +
          `(SPEC-002 §5.9)`
      );
      continue;
    }

    const vivos = new Set((emitidosPorNs.get(prefixo) || []).map((item) => item.numero));
    const anteriores = new Set(baselineEmitidos[prefixo] || []);
    const novos = [...vivos].filter((numero) => !anteriores.has(numero));
    const emitidosHistoricamente = new Set(historicos[prefixo] || []);
    const reciclados = novos.filter(
      (numero) => numero <= baseCfg.ultimo && emitidosHistoricamente.has(numero)
    );
    if (reciclados.length) {
      results.errors.push(
        `${prefixo}: ID(s) ${reciclados.map((n) => String(n).padStart(3, '0')).join(', ')} ` +
          `reutilizam faixa historica ate ${String(baseCfg.ultimo).padStart(3, '0')} ` +
          `(SPEC-002 §5.9)`
      );
    }

    if (cfg.ultimo > baseCfg.ultimo) {
      const faltantes = [];
      for (let n = baseCfg.ultimo + 1; n <= cfg.ultimo; n++) {
        if (!vivos.has(n)) faltantes.push(n);
      }
      if (faltantes.length) {
        results.errors.push(
          `${prefixo}: nova faixa historica possui numero(s) sem emissao: ` +
            `${faltantes.map((n) => String(n).padStart(3, '0')).join(', ')} ` +
            `(SPEC-002 §5.9)`
        );
      }
    }
  }
}

function verificarIdentificadores({ root, results, baseline }) {
  const rel = (p) => path.relative(root, p).replace(/\\/g, '/');
  const registry = carregarRegistry(root);

  if (registry === null) {
    results.warnings.push(
      `${REGISTRY_REL} não encontrado — família Identifiers não executada (SPEC-002)`
    );
    return;
  }
  if (registry.__erro) {
    results.errors.push(`[IDENTIFIERS] ${REGISTRY_REL} é JSON inválido: ${registry.__erro}`);
    return;
  }

  validarRegistryContraSchema(root, registry, results);

  const ns = registry.namespaces || {};
  const conhecidos = new Set(Object.keys(ns));
  const legados = new Set(
    Object.keys(ns).filter((k) => (ns[k].status || '').toUpperCase() === 'LEGACY')
  );

  // 5.8 - todo namespace sequencial declara contador inteiro nao negativo.
  for (const [prefixo, cfg] of Object.entries(ns)) {
    if (cfg.governadoPor !== 'sequencial') continue;
    if (!Number.isInteger(cfg.ultimo) || cfg.ultimo < 0) {
      const valor = Object.prototype.hasOwnProperty.call(cfg, 'ultimo')
        ? JSON.stringify(cfg.ultimo)
        : 'ausente';
      results.errors.push(
        `${prefixo}: ultimo=${valor} deve ser inteiro nao negativo em namespace ` +
          `sequencial (SPEC-002 §5.8)`
      );
    }
  }

  const arquivos = walk(path.join(root, 'docs'));
  const usados = new Set();
  const desconhecidos = new Map(); // ns -> primeiro arquivo onde apareceu
  const legadosCitados = new Map(); // ns -> Set<arquivo>
  const emitidosPorNs = new Map(); // ns -> [{numero, arquivo}]

  for (const arq of arquivos) {
    const rp = rel(arq);
    // O próprio Registry cita todos os namespaces por definição; ignorá-lo evita
    // que ele valide a si mesmo em círculo.
    if (rp === REGISTRY_REL) continue;

    const texto = fs.readFileSync(arq, 'utf8');

    // 5.3 — novo ID emitido em namespace LEGACY (o título declara emissão).
    const titulo = idDoTitulo(texto);
    if (titulo) {
      usados.add(titulo.ns);
      if (legados.has(titulo.ns)) {
        results.errors.push(
          `[IDENTIFIERS] ${rp} emite "${titulo.id}" em namespace LEGACY — ` +
            `use "${ns[titulo.ns].sucessor || 'o sucessor'}" (SPEC-002 §5, DA-098-004).`
        );
      }
      if (!emitidosPorNs.has(titulo.ns)) emitidosPorNs.set(titulo.ns, []);
      emitidosPorNs.get(titulo.ns).push({ numero: titulo.numero, arquivo: rp });
    }

    for (const [prefixo, ids] of coletarIds(texto)) {
      usados.add(prefixo);

      // 5.2 — namespace ausente do Registry.
      if (!conhecidos.has(prefixo) && !desconhecidos.has(prefixo)) {
        desconhecidos.set(prefixo, { arquivo: rp, exemplo: [...ids][0] });
      }

      // 5.5 — namespace LEGACY ainda referenciado.
      if (legados.has(prefixo)) {
        if (!legadosCitados.has(prefixo)) legadosCitados.set(prefixo, new Set());
        legadosCitados.get(prefixo).add(rp);
      }

      // 5.4 — gramática: número com menos de 3 dígitos.
      // Padrões glob (`DOMAIN-02*.md`) não são identificadores. Avalia-se TODA
      // ocorrência: basta uma sem `*` à direita para o aviso ser legítimo.
      for (const id of ids) {
        const m = id.match(/^[A-Z]{2,12}-(\d{1,4})/);
        if (!m || m[1].length >= 3) continue;
        const ocorrencias = [...texto.matchAll(new RegExp(escaparRegex(id) + '(.?)', 'g'))];
        const usadoComoId = ocorrencias.some((o) => o[1] !== '*' && !/\d/.test(o[1]));
        if (!usadoComoId) continue;
        results.warnings.push(
          `${rp}: identificador "${id}" fora da gramática — use 3 dígitos (SPEC-002 §3)`
        );
      }
    }
  }

  for (const [prefixo, info] of desconhecidos) {
    results.errors.push(
      `[IDENTIFIERS] namespace "${prefixo}" usado em ${info.arquivo} (ex.: ${info.exemplo}) ` +
        `mas ausente do Registry. Registre-o primeiro (DA-098-006).`
    );
  }

  for (const [prefixo, arquivos] of legadosCitados) {
    results.warnings.push(
      `namespace LEGACY "${prefixo}" ainda referenciado em ${arquivos.size} documento(s) — ` +
        `referências futuras devem usar "${ns[prefixo].sucessor || 'o sucessor'}"`
    );
  }

  // 5.6 — Registry declara namespace que nenhum documento usa.
  for (const prefixo of conhecidos) {
    if (!usados.has(prefixo)) {
      results.warnings.push(
        `Registry declara o namespace "${prefixo}", que nenhum documento utiliza`
      );
    }
  }

  // 5.7 — buraco na sequência de namespace 'sequencial'.
  for (const [prefixo, itens] of emitidosPorNs) {
    const cfg = ns[prefixo];
    if (!cfg || cfg.governadoPor !== 'sequencial') continue;
    const numeros = [...new Set(itens.map((i) => i.numero))].sort((a, b) => a - b);
    const maiorVivo = Math.max(...numeros);
    for (let n = 1; n < Math.max(...numeros); n++) {
      if (!numeros.includes(n)) {
        results.warnings.push(
          `${prefixo}: número ${String(n).padStart(3, '0')} ausente na sequência ` +
            `(emitidos vão até ${String(Math.max(...numeros)).padStart(3, '0')})`
        );
      }
    }

    // 5.8 — o contador historico nunca fica abaixo de um identificador vivo.
    if (!Number.isInteger(cfg.ultimo) || cfg.ultimo < 0) continue;
    if (maiorVivo > cfg.ultimo) {
      results.errors.push(
        `${prefixo}: ultimo=${String(cfg.ultimo).padStart(3, '0')} esta abaixo do maior ID ` +
          `vivo=${String(maiorVivo).padStart(3, '0')} (SPEC-002 §5.8)`
      );
    }
  }

  let baselineEfetiva = baseline;
  if (baseline === undefined) {
    try {
      baselineEfetiva = carregarBaselineGit(root);
    } catch (error) {
      results.errors.push(
        `[IDENTIFIERS] ${error instanceof Error ? error.message : String(error)} ` +
          `(SPEC-002 §5.9)`
      );
      return;
    }
  }
  validarHistorico({ ns, emitidosPorNs, baseline: baselineEfetiva, results });
}

module.exports = {
  verificarIdentificadores,
  // exportados para os testes (CB-008)
  carregarRegistry,
  validarDefinicaoSchema,
  validarJsonSchema,
  validarRegistryContraSchema,
  coletarIds,
  idDoTitulo,
  carregarBaselineGit,
  validarHistorico,
  REGISTRY_REL,
  REGISTRY_SCHEMA_REL,
};
