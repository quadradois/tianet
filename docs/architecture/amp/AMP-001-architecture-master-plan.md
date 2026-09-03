# AMP-001 — Architecture Master Plan

**ID:** AMP-001

**Versão:** 1.3.0

**Status:** Aprovado como plano diretor; sujeito a revisoes versionadas

**Data:** 2026-08-08

**Alteração na v1.3.0:** ADR-007 (Scheduler / Batch Processing) e ADR-009
(Notifications / Channels) foram emitidas em 11/08/2026 para encerrar as
decisões arquiteturais pendentes do EPIC-010 antes do PLAN técnico.

**Alteração na v1.2.0:** a ADR-004 (Autenticação e Autorização) deixou de ser
reserva — foi emitida em 08/08/2026 com escopo reduzido: ABAC, OIDC e MFA
ficaram fora. Tabela do §8 atualizada. Nenhuma outra alteração.

**Alteração na v1.1.0:** numeração de Épicos alinhada à sequência oficial do
[ROADMAP-ALIGNMENT §5.2](../ROADMAP-ALIGNMENT-PRODUCT-AMP.md). O identificador
EPIC-003 designava dois temas distintos ("Comercial/Propostas" em §10.1 item 2 e
"Contratos" em §10.1 item 3) — conflito CP-003 do relatório de alinhamento.
Passam a valer: EPIC-003 = Comercial, EPIC-004 = Contratos de Crédito,
EPIC-005 = Empréstimos/Pagamentos/Motor Financeiro, EPIC-007 = Operação Diária.
Nenhuma decisão arquitetural de conteúdo foi alterada.

**Autor:** Principal Software Architect / Domain Architect / CTO

---

# 1. Resumo Executivo

A TiaNet é uma plataforma de administração de operações de crédito construída sobre uma base arquitetural acima da média para um MVP: Domain-Driven Design (DDD) em camadas, Domain puro de frameworks, arquitetura multi-tenant lógica (Nível 1), transações atômicas, auditoria append-only e testes automatizados com cobertura elevada.

O EPIC-001 (Gerenciar Tenant) está concluído. O próximo ciclo deve crescer sem destruir as escolhas que já nos diferenciam: o Motor Financeiro como única autoridade de cálculo, a separação entre Platform Context e Credit Context, e a imutabilidade dos dados financeiros.

Este documento consolida a visão arquitetural de curto, médio e longo prazo, identifica os contextos de negócio, mapeia dependências, enumera abstrações emergentes e propõe a ordem de evolução para os próximos anos.

## Posição do CTO

A plataforma **está pronta para crescer, mas com condições**. As fundações estão corretas, mas há dívidas técnicas perigosas que precisam ser pagas antes de qualquer aceleração comercial: autenticação, CI/CD, observabilidade e transação única atravessando contextos. A próxima grande decisão não é funcional — é arquitetural.

---

# 2. Estado Atual (AS-IS)

## 2.1 Arquitetura existente

- **Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, PostgreSQL 16, pytest, ruff/black/mypy, Docker Compose.
- **Padrão arquitetural:** Monólito Modular com DDD em camadas (Presentation → Application → Domain → Infrastructure).
- **Domain:** 100% independente de frameworks (FastAPI, SQLAlchemy) — portátil e testável sem infraestrutura.
- **Persistência:** Repository Pattern + Unit of Work (SQLAlchemy).
- **Transações:** Transação única no MVP enquanto Platform Context e Credit Context compartilharem a mesma base (AD-001).
- **Idempotência:** Idempotency-Key com constraint única (AD-002).
- **Auditoria:** Trilha append-only, imutável, em sessão independente — sobrevive ao rollback (ADR-002).
- **Multi-tenancy:** Nível 1 — shared database, shared schema, isolamento lógico por `tenant_id`.
- **Core Domain:** Motor Financeiro (Domain Service) — única autoridade para cálculos financeiros.

## 2.2 Bounded Contexts existentes

| Contexto | O que existe hoje | Localização principal |
|----------|-------------------|-----------------------|
| **Platform Context** | Tenant, Usuário, Configuração, Unicidade, máquina de estados operacional. | `src/emprestimo/domain/platform` |
| **Credit Context (estrutura)** | Aggregate Carteira vazia (só vínculo com Tenant), ports, ORM. | `src/emprestimo/domain/credit` |

## 2.3 Módulos existentes

