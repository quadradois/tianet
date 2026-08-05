# Raio-X Arquitetural — Ecossistema TiaNet

> **Papel:** Arquiteto de Software Principal
> **Data:** 2026-08-03
> **Escopo:** análise profunda do ecossistema TiaNet sob perspectiva de arquitetura evolutiva e longevidade do produto
> **Fontes:** Foundation, Domain, Product, Discoveries, ADRs, Plans, código, testes, Auditoria As-Is/To-Be

---

## 1. Executive Summary

### 1.1 Primeira impressão

Se eu assumisse este projeto hoje, minha primeira impressão seria de **surpresa positiva com a maturidade documental e a disciplina de camadas**. É raro encontrar um MVP em que Foundation, Domain, Product, ADRs e Plans estejam tão bem desenhados antes da implementação em massa. A separação entre Platform Context e Credit Context, a definição de Aggregate Tenant como fronteira de isolamento e a decisão de manter o Domain puro são sinais de que a equipe está pensando no produto de médio/longo prazo, não apenas no MVP.

No entanto, a impressão deixaria de ser apenas positiva ao perceber que **o código está, propositalmente, muito atrás da documentação**. Isso não é um defeito em si — é uma escolha de engenharia de produto — mas cria uma janela de risco: a documentação representa um ecossistema completo de gestão de empréstimos, enquanto o código implementa apenas o provisionamento de Tenant. A tensão entre o "mundo desejado" (documentado) e o "mundo real" (implementado) é o ponto central deste raio-x.

### 1.2 Maiores preocupações

1. **A transação única (AD-001) já pressupõe uma separação futura de contextos**, mas a implementação atual cria dados em Platform e Credit no mesmo commit. Quando a separação física acontecer, o retrabalho não será pequeno.
2. **A inativação de Tenant (FEATURE-004) foi modelada como máquina de estados**, mas o código não tem `inativar()` nem `reativar()`. A pergunta arquitetural é: inativar um Tenant implica em invalidar sessões, bloquear jobs, congelar carteiras? Isso ainda não foi desenhado.
3. **A auditoria transversal (ADR-002) está acoplada explicitamente aos services**. No futuro, isso virará um interceptor/cross-cutting concern. Se não prepararmos a abstração agora, teremos que reescrever N services.
4. **O multi-tenancy nível 1 (shared database, shared schema) é uma porta de saída**, não um destino. A decisão de quando subir para nível 2 ou 3 ainda não existe, mas já deveria ter critérios.
5. **Não há CI/CD, observabilidade estruturada nem autenticação**. Em um sistema financeiro, isso é aceitável no MVP, mas não pode ser adiado além do primeiro deploy em produção real.

### 1.3 Maiores elogios

- **Domain Model rico e coeso**: aggregates, entities, value objects, invariantes e eventos de domínio bem posicionados.
- **Ports and Adapters consistentes**: Repository Pattern, Unit of Work e Dependency Injection nativa do FastAPI funcionam bem juntos.
- **Decisões arquiteturais registradas**: ADR-001 e ADR-002 já formalizam stack e auditoria.
- **Testes como primeira classe**: 70 testes com alta cobertura e PostgreSQL real mostram compromisso com qualidade.
- **Separação Platform/Credit já presente**: a criação da Carteira via ACL é um sinal de maturidade.

---

## 2. Arquitetura Atual

### 2.1 Mapa completo do ecossistema

