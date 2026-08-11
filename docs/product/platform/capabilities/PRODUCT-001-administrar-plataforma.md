# PRODUCT-001 — Capability Administrar Plataforma

**ID:** PRODUCT-001

**Versão:** 2.1.0

**Status:** Aprovado

---

# 1. Objetivo

Esta Capability é responsável por administrar toda a infraestrutura organizacional da plataforma.

Seu objetivo é garantir que cada Tenant possa operar de forma isolada, segura e controlada, disponibilizando usuários, autenticação, perfis de acesso, permissões e configurações.

Esta Capability segue a hierarquia oficial de governança **Capability → Bounded Context → EPIC → Feature → User Story** definida no FOUNDATION-009 — Capability Map, que é a raiz da camada Product.

Nenhuma operação financeira pertence a esta Capability.

---

# 2. Valor de Negócio

Administrar Plataforma estabelece a base necessária para que todas as demais capacidades do produto possam operar com segurança.

Sem esta Capability não existe controle de acesso, isolamento entre organizações ou governança operacional.

---

# 3. Responsabilidades

Esta Capability é responsável por:

- administrar Tenants;
- controlar autenticação;
- controlar autorização;
- administrar Usuários, Perfis de Acesso e Permissões (via IAM — EPIC-006);
- administrar Configurações da plataforma;
- garantir isolamento entre Tenants;
- registrar informações de auditoria relacionadas ao acesso;
- manter fundacao operacional transversal de qualidade, healthcheck,
  observabilidade tecnica e rastreabilidade de requisicoes.

---

# 4. Limites

Esta Capability não é responsável por:

- administrar Devedores;
- administrar Contratos de Crédito;
- administrar Empréstimos;
- administrar Parcelas;
- administrar Pagamentos;
- calcular juros;
- executar o Motor Financeiro;
- administrar Cobranças;
- administrar Relatórios financeiros.

Essas responsabilidades pertencem às respectivas Capabilities do produto.

Adicionalmente, **Configurações Financeiras** (taxas, modalidades, regras de cálculo e calendário financeiro) não pertencem a esta Capability: são responsabilidade do contexto **Configurações** (FOUNDATION-009 §5), distinto de **Configurações da Plataforma**, que pertence a esta Capability.

---

# 5. Dependências

Esta Capability depende de:

- FOUNDATION-001 — Product Vision;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-007 — Product Map;
- FOUNDATION-008 — Escopo do MVP;
- FOUNDATION-009 — Capability Map (hierarquia oficial e vínculo Capacidade → Contexto → EPIC);
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-018 — Entity Usuário;
- DOMAIN-019 — Business Rule Toda Carteira pertence exatamente a um Tenant.

---

# 6. Épicos

Esta Capability é atendida pelos seguintes Épicos (numeração **global** conforme FOUNDATION-009, BR-003 — sem numeração local por capacidade):

- **EPIC-001 — Gerenciar Tenant** (concluído; Bounded Context: Platform);
- **EPIC-006 — IAM — Autenticação, Usuários, Perfis e Permissões** (concluido; Bounded Context: Platform/IAM);
- **EPIC-008 — Fundacao Operacional e Observabilidade** (proposto; pacote tecnico transversal de Platform/Engineering).

A gestão de Usuários, Perfis de Acesso e Permissões é entregue via **EPIC-006 (IAM)** — não como Épicos independentes.

**Configurações da Plataforma** permanece responsabilidade desta Capability e será entregue quando houver Discovery real (FOUNDATION-009, BR-006), sem EPIC pré-atribuído.

O **EPIC-008** e registrado como excecao tecnica governada: ele nao cria uma
Capability funcional nova nem inaugura um Bounded Context autonomo de
Observability. Seu contexto primario e Platform, com recorte Engineering, para
tratar pre-condicoes operacionais do MVP.

**EPIC ≠ Bounded Context** (FOUNDATION-009, BR-002): um contexto pode conter múltiplos EPICs.

---

# 7. Critérios de Aprovação

Esta Capability será considerada concluída quando:

- os Épicos da Capability (EPIC-001, EPIC-006 e EPIC-008) estiverem
  implementados conforme sua fase e a numeração global;
- o isolamento entre Tenants estiver garantido;
- autenticação e autorização estiverem operacionais (EPIC-006 — IAM);
- usuários puderem administrar a plataforma conforme suas permissões;
- todas as funcionalidades estiverem dentro do escopo definido pelo MVP.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Capability Administrar Plataforma. |
| 2.0.0 | 05/08/2026 | Alinhamento ao FOUNDATION-009 (v1.0.0): hierarquia oficial Capability → Bounded Context → EPIC → Feature → User Story; numeração global de Épicos (EPIC-001 concluído e EPIC-006 IAM); gestão de Usuários/Perfis/Permissões integrada ao IAM; remoção da numeração local EPIC-002..005; desambiguação de Configurações (Plataforma × Financeiras); dependência do FOUNDATION-009 adicionada; critérios de aprovação alinhados. Sem alteração de IDs ou semântica fora do relatório aprovado. |
| 2.1.0 | 2026-08-11 | EPIC-008 registrado como excecao tecnica governada de Platform/Engineering para fundacao operacional e observabilidade. |
