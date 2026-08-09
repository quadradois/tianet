# EPIC-003 — Comercial / Propostas / Simulação

**ID:** EPIC-003

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Épico é responsável por administrar o ciclo comercial inicial das operações
de crédito: simular cenários, criar propostas, registrar decisões comerciais e
entregar propostas aprovadas para formalização futura no contexto Contratos.

Seu objetivo é criar a ponte rastreável entre Cadastro e Contratos sem antecipar
obrigações financeiras ou cálculo definitivo.

---

# 2. Valor de Negócio

O Comercial permite que o Credor avalie e aprove propostas antes de gerar uma
obrigação formal.

Sem este Épico, a plataforma pula a etapa de originação e corre o risco de
criar contratos ou operações financeiras sem decisão comercial auditável.

---

# 3. Escopo

Este Épico contempla:

- criação e consulta de simulações comerciais;
- criação de propostas comerciais para Devedores ativos;
- consulta de proposta por ID;
- listagem de propostas por Carteira, Devedor, estado e período;
- consulta da trilha de decisões comerciais;
- aprovação de proposta;
- recusa, cancelamento e expiração de proposta;
- disponibilização de proposta aprovada para Contratos futuro;
- auditoria das escritas e transições comerciais;
- autorização por IAM/RBAC e isolamento por Tenant/Carteira.

---

# 4. Fora do Escopo

Este Épico não contempla:

- cadastro ou manutenção de Devedores;
- formalização de Contratos de Crédito;
- assinatura, liberação ou geração documental contratual;
- criação de Empréstimos, Parcelas ou Pagamentos;
- cálculo financeiro definitivo;
- memória de cálculo, amortização, juros, saldo ou quitação;
- cobrança, agenda, comunicação ou relatórios operacionais;
- integrações externas de crédito, bancárias ou de scoring.

---

# 5. Features

Este Épico é composto pelas seguintes Features:

- FEATURE-013 — Simular Crédito;
- FEATURE-014 — Criar Proposta Comercial;
- FEATURE-015 — Consultar Propostas;
- FEATURE-016 — Decidir Proposta;
- FEATURE-017 — Integrar Proposta Aprovada.

---

# 6. Dependências

Este Épico depende de:

- PRODUCT-003 — Capability Administrar Comercial;
- PRODUCT-002 — Capability Administrar Cadastro;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- EPIC-002 — Cadastro de Devedores;
- EPIC-006 — IAM;
- FOUNDATION-006 — Arquitetura Multi-Tenant;
- FOUNDATION-009 — Capability Map;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização;
- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-020 — Aggregate Devedor.

---

# 7. Critérios de Aprovação

Este Épico será considerado concluído quando:

- todas as Features estiverem implementadas;
- simulações e propostas estiverem operacionais dentro da Carteira autenticada;
- Devedor inexistente, inativo ou de outra Carteira não originar proposta;
- proposta puder ser aprovada, recusada, cancelada ou expirada conforme estado;
- proposta aprovada estiver disponível para Contratos futuro;
- todas as escritas e decisões comerciais estiverem auditadas;
- endpoints comerciais responderem `401/403/404/409/422` conforme o contrato;
- nenhuma regra de cálculo financeiro definitivo existir no Comercial.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial do EPIC-003 — Comercial / Propostas / Simulação, materializada a partir do Discovery do EPIC-003. |