```
Foundation (Visão, Linguagem Ubíqua, Mapa de Domínio, Core Domain, Inventário, Multi-Tenant, Product Map, MVP)
        ↓ (define linguagem e fronteiras)
Domain (Aggregates, Entities, Value Objects, Domain Services, Events, Business Rules)
        ↓ (fornece contratos de comportamento)
Product (Capability, Epic, Feature, User Story)
        ↓ (traduz necessidades em casos de uso)
Discovery (Decisões de escopo, riscos, regras candidatas, DA-001..DA-014)
        ↓ (alimenta planos técnicos)
Plans (AD-001..AD-004, IMP-001..IMP-023)
        ↓ (orienta implementação)
Implementation
        ├── Application (TenantProvisioningService, Ports: UoW, Auditoria, Idempotência)
        ├── Domain puro (Tenant, Usuario, Configuracao, Carteira)
        ├── Infrastructure (SQLAlchemy ORM, Repositories, Alembic, audit_log, idempotency_key)
        └── Presentation (FastAPI, schemas, exception handlers)
        ↓
API REST (`/platform/tenants`)
        ↓
Runtime (Docker Compose: api + postgres; uv; .venv)
        ↓
Deploy (Dockerfile + manual / futuro CI/CD)
        ↓
Operação (healthcheck básico, logs padrão, sem monitoramento)
        ↓
Cliente (Administrador da Plataforma)
```

### 2.2 Como cada camada conversa com a seguinte

- **Foundation → Domain:** fornece a linguagem ubíqua, os princípios de isolamento multi-tenant e os limites dos contexts. Exemplo: FOUNDATION-006 define isolamento por Tenant; DOMAIN-017 implementa isso como Aggregate Root.
- **Domain → Product:** o Domain diz *o que é possível* (estados, invariantes); o Product diz *o que se deseja* (features, casos de uso). Exemplo: DOMAIN-017 permite estados `provisao | ativo | inativo`; FEATURE-004 define inativação/reativação.
- **Product → Plans:** as User Stories geram IMPs e ADs. Exemplo: US-001 vira IMP-001..IMP-007.
- **Plans → Implementation:** os planos ditam a ordem e as decisões transacionais. Exemplo: AD-001 determina transação única; IMP-014 implementa UoW.
- **Implementation → Runtime:** o código roda em containers com PostgreSQL real.
- **Runtime → Operação:** hoje, apenas healthcheck. Não há ainda instrumentação de métricas, tracing estruturado ou runbooks.

### 2.3 Observação arquitetural central

O fluxo de criação de Tenant é o único que atravessa **dois Bounded Contexts** (Platform e Credit) dentro da mesma transação física. Isso é intencional no MVP, mas é a **primeira rachadura arquitetural visível**: o Credit Context, embora conceitualmente separado, ainda não tem vida própria. Ele é criado por delegação do Platform Context, não por comando próprio.

---

## 3. Hotspots Arquiteturais

### Hotspot 1 — Transação única atravessando contexts
- **Criticidade:** Alta
- **Impacto:** Quando Credit Context for separado fisicamente, o provisionamento quebra.
- **Probabilidade:** 100% em 12-18 meses, se o produto crescer.
- **Quando aparecerá:** Na primeira tentativa de extrair Credit Context para serviço/módulo separado.
- **Custo para corrigir depois:** Alto — exige Saga, eventos de integração e compensação.
- **Como evitar agora:** Publicar eventos de domínio (`TenantCriado`, `CarteiraCriada`) e já desacoplar a criação da Carteira de um método síncrono dentro do Tenant.

### Hotspot 2 — Auditoria acoplada explicitamente aos services
- **Criticidade:** Alta
- **Impacto:** Cada novo service precisará chamar `auditoria.registrar()` manualmente. Em 2 anos, haverá inconsistências e omissões.
- **Probabilidade:** 100% à medida que novas operações surgirem.
- **Quando aparecerá:** Na FEATURE-003/004.
- **Custo para corrigir depois:** Médio/Alto — reescrever services ou adicionar interceptores em código legado.
- **Como evitar agora:** Criar uma abstração de "command handler" ou decorator que registre auditoria automaticamente para operações de escrita.

