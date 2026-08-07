'use strict';

/**
 * Verificações de consistência arquitetural entre documentos (SPEC-001).
 *
 * Complementa o validate-docs.js: onde ele garante estrutura, IDs e links,
 * este módulo compara o CONTEÚDO de documentos que precisam concordar entre si.
 *
 * Origem: a divergência entre PLAN-003 e PLAN-003-EXEC quanto ao contrato HTTP
 * passou pelo congelamento 256a99b sem alarme e originou a DR-001/ADR-018.
 *
 * Princípio (SPEC-001 §2): determinístico. Regex e parsing estrutural, sem
 * heurística probabilística. Regra que não decide com segurança emite aviso,
 * nunca erro — erro bloqueia commit.
 */

const fs = require('fs');
const path = require('path');

const METODOS = 'GET|POST|PATCH|PUT|DELETE';

/**
 * Reduz `{qualquer_nome}` a `{}` (SPEC-001 §3.1, decisão C).
 *
 * Os documentos escrevem `/devedores/{id}` e o código `/devedores/{devedor_id}`.
 * O nome do parâmetro pertence à implementação; o contrato arquitetural é a
 * forma do caminho. Sem esta normalização, todo endpoint acusaria divergência.
 */
function normalizarCaminho(caminho) {
  return caminho
    .trim()
    .replace(/\{[^}]*\}/g, '{}')
    .replace(/\?.*$/, '') // query string não faz parte da identidade do recurso
    .replace(/\/+$/, '');
}

/**
 * Prefixos de contexto omissíveis na prosa dos documentos (SPEC-001 §3.2).
 *
 * O plano escreve `/credit/carteiras/{}/devedores`; o backlog frequentemente
 * omite o prefixo do bounded context e escreve `/carteiras/{}/devedores`. São
 * o mesmo endpoint. Comparar sem isto produz falso positivo (viola CA-002).
 *
 * Só prefixos de contexto entram aqui — nunca segmentos de recurso, cuja
 * ausência é justamente a divergência que se quer detectar.
 */
const PREFIXOS_DE_CONTEXTO = ['/credit', '/platform'];

/**
 * Separa o prefixo de bounded context do restante do caminho.
 *
 * Distinção que importa (CA-002 vs CA-004):
 *  - prefixo AUSENTE de um lado: mesmo endpoint, o documento apenas o omitiu;
 *  - prefixo PRESENTE nos dois lados e DIFERENTE: endpoints distintos, é
 *    divergência real e precisa ser detectada.
 *
 * Por isso o prefixo é separado, não descartado: a chave usa o sufixo (permite
 * o pareamento) e o prefixo fica registrado para a checagem de compatibilidade.
 */
function separarPrefixo(caminho) {
  for (const p of PREFIXOS_DE_CONTEXTO) {
    if (caminho === p) return { prefixo: p, resto: '/' };
    if (caminho.startsWith(p + '/')) return { prefixo: p, resto: caminho.slice(p.length) };
  }
  return { prefixo: '', resto: caminho };
}

/** Chave de pareamento: método + caminho sem o prefixo de contexto. */
function chaveDe(metodo, caminho) {
  return `${metodo} ${separarPrefixo(caminho).resto}`;
}

/**
 * Prefixos compatíveis: iguais, ou ao menos um omitido.
 * `/credit` vs `` → compatível (omissão). `/credit` vs `/platform` → não.
 */
function prefixosCompativeis(a, b) {
  const pa = separarPrefixo(a).prefixo;
  const pb = separarPrefixo(b).prefixo;
  return !pa || !pb || pa === pb;
}

/** Recurso raiz do caminho — usado para detectar formas estruturais distintas. */
function recursoDe(caminho) {
  const segmentos = caminho.split('/').filter((s) => s && s !== '{}');
  return segmentos.length ? segmentos[segmentos.length - 1] : null;
}

/**
 * Linhas que nunca declaram contrato (SPEC-001 §3.3, CA-005/CA-006).
 *
 * Casos reais que motivaram a regra, ambos no PLAN-003-EXEC:
 *  - linha de tabela do Histórico de Versões citando a rota que foi PROIBIDA;
 *  - bloco de citação (`>`) com a nota que declara o contrato oficial.
 */
function linhaIgnorada(linha, dentroDeHistorico) {
  if (dentroDeHistorico) return true;
  const t = linha.trim();
  if (t.startsWith('>')) return true;
  if (/^\|/.test(t)) return true; // qualquer linha de tabela
  return false;
}