- `src/emprestimo/domain/platform/tenant.py` — Aggregate Tenant.
- `src/emprestimo/domain/platform/usuario.py` — Entity Usuário.
- `src/emprestimo/domain/platform/configuracao.py` — Entity Configuração.
- `src/emprestimo/domain/platform/unicidade.py` — Domain Service de unicidade.
- `src/emprestimo/domain/credit/carteira.py` — Aggregate Carteira (estrutura mínima).
- `src/emprestimo/application/{provisioning,atualizacao,estado,consulta}.py` — Casos de uso.
- `src/emprestimo/infrastructure/{db, repositories, auditoria, idempotencia, unit_of_work}.py` — Implementação SQLAlchemy.
- `src/emprestimo/presentation/api/{routes, main, dependencies, schemas}.py` — API REST FastAPI.

## 2.4 Responsabilidades consolidadas

- **Domain:** regras de negócio, invariantes, eventos de domínio, linguagem ubíqua.
- **Application:** orquestração de casos de uso, transações, idempotência, auditoria.
- **Infrastructure:** persistência, repositórios, sessões, ORM, integrações técnicas.
- **Presentation:** validação de entrada, serialização, mapeamento HTTP, injeção de dependências.

## 2.5 Pontos fortes

1. **Domain puro e protegido.** O coração do produto (Motor Financeiro) está blindado contra frameworks e preocupações técnicas.
2. **DDD documentado.** Foundation, Domain, Product, ADRs e PLANs estão alinhados e validados.
3. **Testes fortes.** 178 testes passando, cobertura ≥ 90% nos módulos novos, PostgreSQL real em integração.
4. **Auditoria desde o dia zero.** Append-only, imutável, independente da transação de negócio.
5. **Multi-tenant modelado.** Tenant como Aggregate Root do Platform Context com isolamento lógico.
6. **Eventos de domínio identificados.** `Empréstimo Criado`, `Pagamento Registrado`, `Empréstimo Quitado` já estão no modelo.

## 2.6 Limitações atuais

1. **Apenas o Platform Context está operacional.** O Credit Context ainda é uma estrutura vazia.
2. **Transação única atravessa Platform e Credit.** Funciona no MVP, mas impede a separação física futura.
3. **Autenticação e autorização não implementadas.** Endpoints administrativos expostos sem IAM.
4. **Domain Events sem transporte.** Eventos existem no modelo, mas não há infraestrutura de publicação/consumo.
5. **Auditoria acoplada explicitamente aos services.** Cada novo caso de uso precisa chamar a trilha manualmente.
6. **Session factory e engine globais singleton.** Limita testes paralelos e configuração por tenant.
7. **Repositórios usam `merge()` indiscriminadamente.** Dificulta distinção entre INSERT e UPDATE.
8. **Healthcheck básico.** Não verifica dependências (banco, fila, etc.).
9. **Sem CI/CD, observability, logs estruturados ou correlation ID.**
10. **Inativação de Tenant sem semântica de desligamento.** Não há regra para tokens, jobs, acessos pendentes.

---

# 3. Arquitetura Alvo (TO-BE)

## 3.1 Em 6 meses

Objetivo: **MVP operacional e seguro**.

- EPIC-001 concluído (Tenant Management).
- EPIC-006 (IAM) implementado: autenticação JWT, autorização RBAC, perfis e permissões.
- EPIC-002 (Cadastro de Devedores) concluído.
- EPIC-003 (Comercial — Propostas/Simulação) iniciado.
- CI/CD, logs estruturados, observabilidade básica e healthcheck real implementados.
- Eventos de domínio publicados em memória (bus interno) para desacoplar contextos dentro do monólito.
- Inativação de Tenant com semântica de desligamento (revogação de tokens, suspensão de jobs).
- Monólito modular mantido; separação lógica reforçada.

## 3.2 Em 1 ano

Objetivo: **Operação de crédito completa**.

- EPIC-004 (Contratos de Crédito) concluído.
- EPIC-005 (Empréstimos, Pagamentos e Motor Financeiro) concluído — Motor Financeiro operacional.
- EPIC-007 (Operação Diária — Cobrança, Agenda, Comunicação e Relatórios) operacional.
- Read models / projections para relatórios e listagens pesadas.
- Event Bus formalizado (possivelmente mensageria leve) para comunicação cross-context.
- Search básico para devedores, contratos e operações.
- Scheduler para vencimentos, lembretes e cobranças programadas.
- Notification Service (WhatsApp, SMS, e-mail) com canais abstraídos.
- ~~Critérios para ADR-003 (evolução do multi-tenant)~~ — removido pela [ADR-003](../adrs/ADR-003-escopo-single-tenant-do-v1.md): o v1 é single-tenant e não há expansão a monitorar.

