# 2026-09-10 — Handoff: o deploy que nunca tinha rodado

**Versao:** 1.0.0

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

1. **O gate `precondicoes` falhava 100% das vezes.** O filtro jq era
   interpolado dentro de aspas duplas e o `!= "completed"` chegava ao jq sem
   aspas: `jq: error: completed/0 is not defined`. O `if ! CHECKS=$(gh api ...)`
   capturava e reportava **"API de check-runs falhou (HTTP/permissao/rede)"** —
   e foi por isso que os dois `fix(ci)` anteriores foram atrás de permissão e de
   rede. Nenhum deploy jamais passou desse passo.

2. **O rollback era código morto.** `trap 'falha "..."; rollback' ERR`, e
   `falha` termina em `exit`. Todo deploy quebrado ficaria de pé na imagem nova
   com o log dizendo "rollback tentado".

3. **O gate aprovava com o frontend inteiro vermelho.** A allowlist ancorava
   `^Frontend foundation$`, mas os check runs da matriz se chamam
   `Frontend foundation (ubuntu-latest)`. E `Quality`, também na lista, é nome
   de workflow — check run tem nome de job. Na prática o gate exigia 2 de 4.

Os três só existiam porque **o pipeline nunca rodou uma vez**. Revisão de código
não os pegou em nenhuma das rodadas anteriores; execução pegaria na primeira. É
o mesmo padrão do handoff anterior — um verde que não provava nada — um nível
acima: aqui o verde nem chegava a existir, e a mensagem de erro apontava para o
lugar errado.

---

# 2. O que fechou

| Item | O quê |
|---|---|
| **3 bloqueantes** | Provados em execução antes de corrigir, e cada correção com mutação verificada |
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
