# Auditoria AS-IS / TO-BE do Backend

**Data:** 2026-08-08
**Escopo:** backend do projeto `emprestimo`, incluindo documentacao, codigo, migrations, testes, qualidade e seguranca.
**Objetivo:** entender o estado atual, separar o que ja foi finalizado do que ainda precisa ser finalizado, e apontar o caminho minimo para voltar a um backend verificavel.

---

## 1. Parecer executivo

O backend tem desenho e implementacao avancados: EPIC-001 e EPIC-002 estao documentados, ha rotas FastAPI para Platform e Credit, camadas DDD estao presentes, os repositorios e Unit of Work existem, e a documentacao oficial do EPIC-002 registra certificacao tecnica.

Entretanto, o **AS-IS observado nesta auditoria** nao e o mesmo estado do gate certificado. A arvore local esta com alteracoes nao commitadas e o backend Python nao importa por erro de sintaxe em `src/emprestimo/domain/credit/devedor.py`. Por isso, no estado atual, o backend deve ser tratado como **em recuperacao tecnica**, nao como concluido.

O TO-BE imediato nao e uma feature nova. O proximo alvo correto e restaurar a confiabilidade: codigo importavel, suite coletando, migration alinhada ao ORM, `pytest` verde, `mypy` e `ruff` em baseline formal, e documentacao de gate reconciliada com a evidencia atual.

---

## 2. Fontes auditadas

### Documentos