## 3.3 Em 2 anos

Objetivo: **Escala comercial e automação**.

- Multi-tenant Nível 2 ou 3 avaliado e, se necessário, implementado (banco/schema separado).
- Cobrança automática e integrações bancárias (PIX, boletos, registros de dívida).
- API pública/documentada para parceiros e correspondentes.
- Multi-carteira operacional.
- Workflow para renegociações, acordos e aprovações comerciais.
- Cache para read models e sessões.
- Separação física de alguns contextos (ex.: Comunicação, Relatórios) via Saga/Outbox.

## 3.4 Longo prazo

Objetivo: **Plataforma de ecossistema**.

- Marketplace de serviços financeiros.
- White-label para correspondentes e parceiros.
- Billing e assinaturas.
- Inteligência Artificial (scoring, predição de inadimplência, atendimento).
- Aplicativo mobile.
- Data lake / analytics avançados.
- Arquitetura de serviços autônomos conectados por eventos, quando a separação física for economicamente justificada.

---

# 4. Mapa dos Bounded Contexts

## 4.1 Existentes

- **Platform Context** — Tenant, Usuário, Configuração, Autenticação, Permissões, Perfis.
- **Credit Context (estrutura)** — Carteira (vínculo obrigatório com Tenant).

## 4.2 Emergentes (MVP)

| Contexto | Responsabilidade | Tipo de relacionamento |
|----------|------------------|------------------------|
| **Cadastro** | Devedores, histórico cadastral, contatos, documentos. | Downstream do Platform; upstream do Comercial/Contratos. |
| **Comercial** | Simulações, propostas, análise e aprovação comercial. | Downstream do Cadastro; upstream do Contratos. |
| **Contratos** | Formalização, contrato de crédito, assinatura, liberação. | Downstream do Comercial; upstream do Motor Financeiro. |
| **Motor Financeiro (Core)** | Empréstimos, juros, amortizações, pagamentos, quitação, memória de cálculo. | Upstream de todos os contextos financeiros. |
| **Cobrança** | Recuperação, acordos, promessas, acompanhamento da inadimplência. | Downstream do Motor Financeiro. |
| **Agenda** | Vencimentos, compromissos, lembretes, retornos. | Downstream do Motor Financeiro. |
| **Comunicação** | WhatsApp, SMS, e-mail, histórico de comunicações. | Downstream do Motor Financeiro; nunca calcula. |
| **Relatórios** | Indicadores, fluxo de caixa, carteira ativa, inadimplência. | Downstream de todos; consolida. |
| **Configurações** | Taxas, modalidades, regras de cálculo, calendário financeiro. | Upstream do Motor Financeiro e demais. |

## 4.3 Futuros (pós-MVP)

- **IAM Context** — identidade, autenticação, autorização, SSO, MFA.
- **Billing Context** — cobrança de uso, assinaturas, faturamento entre tenants.
- **Notification Context** — canais de comunicação, templates, preferências, filas.
- **Scheduler Context** — agendamento, cron, batch, workflows temporizados.
- **Workflow Context** — orquestração de processos de negócio (acordos, aprovações).
- **Event Bus Context** — transporte confiável de eventos de domínio (Saga/Outbox).
- **Search Context** — índices de consulta para operações, devedores, contratos.
- **AI Context** — modelos preditivos, scoring, análise de crédito.
- **Integration Context** — adaptadores para bancos, PIX, registros de dívida, APIs de terceiros.
- **Observability Context** — métricas, logs, traces, correlation ID, alerting.
- **API Gateway Context** — API pública, rate limiting, documentação, parceiros.

## 4.4 Ordem recomendada de nascimento

1. **Platform Context** (concluído) — fundação de isolamento e acesso.
2. **IAM Context** (urgente) — segurança pré-requisito para produção.
3. **Cadastro Context** — bloco de construção de todas as operações.
4. **Contratos Context** — origem formal da operação de crédito.
5. **Motor Financeiro Context** — core domain; depende de Carteira/Contrato/Devedor.
6. **Cobrança + Agenda + Comunicação Contexts** — operação diária downstream.
7. **Relatórios Context** — read models e projections.
8. **Scheduler + Notification Contexts** — automação.
9. **Workflow Context** — processos complexos.
10. **Integration + AI + API Gateway Contexts** — expansão comercial.

