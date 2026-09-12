/**
 * Guardrail do gate `precondicoes` (.github/workflows/deploy.yml).
 *
 * Origem: a allowlist de check runs do gate era um regex ancorado
 * `^(Quality|Backend gates|Documentation gates|Frontend foundation)$`. Os
 * check runs gerados pela matriz de `quality.yml` se chamam "Frontend
 * foundation (ubuntu-latest)" e "(windows-latest)", e nenhum casava. O gate
 * aprovava o deploy para produção com as duas suites de frontend vermelhas,
 * e "Quality" — nome do workflow, não de job — nunca casou nada.
 *
 * O defeito não foi o regex: foi a allowlist poder ficar vazia sem ninguém
 * perceber. Este teste amarra a lista NOMINAL do gate aos nomes de job que
 * `quality.yml` realmente produz. Renomear um job, acrescentar um, ou mexer
 * na matriz sem atualizar o gate falha aqui, antes de virar deploy aprovado
 * por engano.
 *
 * As fixtures de comportamento do programa jq rodam quando `jq` existe no
 * PATH (sempre no runner Linux do CI).
 */

import assert from 'node:assert/strict';
import { execFileSync, spawnSync } from 'node:child_process';
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { dirname, join } from 'node:path';

const ROOT = join(dirname(fileURLToPath(import.meta.url)), '..', '..');
const DEPLOY_YML = join(ROOT, '.github', 'workflows', 'deploy.yml');
const QUALITY_YML = join(ROOT, '.github', 'workflows', 'quality.yml');
const PROGRAMA_JQ = join(ROOT, 'scripts', 'ci', 'check-runs-veredito.jq');

const falhas = [];
const checar = (rotulo, fn) => {
  try {
    fn();
    console.log(`  ok  ${rotulo}`);
  } catch (erro) {
    falhas.push(`${rotulo}: ${erro.message}`);
    console.log(`  FALHOU  ${rotulo}`);
  }
};

/** Lê o bloco literal `ESPERADOS: |` do gate. */
function esperadosDoGate() {
  const texto = readFileSync(DEPLOY_YML, 'utf8');
  const bloco = texto.match(/^(\s+)ESPERADOS:\s*\|\s*\n((?:\1\s+.*\n)+)/m);
  assert.ok(bloco, 'bloco `ESPERADOS: |` não encontrado em deploy.yml');
  return bloco[2]
    .split('\n')
    .map((linha) => linha.trim())
    .filter(Boolean);
}

/**
 * Nomes de check run que `quality.yml` produz.
 *
 * Parser mínimo e específico deste arquivo: cada job de topo tem um `name:`,
 * e o único eixo de matriz em uso é `os`. Um eixo novo quebra a asserção de
 * placeholder abaixo em vez de passar silenciosamente.
 */
function nomesDeJobDoQuality() {
  const linhas = readFileSync(QUALITY_YML, 'utf8').split('\n');
  const nomes = [];
  let jobAtual = null;

  for (const linha of linhas) {
    if (/^ {2}[A-Za-z0-9_-]+:\s*$/.test(linha)) {
      jobAtual = { nome: null, os: [] };
      nomes.push(jobAtual);
      continue;
    }
    if (!jobAtual) continue;
    const nome = linha.match(/^ {4}name:\s*(.+?)\s*$/);
    if (nome && jobAtual.nome === null) jobAtual.nome = nome[1];
    const os = linha.match(/^ {10}- (ubuntu-latest|windows-latest|macos-latest)\s*$/);
    if (os) jobAtual.os.push(os[1]);
  }

  return nomes
    .filter((job) => job.nome)
    .flatMap((job) => {
      const placeholders = job.nome.match(/\$\{\{[^}]+\}\}/g) ?? [];
      if (placeholders.length === 0) return [job.nome];
      assert.deepEqual(
        placeholders,
        ['${{ matrix.os }}'],
        `job "${job.nome}" usa um eixo de matriz que este parser não conhece`,
      );
      assert.ok(job.os.length > 0, `job "${job.nome}" usa matrix.os sem valores`);
      return job.os.map((os) => job.nome.replace('${{ matrix.os }}', os));
    });
}

