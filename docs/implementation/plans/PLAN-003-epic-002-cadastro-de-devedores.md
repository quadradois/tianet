# PLAN-003 — Plano Consolidado de Implementação do EPIC-002 (Cadastro de Devedores)

**ID:** PLAN-003

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Contexto

Este plano consolida a implementação técnica do EPIC-002 — Cadastro de Devedores (contexto Cadastro), cobrindo as quatro Features do ciclo cadastral:

- FEATURE-005 — Criar Devedor (US-015..US-020);
- FEATURE-006 — Consultar Devedor (US-021, US-022, US-023);
- FEATURE-007 — Atualizar Devedor (US-024);
- FEATURE-008 — Inativar/Reativar Devedor (US-025, US-026, US-027).

O EPIC-001 (Gerenciar Tenant) foi entregue pelos PLAN-001 e PLAN-002, com backlog IMP-001..IMP-041 concluído e validado por 178 testes. Este plano continua a numeração a partir de IMP-042, preservando a rastreabilidade Product → Implementation → Código.

# 2. Referências

- PLAN-001/PLAN-002 — Planos Técnicos do EPIC-001 (AD-001 transação única, AD-002 Idempotency Key, ADR-002 Auditoria);
- PLAN-001-EXEC/PLAN-002-EXEC — Backlogs de Execução do EPIC-001;
- ADR-001 — Arquitetura em camadas (Presentation → Application → Domain → Infrastructure);
- ADR-002 — Auditoria Independente da Transação (escrita auditada, leitura não auditada);
- EPIC-002 — Cadastro de Devedores;
- FEATURE-005..008 e US-015..027;
- DOMAIN-020 — Aggregate Devedor (estados, invariantes INV-001..INV-006);
- DOMAIN-021 — Entity Contato; DOMAIN-022 — VO Documento;
- DOMAIN-023 — UnicidadeDevedorService; DOMAIN-024 — BR Documento Único por Carteira;
- DOMAIN-025 — BR Exclusão Física Proibida;
- DOMAIN-026..029 — Eventos de domínio do cadastro;
- PRODUCT-002 — Capability Administrar Cadastro;
- FOUNDATION-006 — Arquitetura Multi-Tenant; FOUNDATION-008 — Escopo Oficial do MVP; FOUNDATION-009 — Capability Map;
- Discovery do EPIC-002 (docs/audits/discoveries/EPIC-002-cadastro-de-devedores-discovery.md).

# 3. Situação Atual

## Já implementado (EPIC-001) — reutilizar sem recriar

- Infraestrutura: SqlAlchemyUnitOfWork, repositórios SQLAlchemy, SqlAlchemyIdempotenciaRegistro, Auditoria (audit_log), session/engine, ORM, Alembic;
- Presentation: padrão de routes/schemas/dependencies/errors com mapeamento completo (400/404/409/422/500), handler `TransicaoEstadoInvalidaError` → 409 `conflito_estado`;
- Domain Platform: Aggregate Tenant com máquina de estados (referência de padrão para o Devedor);
- Carteira padrão criada no provisionamento do Tenant (Credit Context — estrutura mínima `carteira.py`).

## Pendente de implementação

- Domain Credit/Cadastro: Aggregate Devedor (DOMAIN-020), Entity Contato (DOMAIN-021), VO Documento (DOMAIN-022), UnicidadeDevedorService (DOMAIN-023), eventos DOMAIN-026..029;
- Repositórios: DevedorRepository, ContatoRepository (ou coleção via Devedor), consultas de listagem;
- Aplicação: DevedorCadastroService (criação), consulta, atualização, estado (inativar/reativar), histórico;
- API: endpoints de criação, consulta, listagem, atualização, transições de estado e histórico;
- Migração: tabelas `devedor` e `contato` com constraint UNIQUE (carteira_id, documento).

# 4. Decisões de Arquitetura

## DA-301 — Reuso integral da infraestrutura do EPIC-001

Nenhum componente de infraestrutura será recriado: Unit of Work, repositórios base, auditoria, idempotência, DTOs e padrão de erros são reaproveitados. As novas operações usam a mesma transação única do UoW (AD-001) e a mesma trilha append-only (ADR-002).

## DA-302 — Devedor como Aggregate do contexto Cadastro