---

# 5. Context Map

## 5.1 Visão geral

```
                    Platform Context
                           │
                           │ customer/supplier
                           │ (Tenant, Usuário, Configuração, IAM)
                           ▼
                    Credit Context (Carteira)
                           │
                           │ ACL / Shared Kernel
                           │ (BR-004: Carteira pertence a um Tenant)
                           ▼
         ┌─────────────────┼─────────────────┐
         │                 │                 │
         ▼                 ▼                 ▼
    Cadastro         Comercial         Contratos
    Context          Context           Context
         │                 │                 │
         │                 │                 │
         └─────────────────┴─────────────────┘
                           │
                           │ upstream
                           ▼
                    Motor Financeiro
                    (Core Domain)
                           │
              ┌────────────┼────────────┐
              │            │            │
              ▼            ▼            ▼
          Cobrança      Agenda     Comunicação
          Context      Context      Context
              │            │            │
              └────────────┴────────────┘
                           │
                           ▼
                      Relatórios
                       Context
```

## 5.2 Relacionamentos detalhados

### Platform Context → Credit Context

- **Tipo:** Customer/Supplier.
- **Descrição:** Platform provê Tenant, Usuário e Configuração. Credit consome esses dados via Carteira.
- **Ponto de contato:** `Carteira.tenant_id` (BR-004).
- **ACL:** O Platform Context cria a Carteira padrão sem acessar o modelo interno do Credit Context.

### Credit Context → Motor Financeiro

- **Tipo:** Shared Kernel / Upstream-Downstream.
- **Descrição:** Carteira é o aggregate root do Credit Context. Motor Financeiro opera dentro de uma Carteira.
- **Contrato:** toda operação financeira pertence a uma Carteira, que pertence a um Tenant.

### Motor Financeiro → Cobrança / Agenda / Comunicação / Relatórios

- **Tipo:** Upstream/Downstream.
- **Descrição:** Motor Financeiro produz eventos; os demais contextos consomem.
- **Padrão:** Conformist — os downstreams aceitam os eventos e interpretações do Motor Financeiro sem contestar.
- **Regra crítica:** nenhum downstream calcula juros, saldo ou amortização.

### Comunicação Context

- **Tipo:** Downstream puro.
- **Descrição:** Consome eventos; nunca altera dados financeiros.

### Relatórios Context

- **Tipo:** Downstream puro / Open Host Service futuro.
- **Descrição:** Consolida informações de todos os contextos. Deve evoluir para read models separados.

---

# 6. Dependências Arquiteturais

## 6.1 O que depende de quê

| Contexto/Componente | Depende de | Por quê |
|---------------------|------------|---------|
| Cadastro | Platform | Todo devedor pertence a um Tenant. |
| Comercial | Cadastro, Platform | Proposta precisa de devedor e de tenant. |
| Contratos | Comercial, Cadastro, Platform | Contrato formaliza proposta e devedor. |
| Motor Financeiro | Contratos, Carteira, Cadastro, Platform | Operação financeira precisa de contrato, devedor, carteira e tenant. |
| Cobrança | Motor Financeiro | Ações de recuperação usam situação da operação. |
| Agenda | Motor Financeiro | Vencimentos e compromissos derivam de operações. |
| Comunicação | Motor Financeiro | Mensagens reagem a eventos financeiros. |
| Relatórios | Todos | Consolida dados de todos os contextos. |
| IAM | Platform | Usuários, perfis e permissões são do Platform Context. |
| Scheduler | Agenda, Cobrança, Comunicação | Dispara ações programadas. |
| Notification | Comunicação | Envia mensagens pelos canais. |
| Search | Cadastro, Contratos, Motor Financeiro | Indexa dados para consulta. |

## 6.2 O que pode evoluir isoladamente

- **Relatórios:** desde que baseado em eventos/read models, pode ter stack própria.
- **Comunicação:** pode trocar canais (WhatsApp, SMS, e-mail) sem tocar no domínio.
- **Notification:** abstração de canais permite evoluir independentemente.
- **Search:** pode ser um índice separado alimentado por eventos.
- **Observability:** cross-cutting, evolui sem alterar regras de negócio.

## 6.3 O que nunca deve ser acoplado

