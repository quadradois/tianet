# PRODUCT-002 — Capability Administrar Cadastro

**ID:** PRODUCT-002

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability é responsável por administrar o cadastro de Devedores da plataforma.

Seu objetivo é garantir que cada Devedor possa ser identificado, mantido e consultado de forma única, segura e auditável dentro da Carteira à qual pertence.

Esta Capability segue a hierarquia oficial de governança **Capability → Bounded Context → EPIC → Feature → User Story** definida no FOUNDATION-009 — Capability Map, que é a raiz da camada Product.

O contexto primário desta Capability é **Cadastro** (FOUNDATION-009 §5), atendido pelo **EPIC-002 — Cadastro de Devedores**.

Nenhuma operação financeira pertence a esta Capability.

---

# 2. Valor de Negócio

Administrar Cadastro estabelece a base de identificação de todas as operações de crédito.

Sem esta Capability não existe Devedor formalizado, e portanto não existe origem para Comercial, Contratos ou Motor Financeiro (FOUNDATION-009 §6.2).

---

# 3. Responsabilidades

Esta Capability é responsável por:

- cadastrar Devedores;
- garantir unicidade do documento do Devedor por Carteira;
- manter histórico cadastral;
- administrar contatos do Devedor;
- consultar Devedores (por ID, documento e listagem);
- atualizar dados cadastrais;
- inativar e reativar Devedores;
- registrar auditoria das escritas cadastrais.

---

# 4. Limites

Esta Capability não é responsável por:

- administrar Empréstimos;
- administrar Parcelas;
- administrar Pagamentos;
- calcular juros;
- executar o Motor Financeiro;
- administrar Contratos de Crédito;
- administrar Propostas e Simulações;
- administrar Cobranças;
- administrar Usuários, Perfis e Permissões (IAM — EPIC-006);
- integrar-se a bureaus de crédito ou consultas externas.

Essas responsabilidades pertencem às respectivas Capabilities do produto.

---

# 5. Dependências

Esta Capability depende de:

- FOUNDATION-001 — Product Vision;
- FOUNDATION-002 — Modelo de Domínio e Linguagem Ubíqua;
- FOUNDATION-005 — Inventário do Domínio;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-007 — Product Map (capacidade Administrar Cadastro);
- FOUNDATION-008 — Escopo do MVP;
- FOUNDATION-009 — Capability Map (hierarquia oficial e vínculo Capacidade → Contexto → EPIC);
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-002 — Entity Pessoa;
- DOMAIN-019 — Business Rule Toda Carteira pertence exatamente a um Tenant;
- PRODUCT-001 — Capability Administrar Plataforma (Tenant como fronteira de isolamento).

---

# 6. Épicos

Esta Capability é atendida pelo seguinte Épico (numeração **global** conforme FOUNDATION-009, BR-003 — sem numeração local por capacidade):

- **EPIC-002 — Cadastro de Devedores** (proposto; Bounded Context: Cadastro).

---

# 7. Critérios de Aprovação

Esta Capability será considerada concluída quando:

- os Épicos da Capability estiverem implementados conforme a numeração global;
- o cadastro de Devedores estiver operacional com unicidade de documento por Carteira;
- o histórico cadastral estiver preservado e auditado;
- o isolamento entre Tenants estiver garantido via Carteira;
- todas as funcionalidades estiverem dentro do escopo definido pelo MVP.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da Capability Administrar Cadastro, nascida no Discovery do EPIC-002 conforme FOUNDATION-009 BR-006 e §10.2 (criação tardia de PRODUCT-N). |
