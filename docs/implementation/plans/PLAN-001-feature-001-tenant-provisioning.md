# PLAN-001 — Plano Técnico FEATURE-001 (Criar Tenant)

**ID:** PLAN-001

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Contexto

Este plano define a implementação técnica da FEATURE-001 — Criar Tenant, que provisiona uma nova organização na plataforma.

O provisionamento deve tratar a criação do Tenant como um processo completo (US-001 §5): validar dados, garantir unicidade, criar a Carteira padrão, criar o primeiro Usuário Administrador, inicializar configurações, registrar auditoria e confirmar a criação.

O escopo segue o Multi-Tenant Nível 1 do MVP (FOUNDATION-008) e as fronteiras de isolamento definidas em FOUNDATION-006.

---

# 2. Componentes do Domínio Envolvidos

- Platform Context: Aggregate Tenant (DOMAIN-017) com entidades filhas Usuário (DOMAIN-018) e Configurações (FOUNDATION-002 §Configuração);
- Credit Context: Aggregate Carteira (DOMAIN-001) — criada durante o provisionamento;
- Regra BR-004 (DOMAIN-019): toda Carteira pertence exatamente a um Tenant; na v1 apenas uma Carteira por Tenant (DOMAIN-017 INV-005);
- Auditoria: DOMAIN-018 INV-003 (toda ação auditável) — trilha do provisionamento;
- Fora do componente: autenticação, perfis de acesso, permissões, devedores, contratos, empréstimos e processamento financeiro (FEATURE-001 §4).

---

# 3. Casos de Uso

- UC-001 — Criar Tenant: coletar dados obrigatórios, validar e definir estado inicial;
- UC-002 — Validar Unicidade: garantir que a organização não exista na plataforma;
- UC-003 — Provisionar Carteira Padrão: criar via Credit Context e vincular ao Tenant (BR-004);
- UC-004 — Provisionar Primeiro Usuário Administrador: criar Usuário e associá-lo ao Tenant (DOMAIN-018 RN-001/RN-002);
- UC-005 — Inicializar Configurações Padrão;
- UC-006 — Registrar Auditoria do processo completo;
- UC-007 — Confirmar Criação: retornar sucesso com o estado operacional final.

---

# 4. Decisões de Arquitetura

## AD-001 — Estratégia Transacional

No MVP, enquanto o Platform Context e o Credit Context compartilharem a mesma base de dados, o provisionamento deverá ser executado em transação única.

Todo o processo (Tenant, Carteira, Usuário, Configurações e Auditoria) será atômico: qualquer falha resulta em rollback completo, sem estados parciais visíveis.

A evolução para Saga (orquestrada ou coreografada) somente será adotada quando houver separação física dos contextos.

## AD-002 — Idempotência

Toda solicitação de provisionamento deverá carregar uma Idempotency Key (gerada pelo cliente ou pelo produto).

A combinação (Idempotency Key) deverá ser persistida com constraint único, de forma que uma nova solicitação com a mesma chave não replique o provisionamento:

- primeira solicitação com a chave: executa o provisionamento e registra o resultado;
- solicitações repetidas com a mesma chave: retornam o resultado original, sem criar novos recursos.

Além disso, a unicidade da organização será garantida por constraint único no banco (identificador institucional), protegendo contra corridas concorrentes independentemente da checagem em memória.

## AD-003 — Integração entre Contextos

A criação da Carteira no Credit Context ocorrerá através de ACL (Anti-Corruption Layer): o Platform Context expõe apenas a operação de criação e não acessa o modelo interno do Credit Context.

## AD-004 — Auditoria

A trilha de auditoria do provisionamento será append-only e imutável, registrando cada passo executado (dados validados, carteira criada, usuário criado, configurações aplicadas, confirmação).

---

# 5. Modelo de Dados

## Tenant

- id (PK);
- identificador institucional — constraint UNIQUE (suporta UC-002 e AD-002);
- dados cadastrais obrigatórios;
- estado operacional (Provisão, Ativo, Inativo);
- idempotency_key (constraint UNIQUE — AD-002).

