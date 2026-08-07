# PLAN-003-EXEC — Backlog de Execução do EPIC-002 (Cadastro de Devedores)

**ID:** PLAN-003-EXEC

**Versão:** 1.0.0

**Status:** Proposto

> **A execução deste backlog deve seguir obrigatoriamente o AGENT-LOOP-EXECUTION-PROTOCOL (ALP-001).**

---

# 1. Contexto

Este documento decompõe o PLAN-003 em um backlog técnico executável para o EPIC-002 —
Cadastro de Devedores, cobrindo a FEATURE-005 (Criar Devedor), a FEATURE-006 (Consultar
Devedor), a FEATURE-007 (Atualizar Devedor) e a FEATURE-008 (Inativar/Reativar Devedor).

A numeração continua a sequência do PLAN-002-EXEC: inicia em IMP-042.

É a fonte oficial para execução: a implementação deverá ocorrer na ordem definida aqui,
permitindo rastreabilidade entre Product → Implementation → Código.

---

# 2. Referências

- PLAN-003 — Plano Consolidado de Implementação do EPIC-002;
- PLAN-002-EXEC — Backlog de Execução do EPIC-001 (IMP-024..IMP-041);
- PLAN-001-EXEC — Backlog de Execução da FEATURE-001 (IMP-001..IMP-023);
- FEATURE-005, FEATURE-006, FEATURE-007, FEATURE-008;
- US-015..US-027; PRODUCT-002; EPIC-002;
- DOMAIN-020 (Devedor), DOMAIN-021 (Contato), DOMAIN-022 (Documento),
  DOMAIN-023 (UnicidadeDevedorService), DOMAIN-024, DOMAIN-025, DOMAIN-026..DOMAIN-029;
- ADR-001, ADR-002, AD-001, AD-002; FOUNDATION-006, FOUNDATION-009.

---

# 3. Domínio e Persistência — IMP-042..IMP-050

## IMP-042 — Migração aditiva das tabelas `devedor` e `contato`

- **Objetivo:** criar migração Alembic aditiva (sem alterar tabelas existentes) com as
  tabelas `devedor` e `contato` e suas constraints UNIQUE e FKs (PLAN-003 §5, DA-303).
- **Componentes afetados:** novo `migrations/versions/0004_devedor_contato.py`.
- **Dependências:** nenhuma (novas tabelas; reutiliza `tenant`/`carteira` existentes).
- **Critérios de conclusão:** `devedor` com `carteira_id` FK NOT NULL, `documento`
  varchar(11) (dígitos), `estado`, `criado_em`/`atualizado_em` e **UNIQUE (carteira_id,
  documento)**; `contato` com `devedor_id` FK NOT NULL, `tipo`, `valor`, `preferencial`
  e UNIQUE (devedor_id, tipo, valor); downgrade reversível (drop aditivo).

## IMP-043 — Value Object Documento (DOMAIN-022)

- **Objetivo:** implementar o VO `Documento` com normalização (somente dígitos), validação
  de CPF (dígitos verificadores) e imutabilidade (DOMAIN-022 `VO-022-VAL-001..004`).
- **Componentes afetados:** novo `domain/credit/documento.py`.
- **Dependências:** DOMAIN-022, ADR-001.
- **Critérios de conclusão:** valor normalizado (somente dígitos); validação de CPF válido
  (rejeita algarismos repetidos e dígitos verificadores incorretos); imutável; `str()` e
  `==` sobre o valor canônico.

## IMP-044 — Entity Contato (DOMAIN-021)

- **Objetivo:** implementar a entidade `Contato` (tipos, valor, preferencial) como entidade
  filha do Devedor (DOMAIN-020 §4).
- **Componentes afetados:** novo `domain/credit/contato.py`.
- **Dependências:** DOMAIN-021, ADR-001.
- **Critérios de conclusão:** `tipo` validado (telefone, e-mail, WhatsApp — DOMAIN-021 RN-002),
  `valor` não vazio, marcador `preferencial` (exatamente um por tipo por Devedor — DOMAIN-021
  RN-005) preservado no domínio.

## IMP-045 — Aggregate Devedor (DOMAIN-020) — criação, invariantes e contatos

- **Objetivo:** implementar o Aggregate Root `Devedor` do contexto Cadastro protegendo
  INV-001..INV-006: vínculo obrigatório à Carteira, documento único/imutável, histórico
  preservado, isolamento via Carteira e gestão de contatos.
- **Componentes afetados:** novo `domain/credit/devedor.py` (estado `DevedorState`,
  construtores, métodos de contato, máquina de estados).