- **Cálculos financeiros fora do Motor Financeiro.** (Princípio 05 do FOUNDATION-001 e FOUNDATION-004).
- **Dados entre Tenants.** (Princípio 02 do FOUNDATION-006).
- **Frameworks no Domain.** (ADR-001).
- **Regras de negócio na Presentation.** (PLAN-001, PLAN-002).
- **Escrita financeira sem auditoria.** (ADR-002).
- **Repositórios executando commit.** (AD-001).

---

# 7. Abstrações Emergentes

Abstrações que ainda não existem como contextos, mas inevitavelmente surgirão:

| Abstração | Quando emerge | Motivação |
|-----------|---------------|-----------|
| **IAM Context** | Imediato | Segurança, autenticação, autorização, perfis. |
| **Notification Context** | MVP | WhatsApp, SMS, e-mail, templates. |
| **Scheduler Context** | MVP | Vencimentos, lembretes, cobranças programadas. |
| **Workflow Context** | 1 ano | Renegociação, acordos, aprovações comerciais. |
| **Event Bus Context** | 6-12 meses | Transporte de eventos de domínio entre contextos. |
| **Search Context** | 1 ano | Consultas rápidas em devedores, contratos, operações. |
| **Read Model / Projections** | 1 ano | Relatórios e listagens sem sobrecarregar o transactional store. |
| **Cache Context** | 1-2 anos | Sessões, configurações, read models. |
| **Integration Context** | 1-2 anos | Bancos, PIX, registros de dívida. |
| **AI Context** | 2+ anos | Scoring, predição de inadimplência, atendimento. |
| **Observability Context** | Imediato | Logs, métricas, traces, correlation ID, alerting. |
| **File Storage Context** | 1 ano | Contratos, documentos, comprovantes. |
| **API Gateway Context** | 2+ anos | API pública, parceiros, rate limiting. |
| **Billing Context** | 2+ anos | Cobrança de uso, assinaturas, white-label. |
| **Snapshot Financeiro** | 1-2 anos | Cachear resultados de cálculos intensivos quando a recalculação total não escalar. |

---

# 8. Decisões Arquiteturais Futuras (ADRs)

Esta tabela é a fonte de verdade para as reservas de ADR. Uma ADR é emitida
somente quando o gatilho indicado se materializa; itens emitidos permanecem na
tabela para preservar o histórico da reserva.

| ADR | Nome | Motivo | Momento adequado |
|-----|------|--------|------------------|
| ~~**ADR-003**~~ | ~~Nível de isolamento Multi-Tenant~~ | **EMITIDA em 31/08/2026** — ver [ADR-003](../adrs/ADR-003-escopo-single-tenant-do-v1.md). Escopo **diferente** da reserva: em vez de escolher um nível de isolamento, decide que o v1 é single-tenant (um Credor, um Tenant, um usuário) e a pergunta fica sem objeto. `tenant_id` permanece como invariante estrutural. | — |
| ~~**ADR-004**~~ | ~~Autenticação e Autorização (IAM)~~ | **EMITIDA em 08/08/2026** — ver [ADR-004](../adrs/ADR-004-autenticacao-e-autorizacao-iam.md). Escopo reduzido em relação à reserva: ABAC, OIDC e MFA ficaram fora. | — |
| **ADR-005** | Event Bus / Mensageria | Transporte de eventos de domínio entre contextos. | Quando separar contextos físicos ou introduzir read models. |
| **ADR-006** | Workflow / Orchestration | Processos de renegociação, acordos, aprovações. | Quando esses processos se tornarem complexos. |
| ~~**ADR-007**~~ | ~~Scheduler / Batch Processing~~ | **EMITIDA em 11/08/2026** — ver [ADR-007](../adrs/ADR-007-scheduler-batch-processing.md). Define fila PostgreSQL, worker separado, lease, relógio, health, retry e retenção para o EPIC-010. | — |
| **ADR-008** | Search / Indexing | Consultas rápidas e full-text. | Quando listagens simples não atenderem performance. |
| ~~**ADR-009**~~ | ~~Notifications / Channels~~ | **EMITIDA em 11/08/2026** — ver [ADR-009](../adrs/ADR-009-notifications-channels.md). Define e-mail via Resend, porta, idempotência, consentimento, templates e conciliação para o EPIC-010. | — |
| **ADR-010** | External Integrations / Adapters | Bancos, PIX, registros de dívida. | Quando integrações bancárias forem prioridade. |
| **ADR-011** | API Pública / Gateway | Exposição para parceiros e correspondentes. | Quando abrir API para terceiros. |
| **ADR-012** | Data Lake / Analytics | Relatórios avançados, BI, machine learning. | 2+ anos, quando volume de dados justificar. |
| **ADR-013** | Caching / Read Models | Performance de consultas e sessões. | Quando latência de leitura for problema. |
| **ADR-014** | Snapshot Financeiro / Materialized Views | Cachear resultados de cálculos intensivos. | Quando recalcular toda operação for inviável. |
| **ADR-015** | CI/CD / Deployment Strategy | Pipelines, ambientes, rollback. | Imediato. |
| **ADR-016** | Observability / Logging / Tracing | Logs estruturados, métricas, correlation ID. | Imediato. |
| **ADR-017** | Billing / Subscriptions / Monetização | Cobrança entre tenants, white-label. | Quando modelo de receita exigir. |

