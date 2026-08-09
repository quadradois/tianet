# PLAN-004 - Plano de Implementacao Prioritario do Backend

**ID:** PLAN-004

**Versao:** 1.1.0

**Status:** Proposto

---

# 1. Contexto

Este plano organiza as prioridades de implementacao do backend apos a auditoria
AS-IS/TO-BE de 2026-08-08.

O projeto possui EPIC-001 e EPIC-002 documentados e historicamente certificados,
mas o estado atual do worktree nao e reproduzivel: `uv run pytest` falha na
coleta por erro de sintaxe em `src/emprestimo/domain/credit/devedor.py`, e ha
divergencia entre o ORM de `Contato` e a migration `0004_devedor_contato.py`
quanto ao campo `removido_em`.

Assim, a prioridade nao e abrir uma feature nova. A ordem correta e:

1. recuperar a executabilidade do backend;
2. recertificar o EPIC-002 com evidencia atual;
3. fechar as suites de teste que ainda nao existem ou nao provam os riscos
   encontrados;
4. implementar o EPIC-006/IAM antes de qualquer exposicao com dado real;
5. so entao preparar o proximo ciclo do roadmap, com Comercial antes de
   Contratos e Motor Financeiro.

---

# 2. Referencias

- `docs/audits/audits/auditoria-as-is-to-be-backend-2026-08-08.md`;
- `docs/audits/audits/vistoria-backend-2026-08-08.md`;
- `docs/audits/audits/GATE-TECNICO-EPIC-002-certificacao.md`;
- `docs/governance/handoffs/2026-08-08-handoff-epic-002-certificado.md`;
- `docs/implementation/plans/PLAN-003-epic-002-cadastro-de-devedores.md`;
- `docs/implementation/backlogs/PLAN-003-execution-backlog.md`;
- `docs/architecture/adrs/ADR-001-stack-tecnologica-oficial-mvp.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`;
- `docs/architecture/adrs/ADR-018-identidade-externa-do-devedor.md`;
- `docs/product/platform/epics/EPIC-006-iam.md`;
- `docs/product/platform/features/FEATURE-009-autenticar-usuario.md`;
- `docs/product/platform/features/FEATURE-010-gerir-credenciais.md`;
- `docs/product/platform/features/FEATURE-011-gerir-perfis-e-permissoes.md`;
- `docs/product/platform/features/FEATURE-012-autorizar-requisicao.md`.

---

# 3. Situacao Atual

## 3.1 Finalizado com evidencia documental

- Arquitetura documental congelada e validavel.
- Validador documental ativo (`npm run docs:validate`).
- EPIC-001 documentado e historicamente entregue.
- EPIC-002 documentado e historicamente certificado.
- ADR-004 aceita, definindo JWT, refresh token, RBAC e IAM no Platform Context.
- ADR-018 aceita, definindo identidade externa do Devedor por Carteira.

## 3.2 Implementado, mas nao verificavel agora

- Rotas de Platform e Credit existem.
- Services de Tenant e Devedor existem.
- Repositorios SQLAlchemy e Unit of Work existem.
- Migrations `0001` a `0005` existem.
- Testes unitarios, integracao e API existem, mas a suite nao coleta.

## 3.3 Bloqueios atuais

| ID | Bloqueio | Evidencia | Severidade |
|---|---|---|---|
| B-001 | `Devedor` nao importa por erro de sintaxe | `uv run pytest` e `uv run mypy src` | Critica |
| B-002 | `ContatoORM.removido_em` nao existe na migration `0004` | comparacao ORM x Alembic | Critica |
| B-003 | `ruff` abaixo do gate declarado | 158 achados | Alta |
| B-004 | Gate/handoff dizem certificado, mas estado local nao reproduz | auditorias 2026-08-08 | Alta |
| B-005 | IAM nao implementado | ADR-004 e EPIC-006 | Alta para producao |

---

# 4. Objetivos do Plano

## Objetivo 1 - Recuperar executabilidade

O backend deve voltar a importar e a suite deve voltar a coletar.