- **Dependências:** IMP-042 (persistência), IMP-043, IMP-044.
- **Critérios de conclusão:** estado inicial `ativo`; documento válido e imutável
  (INV-003); contatos adicionados/alterados/removidos com preferencial único por tipo
  (DOMAIN-021 RN-005); transições
  exclusivas no Domain (INV-005); sem exclusão física (DOMAIN-025).

## IMP-046 — UnicidadeDevedorService (DOMAIN-023/DOMAIN-024)

- **Objetivo:** implementar o serviço de unicidade do documento dentro da Carteira
  (DOMAIN-024 — documento único por carteira); reutilizável na criação (US-017) e na
  reativação (US-026).
- **Componentes afetados:** `domain/credit/unicidade_devedor.py`.
- **Dependências:** IMP-042, IMP-043, DOMAIN-023/DOMAIN-024.
- **Critérios de conclusão:** detecta Devedor na Carteira com o mesmo documento; erro de
  domínio preciso (`documento_ja_cadastrado`).

## IMP-047 — Eventos de domínio (DOMAIN-026..DOMAIN-029)

- **Objetivo:** implementar os eventos de domínio do cadastro (DOMAIN-026
  DevedorCadastrado, DOMAIN-027 DevedorAtualizado, DOMAIN-028 DevedorInativado, DOMAIN-029
  DevedorReativado).
- **Componentes afetados:** novo `domain/credit/eventos_devedor.py`.
- **Dependências:** DOMAIN-026..029, IMP-045.
- **Critérios de conclusão:** eventos dataclass (id do Devedor, Carteira, timestamp);
  registro na trilha de auditoria (ADR-002); publicação em bus interno postergada (DA-307).

## IMP-048 — Ports do contexto Cadastro (repositórios Devedor/Contato)

- **Objetivo:** definir os contratos de persistência (ports) de Devedor e Contato,
  reutilizando a infraestrutura do EPIC-001 (ADR-001).
- **Componentes afetados:** `domain/credit/ports.py` (estende com `DevedorRepository` e
  `ContatoRepository`).
- **Dependências:** IMP-043..IMP-045.
- **Critérios de conclusão:** `DevedorRepository` com `save`, `find_by_id`, `find_by_documento`,
  `listar_paginado(carteira_id, filtros)`; `ContatoRepository` com `save`; contratos tipados
  sem acoplamento a SQLAlchemy no Domain.

## IMP-049 — Repositórios SQLAlchemy de Devedor/Contato

- **Objetivo:** implementar `SqlAlchemyDevedorRepository` e `SqlAlchemyContatoRepository`
  reutilizando o padrão do EPIC-001 (merge/flush, nenhum commit — transação única no UoW).
- **Componentes afetados:** `infrastructure/repositories/__init__.py`,
  `infrastructure/db/orm.py` (novos ORMs), `infrastructure/unit_of_work.py`.
- **Dependências:** IMP-042, IMP-048.
- **Critérios de conclusão:** repositórios com `find_by_id`, `find_by_documento_carteira`,
  `listar_paginado`; tradução de `IntegrityError` UNIQUE em `DevedorJaExisteError`
  (padrão IMP-008/IMP-21 do EPIC-001).

## IMP-050 — Integração no UnitOfWork e suporte de troca

- **Objetivo:** expor `uow.devedor` e `uow.contato` no `SqlAlchemyUnitOfWork` (verificando
  o `UnitOfWork` da Application) e assegurar que a transação única (AD-001) e a auditoria
  (ADR-002) cubram as novas escritas.
- **Componentes afetados:** `infrastructure/unit_of_work.py`, `application/ports.py`.
- **Dependências:** IMP-049.
- **Critérios de conclusão:** novos repositórios dentro do mesmo UoW; commit único no fim;
  rollback automático em falha; auditoria de escrita no mesmo fluxo.

---

# 4. Aplicação — IMP-051..IMP-055

## IMP-051 — DevedorCadastroService (criação)

- **Objetivo:** orquestrar a criação (`criar(carteira_id, nome, documento, contatos)`):
  verificação de unicidade, criação do Aggregate, persistência via UoW em transação única
  (AD-001), auditoria (ADR-002) e Idempotency-Key (AD-002).
- **Componentes afetados:** novo `application/cadastro_devedor.py`, `application/ports.py`.
- **Dependências:** IMP-045..IMP-050.
- **Critérios de conclusão:** resultado imutável com ID, documento, estado `ativo`; eventos de
  auditoria `.inicio/.sucesso/.falha`; replay com a mesma Idempotency-Key retorna o
  resultado original (US-020, AD-002).

