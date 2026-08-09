# FEATURE-013 — Simular Crédito

**ID:** FEATURE-013

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por registrar simulações comerciais de crédito para
Devedores ativos.

Seu objetivo é permitir que o Credor avalie cenários comerciais antes de criar
uma proposta, sem gerar obrigação financeira ou cálculo definitivo.

---

# 2. Valor de Negócio

A simulação reduz retrabalho comercial e permite comparar condições antes de
submeter uma proposta para análise.

---

# 3. Escopo

Esta Feature contempla:

- criar simulação comercial vinculada a Carteira e Devedor;
- registrar parâmetros comerciais informados pelo Credor;
- consultar simulação por ID;
- validar Devedor ativo na Carteira autenticada;
- proteger operações por IAM/RBAC;
- auditar a criação da simulação.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- criar proposta automaticamente;
- aprovar crédito;
- formalizar contrato;
- criar operação financeira;
- executar cálculo financeiro definitivo.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-043 — Criar Simulação Comercial;
- US-044 — Consultar Simulação Comercial.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-020 — Aggregate Devedor.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- a simulação puder ser criada para Devedor ativo da Carteira autenticada;
- simulação de Devedor inexistente, inativo ou de outra Carteira for recusada;
- a simulação puder ser consultada por ID;
- a criação estiver auditada;
- as operações exigirem Principal autenticado e permissão comercial;
- nenhum cálculo financeiro definitivo for executado.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da Feature Simular Crédito, criada no ciclo SDD do EPIC-003. |