function rodarJq(fixture, esperados) {
  const saida = execFileSync(
    'jq',
    ['-c', '--arg', 'esperados', esperados.join('\n'), '-f', PROGRAMA_JQ],
    { input: JSON.stringify(fixture), encoding: 'utf8' },
  );
  return JSON.parse(saida);
}

const run = (nome, status, conclusion) => ({
  app: { slug: 'github-actions' },
  name: nome,
  status,
  conclusion,
});

console.log('test-deploy-gate');

const ESPERADOS = esperadosDoGate();
const JOBS = nomesDeJobDoQuality();

checar('a allowlist do gate não está vazia', () => {
  assert.ok(ESPERADOS.length > 0, 'ESPERADOS vazio');
});

checar('a allowlist do gate cobre exatamente os jobs de quality.yml', () => {
  assert.deepEqual([...ESPERADOS].sort(), [...JOBS].sort());
});

checar('a allowlist não contém o nome do workflow', () => {
  assert.ok(
    !ESPERADOS.includes('Quality'),
    '"Quality" é o nome do workflow; check run tem nome de job e nunca casaria',
  );
});

/**
 * Mesma cadeia de garantia: o gate exige "Frontend foundation" verde, então o
 * que esse job NÃO roda é o que vai para produção sem gate nenhum. `test:unit`
 * e `test:openai` estavam em `test:harness` e nunca foram enumerados no
 * quality.yml — a suite de WhatsApp, jornada em obra no PLAN-034, era uma
 * delas. A lista do CI é escrita à mão; este teste impede que ela fique atrás.
 */
const suitesDoHarness = () => {
  const pkg = JSON.parse(readFileSync(join(ROOT, 'frontend', 'package.json'), 'utf8'));
  return pkg.scripts['test:harness']
    .split('&&')
    .map((s) => s.trim().replace(/^npm run /, ''))
    .filter(Boolean);
};

checar('quality.yml roda todas as suites de test:harness', () => {
  const noCi = new Set(
    (readFileSync(QUALITY_YML, 'utf8').match(/npm run (test:[a-z0-9:]+)/g) ?? []).map((m) =>
      m.replace('npm run ', ''),
    ),
  );
  const ausentes = suitesDoHarness().filter((s) => !noCi.has(s));
  assert.deepEqual(ausentes, [], `suites fora do CI: ${ausentes.join(', ')}`);
});

/**
 * O pre-push se declara "mesmo conjunto e mesma ordem do CI" — então tem que
 * ser verdade. Ele ficou com a mesma lacuna: whatsapp e openai não estavam
 * nem na lista do loop nem no CI.
 */