### Hotspot 3 — Multi-tenancy nível 1 sem critério de evolução
- **Criticidade:** Alta
- **Impacto:** Dados de todos os tenants no mesmo schema dificultam compliance, performance por tenant e isolamento físico.
- **Probabilidade:** Alta quando o número de tenants crescer ou houver clientes enterprise.
- **Quando aparecerá:** Primeiro incidente de vazamento ou primeiro cliente exigindo isolamento dedicado.
- **Custo para corrigir depois:** Muito alto — migração massiva de dados.
- **Como evitar agora:** Definir ADR-003 com critérios claros para subir de nível (schema separado, database separado) e garantir que `tenant_id` seja a única dependência de isolamento.

### Hotspot 4 — Inativação de Tenant sem semântica de desligamento
- **Criticidade:** Alta
- **Impacto:** Inativar um Tenant hoje é só mudar um enum. No futuro, precisará invalidar tokens, pausar jobs, bloquear acessos, arquivar dados.
- **Probabilidade:** 100% quando FEATURE-004 for implementada.
- **Quando aparecerá:** Durante a implementação de FEATURE-004 ou quando um cliente inativar um tenant com usuários logados.
- **Custo para corrigir depois:** Médio — refatorar Domain e Application.
- **Como evitar agora:** Modelar `inativar()` e `reativar()` como processos que emitem eventos de domínio (`TenantInativado`, `TenantReativado`) desde o início.

### Hotspot 5 — Idempotency Key global sem escopo de operação
- **Criticidade:** Média/Alta
- **Impacto:** Uma chave de idempotência usada para provisionamento pode conflitar com uma chave usada para atualização se ambas forem globais.
- **Probabilidade:** Média — depende de quantos endpoints usarão idempotência.
- **Quando aparecerá:** Quando FEATURE-003/004 adotarem Idempotency-Key.
- **Custo para corrigir depois:** Médio — alterar schema e lógica.
- **Como evitar agora:** Formalizar que toda Idempotency Key deve incluir um `escopo` (já existe no schema) e validar escopo por operação.

### Hotspot 6 — Repositórios usando `merge()` para INSERT e UPDATE
- **Criticidade:** Média
- **Impacto:** `merge()` pode gerar SELECTs implícitos, conflitos de identidade e comportamentos inesperados em updates parciais.
- **Probabilidade:** Média — problemas aparecem em concorrência e em entidades desanexadas.
- **Quando aparecerá:** Na FEATURE-003 (PATCH) ou em operações concorrentes.
- **Custo para corrigir depois:** Médio — refatorar repositories.
- **Como evitar agora:** Separar `add()` para inserts e `update()` explícito para updates, ou adotar Unit of Work com tracking de estado.

### Hotspot 7 — Motor Financeiro como Domain Service puro
- **Criticidade:** Média
- **Impacto:** PD-011 decide que valores derivados são calculados no momento da consulta. Com grandes volumes e histórico longo, isso pode ficar caro.
- **Probabilidade:** Média/Alta à medida que o histórico de pagamentos cresce.
- **Quando aparecerá:** Quando houver empréstimos com centenas de parcelas e consultas frequentes.
- **Custo para corrigir depois:** Alto — pode exigir materialização de saldos/event sourcing.
- **Como evitar agora:** Planejar eventos de snapshot (`SaldoAtualizado`) e garantir que o Motor Financeiro possa ser extraído sem reescrever regras.

### Hotspot 8 — Ausência de autenticação e autorização
- **Criticidade:** Alta
- **Impacto:** Sistema financeiro sem controle de acesso é inaceitável em produção.
- **Probabilidade:** 100% — está no roadmap como EPIC-006, mas é um risco de segurança até lá.
- **Quando aparecerá:** No primeiro deploy em ambiente acessível.
- **Custo para corrigir depois:** Médio — depende de quantos endpoints existirem.
- **Como evitar agora:** Isolar a interface administrativa, documentar que endpoints são internos/protegidos por VPN até EPIC-006.