## IMP-052 — DevedorConsultaService (consulta por ID e por documento)

- **Objetivo:** consulta por ID (US-021) e por documento (US-022), leitura sem auditoria (ADR-002),
  acesso sempre mediado pela Carteira do usuário (FOUNDATION-006 — isolamento).
- **Componentes afetados:** novo `application/consulta_devedor.py`.
- **Dependências:** de IMP-049, IMP-050.
- **Critérios de conclusão:** retorno `Devedor | None`; nenhuma resposta crua antes 404 (a fronteira é na Presentation).

## IMP-053 — DevedorListagemService (listagem paginada)

- **Objetivo:** listagem com paginação, ordenação determinística (criado_em,id)
  e filtros por nome/estado/documento (US-023, DA-305).
- **Componentes afetados:** `application/consulta_devedor.py` (estende) + schemas de paginação.
- **Dependências:** IMP-052.
- **Critérios de conclusão:** `items,total,page,size,pages`; registros da Carteira apenas.

## IMP-054 — DevedorAtualizacaoService (atualização parcial)

- **Objetivo:** atualização de nome e contatos (US-024) com fluxo atômico. Preserva
  INV-003 (imutabilidade do documento e da Carteira).
- **Componentes afetados:** novo `application/atualizacao_devedor.py`.
- **Dependências:** IMP-051.
- **Critérios de conclusão:** mantém documento sem alteração; auditoria; requisições parciais.

## IMP-055 — DevedorEstadoService e DevedorHistoricoService

- **Objetivo:** transições Ativo→Inativo (US-025) e Inativo→Ativo (US-026) e histórico cadastral
  (US-027), reutilizando a trilha (ADR-002).
- **Componentes afetados:** novos `application/estado_devedor.py`,
  `application/historico_devedor.py`.
- **Dependências:** IMP-045, IMP-054.
- **Critérios de conclusão:** 409 se estado divergente (padrão EPIC-001 IMP-036);
  histórico sem escrever nova trilha.

---

# 5. API — Presentation — IMP-056..IMP-059

## IMP-056 — Schemas da apresentação (DevedorResponse e requests)

- **Objetivo:** `DevedorResponse` (DTO único, RA-012 — sem exposição de dados internos),
  requests de criação/atualização e parâmetros de listagem.
- **Componentes afetados:** novo `presentation/api/devedores_schemas.py` (ou estende
  `schemas.py`); `presentation/api/dependencies.py`.
- **Dependências:** IMP-051..IMP-055.
- **Critérios de conclusão:** DTO único com id, nome, documento, contatos, estado,
  criado_em/atualização; validação de entrada na fronteira.

## IMP-057 — Endpoint POST /credit/carteiras/{carteira_id}/devedores

- **Objetivo:** criação de Devedor na Carteira (US-015..US-020; 201, AD-002 — Idempotency-Key).
- **Componentes afetados:** `routes.py` (estende router credit), `dependencies.py`.
- **Dependências:** IMP-051, IMP-056.
- **Critérios de conclusão:** 201 com `DevedorResponse`; 404 carteira não encontrada; 409
  documento já cadastrado; 409 conflito de Idempotency-Key; 422 regra_violada.

## IMP-058 — Endpoints de consulta (GET devedores)

- **Objetivo:** GET `/carteiras/{carteira_id}/devedores/{id}` (US-021), GET por documento
  (US-022) e listagem paginada (US-023) com filtros `nome`, `estado`, `documento`.
- **Componentes afetados:** `routes/api`, `dependencies.py`.
- **Dependências:** IMP-052, IMP-053, IMP-056.
- **Critérios de conclusão:** 200 com DTO único; 404 inexistente; 404
  `devedor_nao_encontrado` quando o Devedor pertence a outra Carteira (ADR-018); leitura
  sem auditoria; ordenação determinística.

## IMP-059 — Endpoints PATCH, inativar/reativar e histórico

- **Objetivo:** PATCH `/carteiras/{carteira_id}/devedores/{id}` (US-024), POST
  `/carteiras/{carteira_id}/devedores/{id}/inativar` e `/reativar` (US-025/026), GET
  `/carteiras/{carteira_id}/devedores/{id}/historico` (US-027).
- **Componentes afetados:** `routes/api`, `dependencies.py`.
- **Dependências:** IMP-054, IMP-055.
- **Critérios de conclusão:** 200 com DTO atualizado; 404; 404 `devedor_nao_encontrado`
  quando o Devedor pertence a outra Carteira (ADR-018); 409 `conflito_estado`; histórico
  com trilha.