/** Percorre linhas sinalizando quando se está sob a seção de Histórico de Versões. */
function* linhasComContexto(texto) {
  let emHistorico = false;
  for (const linha of texto.split(/\r?\n/)) {
    if (/^#{1,3}\s+(\d+\.\s+)?hist[óo]rico\s+de\s+vers[õo]es/i.test(linha)) {
      emHistorico = true;
    } else if (/^#{1,3}\s+/.test(linha)) {
      emHistorico = false;
    }
    yield { linha, emHistorico };
  }
}

/**
 * Extrai endpoints de um trecho, exigindo método HTTP explícito.
 *
 * Exigir o método é o que descarta `/reativar` solto (CA-006): fragmentos de
 * frase não trazem verbo. Caminhos sem método são ignorados por construção.
 */
function extrairEndpoints(texto) {
  const achados = new Map();
  // A crase entre método e caminho é opcional: os documentos usam as duas formas
  // — `GET /credit/...` (PLAN §API) e ``GET `/devedores/{id}` `` (PLAN-EXEC).
  const re = new RegExp('\\b(' + METODOS + ')\\s+`?(/[A-Za-z0-9{}/_.-]*)', 'g');

  for (const { linha, emHistorico } of linhasComContexto(texto)) {
    if (linhaIgnorada(linha, emHistorico)) continue;
    let m;
    while ((m = re.exec(linha))) {
      const caminho = normalizarCaminho(m[2]);
      if (!caminho || caminho === '/') continue;
      const metodo = m[1].toUpperCase();
      achados.set(chaveDe(metodo, caminho), { metodo, caminho });
    }
  }
  return achados;
}

