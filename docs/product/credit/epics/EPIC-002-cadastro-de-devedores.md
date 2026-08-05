# EPIC-002 — Cadastro de Devedores

**ID:** EPIC-002

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Épico é responsável por administrar o cadastro de Devedores da plataforma.

Seu objetivo é garantir que cada Devedor possa ser criado, identificado, mantido e consultado de forma única, segura e auditável dentro da Carteira à qual pertence, servindo de base para todas as operações de crédito posteriores.

---

# 2. Valor de Negócio

O cadastro de Devedores é o bloco de construção de todas as operações de crédito.

Sem este Épico não existe origem formalizada para Comercial, Contratos e Motor Financeiro, nem rastreabilidade do relacionamento do Credor com seus tomadores.

---

# 3. Escopo

Este Épico contempla:

- criação de Devedor;
- validação de dados obrigatórios e unicidade do documento;
- vínculo do Devedor com a Carteira;
- consulta de Devedor (por ID, por documento e listagem);
- atualização de dados cadastrais e contatos;
- inativação e reativação;
- consulta do histórico cadastral;
- registro de auditoria das escritas.

---

# 4. Fora do Escopo

Este Épico não contempla:

- gerenciamento de Usuários, Perfis e Permissões (IAM — EPIC-006);
- autenticação e autorização;
- operações de crédito (Empréstimos, Parcelas, Pagamentos — EPIC-004);
- Contratos de Crédito e formalização (EPIC-003);
- Propostas e Simulações (EPIC-003);
- integrações externas (bureaus de crédito);
- cobranças.

---

# 5. Features

Este Épico é composto pelas seguintes Features:

- FEATURE-005 — Criar Devedor;
- FEATURE-006 — Consultar Devedor;
- FEATURE-007 — Atualizar Devedor;
- FEATURE-008 — Inativar/Reativar Devedor.

---

# 6. Dependências

Este Épico depende de:

- PRODUCT-002 — Capability Administrar Cadastro;
- PRODUCT-001 — Capability Administrar Plataforma;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-008 — Escopo do MVP;
- FOUNDATION-009 — Capability Map;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-002 — Entity Pessoa;
- DOMAIN-019 — Toda Carteira pertence exatamente a um Tenant;
- DOMAIN-020 — Aggregate Devedor.

---

# 7. Critérios de Aprovação

Este Épico será considerado concluído quando:

- todas as Features estiverem implementadas;
- o cadastro de Devedores estiver operacional com unicidade de documento por Carteira;
- o histórico cadastral estiver preservado e auditado;
- o isolamento entre organizações estiver garantido via Carteira;
- todas as funcionalidades estiverem aderentes ao escopo do MVP.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do EPIC-002 — Cadastro de Devedores, materializada no ciclo SDD conforme ROADMAP-ALIGNMENT-001 §10 e FOUNDATION-009. |