> **Contrato oficial (ADR-018):** todos os endpoints de Devedor são aninhados sob
> `/credit/carteiras/{carteira_id}/devedores`. Não existe rota oficial em
> `/credit/devedores/...`. A validação de pertinência Carteira↔Devedor é centralizada
> em dependência única de rota, nunca duplicada nos handlers.

---

# 6. Testes e GATE — IMP-060..IMP-064

## IMP-060 — Testes unitários de domínio (VO, contatos, invariantes)

- **Objetivo:** cobrir `Documento` (CPF válido/inválido e normalização), `Contato` (tipos,
  preferência), invariantes do `Devedor` (INV, imutabilidade do documento, estado) e
  UnicidadeDevedorService.
- **Componentes afetados:** `tests/unit/domain/test_devedor.py`, `test_documento.py`,
  `test_contato.py`.
- **Dependências:** IMP-043..IMP-047.
- **Critérios de conclusão:** covariância de invariantes; violações intenindos levantando
  `ViolacaoInvarianteError`.

## IMP-061 — Testes de integração (UoW, idempotência, UNIQUE, auditoria)

- **Objetivo:** transação única, replay de Idempotency-Key, constraint UNIQUE
  (`documento_ja_cadastrado`), trilha de auditoria (ADR-002) e rollback automático.
- **Componentes afetados:** `tests/integration/application/test_cadastro_devedor.py`,
  `test_consulta_devedor.py`, `test_estado_devedor.py`.
- **Dependências:** IMP-050, IMP-051..IMP-055.
- **Critérios de conclusão:** fluxos completos em transação única; eventos de auditoria em
  sucesso/falhas; sem dados parciais.

## IMP-062 — Testes de API (contratos HTTP)

- **Objetivo:** validar os endpoints das quatro Features (201/200/404/409/422), serialização
  com `DevedorResponse` único, paginação determinística e isolamento por Carteira.
- **Componentes afetados:** `tests/integration/api/test_api_credit.py` (novo).
- **Dependências:** IMP-057..IMP-059.
- **Critérios de conclusão:** Todos os contratos cobertos; DTO sem vazamento de dados
  internos.

## IMP-063 — Testes de regressão (suíte completa) e qualidade

- **Objetivo:** executar a suíte total (EPIC-001 + EPIC-002) e garantir ≥ 90% de cobertura
  nos novos módulos; sem regressão no ciclo existente.
- **Componentes afetados:** CI config, `pytest.ini`.
- **Dependências:** IMP-060..IMP-062.
- **Critérios de conclusão:** `uv run pytest` 100% pass; `ruff`/`black`/`mypy` limpos;
  `npm run docs:validate` sem novos erros.

## IMP-064 — GATE técnico consolidado e atualização do HANDOFF

- **Objetivo:** validar critérios do EPIC-002 (Features 005..008 implementadas, ciclo
  cadastral, isolamento, aderência ao MVP); congelar o pacote SDD do EPIC-002 e apontar
  para o próximo passo do ROADMAP.
- **Componentes afetados:** `docs/handoffs/`, `docs/implementation/plans/`.
- **Dependências:** IMP-063.
- **Critérios de conclusão:** parecer 🟢 EPIC-002 ENCERRADO (documental + código); HANDOFF
  atualizado; commit final realizado.

---

# 7. Ordem de Execução

A implementação segue a sequência IMP-042 → IMP-064, consistente com a ordem do PLAN-003 §8
(Domínio → Repositórios → Aplicação → API → Testes → Consolidação).

Cada tarefa só inicia com todas as suas dependências concluídas. Este backlog é a fonte
oficial de execução para o próximo Agent Loop (fase de implementação, fora do escopo
documental desta missão).

---

# 8. Estratégia de testes consolidada

- **Unitários de domínio (IMP-060):** VO Documento, Contato, Devedor, Unicidade.
- **Integração (IMP-061):** transação única via UoW, Idempotency-Key, constraint UNIQUE,
  auditoria e rollback.
- **API (IMP-062):** contratos HTTP das quatro Features, DTO único, isolamento.
- **Regressão e qualidade (IMP-063):** suíte completa, cobertura ≥ 90%, quality gates.
- **GATE (IMP-064):** consolidação do EPIC-002 e HANDOFF.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Backlog de Execução do PLAN-003 — EPIC-002, IMP-042..IMP-064. |
| 1.1.0 | 07/08/2026 | IMP-058/IMP-059 — rotas corrigidas de `/devedores/{id}` para o contrato aninhado oficial, conforme ADR-018. |