### Emitidas fora da reserva

A tabela acima reserva 005–017 por **tema previsto**. Decisões que não
correspondem a nenhum tema reservado recebem o próximo número livre acima de 017
e são registradas aqui — sem isto, esta tabela deixa de ser a fonte de verdade
que o Identifier Registry declara que ela é, e o próximo emissor colide.

**A ADR-018 esteve ausente desta seção até 2026-09-03**, embora emitida em
2026-08-07. Quem consultasse a tabela para escolher o próximo número escolheria
`018` outra vez — a colisão que a SPEC-002 §5.2 existe para impedir.

| ID | Tema | Situação |
|---|---|---|
| **ADR-018** | Identidade externa do Aggregate Devedor | **EMITIDA em 07/08/2026** — ver [ADR-018](../adrs/ADR-018-identidade-externa-do-devedor.md). Endereçamento HTTP do Devedor contextualizado por Carteira. |
| **ADR-019** | Isenção de `Idempotency-Key` nas escritas da conexão de WhatsApp | **EMITIDA em 03/09/2026** — ver [ADR-019](../adrs/ADR-019-isencao-de-idempotency-key-nas-escritas-da-conexao-de-whatsapp.md). Promove a decisão do PLAN-034 §3.1 a decisão arquitetural, depois de quatro rodadas de review reabrirem a mesma pergunta. |

---

# 9. Hotspots Arquiteturais

## 9.1 Onde o software tende a crescer

1. **Motor Financeiro.** Será o contexto mais complexo (cálculos, regras, memória de cálculo, renegociação).
2. **Auditoria.** A tabela `audit_log` crescerá rapidamente. Sem retenção, vira problema operacional.
3. **Relatórios.** Leituras pesadas podem degradar o transactional store.
4. **Comunicação.** Volume de mensagens tende a crescer com número de operações.
5. **Multi-tenant.** A medida que tenants e dados crescem, o nível 1 pode virar gargalo.

## 9.2 Onde há maior risco de acoplamento

1. **Transação única entre Platform e Credit.** Se não for desfeita com critério, vira dependência indivisível.
2. **Auditoria chamada manualmente nos services.** Novos devs podem esquecer; padronização via decorator/command handler é necessária.
3. **Repositórios usando `merge()` para tudo.** Dificulta distinção de INSERT/UPDATE e pode mascarar bugs.
4. **Session factory global.** Cria acoplamento com configuração de processo único.
5. **Inativação de Tenant sem semântica de desligamento.** Risco de tokens/jobs continuarem ativos.

## 9.3 Onde haverá maior risco de retrabalho

1. **Autenticação.** Colocá-la depois exige reescrever todos os endpoints e testes.
2. **Eventos de domínio.** Se não forem publicados agora, a separação futura será cara.
3. **Multi-tenant.** Evoluir para nível 2/3 sem critérios definidos gera migração traumática.
4. **Repositórios.** `merge()` indiscriminado pode exigir refatoração para operações separadas.
5. **Auditoria.** Sem padrão de retenção, migração/arquivamento será difícil.

---

# 10. Roadmap Arquitetural

## 10.1 Ordem recomendada

1. **Segurança e Fundação Técnica (agora)**
   - IAM (ADR-004)
   - CI/CD (ADR-015)
   - Observability (ADR-016)
   - Healthcheck real
   - Logs estruturados + correlation ID

2. **Cadastro e Comercial (0-3 meses)**
   - EPIC-002: Cadastro de Devedores
   - Início do EPIC-003: Comercial/Propostas

3. **Contratos e Operação Financeira (3-9 meses)**
   - EPIC-004: Contratos de Crédito
   - EPIC-005: Empréstimos + Pagamentos + Motor Financeiro
   - Event Bus interno (ADR-005)

