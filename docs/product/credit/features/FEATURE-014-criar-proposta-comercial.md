# FEATURE-014 — Criar Proposta Comercial

**ID:** FEATURE-014

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por criar uma proposta comercial de crédito vinculada
a um Devedor ativo.

Seu objetivo é transformar uma intenção comercial em registro rastreável,
auditável e preparado para decisão.

---

# 2. Valor de Negócio

A proposta comercial cria a ponte formal entre o cadastro do Devedor e a futura
formalização contratual.

---

# 3. Escopo

Esta Feature contempla:

- criar proposta comercial;
- vincular proposta a Carteira, Tenant e Devedor;
- aceitar parâmetros comerciais aprováveis;
- validar Devedor ativo e pertencente à Carteira;
- definir estado inicial da proposta;
- auditar a criação.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- decidir a proposta;
- editar proposta aprovada;
- formalizar contrato;
- criar empréstimo ou pagamento;
- executar cálculo financeiro definitivo.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-045 — Criar Proposta Comercial;
- US-046 — Validar Devedor Ativo para Proposta.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- FEATURE-013 — Simular Crédito;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-020 — Aggregate Devedor.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- proposta puder ser criada para Devedor ativo da Carteira autenticada;
- proposta nascer com estado inicial válido;
- Devedor inativo, inexistente ou de outra Carteira não originar proposta;
- parâmetros comerciais forem registrados sem cálculo financeiro definitivo;
- a criação estiver auditada;
- as User Stories estiverem concluídas.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da Feature Criar Proposta Comercial, criada no ciclo SDD do EPIC-003. |
