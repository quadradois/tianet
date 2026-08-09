# US-050 — Aprovar Proposta

**ID:** US-050

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial autorizado

**Quero** aprovar uma proposta elegível

**Para** permitir que ela siga para formalização futura no contexto Contratos.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- proposta em estado elegível puder ser aprovada;
- proposta já terminal não puder ser aprovada;
- proposta aprovada preservar seus parâmetros comerciais como imutáveis;
- a aprovação registrar ator, instante, estado anterior e estado posterior;
- a operação exigir Principal autenticado e permissão de decisão;
- aprovação de proposta de outro Tenant responder como não encontrada.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-016 — Decidir Proposta;
- FEATURE-017 — Integrar Proposta Aprovada;
- EPIC-003 — Comercial / Propostas / Simulação;
- ADR-002 — Auditoria Independente da Transação;
- ADR-004 — Autenticação e Autorização.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-016 — Decidir Proposta;
- FEATURE-014 — Criar Proposta Comercial.

---

# 5. Observações Técnicas

A aprovação é a única saída do Comercial para Contratos futuro. Ela não deve
criar Contrato de Crédito nem operação financeira dentro do EPIC-003.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Aprovar Proposta. |