## Carteira

- id (PK);
- tenant_id (FK NOT NULL — BR-004: nenhuma Carteira sem Tenant);
- dados de identificação da Carteira.

## Usuário

- id (PK);
- tenant_id (FK NOT NULL — DOMAIN-017 INV-001);
- dados do primeiro Administrador;
- perfil de acesso mínimo de Administrador (DOMAIN-018 RN-002).

## Configuração

- id (PK);
- tenant_id (FK NOT NULL);
- parâmetros iniciais da plataforma.

## Auditoria

- id (PK);
- tenant_id (FK NOT NULL);
- idempotency_key (referência ao provisionamento);
- evento, dados, timestamp — tabela append-only.

---

# 6. API

- `POST /platform/tenants` — inicia o provisionamento (payload: dados obrigatórios + header `Idempotency-Key`);
  - `201` — Tenant provisionado (com ID e estado final);
  - `409` — organização já existente ou Idempotency Key já utilizada com resultado divergente;
  - `422` — dados obrigatórios inválidos.
- `GET /platform/tenants/{id}` — consulta o Tenant e seu estado operacional (suporte ao fluxo de confirmação — UC-007);
- Endpoints internos de contexto (fora da API pública): criar-carteira, criar-usuário-administrador, inicializar-configurações.

Autenticação está fora do escopo da FEATURE-001 (§4); o endpoint opera no contexto autenticado existente do MVP (FOUNDATION-008).

---

# 7. Estratégia de Testes

- Unitários de domínio: invariantes — unicidade, vínculo obrigatório Tenant→Carteira, estado inicial, RN-002 do primeiro Usuário;
- Integração — transação única: falha em qualquer passo deve resultar em rollback completo, sem resíduos parciais (AD-001);
- Idempotência: replay com a mesma Idempotency Key retorna o resultado original sem duplicar recursos; chaves distintas geram provisionamentos independentes (AD-002);
- Concorrência: criação simultânea do mesmo Tenant → apenas um provisionamento vence (constraint único);
- Contrato: integração Platform↔Credit Context (criação da Carteira via ACL);
- Auditoria: trilha completa e imutável do provisionamento;
- E2E/QA: mapeamento dos 10 critérios da US-001 §2 em cenários Given/When/Then.

---

# 8. Ordem de Implementação

1. Modelo de domínio: Tenant + Usuário + Configuração + criação de Carteira;
2. Validação e unicidade (regras/invariantes);
3. Persistência com constraints de unicidade e de idempotência;
4. Serviço de provisionamento (transação única + Idempotency Key);
5. Auditoria (append-only);
6. API REST;
7. Testes ponta a ponta e validação dos ACs da US-001.

---

# 9. Riscos Técnicos

| Risco | Mitigação |
|-------|-----------|
| Falha parcial entre contextos | Transação única no MVP (AD-001) — atomicidade total; eventos (Tenant Criado, Carteira Criada) já definidos preparam evolução para Saga |
| Race de unicidade na criação | Constraint único no banco + Idempotency Key (AD-002) — independe da checagem em memória |
| Provisionamento duplicado (retry/duplo envio) | Idempotency Key com constraint único (AD-002) |
| Migração futura para bases separadas | Saga só após separação física (AD-001); eventos de domínio já publicados reduzem custo da mudança |
| Limite de 1 Carteira por Tenant (INV-005) | Controle operacional na v1; modelo já aceita N Carteiras sem alteração de domínio |
| Perfil mínimo do primeiro Administrador sem gestão completa de perfis (RN-002) | Perfil Administrador provisionado junto com o Usuário; gestão de perfis pertence a EPIC-003 (futuro) |
| Escopo do MVP (FOUNDATION-008) | Restrito a Multi-Tenant Nível 1; sem billing, white-label ou API pública no provisionamento |
| Auditoria imutável | Desenho append-only desde o primeiro dia |

---

# 10. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Plano Técnico da FEATURE-001 — Criar Tenant, incorporando decisões de estratégia transacional (transação única no MVP) e idempotência (Idempotency Key). |