### Hotspot 9 — `audit_log` sem política de retenção
- **Criticidade:** Média
- **Impacto:** Tabela que só cresce. Pode degradar performance e custar armazenamento.
- **Probabilidade:** 100% em escala.
- **Quando aparecerá:** Em 6-12 meses com uso intenso.
- **Custo para corrigir depois:** Médio — arquivamento, particionamento, política de retenção.
- **Como evitar agora:** Definir ADR ou regra: reter N anos, arquivar em storage frio, particionar por mês.

### Hotspot 10 — Engine de sessão global singleton
- **Criticidade:** Média
- **Impacto:** `get_engine()` e `get_session_factory()` globais dificultam testes paralelos, múltiplos bancos e isolamento por tenant.
- **Probabilidade:** Média — impacta mais em testes e CI.
- **Quando aparecerá:** Quando o CI crescer ou quando houver necessidade de conectar a múltiplos bancos.
- **Custo para corrigir depois:** Médio — refatorar session factory.
- **Como evitar agora:** Injetar engine/session_factory explicitamente, evitando globals em novos módulos.

---

## 4. Evolução Natural do Produto (se nada mudar)

### 4.1 Em 6 meses

- FEATURE-002, 003 e 004 estarão implementadas.
- A API terá endpoints de CRUD básico de Tenant.
- O `TenantProvisioningService` terá ganho métodos ou serviços adjacentes (consulta, atualização, inativação).
- O `audit_log` terá crescido com eventos de todas as operações.
- A primeira dúvida surgirá: *"Como sabemos se um Tenant inativo ainda tem usuários logados?"*

### 4.2 Em 1 ano

- O sistema terá múltiplos tenants reais.
- Alguém pedirá: *"Quero um relatório de todos os provisionamentos falhos do último mês"*. O `audit_log` será consultado frequentemente.
- Surgirá a necessidade de autenticação (EPIC-006).
- A transação única começará a doer: alguém proporá separar Credit Context fisicamente.
- O multi-tenancy nível 1 será questionado por clientes enterprise.

### 4.3 Em 2 anos

- O monólito modular terá se tornado um monólito inchado se não houver fronteiras claras.
- A auditoria, inicialmente bem-feita, estará espalhada e inconsistente entre services.
- O Motor Financeiro poderá virar gargalo se todos os cálculos forem feitos em tempo real.
- A migração para Saga ou extração de contexts custará meses.
- O banco de dados shared schema será o maior impeditivo para isolamento e performance por tenant.

---

## 5. Abstrações Futuras Inevitáveis

Não são soluções — são abstrações que **surgirão**, quer queiramos ou não:

1. **Event Bus / Message Broker** — para desacoplar Platform e Credit, e posteriormente outros contexts.
2. **Identity & Access Management** — autenticação, tokens, sessions, perfis, permissões (EPIC-006).
3. **Notification Service** — e-mails, SMS, webhooks para eventos de tenant e empréstimo.
4. **Scheduler / Job Queue** — cobranças recorrentes, lembretes, geração de relatórios.
5. **Billing / Pricing Engine** — cobrança por tenant, planos, uso.
6. **Configuration Service** — configurações tipadas, defaults e overrides por tenant.
7. **Feature Flags** — liberar funcionalidades por tenant/plano.
8. **Audit Query Service** — leitura otimizada do `audit_log` para compliance e dashboards.
9. **Search / Indexing** — busca de tenants, devedores, empréstimos.
10. **File / Document Storage** — contratos, comprovantes, documentos.
11. **Analytics / Data Warehouse** — relatórios financeiros e operacionais.
12. **API Gateway / BFF** — separar APIs administrativa e pública.

---

## 6. Dependências Ocultas

### 6.1 Credit Context depende do Platform Context para nascer

Hoje parece que Credit é independente. Na prática, toda Carteira é criada durante o provisionamento de Tenant. Se amanhã quisermos criar uma Carteira fora desse fluxo, não há endpoint, service nem regra para isso.

### 6.2 Usuário depende implicitamente do primeiro provisionamento