## Objetivo 2 - Recertificar EPIC-002

O Cadastro de Devedores deve voltar a ter evidencia atual, nao apenas historica.

## Objetivo 3 - Fechar lacunas de testes

As suites devem provar os defeitos encontrados: soft-delete, migration, idempotencia
por escopo, wiring real de dependencias, isolamento Carteira-Devedor e regressao do
EPIC-001.

## Objetivo 4 - Implementar IAM antes de dado real

O backend so deve ser tratado como pronto para dado real quando EPIC-006 proteger
os endpoints, resolver Principal/Tenant e aplicar RBAC.

## Objetivo 5 - Preparar proximo ciclo de credito

Depois da recuperacao, do IAM e do P4 operacional, o projeto pode voltar ao
roadmap de credito. A ordem corrigida e: Comercial primeiro, Contratos depois,
e apenas entao Emprestimos, Parcelas, Pagamentos e Motor Financeiro.

---

# 5. Ordem de Prioridade

## P0 - Recuperacao tecnica imediata

**Resultado esperado:** codigo importavel, teste unitario de Devedor executando e
falhas reais visiveis.

Tarefas:

1. Corrigir o bloco `Devedor.remover_contato`.
2. Rodar `uv run pytest tests/unit/domain/test_devedor.py`.
3. Rodar `uv run pytest` para obter o mapa real de falhas depois da coleta.
4. Rodar `uv run mypy src`.
5. Rodar `uv run ruff check src tests`.

Suites de teste necessarias:

| Suite | Arquivo alvo | Objetivo |
|---|---|---|
| Unit domain | `tests/unit/domain/test_devedor.py` | provar `remover_contato`, estado inativo, atualizacao e invariantes |
| Unit domain | `tests/unit/domain/test_contato.py` | provar `Contato.remover()` idempotente e `removido_em` |
| Smoke import | novo teste ou comando dedicado | garantir que `emprestimo.presentation.api.main` importa |

## P1 - Persistencia e migration de soft-delete

**Resultado esperado:** schema, ORM, repositorio e dominio concordam sobre
`contato.removido_em`.

Tarefas:

1. Confirmar decisao: Contato removido e soft-delete, nao DELETE fisico.
2. Criar migration aditiva `0006_contato_removido_em.py`.
3. Atualizar testes de repositorio para gravar, ler e listar Contato removido.
4. Garantir que consultas publicas nao retornam contatos removidos quando a regra
   assim exigir.
5. Executar ciclo Alembic upgrade/downgrade/upgrade em banco dedicado.

Suites de teste necessarias:

| Suite | Arquivo alvo | Objetivo |
|---|---|---|
| Migration | novo `tests/integration/migrations/test_contato_removido_em.py` | provar coluna criada, downgrade reversivel e schema coerente |
| Repository | `tests/integration/repositories/test_devedor_repository.py` | provar persistencia e leitura de soft-delete |
| Application | `tests/integration/application/test_devedor_application.py` | provar atualizacao substitui contatos sem perda indevida de historico |
| API | `tests/integration/api/test_api_devedores.py` | provar contrato HTTP apos remover contato |

## P2 - Recertificacao do EPIC-002

**Resultado esperado:** FEATURE-005..008 voltam a ser verificaveis na arvore atual.

Tarefas:

1. Rodar suite completa: `uv run pytest`.
2. Rodar cobertura se o gate continuar exigindo 90%+ nos modulos do EPIC-002.
3. Rodar `uv run ruff check src tests`.
4. Rodar `uv run black --check src tests`.
5. Rodar `uv run mypy src`.
6. Rodar `npm run docs:validate` e `npm run docs:test`.
7. Emitir novo gate ou retificacao do gate tecnico do EPIC-002 com comandos atuais.

Suites de teste necessarias:

