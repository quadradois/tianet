# FEATURE-005 — Criar Devedor

**ID:** FEATURE-005

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por cadastrar um novo Devedor na Carteira.

Seu objetivo é permitir que um Devedor seja criado de forma consistente, garantindo a validação dos dados obrigatórios, a unicidade do documento e o registro do histórico desde o primeiro momento.

---

# 2. Valor de Negócio

Esta Feature estabelece a base de identificação da operação de crédito.

Ao final do processo, o Devedor está formalizado, vinculado à Carteira e pronto para originar operações comerciais futuras.

---

# 3. Escopo

Esta Feature contempla:

- criar o Devedor;
- validar dados obrigatórios;
- validar unicidade do documento na Carteira;
- vincular o Devedor à Carteira;
- registrar contatos;
- definir estado inicial;
- registrar auditoria da criação;
- confirmar a criação do Devedor.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- autenticação do usuário;
- gerenciamento de perfis e permissões;
- criação de Contratos de Crédito;
- criação de Empréstimos;
- processamento financeiro;
- integrações externas de consulta de crédito.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-015 — Criar Devedor;
- US-016 — Validar Dados Obrigatórios do Devedor;
- US-017 — Validar Unicidade do Documento;
- US-018 — Registrar Contatos do Devedor;
- US-019 — Registrar Auditoria do Cadastro;
- US-020 — Confirmar Criação do Devedor.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-002 — Cadastro de Devedores;
- PRODUCT-002 — Capability Administrar Cadastro;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-020 — Aggregate Devedor;
- DOMAIN-022 — Value Object Documento;
- DOMAIN-023 — Domain Service UnicidadeDevedorService;
- DOMAIN-024 — Business Rule Documento Único por Carteira;
- AD-002 — Idempotency Key;
- ADR-002 — Auditoria Independente da Transação.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- o Devedor puder ser criado com sucesso;
- a unicidade do documento for garantida na Carteira;
- o Devedor for vinculado à Carteira;
- os contatos forem registrados;
- a criação estiver registrada para auditoria;
- todas as User Stories estiverem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da Feature Criar Devedor, criada no ciclo SDD do EPIC-002. |
