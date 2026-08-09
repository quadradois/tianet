# FEATURE-015 — Consultar Propostas

**ID:** FEATURE-015

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Esta Feature é responsável por consultar propostas comerciais e sua trilha de
decisão.

Seu objetivo é permitir que o Credor acompanhe o funil comercial da Carteira com
filtros seguros, rastreáveis e isolados por Tenant.

---

# 2. Valor de Negócio

A consulta de propostas dá visibilidade operacional ao ciclo comercial sem
depender de planilhas ou buscas manuais.

---

# 3. Escopo

Esta Feature contempla:

- consultar proposta por ID;
- listar propostas por Carteira;
- filtrar por Devedor, estado e período;
- consultar a trilha de decisões comerciais;
- preservar isolamento por Tenant/Carteira;
- aplicar paginação e ordenação determinística.

---

# 4. Fora do Escopo

Esta Feature não contempla:

- criar proposta;
- decidir proposta;
- exportar relatórios analíticos;
- consultar contratos ou operações financeiras;
- consultar dados de outro Tenant.

---

# 5. User Stories

Esta Feature é composta pelas seguintes User Stories:

- US-047 — Consultar Proposta por ID;
- US-048 — Listar Propostas;
- US-049 — Consultar Trilha de Decisões Comerciais.

---

# 6. Dependências

Esta Feature depende de:

- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- FEATURE-014 — Criar Proposta Comercial;
- EPIC-006 — IAM;
- ADR-004 — Autenticação e Autorização.

---

# 7. Critérios de Aprovação

Esta Feature será considerada concluída quando:

- proposta puder ser consultada por ID dentro da Carteira autenticada;
- propostas puderem ser listadas com filtros e paginação;
- trilha de decisões comerciais puder ser consultada;
- recurso inexistente ou de outro Tenant responder como não encontrado;
- leitura exigir Principal autenticado e permissão comercial;
- consultas não alterarem a trilha de auditoria de escrita.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da Feature Consultar Propostas, criada no ciclo SDD do EPIC-003. |