O Devedor (DOMAIN-020) é o Aggregate Root do contexto Cadastro, referenciando a Carteira por ID (DOMAIN-001 INV-001 preservado como invariante de referência). Contatos (DOMAIN-021) são entidades filhas do Devedor, persistidas no mesmo aggregate.

## DA-303 — Unicidade em duas camadas

Unicidade do documento: Domain (UnicidadeDevedorService — DOMAIN-023) para mensagens de erro precisas + constraint UNIQUE (carteira_id, documento) no repositório para proteção contra corrida (padrão FEATURE-001 IMP-008/IMP-021). Reativação reutiliza a mesma verificação (DOMAIN-024).

## DA-304 — Transições de estado exclusivas no Domain

Inativar e reativar são métodos do Aggregate Devedor, respeitando a máquina de estados (Ativo → Inativo; Inativo → Ativo); estados divergentes geram violação de invariante traduzida pela Application em 409 `conflito_estado` (padrão IMP-036 do EPIC-001).

## DA-305 — DTO único de resposta

Todas as operações respondem com DevedorResponse, sem expor dados internos de infraestrutura (RA-012). Listagem com DevedorListagemResponse paginado e ordenação determinística (criado_em + id).

## DA-306 — Leitura sem auditoria

Consultas (FEATURE-006/007 GET e US-027) não geram trilha de auditoria (ADR-002 — somente escrita é auditada). O histórico cadastral (US-027) é lido da trilha append-only já existente.

## DA-307 — Eventos de domínio registrados, publicação em bus interno postergada

Os eventos DOMAIN-026..029 são produzidos e registrados na trilha de auditoria; a publicação em bus interno (em memória) ocorre quando o Event Bus interno do AMP-001 §3.1 for introduzido. Nenhum downstream é acoplado nesta versão.

# 5. Modelo de Dados

Nova migração (apenas Cadastro; sem alteração de tabelas existentes):

- `devedor`: id (UUID, PK), carteira_id (UUID, FK → carteira, NOT NULL), nome (varchar, NOT NULL), documento (varchar(11), NOT NULL, dígitos), estado (varchar, NOT NULL, default 'ativo'), criado_em, atualizado_em; **UNIQUE (carteira_id, documento)**;
- `contato`: id (UUID, PK), devedor_id (UUID, FK → devedor, NOT NULL), tipo (varchar, NOT NULL), valor (varchar, NOT NULL), preferencial (bool, default false), criado_em, atualizado_em; UNIQUE (devedor_id, tipo, valor).

Nenhuma tabela existente (tenant, carteira, usuario, configuracao, idempotency_key, audit_log) é alterada.

# 6. API

- `POST /credit/carteiras/{carteira_id}/devedores` — criação (201; 404 carteira não encontrada; 409 documento_ja_cadastrado; 409 conflito_idempotencia; 422 dados inválidos);
- `GET /credit/carteiras/{carteira_id}/devedores/{id}` — consulta por ID (US-021);
- `GET /credit/carteiras/{carteira_id}/devedores?documento={cpf}` — consulta por documento (US-022);
- `GET /credit/carteiras/{carteira_id}/devedores` — listagem paginada (page, size, sort, nome, documento, estado) (US-023);
- `PATCH /credit/carteiras/{carteira_id}/devedores/{id}` — atualização de nome/contatos (US-024);
- `POST /credit/carteiras/{carteira_id}/devedores/{id}/inativar` — transição Ativo → Inativo (US-025);
- `POST /credit/carteiras/{carteira_id}/devedores/{id}/reativar` — transição Inativo → Ativo (US-026);
- `GET /credit/carteiras/{carteira_id}/devedores/{id}/historico` — histórico cadastral (US-027).

Todos os endpoints são aninhados sob `/credit/carteiras/{carteira_id}` (ADR-018): a identidade externa do Devedor é contextualizada pela Carteira, ainda que ele permaneça Aggregate Root do contexto Cadastro. Não existe rota oficial em `/credit/devedores/...`.

Padrões de erro: 400 payload_invalido / 404 devedor_nao_encontrado, carteira_nao_encontrada / 409 documento_ja_cadastrado, conflito_idempotencia, conflito_estado / 422 regra_violada / 500.

