# US-044 — Consultar Simulação Comercial

**ID:** US-044

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial

**Quero** consultar uma simulação comercial da minha Carteira

**Para** revisar os parâmetros avaliados antes de criar ou comparar propostas.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- o sistema permitir consultar simulação por ID;
- apenas simulações da Carteira autenticada forem retornadas;
- simulação inexistente ou de outro Tenant responder como não encontrada;
- a resposta incluir os parâmetros comerciais registrados;
- a operação exigir Principal autenticado e permissão comercial;
- a consulta não alterar estado nem criar auditoria de escrita.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-013 — Simular Crédito;
- EPIC-003 — Comercial / Propostas / Simulação;
- PRODUCT-003 — Capability Administrar Comercial;
- ADR-004 — Autenticação e Autorização.

---

# 4. Dependências

Esta User Story depende de:

- US-043 — Criar Simulação Comercial;
- FEATURE-013 — Simular Crédito.

---

# 5. Observações Técnicas

A consulta deve seguir o padrão de isolamento já adotado no backend: recurso de
outro Tenant não revela existência e deve ser tratado como não encontrado.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Consultar Simulação Comercial. |