/** Seção de API de um PLAN: `# N. API` até o próximo cabeçalho de mesmo nível. */
function secaoApi(texto) {
  const linhas = texto.split(/\r?\n/);
  const inicio = linhas.findIndex((l) => /^#\s+\d+\.\s+API\s*$/i.test(l.trim()));
  if (inicio === -1) return null;
  const resto = linhas.slice(inicio + 1);
  const fim = resto.findIndex((l) => /^#\s+\d+\./.test(l.trim()));
  return (fim === -1 ? resto : resto.slice(0, fim)).join('\n');
}

/** Blocos `## IMP-NNN` de um backlog de execução. */
function blocosImp(texto) {
  const blocos = [];
  const linhas = texto.split(/\r?\n/);
  let atual = null;
  for (const linha of linhas) {
    const m = linha.match(/^##\s+(IMP-\d+)/);
    if (m) {
      if (atual) blocos.push(atual);
      atual = { id: m[1], linhas: [linha] };
    } else if (atual) {
      atual.linhas.push(linha);
    }
  }
  if (atual) blocos.push(atual);
  return blocos.map((b) => ({ id: b.id, texto: b.linhas.join('\n') }));
}

/** Rotas declaradas em um módulo de rotas FastAPI (decisão A: parsing estático). */
function extrairRotasDoCodigo(arquivo) {
  const txt = fs.readFileSync(arquivo, 'utf8');
  const prefixo = (txt.match(/APIRouter\([^)]*prefix\s*=\s*["']([^"']*)["']/) || [, ''])[1];
  const achados = new Map();
  const re = /@router\.(get|post|patch|put|delete)\(\s*\n?\s*["']([^"']+)["']/g;
  let m;
  while ((m = re.exec(txt))) {
    const caminho = normalizarCaminho(prefixo + m[2]);
    const metodo = m[1].toUpperCase();
    achados.set(chaveDe(metodo, caminho), { metodo, caminho });
  }
  return achados;
}

/**
 * Fase 1 — coerência PLAN ↔ PLAN-EXEC (SPEC-001 §4).
 *
 * Bidirecional (regra 1.3, decisão da Arquitetura): o conjunto do backlog deve
 * ser IGUAL ao do plano, não apenas contido nele. Endpoint que entra pela
 * execução sem passar pelo planejamento é tão grave quanto o inverso.
 */
function compararPlanoEBacklog(plano, backlog, res) {
  const secao = secaoApi(plano.texto);
  if (secao === null) {
    res.warnings.push(`${plano.rel}: seção "# N. API" não encontrada — comparação de contrato ignorada`);
    return;
  }

  const doPlano = extrairEndpoints(secao);
  const doBacklog = new Map();
  for (const bloco of blocosImp(backlog.texto)) {
    for (const [chave, ep] of extrairEndpoints(bloco.texto)) {
      if (!doBacklog.has(chave)) doBacklog.set(chave, { ...ep, imp: bloco.id });
    }
  }

  if (doPlano.size === 0 || doBacklog.size === 0) return;

  // Recursos do plano, por nome, para detectar forma estrutural divergente.
  const formasDoPlano = new Map();
  for (const ep of doPlano.values()) {
    const r = recursoDe(ep.caminho);
    if (!r) continue;
    if (!formasDoPlano.has(r)) formasDoPlano.set(r, new Set());
    formasDoPlano.get(r).add(ep.caminho);
  }

  for (const [chave, ep] of doBacklog) {
    const noPlano = doPlano.get(chave);
    if (noPlano) {
      // Pareados pelo sufixo: resta conferir o bounded context (CA-004).
      if (!prefixosCompativeis(noPlano.caminho, ep.caminho)) {
        res.errors.push(
          `[CONTRATO] Bounded context divergente para "${ep.metodo} ${ep.caminho}":\n` +
            `           ${plano.rel} §API : ${noPlano.caminho}\n` +
            `           ${backlog.rel} ${ep.imp} : ${ep.caminho}`
        );
      }
      continue;
    }

    const recurso = recursoDe(ep.caminho);
    const formas = recurso ? formasDoPlano.get(recurso) : null;

    if (formas && formas.size) {
      // Regra 1.2: mesmo recurso, forma estrutural distinta. Foi este o caso da DR-001.
      res.errors.push(
        `[CONTRATO] Contrato HTTP inconsistente para o recurso "${recurso}":\n` +
          `           ${plano.rel} §API : ${[...formas].map((f) => `${ep.metodo} ${f}`).join(', ')}\n` +
          `           ${backlog.rel} ${ep.imp} : ${ep.metodo} ${ep.caminho}\n` +
          `           O backlog de execução deve refletir o plano.`
      );
    } else {
      // Regra 1.1/1.3: endpoint no backlog sem contrapartida no plano.
      res.errors.push(
        `[CONTRATO] ${backlog.rel} ${ep.imp} declara "${ep.metodo} ${ep.caminho}", ` +
          `ausente da seção API de ${plano.rel}.`
      );
    }
  }

  // Direção inversa permanece aviso: backlog incompleto é estado legítimo.
  for (const [chave, ep] of doPlano) {
    if (!doBacklog.has(chave)) {
      res.warnings.push(
        `${plano.rel}: endpoint "${ep.metodo} ${ep.caminho}" sem IMP correspondente em ${backlog.rel}`
      );
    }
  }
}

/** Fase 2 — coerência PLAN ↔ implementação (SPEC-001 §5). */
function compararPlanoEImplementacao(planos, arquivosDeRotas, res) {
  const doPlano = new Map();
  for (const p of planos) {
    const secao = secaoApi(p.texto);
    if (secao === null) continue;
    for (const [chave, ep] of extrairEndpoints(secao)) doPlano.set(chave, { ...ep, plano: p.rel });
  }
  if (doPlano.size === 0) return;

  const doCodigo = new Map();
  for (const arq of arquivosDeRotas) {
    for (const [chave, ep] of extrairRotasDoCodigo(arq.abs)) {
      doCodigo.set(chave, { ...ep, arquivo: arq.rel });
    }
  }

  for (const [chave, ep] of doCodigo) {
    if (!doPlano.has(chave)) {
      res.errors.push(
        `[CONTRATO] ${ep.arquivo} implementa "${ep.metodo} ${ep.caminho}", ` +
          `ausente da seção API dos planos.`
      );
    }
  }
  for (const [chave, ep] of doPlano) {
    if (!doCodigo.has(chave)) {
      res.warnings.push(
        `${ep.plano}: endpoint "${ep.metodo} ${ep.caminho}" planejado e ainda não implementado`
      );
    }
  }
}

/**
 * Fase 3 — códigos HTTP entre PLAN e PLAN-EXEC (SPEC-001 §6).
 *
 * Limitada por decisão da Arquitetura à comparação documento↔documento: os
 * status no código vêm de três origens, uma delas os add_exception_handler de
 * main.py, que mapeiam exceção→status fora da rota. Rastreá-los é análise de
 * fluxo, não parsing.
 */
function compararCodigosHttp(plano, backlog, res) {
  /**
   * Extrai códigos HTTP exigindo evidência de que o número é um status.
   *
   * Números soltos NÃO servem: "max 100" (paginação) e "100% pass" (cobertura)
   * foram falsos positivos reais desta regra. Aceita-se apenas 2xx–5xx (100 e
   * demais 1xx não ocorrem nesta API) acompanhado de um rótulo de erro, da
   * palavra "HTTP"/"status", ou dentro de uma enumeração separada por `/`.
   */
  const codigos = (texto) => {
    const set = new Set();
    for (const { linha, emHistorico } of linhasComContexto(texto)) {
      if (linhaIgnorada(linha, emHistorico)) continue;
      for (const m of linha.matchAll(/\b([2-5]\d\d)\b(?!\s*%)([^\s]?)/g)) {
        const codigo = m[1];
        const posterior = linha.slice(m.index + codigo.length, m.index + codigo.length + 40);
        const anterior = linha.slice(Math.max(0, m.index - 20), m.index);
        // Sufixo de identificador (DA-303, US-027, IMP-059, ADR-018…) nunca é status.
        if (/[A-Za-z]+-$/.test(anterior)) continue;
        const pareceStatus =
          /^`?\s*[—\-–]?\s*[a-z_]{3,}/i.test(posterior) || // "404 devedor_nao_encontrado", "`201` — Tenant…"
          /\b(HTTP|status|c[óo]digo|retorna|responde)\b/i.test(anterior + posterior) ||
          /^`?\s*[/;,)]/.test(posterior); // "201; 404; 409" ou "400 / 404"
        if (pareceStatus) set.add(codigo);
      }
    }
    return set;
  };

  const doPlano = codigos(plano.texto);
  if (!doPlano.size) return;

  for (const bloco of blocosImp(backlog.texto)) {
    for (const c of codigos(bloco.texto)) {
      if (!doPlano.has(c)) {
        res.errors.push(
          `[CONTRATO] ${backlog.rel} ${bloco.id} cita o código HTTP ${c}, ausente de ${plano.rel}.`
        );
      }
    }
  }
}

/**
 * Executa as verificações de contrato.
 *
 * @param {object} opts
 * @param {string} opts.root      raiz do repositório
 * @param {object} opts.results   acumulador { errors, warnings } compartilhado
 */
function verificarContratos({ root, results }) {
  const rel = (p) => path.relative(root, p).replace(/\\/g, '/');
  const ler = (p) => ({ abs: p, rel: rel(p), texto: fs.readFileSync(p, 'utf8') });

  const dirPlanos = path.join(root, 'docs', 'implementation', 'plans');
  const dirBacklogs = path.join(root, 'docs', 'implementation', 'backlogs');
  if (!fs.existsSync(dirPlanos)) return;

  const planos = fs
    .readdirSync(dirPlanos)
    .filter((f) => /^PLAN-\d+.*\.md$/i.test(f))
    .map((f) => ({ ...ler(path.join(dirPlanos, f)), num: f.match(/PLAN-(\d+)/i)[1] }));

  const backlogs = new Map();
  if (fs.existsSync(dirBacklogs)) {
    for (const f of fs.readdirSync(dirBacklogs)) {
      const m = f.match(/^PLAN-(\d+)-execution-backlog\.md$/i);
      if (m) backlogs.set(m[1], ler(path.join(dirBacklogs, f)));
    }
  }

  for (const plano of planos) {
    const backlog = backlogs.get(plano.num);
    if (!backlog) {
      results.warnings.push(`${plano.rel}: sem backlog de execução correspondente`);
      continue;
    }
    compararPlanoEBacklog(plano, backlog, results);
    compararCodigosHttp(plano, backlog, results);
  }

  const dirRotas = path.join(root, 'src', 'emprestimo', 'presentation', 'api');
  if (fs.existsSync(dirRotas)) {
    const arquivos = fs
      .readdirSync(dirRotas)
      .filter((f) => f.endsWith('.py'))
      .map((f) => ({ abs: path.join(dirRotas, f), rel: rel(path.join(dirRotas, f)) }))
      .filter((a) => /@router\./.test(fs.readFileSync(a.abs, 'utf8')));
    compararPlanoEImplementacao(planos, arquivos, results);
  }
}

module.exports = {
  verificarContratos,
  // exportados para os testes (SPEC-001 CA-007)
  normalizarCaminho,
  recursoDe,
  extrairEndpoints,
  secaoApi,
  blocosImp,
  extrairRotasDoCodigo,
  compararPlanoEBacklog,
  compararCodigosHttp,
};