Pertinência Carteira↔Devedor (ADR-018): quando o Devedor existe mas pertence a outra Carteira, a resposta é **404 devedor_nao_encontrado** — o mesmo código de identificador inexistente. A indistinguibilidade é intencional: um código distinto confirmaria a existência do identificador em outra Carteira, vazando informação através da fronteira de isolamento. A validação é centralizada em dependência única de rota, nunca duplicada nos handlers.

# 7. Estratégia de Testes

- **Unitários de domínio:** criação do Devedor, validação do documento (CPF), unicidade (DOMAIN-024), contatos (tipos, preferencial), transições de estado (inativar/reativar), rejeição de estados divergentes, imutabilidade do documento;
- **Integração:** criação/atualização/transições em transação única via UoW, com auditoria completa (ADR-002); constraint UNIQUE (corrida de criação com mesmo documento);
- **API:** contratos HTTP das quatro Features (201/200/404/409/422), serialização com DTO único, listagem paginada determinística, isolamento por Carteira/Tenant;
- **Regressão:** suíte completa do EPIC-001 permanece verde (178 testes + novos);
- **Qualidade:** cobertura ≥ 90% nos novos módulos; `ruff`, `black`, `mypy` limpos; `npm run docs:validate` sem novos erros.

# 8. Ordem de Implementação

1. Domínio e persistência: Aggregate Devedor, Contato, VO Documento, UnicidadeDevedorService, eventos, repositórios e migração (IMP-042..IMP-050);
2. Aplicação: DevedorCadastroService, consulta, atualização, estado, histórico (IMP-051..IMP-055);
3. API: endpoints de criação/consulta/atualização/estado/histórico (IMP-056..IMP-059);
4. Verificação: testes unitários/integração/API/E2E e GATE (IMP-060..IMP-064).

Cada tarefa só inicia com todas as suas dependências concluídas.

# 9. Estratégia de Rollout

- **Fase única:** EPIC-002 é entregue integralmente no mesmo ciclo de release do EPIC-001 (monólito modular, deploy único);
- A migração adiciona apenas tabelas novas (`devedor`, `contato`) — sem alteração destrutiva, permitindo deploy contínuo sem janela de indisponibilidade;
- Retrocompatibilidade: nenhum endpoint existente é alterado; novos endpoints são aditivos;
- Sem CI/CD formal ainda (dívida registrada no AMP-001 §11.2): a validação de rollout permanece manual (suíte local + docs:validate) até ADR-015.

# 10. Estratégia de Migração

- **Tipo:** aditiva (novas tabelas, sem alteração de dados existentes);
- Migração Alembic cria `devedor` e `contato` com constraints UNIQUE e FKs NOT NULL;
- Nenhum backfill é necessário — nenhum Devedor existe antes deste EPIC;
- Rollback: reversível via downgrade da migração (drop das tabelas), sem perda de dados pré-existentes;
- O `audit_log` existente é reutilizado, sem alteração de schema.

# 11. Riscos

| Risco | Mitigação |
|-------|-----------|
| Recriar componentes existentes | Reuso integral (DA-301) — nada duplicado |
| Duplicidade de Devedor por variação de CPF | Normalização (somente dígitos) + UNIQUE (carteira_id, documento) + UnicidadeDevedorService |
| Transição de estado inválida | Regra exclusiva no Domain (DA-304) + testes |
| Corrida em criação/atualização concorrente | Transação única via UoW + constraint UNIQUE |
| Vazamento de dados pessoais (LGPD) | Isolamento por Carteira/Tenant em toda consulta; DTO único (DA-305); sem exposição de dados internos |
| Exclusão acidental de cadastro com histórico | Exclusão física proibida (DOMAIN-025); apenas inativação |
| Paginação sem ordenação determinística | Ordenação por criado_em + id (DA-305) |
| Auditoria incompleta | Eventos inicio/sucesso/falha em todas as escritas |
| Endpoints sem autenticação (MVP) | Aceito temporariamente (EPIC-006 precede expansão); endpoints revistados quando a autorização existir |

# 12. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Plano Consolidado de Implementação do EPIC-002 — Cadastro de Devedores, reutilizando a infraestrutura do EPIC-001 com backlog IMP-042+. |
| 1.1.0 | 07/08/2026 | §6 — endpoints aninhados confirmados como contrato oficial e contrato de erro de pertinência Carteira↔Devedor registrado, conforme ADR-018. |