4. **Operação Diária (9-12 meses)**
   - EPIC-007: Cobrança, Agenda, Comunicação, Relatórios
   - Scheduler (ADR-007)
   - Notification (ADR-009)
   - Read Models / Projections (ADR-013)

5. **Automação e Escala (1-2 anos)**
   - Workflow (ADR-006)
   - Integrações bancárias (ADR-010)
   - Search (ADR-008)
   - Multi-carteira
   - API Pública (ADR-011)

6. **Ecossistema (2+ anos)**
   - Billing (ADR-017)
   - AI (ADR-012)
   - Marketplace / White-label
   - Data Lake / Analytics

## 10.2 Justificativa técnica

- **IAM primeiro:** segurança é pré-requisito, não feature. Sem ela, não há produção responsável.
- **Cadastro antes de Contratos:** o contrato precisa de um devedor formalizado.
- **Contratos antes do Motor Financeiro:** o Motor precisa do contrato como entrada de regras.
- **Event Bus antes de separação física:** permite desacoplamento sem ainda pagar o preço de infraestrutura distribuída.
- **Read Models antes de Relatórios pesados:** protege o transactional store desde cedo.
- **Integrações bancárias após operação estável:** reduz risco de inconsistência financeira.

---

# 11. Dívida Arquitetural

## 11.1 Dívida aceitável

| Dívida | Por que é aceitável | Quando pagar |
|--------|---------------------|--------------|
| Transação única Platform/Credit no MVP | Compartilham base; simplifica consistência. | Quando separar fisicamente os contextos. |
| Auditoria acoplada explicitamente nos services | MVP pequeno; regras claras. | Quando introduzir command handler/decorator. |
| ~~Multi-tenant Nível 1~~ | **Deixou de ser dívida** pela [ADR-003](../adrs/ADR-003-escopo-single-tenant-do-v1.md): single-tenant é decisão de escopo, não débito. | — |
| Domínio do Motor Financeiro não implementado | Core Domain está modelado; implementação ordenada. | Nos EPICs de Operações de Crédito. |

## 11.2 Dívida perigosa

| Dívida | Risco | Ação imediata |
|--------|-------|---------------|
| **Autenticação e autorização ausentes** | Exposição de dados, acesso indevido. | Priorizar EPIC-006 / ADR-004. |
| **CI/CD e observabilidade ausentes** | Falhas silenciosas, deploy manual, debugging difícil. | ADR-015 e ADR-016 imediatos. |
| **Session factory/engine globais singleton** | Limita paralelismo, testes e isolamento. | Parametrizar criação de sessão. |
| **`merge()` indiscriminado nos repositórios** | Perda de semântica INSERT/UPDATE, bugs de persistência. | Separar `add()` e `update()` explícitos. |
| **Inativação de Tenant sem desligamento** | Tokens, jobs e acessos podem persistir. | Modelar semântica de desligamento. |
| **Auditoria sem retenção/arquivamento** | Crescimento irrestrito da tabela. | Definir política de retenção. |
| **Healthcheck básico** | Falsos positivos de saúde. | Verificar dependências reais. |

## 11.3 Dívida proibida

| Dívida | Por que é proibida |
|--------|-------------------|
| Cálculos financeiros fora do Motor Financeiro. | Quebra o Core Domain e a fonte única de verdade. |
| Armazenar valores derivados quando puderem ser calculados. | Viola Princípio 01 do Core Domain. |
| Compartilhar dados entre Tenants. | Viola isolamento e cria risco legal/regulatório. |
| Frameworks ou SQL no Domain. | Destrói portabilidade e testabilidade. |
| Escrita sem auditoria. | Viola ADR-002 e rastreabilidade. |
| Repositories executando commit. | Quebra controle transacional da Application. |

---

# 12. Oportunidades

Oportunidades que desaparecem se decisões não forem tomadas agora:

1. **Eventos de domínio já modelados.** Publicá-los agora permite evoluir para Saga sem refatorar o Domain. Se adiarmos, a separação de contextos será cara.
2. **Arquitetura em camadas limpa.** Manter o Domain puro agora garante que possamos trocar frameworks, bancos ou infraestrutura no futuro.
3. **Testes automatizados robustos.** CI/CD pode ser introduzido sem retrabalho massivo.
4. **Auditoria desde o dia zero.** A cultura de trilha está formada; perde-la agora é irreversível.
5. **Modelo multi-tenant correto.** Nível 1 é barato e válido; definir critérios de evolução agora evita migração traumática.
6. **Linguagem ubíqua documentada.** Todo novo contexto pode ser construído sobre vocabulário compartilhado.

