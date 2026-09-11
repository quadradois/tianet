# 2026-09-10 — Handoff: o deploy que nunca tinha rodado

**Versao:** 1.1.0

**Status:** PLAN-034 concluído. IMP-359 Slice 3 com **código pronto e revisado,
execução pendente** dos segredos do proprietário.

**Periodo coberto:** 2026-09-10.

**Base:** `origin/master` em `170b3ed` (merge do PR #63). PR #64 aberto e
**CLEAN**, com os 4 checks verdes; merge é do fundador.

**Substitui:** `2026-09-04-handoff-imp-371-e-os-testes-que-nao-provavam-nada.md`.

---

# 1. A lição do dia: código de deploy nunca executado é ficção

O pipeline de deploy existia inteiro desde o Slice 3 — workflow, compose de
produção, gate na VPS, environment com aprovação. Parecia pronto. Uma revisão
completa achou **três defeitos bloqueantes**, e nenhum dos três era sutil:

1. **O gate `precondicoes` quebraria no próximo deploy.** O filtro jq era
   interpolado dentro de aspas duplas e o `!= "completed"` chegava ao jq sem
   aspas. Medido nas duas implementações: `jq 1.7.1` responde
   `completed/0 is not defined`, e o `--jq` do `gh` (gojq) responde
   `function not defined: completed/0`, saindo com **exit 1 e stdout vazio**.
   O `if ! CHECKS=$(gh api ...)` capturaria isso e reportaria
   **"API de check-runs falhou (HTTP/permissao/rede)"** — uma mensagem que
   aponta para rede e permissão quando o problema é sintaxe.

   > **Correção de registro (2026-09-11).** A primeira versão deste handoff
   > dizia que o gate "falhava 100% das vezes" e que "nenhum deploy jamais
   > passou desse passo por causa disso". Errado, e a evidência estava
   > disponível: o único run de deploy que falhou (`34517798801`,
   > 2026-09-10T19:00) usou o workflow **do commit da tag** `prod-v1.0.0`
   > (`70a0552`), que ainda tinha o filtro anterior — funcional. Ele executou e
   > reprovou por conteúdo: `Quality com falha no commit: ,failure,success`,
   > isto é, um check `failure` e um `null`. O jq quebrado entrou depois, em
   > `55ab5d1`, que **não** está na tag; nenhuma tag foi criada desde então,
   > então o defeito nunca chegou a rodar. Era um defeito latente, não uma
   > falha observada — e a frase sobre "os dois `fix(ci)` anteriores foram
   > atrás do alvo errado" era especulação apresentada como fato.

2. **O rollback era código morto.** `trap 'falha "..."; rollback' ERR`, e
   `falha` termina em `exit`. Todo deploy quebrado ficaria de pé na imagem nova
   com o log dizendo "rollback tentado".

3. **O gate aprovava com o frontend inteiro vermelho.** A allowlist ancorava
   `^Frontend foundation$`, mas os check runs da matriz se chamam
   `Frontend foundation (ubuntu-latest)`. E `Quality`, também na lista, é nome
   de workflow — check run tem nome de job. Na prática o gate exigia 2 de 4.

Os três só existiam porque **o pipeline quase nunca rodou** — uma única
execução, e ela morreu antes do build. Revisão de código não os pegou em
nenhuma das rodadas anteriores; execução pegaria na primeira.

A correção de registro acima vale como lição própria, e é do mesmo tipo que o
handoff anterior descreve. Lá, um teste verde não provava o que eu achava que
provava. Aqui, reproduzi o defeito num teste local, vi que quebrava, e daí
**inferi** a história de que ele vinha causando as falhas observadas — sem
olhar o log do run, que estava a um comando de distância e contava outra
coisa. Reproduzir um defeito prova que ele existe; não prova que foi ele que
causou o que você viu.

---

# 2. O que fechou

| Item | O quê |
|---|---|
| **3 bloqueantes** | Cada um reproduzido localmente antes de corrigir, e cada correção com mutação verificada. Reproduzido ≠ observado em produção: ver a correção de registro na §1 |
| **Cobertura** | `test:whatsapp` e `test:openai` estavam em `test:harness` e fora do CI **e** do pre-push — a jornada do PLAN-034 era a única sem gate |
| **Frontend em produção** | `compose.prod` publicava só 8000; o frontend escuta 3000 na netns da api. O Caddy não tinha destino |
| **Artefatos presos à tag** | A imagem carrega `/app/deploy`; o gate compara digests e recusa (exit 3) antes de tocar produção |
| **Health** | Cobria 1 serviço de 5. Worker em crash-loop saía como `DEPLOY-OK` |
| **Chave restrita** | A tag nunca chegava ao gate: com `command=` o sshd entrega em `$SSH_ORIGINAL_COMMAND`, não em `$1` |
| **Supply chain** | `appleboy/ssh-action@v1`, tag móvel, no único job que recebe `VPS_DEPLOY_KEY`. Pinada por SHA |
| **Governança** | `master` **não tinha** branch protection nem ruleset |

---

# 3. A governança que não existia

O comentário no `deploy.yml` afirma que a suíte tem "porta de entrada: PR +
push em master, **com branch protection**". Não havia. Dava para dar push
direto em `master` e para mergear PR com o CI vermelho.

Aplicado, com autorização do fundador e verificado por leitura da API:

- `master`: PR obrigatório (0 aprovações — ele é solo), os 4 checks nominais,
  `strict: true`, sem force push, sem deleção. `enforce_admins: false` por
  escolha — com um único mantenedor, `true` transforma emergência em impasse.
- environment `production`: `deployment_branch_policy` restrita a tags
  `prod-v*`, revisor preservado.

O PR #64 saiu de `BLOCKED` para `CLEAN` só quando os 4 checks fecharam — a
proteção foi observada funcionando, não presumida.

---

# 4. Onde parou

O caminho crítico agora é **um item, e é do fundador**: Slice 1b, os valores
dos segredos em `/root/tianet/.env.prod`. Sem eles o gate morre no `pull` e
nenhum ensaio de deploy acontece.

Entregue para quando os segredos entrarem:

- `scripts/vps-install.sh` — extrai os artefatos da **própria imagem** da tag
  (não do git, para não instalar arquivo de commit diferente do que gerou a
  imagem), guarda a versão anterior e confere os digests;
- [`docs/operations/deploy-producao.md`](../../operations/deploy-producao.md) —
  as seis portas do fluxo, pré-requisitos, deploy, os três desfechos distintos
  de rollback e a tabela de recusas do gate.

---

# 5. Limites conhecidos, escritos de propósito

- **O rollback volta imagem, não schema.** Um deploy que migrou deixa o schema
  à frente do código antigo. Isso só é seguro porque migrations são aditivas
  com downgrade reversível (SPEC-004, regra 8). Backup e restore ensaiados são
  o Slice 4 e **não existem** — até lá o rollback depende dessa regra e de mais
  nada. Produção com dado real antes do Slice 4 é risco aceito, não coberto.
- **Nenhum deploy foi executado.** Tudo acima é código revisado e testado por
  guardrail, não ensaio observado. O Slice 3 só fecha com deploy real,
  `docker kill` e rollback cronometrado contra o RTO de 15 min.
- **`enforce_admins: false`** é uma porta que o próprio fundador pode
  atravessar. Deliberado.

---

# 6. Pendências preservadas, não resolvidas

- **`CONTRIBUTING.md`** está modificado no working tree e não é desta sessão.
  Preservado conforme o AGENTS.md. A alteração institui revisão de workflow
  antes do merge — regra que se aplica justamente ao PR #64.
- **Worktree `d9c1`** (`~/.codex/worktrees/d9c1/emprestimo`): 111 arquivos
  sujos. A investigação mostrou **87 idênticos ao que já está em master**, 13
  divergentes, 8 `.pyc` (lixo), e **3 documentos de discovery de 2026-09-09 que
  não existem em master** — pesquisa de provedores LLM (NVIDIA Nemotron,
  OmniRoute, OpenRouter, 389 linhas) diretamente ligada à DR-005. Não é lixo:
  é trabalho não commitado. Nada foi apagado.
- **Worktree `4927`**: 1 arquivo (`contratos.spec.ts`, +6 linhas).

---

# 7. Próximo passo

1. Merge do PR #64.
2. Fundador preenche `/root/tianet/.env.prod` (Slice 1b).
3. `vps-install.sh` na VPS, primeira tag `prod-v*`, ensaio de deploy com
   rollback cronometrado — o que fecha o Slice 3 de verdade.
4. Slice 4 (backup/restore) antes de qualquer dado real de cliente.