O primeiro usuário administrador é criado automaticamente. Não existe um fluxo independente de criação de usuários. EPIC-002 (Gerenciar Usuários) parece simples, mas precisará desenhar a relação "primeiro usuário vs. convite".

### 6.3 Configurações dependem de catálogo implícito

Hoje `CONFIGURACOES_PADRAO` é uma constante. No futuro, haverá catálogo de configurações, valores por tenant, validação de tipos e defaults. Isso não está modelado.

### 6.4 Auditoria depende de convenção de strings

`acao="provisionar.inicio"` é uma string. Quando houver dezenas de ações, precisaremos de catálogo, tipagem e validação.

### 6.5 Domain Events existem apenas como conceito

DOMAIN-011..013 estão modelados, mas não há infraestrutura de publicação/consumo. Eventualmente precisarão de transporte.

---

## 7. Bounded Contexts Futuros

### 7.1 Ecossistema completo previsto

```
┌─────────────────────────────────────────────────────────────┐
│                         Platform Context                     │
│  (Tenant, Usuários, Configurações, Permissões, Billing)     │
└──────────────┬─────────────────────────────────┬────────────┘
               │                                 │
               ▼                                 ▼
        ┌──────────────┐                 ┌──────────────┐
        │ Credit Context│                 │ Identity Context│
        │ (Carteira,    │                 │ (Auth, SSO,    │
        │  Empréstimo,  │                 │  MFA, Sessions) │
        │  Parcela,     │                 └──────────────┘
        │  Pagamento)   │
        └──────────────┘
               │
               ▼
        ┌──────────────┐
        │ Notification │
        │ Context      │
        └──────────────┘
```

### 7.2 Ordem recomendada de extração

1. **Identity Context (EPIC-006)** — natural, autenticação é cross-cutting.
2. **Notification Context** — quando houver comunicação com clientes finais.
3. **Credit Context** — quando separação física for justificada por volume/equipe.
4. **Billing Context** — quando houver cobrança por uso/plano.

---

## 8. Decisões Arquiteturais Pendentes

### Baixo impacto
- Formatação de arquivos de migration (ruff/black).
- Padronização de logging estruturado.
- Configuração de healthcheck completo.

### Médio impacto
- Padrão de auditoria transversal (decorator vs. explicit calls).
- Uso de `merge()` vs. `add/update` nos repositórios.
- Versionamento de API.
- Paginação e ordenação padrão em listagens.
- Estratégia de cache (Redis).

### Alto impacto
- Nível de multi-tenancy (1 → 2 → 3).
- Estratégia de transação entre contexts (transação única → Saga → eventos).
- Autenticação e autorização (RBAC vs. ABAC).
- Política de retenção do `audit_log`.
- Motor financeiro: cálculo em tempo real vs. materialização.

### Irreversíveis
- Escolha do nível de multi-tenancy (migração de dados).
- Modelo de eventos de domínio e contratos de integração entre contexts.
- Formato dos contratos públicos da API (breaking changes).
- Estratégia de particionamento/sharding do banco.

---

## 9. Pontos de Retrabalho Inevitáveis

Se continuar implementando exatamente como está:

1. **Refatorar auditoria manual para cross-cutting** — todos os services terão chamadas espalhadas.
2. **Refatorar repositórios `merge()`** — quando updates parciais e concorrência aparecerem.
3. **Desacoplar criação de Carteira do provisionamento** — quando separar contexts.
4. **Adicionar escopo à Idempotency Key** — quando mais endpoints usarem.
5. **Criar política de retenção de `audit_log`** — quando performance degradar.
6. **Extrair Motor Financeiro** — quando cálculos em tempo real falharem em escala.
7. **Reescrever healthcheck** — quando monitoramento real for exigido.
8. **Adicionar autenticação em endpoints existentes** — retrabalho de rotas e testes.
9. **Materializar snapshots financeiros** — quando relatórios ficarem lentos.
10. **Refatorar session factory global** — quando testes paralelos ou múltiplos bancos forem necessários.