- `docs/audits/audits/auditoria-as-is-to-be-ecossistema.md`
- `docs/audits/audits/GATE-TECNICO-EPIC-002-certificacao.md`
- `docs/governance/handoffs/2026-08-08-handoff-epic-002-certificado.md`
- `docs/audits/audits/vistoria-backend-2026-08-08.md`
- `docs/architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md`
- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`
- `docs/implementation/plans/PLAN-003-epic-002-cadastro-de-devedores.md`
- `docs/implementation/backlogs/PLAN-003-execution-backlog.md`

### Codigo e verificacoes

- Estrutura de `src/emprestimo`
- Migrations em `migrations/versions`
- Testes em `tests`
- `git status --short`
- `uv run pytest`
- `uv run mypy src`
- `uv run ruff check src tests`
- `npm run docs:validate`

---

## 3. AS-IS observado

### 3.1 Estado documental

| Area | Estado observado | Evidencia |
|---|---|---|
| Foundation | Congelada e extensa | `docs/foundation/FOUNDATION-001..009` |
| Arquitetura | ADRs centrais presentes | ADR-001, ADR-002, ADR-004, ADR-018 |
| EPIC-001 | Documentado e historicamente certificado | planos, backlogs e handoffs existentes |
| EPIC-002 | Documentado e certificado em gate | `GATE-TECNICO-EPIC-002-certificacao.md` |
| EPIC-006/IAM | Especificado em Product/ADR, nao implementado | ADR-004 e Product Platform |
| Validacao docs | Verde | `npm run docs:validate`: 134 OK, 47 avisos, 0 erros |

Leitura: a documentacao esta em bom estado estrutural. Ela e a parte mais estavel do projeto neste momento.

### 3.2 Estado do codigo

| Camada | AS-IS |
|---|---|
| Domain | Platform e Credit existem; `Devedor` esta sintaticamente quebrado no worktree atual |
| Application | Services de Tenant e Devedor existem, incluindo cadastro, consulta, atualizacao, estado e historico |
| Infrastructure | ORM, repositorios, UoW, auditoria e idempotencia existem |
| Presentation | FastAPI monta rotas de Platform e Credit; Devedor tem endpoints aninhados por Carteira |
| Migrations | Revisions `0001` a `0005` existem |
| Testes | Suite existe, mas nao coleta no estado atual |

### 3.3 Estado dos comandos de qualidade

| Comando | Resultado observado | Leitura |
|---|---|---|
| `npm run docs:validate` | 134 OK, 47 avisos, 0 erros | Governanca documental segue valida |
| `uv run pytest` | 16 erros de coleta | Backend nao esta executavel |
| `uv run mypy src` | 1 erro de sintaxe | Tipagem bloqueada antes da analise real |
| `uv run ruff check src tests` | 158 erros | Qualidade abaixo do gate atual |

### 3.4 Estado do worktree

Antes desta auditoria ja existiam alteracoes locais em arquivos de dominio, aplicacao, ORM, repositorios e testes. Tambem havia a vistoria criada em `docs/audits/audits/vistoria-backend-2026-08-08.md`.

Arquivos modificados antes desta auditoria:

- `docs/domain/credit/aggregates/DOMAIN-020-aggregate-devedor.md`
- `src/emprestimo/application/atualizacao_devedor.py`
- `src/emprestimo/domain/credit/contato.py`
- `src/emprestimo/domain/credit/devedor.py`
- `src/emprestimo/domain/credit/ports.py`
- `src/emprestimo/domain/platform/usuario.py`
- `src/emprestimo/infrastructure/db/orm.py`
- `src/emprestimo/infrastructure/repositories/__init__.py`
- `tests/unit/domain/test_contato.py`
- `tests/unit/domain/test_devedor.py`
- `tests/unit/domain/test_usuario.py`

Leitura: a auditoria deve tratar o codigo atual como uma arvore em andamento, nao como o ultimo estado certificado.

---

## 4. O que ja foi finalizado

### 4.1 Finalizado com boa evidencia documental

| Item | Status | Observacao |
|---|---|---|
| Arquitetura documental | Finalizado | `MILESTONE.md` congela a estrutura de `docs/` |
| Validador documental | Finalizado | `docs:validate` passa com 0 erros |
| EPIC-001 / Tenant Management | Finalizado historicamente | Documentos e codigo existem para criacao, consulta, listagem, atualizacao e estado |
| EPIC-002 / Cadastro de Devedores | Finalizado documentalmente | Gate e handoff afirmam certificacao |
| ADR-004 / IAM | Decisao finalizada | Define JWT, refresh token, RBAC e Platform Context |
| ADR-018 / Identidade externa do Devedor | Decisao finalizada | Rotas de Devedor aninhadas por Carteira |

### 4.2 Implementado, mas precisa ser reverificado

| Item | Por que precisa reverificar |
|---|---|
| Devedor Domain/Application/API | A suite nao coleta por erro em `devedor.py` |
| Soft-delete de Contato | ORM/testes apontam `removido_em`, mas migration `0004` nao cria a coluna |
| Idempotencia por escopo | Migration `0005` existe, mas a suite atual nao passa para confirmar regressao |
| Repositorios de Credit | Codigo existe, mas nao pode ser exercitado enquanto o import falha |
| Cobertura de 98% do EPIC-002 | E historica/documentada, nao observavel no worktree atual |

### 4.3 Nao finalizado

| Item | Status atual |
|---|---|
| EPIC-006/IAM implementado | Pendente |
| Protecao de endpoints por token | Pendente |
| Autorizacao RBAC | Pendente |
| Resolucao de Principal/Tenant por token | Pendente |
| Bloqueio cross-tenant real | Pendente |
| CI/CD | Nao evidenciado no repositorio atual |
| Observabilidade alem de `/health` basico | Pendente |
| Core financeiro: contratos, emprestimos, parcelas, pagamentos, motor financeiro | Documentado parcialmente, nao implementado como backend operacional |

---

## 5. Gaps AS-IS -> TO-BE

### G1. Gap critico de executabilidade

**AS-IS:** `uv run pytest` falha na coleta por `SyntaxError` em `src/emprestimo/domain/credit/devedor.py:274`.

**TO-BE:** todos os modulos importam, a suite coleta e falhas passam a representar comportamento, nao sintaxe.

**Acao minima:** corrigir o bloco de `remover_contato`, rodar teste unitario de `Devedor`, depois suite completa.

### G2. Gap de persistencia: `Contato.removido_em`

**AS-IS:** `ContatoORM` e o repositorio usam `removido_em`; a migration `0004_devedor_contato.py` nao cria essa coluna.

**TO-BE:** schema do banco, ORM, dominio, repositorio e testes concordam.

**Acao minima:** criar migration aditiva para `contato.removido_em` ou reverter formalmente a decisao de soft-delete. Pela documentacao atual do codigo, a direcao recomendada e manter soft-delete e adicionar a migration.

### G3. Gap de qualidade automatizada

**AS-IS:** `ruff` mostra 158 achados e `mypy` nao passa da sintaxe.

**TO-BE:** gate claro e repetivel. Ideal: `pytest`, `ruff`, `black`, `mypy`, `docs:validate` verdes. Alternativa aceitavel: baseline formalizado, com lista nominal do que e legado.

**Acao minima:** depois da sintaxe, separar erros introduzidos dos legados e limpar o escopo atual.

### G4. Gap de reconciliacao documental

**AS-IS:** gate e handoff afirmam EPIC-002 certificado; auditoria atual observa worktree quebrado.

**TO-BE:** documentacao diferencia claramente "estado certificado historico" de "estado atual da arvore local".

**Acao minima:** apos recuperar a suite, emitir retificacao ou nova nota de gate com comandos atuais.

### G5. Gap de seguranca para dado real

**AS-IS:** endpoints nao exigem token nem resolvem Tenant do Principal. A propria ADR-004 reconhece retrofit em endpoints protegidos.

**TO-BE:** 13 de 14 endpoints protegidos; `/health` publico; sem token retorna 401; usuario sem permissao retorna 403; recurso de outro Tenant retorna 404 indistinguivel.

**Acao minima:** abrir implementacao do EPIC-006/IAM antes de expor backend para dados reais.

### G6. Gap de produto/core financeiro

**AS-IS:** o backend cobre plataforma e cadastro, mas nao cobre ainda o nucleo operacional de credito: contrato, emprestimo, parcelas, pagamentos e motor financeiro.

**TO-BE:** depois de IAM, avancar para EPICs de operacao de credito com rastreabilidade Product -> Domain -> Implementation -> Tests.

**Acao minima:** nao iniciar core financeiro enquanto o gate tecnico atual estiver quebrado.

---

## 6. TO-BE recomendado

### TO-BE 0: backend recuperado

Estado esperado:

- `src/emprestimo/domain/credit/devedor.py` importa sem erro.
- `uv run pytest` coleta todos os testes.
- `uv run mypy src` executa analise real.
- `uv run ruff check src tests` tem 0 erro ou baseline documentado.
- `npm run docs:validate` segue com 0 erro.
- Migration de `Contato.removido_em` resolvida.

Esse e o TO-BE mais urgente.

### TO-BE 1: EPIC-002 novamente certificavel

Estado esperado:

- Features FEATURE-005..008 verdes em dominio, application, infrastructure e API.
- Migrations `0001..head` validadas em ciclo upgrade/downgrade/upgrade.
- Idempotencia por `(chave, escopo)` provada em teste.
- Soft-delete de Contato provado em teste de repositorio/application.
- Gate tecnico atualizado com resultados atuais, nao apenas historicos.

### TO-BE 2: backend seguro para dado real

Estado esperado:

- EPIC-006/IAM implementado.
- JWT de acesso curto e refresh token persistido, conforme ADR-004.
- RBAC por Perfil.
- Tenant resolvido do Principal autenticado.
- Endpoints protegidos por default; `/health` publico.
- Testes de 401, 403 e 404 cross-tenant.

### TO-BE 3: backend de credito operacional

Estado esperado:

- Contratos de credito implementados.
- Emprestimos, parcelas e pagamentos implementados.
- Motor financeiro implementado e testado.
- Auditoria e idempotencia mantidas nas escritas.
- Observabilidade e operacao minimamente prontas.

---

## 7. Roadmap de fechamento recomendado

### Fase 1: recuperacao tecnica imediata

1. Corrigir sintaxe de `Devedor.remover_contato`.
2. Rodar `uv run pytest tests/unit/domain/test_devedor.py`.
3. Rodar `uv run pytest` para revelar falhas reais.
4. Corrigir schema de `Contato.removido_em` via migration aditiva.
5. Rodar ciclo de migration.

### Fase 2: gate de qualidade

1. Rodar `ruff`, `black`, `mypy`, `pytest` e `docs:validate`.
2. Corrigir o que for do escopo atual.
3. Formalizar qualquer baseline legado que sobrar.
4. Atualizar gate/handoff com evidencia atual.

### Fase 3: seguranca

1. Implementar EPIC-006/IAM conforme ADR-004.
2. Fazer retrofit dos endpoints existentes.
3. Adicionar testes de contrato para ausencia de token, permissao insuficiente e cross-tenant.

### Fase 4: produto de credito

1. Abrir proximo EPIC operacional apenas apos gate verde.
2. Seguir o fluxo Product -> Discovery -> SDD -> Agent Loop -> Implementacao -> Review.
3. Implementar contratos, emprestimos, parcelas, pagamentos e motor financeiro com migrations e testes.

---

## 8. Matriz de decisao

| Pergunta | Resposta curta |
|---|---|
| O backend esta concluido hoje? | Nao, o worktree atual nao passa da coleta de testes. |
| O EPIC-001 parece finalizado? | Sim, historicamente/documentalmente. Deve ser regressado apos corrigir sintaxe. |
| O EPIC-002 foi finalizado? | Documentalmente sim; no worktree atual, precisa ser recuperado e recertificado. |
| Podemos iniciar feature nova agora? | Nao recomendado. Primeiro restaurar gate tecnico. |
| Podemos ir para producao/dado real? | Nao. IAM esta pendente. |
| Qual e o primeiro trabalho? | Corrigir `devedor.py` e alinhar `contato.removido_em` com migration. |

---

## 9. Parecer final

O backend esta em um ponto bom de arquitetura, mas em um ponto ruim de confiabilidade local. A documentacao mostra que houve um estado certificado; a auditoria atual mostra que esse estado nao esta reproduzivel na arvore de trabalho de 2026-08-08.

Portanto, o caminho mais seguro e tratar o proximo ciclo como **recuperacao e recertificacao**, nao como expansao. Depois que o gate voltar a ser observavel, a ordem recomendada e EPIC-006/IAM antes do core financeiro, porque sem IAM o cadastro ja implementado continua funcional, mas nao seguro para dado real.