checar('hooks/pre-push roda todas as suites de test:harness', () => {
  const texto = readFileSync(join(ROOT, 'hooks', 'pre-push'), 'utf8');
  const cobertas = new Set(
    (texto.match(/npm run (?:")?(test:[a-z0-9:]+)/g) ?? []).map((m) =>
      m.replace(/npm run "?/, ''),
    ),
  );
  // As suites do loop aparecem como `npm run "test:$suite"`: os nomes vêm da
  // lista do `for`, não de chamadas literais.
  const loop = texto.match(/for suite in ([\s\S]*?); do/);
  assert.ok(loop, 'loop `for suite in ...` não encontrado no pre-push');
  for (const nome of loop[1].split(/[\s\\]+/).filter(Boolean)) {
    cobertas.add(`test:${nome}`);
  }
  const ausentes = suitesDoHarness().filter((s) => !cobertas.has(s));
  assert.deepEqual(ausentes, [], `suites fora do pre-push: ${ausentes.join(', ')}`);
});

/**
 * O job `deploy` é o único que recebe VPS_DEPLOY_KEY. Uma action de terceiro
 * numa tag móvel ali significa que quem controlar aquele repositório passa a
 * ver a chave da VPS — a tag pode ser reapontada sem que nada mude aqui.
 * Actions do próprio GitHub (`actions/*`) ficam de fora: a confiança já é a
 * mesma do runner.
 */
checar('actions de terceiro no job deploy estão pinadas por SHA', () => {
  const texto = readFileSync(DEPLOY_YML, 'utf8');
  const jobDeploy = texto.slice(texto.indexOf('\n  deploy:'));
  assert.ok(jobDeploy.length > 0, 'job `deploy` não encontrado');
  const naoPinadas = (jobDeploy.match(/uses:\s*\S+/g) ?? [])
    .map((u) => u.replace(/uses:\s*/, ''))
    .filter((u) => !u.startsWith('actions/'))
    .filter((u) => !/@[0-9a-f]{40}$/.test(u));
  assert.deepEqual(naoPinadas, [], `sem SHA: ${naoPinadas.join(', ')}`);
});

/**
 * Todo serviço do compose de produção que roda a imagem da api precisa de
 * DATABASE_URL apontando para o serviço `postgres`.
 *
 * Origem: `migrate` só tinha env_file. O alembic derivou a URL para
 * 127.0.0.1 (o padrão de fora do Compose) e o primeiro deploy real morreu com
 * "connection refused" — dentro da netns do container não há postgres em
 * loopback. Leitura textual, sem parser YAML: o compose é indentado em 2
 * espaços e cada serviço começa em `  nome:`.
 */
checar('todo serviço da imagem api no compose de produção aponta DATABASE_URL para postgres', () => {
  const texto = readFileSync(join(ROOT, 'docker-compose.prod.yml'), 'utf8');
  const servicos = texto.split(/\n(?=  [a-z][\w-]*:\n)/);
  const semUrl = servicos
    .filter((bloco) => /^  [\w-]+:\n/.test(bloco) && /-tianet-api:/.test(bloco))
    .filter((bloco) => !/DATABASE_URL: .*@postgres:5432\//.test(bloco))
    .map((bloco) => bloco.match(/^  ([\w-]+):/)[1]);
  assert.deepEqual(semUrl, [], `sem DATABASE_URL para @postgres: ${semUrl.join(', ')}`);
});

/**
 * Todo `COPY` do Dockerfile precisa sobreviver ao .dockerignore.
 *
 * Origem: o Dockerfile passou a copiar `scripts/deploy-gate.sh` para
 * `/app/deploy`, mas o .dockerignore exclui `scripts` inteiro. O arquivo nunca
 * esteve no contexto e o build da imagem `api` morreu em produção com
 * `"/scripts/deploy-gate.sh": not found` — depois da tag publicada, no job de
 * build, que é onde custa mais caro descobrir.
 *
 * Implementa a precedência do .dockerignore: a última regra que casa vence,
 * e `!` re-inclui.
 */
checar('todo COPY do Dockerfile sobrevive ao .dockerignore', () => {
  const dockerfile = readFileSync(join(ROOT, 'Dockerfile'), 'utf8');
  const regras = readFileSync(join(ROOT, '.dockerignore'), 'utf8')
    .split('\n')
    .map((l) => l.trim())
    .filter((l) => l && !l.startsWith('#'));

  // Em `COPY a b ./destino/`, o último token é o destino.
  const fontes = [...dockerfile.matchAll(/^COPY\s+(.+)$/gm)]
    .flatMap((m) => m[1].trim().split(/\s+/).slice(0, -1))
    .filter((f) => !f.startsWith('--'));

  const excluido = (caminho) => {
    let fora = false;
    for (const regra of regras) {
      const nega = regra.startsWith('!');
      const padrao = nega ? regra.slice(1) : regra;
      if (caminho === padrao || caminho.startsWith(`${padrao}/`)) fora = !nega;
    }
    return fora;
  };

  const perdidos = fontes.filter(excluido);
  assert.deepEqual(
    perdidos,
    [],
    `COPY de caminho excluído pelo .dockerignore: ${perdidos.join(', ')}`,
  );
});

const temJq = spawnSync('jq', ['--version'], { stdio: 'ignore' }).status === 0;
if (!temJq) {
  console.log('  AVISO  jq ausente: fixtures do programa jq não rodaram (o CI Linux roda)');
} else {
  checar('tudo success aprova', () => {
    const v = rodarJq({ check_runs: ESPERADOS.map((n) => run(n, 'completed', 'success')) }, ESPERADOS);
    assert.deepEqual(v, { ausentes: [], pendentes: [], reprovados: [] });
  });

  checar('frontend vermelho reprova', () => {
    const alvo = ESPERADOS.find((n) => n.startsWith('Frontend foundation'));
    assert.ok(alvo, 'nenhum check de frontend na allowlist');
    const v = rodarJq(
      {
        check_runs: ESPERADOS.map((n) =>
          run(n, 'completed', n === alvo ? 'failure' : 'success'),
        ),
      },
      ESPERADOS,
    );
    assert.deepEqual(v.reprovados, [`${alvo}=failure`]);
  });

  checar('check ausente não vira verde', () => {
    const [primeiro, ...resto] = ESPERADOS;
    const v = rodarJq({ check_runs: resto.map((n) => run(n, 'completed', 'success')) }, ESPERADOS);
    assert.deepEqual(v.ausentes, [primeiro]);
  });

  checar('check pendente não vira verde', () => {
    const [primeiro, ...resto] = ESPERADOS;
    const v = rodarJq(
      {
        check_runs: [
          run(primeiro, 'in_progress', null),
          ...resto.map((n) => run(n, 'completed', 'success')),
        ],
      },
      ESPERADOS,
    );
    assert.deepEqual(v.pendentes, [primeiro]);
    assert.deepEqual(v.reprovados, []);
  });

  checar('skipped e neutral não passam como success', () => {
    const [primeiro, ...resto] = ESPERADOS;
    for (const conclusao of ['skipped', 'neutral', 'cancelled', 'stale']) {
      const v = rodarJq(
        {
          check_runs: [
            run(primeiro, 'completed', conclusao),
            ...resto.map((n) => run(n, 'completed', 'success')),
          ],
        },
        ESPERADOS,
      );
      assert.deepEqual(v.reprovados, [`${primeiro}=${conclusao}`]);
    }
  });

  checar('check de outro app não conta como o exigido', () => {
    const runs = ESPERADOS.map((n) => run(n, 'completed', 'success'));
    runs[0].app = { slug: 'algum-app-de-terceiro' };
    const v = rodarJq({ check_runs: runs }, ESPERADOS);
    assert.deepEqual(v.ausentes, [ESPERADOS[0]]);
  });
}

/**
 * Validação da tag no gate da VPS.
 *
 * A chave de deploy é restrita com `command=` no authorized_keys, e nesse modo
 * o sshd entrega o comando do cliente em $SSH_ORIGINAL_COMMAND em vez de "$1".
 * O script lia só "$1" — todo deploy pela chave morreria em "uso: deploy".
 * Estas fixtures fixam as duas formas de entrada e o que precisa ser recusado.
 */
const GATE_SH = join(ROOT, 'scripts', 'deploy-gate.sh');
const temBash = spawnSync('bash', ['-c', 'true'], { stdio: 'ignore' }).status === 0;

if (!temBash) {
  console.log('  AVISO  bash ausente: validação de tag do gate não rodou (o CI Linux roda)');
} else {
  // Uma tag aceita segue o fluxo e para na ausência do .env.prod da VPS. Essa
  // mensagem é, portanto, a prova de que a tag passou pela validação.
  const ACEITA = /falta \/root\/tianet\/\.env\.prod/;

  const rodar = (args, env = {}) =>
    spawnSync('bash', [GATE_SH, ...args], {
      encoding: 'utf8',
      env: { ...process.env, ...env },
    });

  const casos = [
    ['tag válida como argumento', ['prod-v1.2.0'], {}, ACEITA],
    [
      'tag válida via SSH_ORIGINAL_COMMAND (chave restrita)',
      [],
      { SSH_ORIGINAL_COMMAND: '/opt/tianet/bin/deploy prod-v1.2.0' },
      ACEITA,
    ],
    ['sem tag em lugar nenhum', [], {}, /uso: deploy prod-vX\.Y\.Z/],
    ['tag fora do padrão', ['v1.2.0'], {}, /fora do padrão/],
    ['tag de branch não passa por tag de produção', ['master'], {}, /fora do padrão/],
    [
      'injeção pela SSH_ORIGINAL_COMMAND',
      [],
      { SSH_ORIGINAL_COMMAND: '/opt/tianet/bin/deploy prod-v1.0.0; rm -rf /' },
      /fora do padrão/,
    ],
    ['metacaractere colado na tag', ['prod-v1.0.0;evil'], {}, /caractere fora de/],
    ['espaço na tag', ['prod-v1.0.0 extra'], {}, /caractere fora de/],
  ];

  for (const [rotulo, args, env, esperado] of casos) {
    checar(`gate recusa/aceita: ${rotulo}`, () => {
      const r = rodar(args, env);
      const saida = `${r.stdout ?? ''}${r.stderr ?? ''}`;
      assert.match(saida, esperado, `saída inesperada: ${saida.trim()}`);
      assert.equal(r.status, 2, `exit code inesperado: ${r.status}`);
    });
  }

  /**
   * Roteamento de escopo do pre-push: quais gates cada caminho dispara.
   *
   * Extrai o `case` do próprio hook e roda contra fixtures — testar uma cópia
   * da regra em JS não provaria nada sobre o hook que de fato executa.
   *
   * O que este teste protege: classificar caminho de aplicação como tooling
   * (e deixar de rodar o gate que pegaria a quebra) é o erro caro aqui; o
   * inverso só custa tempo.
   */
  checar('pre-push roteia cada caminho para o gate certo', () => {
    const hook = readFileSync(join(ROOT, 'hooks', 'pre-push'), 'utf8');
    // `\r?\n`: o hook não tem extensão, e até o .gitattributes cobrir `hooks/*`
    // ele chegava em CRLF no worktree Windows.
    const bloco = hook.match(/for arquivo in \$ALTERADOS; do\r?\n([\s\S]*?\r?\n)done/);
    assert.ok(bloco, 'laço de classificação não encontrado no pre-push');

    const rotear = (arquivo) => {
      const script = [
        'TOCA_BACKEND=0',
        'TOCA_FRONTEND=0',
        `ALTERADOS='${arquivo}'`,
        'for arquivo in $ALTERADOS; do',
        bloco[1],
        'done',
        'echo "$TOCA_BACKEND$TOCA_FRONTEND"',
      ].join('\n');
      const r = spawnSync('bash', ['-c', script], { encoding: 'utf8' });
      assert.equal(r.status, 0, `bash falhou: ${r.stderr}`);
      return r.stdout.trim();
    };

    // arquivo -> "<backend><frontend>"
    const esperado = {
      'src/emprestimo/domain/credit/devedor.py': '10',
      'tests/unit/domain/test_devedor.py': '10',
      'migrations/versions/abc_x.py': '10',
      'pyproject.toml': '10',
      'frontend/src/app/app/page.tsx': '01',
      'docs/foundation/FOUNDATION-001-product-vision.md': '00',
      // contrato mora em docs/ mas quebra os dois lados
      'docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json': '11',
      // tooling: não entra em build nem runtime
      '.github/workflows/deploy.yml': '00',
      'scripts/ci/check-runs-veredito.jq': '00',
      'scripts/tests/test-deploy-gate.mjs': '00',
      'scripts/vps-install.sh': '00',
      // exceção: script Python de scripts/ mexe em migrations e no contrato
      'scripts/validate_migrations.py': '10',
      'scripts/export_openapi.py': '10',
      // desconhecido roda tudo, de propósito
      Dockerfile: '11',
      'docker-compose.prod.yml': '11',
      'arquivo-novo-que-ninguem-previu.xyz': '11',
    };

    const errados = Object.entries(esperado)
      .map(([arquivo, quer]) => [arquivo, quer, rotear(arquivo)])
      .filter(([, quer, tem]) => quer !== tem)
      .map(([arquivo, quer, tem]) => `${arquivo}: esperado ${quer}, obtido ${tem}`);
    assert.deepEqual(errados, [], errados.join('; '));
  });

  checar('o rollback não é código morto depois do handler de erro', () => {
    const texto = readFileSync(GATE_SH, 'utf8');
    // O defeito original: `trap 'falha "..."; rollback' ERR` — `falha` termina
    // em exit, então o rollback nunca rodava.
    assert.ok(
      !/trap\s+'falha[^']*rollback/.test(texto),
      'trap chama falha() antes de rollback(): o rollback vira código morto',
    );
    assert.match(texto, /trap\s+'ao_falhar'\s+ERR/, 'trap ERR não usa o handler ao_falhar');
  });
}

if (falhas.length > 0) {
  console.error(`\n${falhas.length} falha(s):`);
  for (const f of falhas) console.error(`  - ${f}`);
  process.exit(1);
}
console.log('test-deploy-gate: ok');