**Como evitá-los:** introduzir abstrações corretas agora (eventos de domínio, escopo de idempotência, repositórios explícitos, sessão injetada, auditoria cross-cutting).

---

## 10. Débito Arquitetural Futuro

Hoje parece simples, mas no futuro custará caro:

1. **Shared schema multi-tenant** — a separação física de dados será dolorosa.
2. **Strings mágicas em ações de auditoria** — sem catálogo, torna-se impossível auditar consistentemente.
3. **Tenant inativação como flip de enum** — sem semântica de desligamento, haverá vazamentos de acesso.
4. **Domain Service MotorFinanceiro sem persistência de snapshots** — cada consulta recalcula tudo.
5. **Configurações como chave-valor string** — sem schema, defaults ou tipos.
6. **Idempotency Key global** — colisões entre operações distintas.
7. **Ausência de eventos publicados** — integração futura exigirá recriar histórico.
8. **Healthcheck simplório** — não detecta degradação real.
9. **Sem CI/CD** — deploys manuais acumulam risco.
10. **Logging sem correlation ID** — impossível rastrear fluxos em produção.

---

## 11. Roadmap Arquitetural

```
Hoje (2026-08)
│
├─ Monólito modular, DDD, transação única, shared-schema multi-tenant
├─ FEATURE-001 implementada; 002/003/004 documentadas
└─ ADRs 001 e 002 formalizadas
│
▼
Próximo marco (2026-09)
│
├─ FEATURE-002/003/004 implementadas
├─ CI/CD básico
├─ Healthcheck real
├─ Logging estruturado com correlation ID
└─ ADR-003: critérios de evolução do multi-tenancy
│
▼
MVP (2026-10)
│
├─ EPIC-001 fechado em produção
├─ Autenticação/autorização (EPIC-006)
├─ Eventos de domínio publicados localmente
└─ Política de retenção do audit_log
│
▼
Escala (2027)
│
├─ Event Bus entre contexts
├─ Read replicas para consultas
├─ Cache (Redis)
├─ Notification Context
└─ Possível separação física inicial (Credit Context)
│
▼
Plataforma (2027-2028)
│
├─ Multi-tenancy nível 2/3 para clientes enterprise
├─ Billing Engine
├─ Scheduler/Job Queue
├─ Feature Flags
└─ API Gateway administrativo vs. público
│
▼
Ecossistema (2028+)
│
├─ Services especializados
├─ Saga/Orchestration entre contexts
├─ Data Warehouse / Analytics
└─ Marketplace/integrações
```

---

## 12. O que NÃO deve ser feito

1. **Não criar microservices agora** — o MVP não justifica o custo operacional.
2. **Não adicionar cache antes de ter métricas** — otimização prematura.
3. **Não materializar saldos financeiros sem necessidade** — adia conforme PD-011, mas monitore.
4. **Não usar fila/mensageria para auditoria** — ADR-002 exige sobrevivência ao rollback, o que async não garante no MVP.
5. **Não expor dados internos nas APIs** — RA-012 é correta; mantê-la.
6. **Não misturar permissões de tenant com permissões de plataforma** — são concerns distintos.
7. **Não fazer breaking changes na API sem versionamento** — decida versionamento antes do primeiro cliente.
8. **Não ignorar LGPD/GDPR** — inativação não é exclusão; direito ao esquecimento precisará ser modelado.
9. **Não deixar o `audit_log` crescer sem limite** — defina retenção agora.
10. **Não acoplar auditoria a frameworks** — mantê-la como porta/contrato.

---

## 13. Oportunidades Arquiteturais

Oportunidades que existem hoje e que desaparecerão ou ficarão caras depois:

1. **Publicar eventos de domínio agora** — o custo é baixo e abre portas para Saga, webhooks, audit, analytics.
2. **Definir contratos de integração entre contexts** — antes que novos contexts surjam.
3. **Modelar permissões desde o início** — mesmo sem implementar, ter a estrutura evita retrabalho.
4. **Criar ADR-003 (multi-tenancy)** — barato agora, caro depois.
5. **Estabelecer CI/CD** — quanto antes, menos débito acumula.
6. **Adotar correlation ID e logging estruturado** — fácil agora, difícil retrofit.
7. **Desenhar API versioning** — antes do primeiro cliente externo.
8. **Criar testes de contrato** — garante que a API não quebra.

---

## 14. Matriz de Risco

| Área | Risco | Impacto | Probabilidade | Prioridade |
|---|---|---|---|---|
| Arquitetura | Transação única atravessar contexts | Alto | Alta | 🔴 Alta |
| Arquitetura | Multi-tenancy nível 1 sem critério de evolução | Alto | Alta | 🔴 Alta |
| Segurança | Ausência de autenticação/autorização | Alto | 100% | 🔴 Alta |
| Qualidade | Auditoria acoplada explicitamente | Médio/Alto | 100% | 🟡 Alta |
| Dados | `audit_log` sem retenção | Médio | Alta | 🟡 Alta |
| Performance | Motor financeiro recalculando tudo | Médio/Alto | Média | 🟡 Média |
| Qualidade | Repositórios usando `merge()` | Médio | Média | 🟡 Média |
| Performance | Repositório sem paginação | Médio | Alta | 🟡 Média |
| Operação | CI/CD ausente | Alto | 100% | 🟡 Média |
| Operação | Healthcheck simplório | Médio | Alta | 🟢 Baixa |
| Compliance | LGPD/GDPR não modelado | Alto | Média | 🟡 Média |
| Dados | Idempotency Key global | Médio | Média | 🟢 Baixa |

---

## 15. Parecer Final

### Se eu fosse o CTO deste projeto:

#### O que faria amanhã

1. **Aprovar a criação da ADR-003** com critérios de evolução do multi-tenancy (nível 1 → 2 → 3).
2. **Exigir CI/CD** antes de qualquer novo merge na `master`.
3. **Definir a semântica completa de inativação de Tenant** antes de implementar FEATURE-004.
4. **Aprovar logging estruturado com correlation ID** para todos os endpoints.
5. **Revisar o uso de `merge()`** nos repositórios antes de implementar PATCH.

#### O que faria daqui a um mês

1. Implementar FEATURE-002, 003 e 004 com testes e ADRs de escopo.
2. Publicar eventos de domínio (`TenantCriado`, `TenantInativado`, etc.) localmente.
3. Adicionar healthcheck real e monitoramento básico.
4. Criar a estrutura de autenticação (EPIC-006), mesmo que mínima.
5. Estabelecer política de retenção do `audit_log`.

#### O que faria daqui a um ano

1. Avaliar a separação física do Credit Context com Event Bus.
2. Implementar read replicas e cache para consultas administrativas.
3. Criar Notification Context e Billing Engine.
4. Evoluir multi-tenancy para nível 2/3 conforme critérios da ADR-003.
5. Construir Analytics/Data Warehouse com eventos históricos.

### Conclusão

O TiaNet tem **uma base arquitetural acima da média para um MVP**. As decisões já tomadas (DDD, camadas, ADRs, testes, multi-tenant conceitual) pagarão dividendos. O risco não está no hoje — está na **velocidade com que a arquitetura precisará evoluir** para acompanhar a documentação e as expectativas do produto. As próximas 3-4 decisões arquiteturais (CI/CD, eventos de domínio, multi-tenancy, autenticação) definirão se o projeto vira uma plataforma sustentável ou um monólito difícil de evoluir.

**Recomendação estratégica:** manter o ritmo de documentação, mas acelerar a formalização de ADRs para as decisões de fronteira (multi-tenancy, eventos, autenticação) **antes** de implementar as próximas Features. Decidir arquitetura no momento da implementação é sempre mais caro.