| Suite | Arquivo alvo | Objetivo |
|---|---|---|
| Regression EPIC-001 | `tests/integration/api/test_api.py` e suites Platform | garantir que Tenant nao regrediu |
| API contract EPIC-002 | `tests/integration/api/test_api_devedores.py` | validar 201/200/400/404/409/422 |
| Dependency wiring | `tests/integration/api/test_dependencies_wiring.py` | exercitar providers reais sem override |
| Idempotencia | application + repository | provar replay, conflito em andamento e conflito de hash por escopo |
| Auditoria | application + historico | provar inicio/sucesso/falha e historico cadastral |

## P3 - EPIC-006/IAM minimo de seguranca

**Resultado esperado:** backend protegido para uso com dado real controlado.

Tarefas:

1. Criar plano tecnico detalhado do EPIC-006 a partir da ADR-004.
2. Modelar Credencial, Sessao/RefreshToken, Perfil e Permissao no Platform Context.
3. Criar migrations aditivas para credenciais, refresh tokens, perfis, permissoes
   e associacoes.
4. Implementar FEATURE-010 antes de FEATURE-009 quando necessario para permitir
   usuario com credencial definida.
5. Implementar FEATURE-009: login, refresh e logout.
6. Implementar FEATURE-011: perfis e permissoes.
7. Implementar FEATURE-012: middleware/dependencies de autenticacao, Principal,
   RBAC e bloqueio cross-tenant.
8. Fazer retrofit dos endpoints existentes.

Suites de teste necessarias:

| Suite | Arquivo alvo | Objetivo |
|---|---|---|
| Unit domain IAM | novos `tests/unit/domain/test_credencial.py`, `test_perfil.py`, `test_permissao.py`, `test_sessao.py` | provar invariantes de seguranca |
| Unit application IAM | novos `tests/unit/application/test_autenticacao.py`, `test_credenciais.py`, `test_autorizacao.py` | provar casos de uso sem banco |
| Integration IAM | novos `tests/integration/application/test_iam.py` | provar transacao, auditoria e revogacao de refresh |
| API auth | novo `tests/integration/api/test_api_auth.py` | login, refresh, logout, 401 uniforme |
| API authorization | novo `tests/integration/api/test_api_authorization.py` | 403 sem permissao, 404 cross-tenant |
| API retrofit | novo `tests/integration/api/test_api_protected_endpoints.py` | 13 endpoints recusam sem token; `/health` publico |
| Security regression | novo `tests/integration/api/test_cross_tenant_isolation.py` | dois Tenants reais, zero vazamento |

## P4 - Operacao e automacao de qualidade

**Resultado esperado:** checks deixam de depender de memoria local.

Tarefas:

1. Criar pipeline CI com `pytest`, `ruff`, `black`, `mypy`, `docs:validate` e
   `docs:test`.
2. Adicionar alvo ou script para ciclo de migration em banco dedicado.
3. Melhorar `/health` para verificar banco quando apropriado.
4. Padronizar baseline de `ruff`/`mypy`, se houver divida aceita.
5. Documentar runbook local de verificacao.

Suites de teste necessarias:

| Suite | Arquivo alvo | Objetivo |
|---|---|---|
| CI smoke | workflow futuro | garantir checks em PR |
| Healthcheck | `tests/integration/api/test_api.py` ou novo arquivo | provar `/health` publico e dependencia de DB quando habilitada |
| Docs validator | `scripts/tests/*` | manter governanca documental |

## P5 - Proximo ciclo de credito

**Resultado esperado:** iniciar o SDD do proximo ciclo somente depois de backend
seguro e gates operacionais reproduziveis.

Tarefas futuras:

1. Abrir Discovery/SDD do Epico 003 Comercial.
2. Definir fronteiras entre Comercial, Contratos e Motor Financeiro.
3. Planejar suites de dominio, aplicacao, API, autorizacao e migrations do
   ciclo Comercial antes de codigo.
4. Preservar Contratos e Motor Financeiro como ciclos posteriores.

Suites de teste necessarias:

| Suite | Objetivo |
|---|---|
| Unit domain Comercial | proposta, simulacao, estado comercial e invariantes |
| Property/table tests | cenarios de simulacao sem calculo financeiro definitivo fora do Motor |
| Integration application | criacao, consulta, aprovacao/reprovacao e auditoria de propostas |
| API contract | endpoints comerciais e erros esperados |
| Authorization regression | RBAC comercial e bloqueio cross-tenant |

---

# 6. Gates por Fase

| Fase | Gate minimo para avancar |
|---|---|
| P0 -> P1 | `test_devedor.py` passa e suite completa coleta |
| P1 -> P2 | migration de `removido_em` validada e testes de repositorio passam |
| P2 -> P3 | `pytest`, `mypy`, `ruff`, `black`, `docs:validate`, `docs:test` verdes ou baseline formal |
| P3 -> P4 | endpoints protegidos, 401/403/404 testados, cross-tenant bloqueado |
| P4 -> P5 | CI reproduz os gates localmente e o proximo ciclo respeita Comercial antes de Contratos/Motor |

---

# 7. Suites que Ainda Nao Existem ou Precisam Ser Criadas

| Prioridade | Suite | Motivo |
|---|---|---|
| Alta | `tests/integration/migrations/test_contato_removido_em.py` | provar que Alembic e ORM estao alinhados |
| Alta | `tests/integration/api/test_api_protected_endpoints.py` | provar que endpoints recusam chamada sem token |
| Alta | `tests/integration/api/test_cross_tenant_isolation.py` | provar isolamento real entre Tenants |
| Alta | `tests/integration/api/test_api_authorization.py` | provar 403 por falta de permissao e 404 cross-tenant |
| Alta | `tests/integration/api/test_api_auth.py` | provar login, refresh e logout |
| Media | `tests/unit/domain/test_credencial.py` | provar hash, validade e ausencia de texto legivel |
| Media | `tests/unit/domain/test_perfil.py` | provar RBAC e estado do Perfil |
| Media | `tests/unit/domain/test_permissao.py` | provar catalogo de permissoes |
| Media | `tests/unit/domain/test_sessao.py` | provar refresh token revogavel |
| Media | `tests/integration/application/test_iam.py` | provar IAM com UoW e auditoria |
| Media | teste smoke de import da API | evitar novo erro de sintaxe chegar tarde |
| Baixa | suites do proximo ciclo de credito | so depois de IAM, recertificacao e P4 operacional |

---

# 8. Riscos e Mitigacoes

| Risco | Impacto | Mitigacao |
|---|---|---|
| Corrigir sintaxe revelar muitas falhas reais | Alto | tratar P0 como fase de descoberta controlada |
| Migration de soft-delete conflitar com dados existentes | Medio | migration aditiva nullable e ciclo Alembic |
| Gate historico continuar divergente do estado atual | Alto | emitir retificacao baseada em comandos atuais |
| IAM crescer demais | Alto | dividir FEATURE-009..012 e testar por contrato |
| Testes de seguranca usarem dublês demais | Alto | incluir integracao com dois Tenants reais |
| Contratos ou Motor Financeiro iniciar antes de Comercial | Alto | bloquear P5 ate o plano pos-IAM/P4 respeitar a ordem do roadmap |

---

# 9. Definicao de Pronto do Backend Recuperado

O backend recuperado sera considerado pronto para avancar quando:

- `uv run pytest` passar;
- `uv run ruff check src tests` estiver verde ou com baseline aceito;
- `uv run black --check src tests` passar;
- `uv run mypy src` estiver verde ou com baseline aceito;
- `npm run docs:validate` passar com 0 erros;
- `npm run docs:test` passar;
- migrations forem validadas em ciclo upgrade/downgrade/upgrade;
- gate tecnico atualizado refletir resultados atuais;
- worktree estiver organizado em mudancas intencionais.

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|---------|------|-----------|
| 1.1.0 | 2026-08-09 | P5 corrigido para preparar o ciclo Comercial antes de Contratos e Motor Financeiro, conforme IMP-081. |
| 1.0.0 | 2026-08-08 | Plano prioritario para recuperar, recertificar e organizar a implementacao do backend, incluindo suites de teste ausentes. |