---

# 13. Parecer Final do CTO

## 13.1 A plataforma está pronta para crescer?

**Sim, com reservas.** As escolhas fundamentais estão corretas: DDD, Domain puro, Core Domain protegido, auditoria, multi-tenant lógico. O EPIC-001 provou que a máquina funciona.

No entanto, três frentes precisam ser resolvidas antes de acelerar:

1. **Segurança:** autenticação e autorização são obrigatórias.
2. **Engenharia:** CI/CD, observabilidade e logs estruturados são obrigatórios.
3. **Acoplamento transacional:** a transação única entre Platform e Credit precisa de um plano de saída, mesmo que ainda não executado.

## 13.2 Qual deve ser o próximo grande passo?

O próximo grande passo não é uma funcionalidade de negócio — é **infraestrutura de engenharia e segurança**:

1. **EPIC-006 — IAM** (autenticação/autorização).
2. **ADR-015 — CI/CD**.
3. **ADR-016 — Observability**.

Em paralelo, pode-se iniciar o **EPIC-002 — Cadastro de Devedores**, pois é bloco de construção de todas as operações de crédito.

## 13.3 Quais riscos precisam ser monitorados?

1. **Segurança:** endpoints administrativos sem autenticação.
2. **Acoplamento:** transação única entre Platform e Credit.
3. **Auditoria:** crescimento irrestrito da tabela `audit_log`.
4. **Multi-tenancy:** evolução para nível 2/3 sem critérios.
5. **Persistência:** `merge()` indiscriminado e session factory global.
6. **Inativação:** semântica de desligamento incompleta.
7. **Eventos:** domain events sem transporte.
8. **Cálculo:** Motor Financeiro recalculando tudo sem snapshots.

---

# 14. Conclusões e Próximos Passos Recomendados

## 14.1 Principais riscos

- Exposição de endpoints sem IAM.
- Deploy sem CI/CD.
- Debugging sem observabilidade.
- Crescimento do `audit_log` sem retenção.
- Acoplamento transacional entre Platform e Credit.

## 14.2 Principais oportunidades

- Eventos de domínio já modelados.
- Domain puro e testável.
- Auditoria desde o início.
- DDD documentado.
- Arquitetura em camadas que suporta crescimento modular.

## 14.3 Próximos passos recomendados

1. **Aprovar e priorizar EPIC-006 (IAM)** — segurança é pré-requisito.
2. **Aprovar ADR-004 (IAM)**, ADR-015 (CI/CD) e ADR-016 (Observability).
3. **Iniciar EPIC-002 (Cadastro de Devedores)** em paralelo.
4. ~~**Definir critérios para ADR-003**~~ — resolvido pela [ADR-003](../adrs/ADR-003-escopo-single-tenant-do-v1.md), que emitiu a reserva decidindo o escopo single-tenant do v1.
5. **Refatorar repositórios** para separar `add()`/`update()` e eliminar `merge()` indiscriminado.
6. **Modelar semântica de desligamento** para inativação de Tenant.
7. **Publicar eventos de domínio** em bus interno antes de introduzir mensageria.
8. **Definir política de retenção** do `audit_log`.

---

# 15. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.3.0 | 2026-08-11 | ADR-007 e ADR-009 emitidas para o EPIC-010; reservas e orientação da seção 8 atualizadas. |
| 1.2.0 | 2026-08-08 | ADR-004 emitida com escopo reduzido; ABAC, OIDC e MFA permaneceram fora. |
| 1.1.0 | 2026-08-08 | Numeração dos Épicos alinhada ao ROADMAP-ALIGNMENT, preservando EPIC-003 Comercial e EPIC-004 Contratos. |
| 1.0.0 | 2026-08-04 | Rascunho do AMP-001 consolidando AS-IS, TO-BE, Context Map, dependências, abstrações emergentes, ADRs futuras, hotspots, roadmap, dívida, oportunidades e parecer do CTO. |

---

## Nota de encerramento

Este documento é o **plano diretor arquitetural aprovado e versionado**. A
revisao 1.3.0 materializou somente decisoes documentais; nenhuma implementacao
de Scheduler ou Notification foi realizada. As conclusoes foram derivadas da
documentacao oficial e do codigo observado.

**Revisao arquitetural consolidada; novas mudancas exigem versao e historico.**
