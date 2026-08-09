# US-051 — Encerrar Proposta sem Aprovação

**ID:** US-051

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Operador Comercial autorizado

**Quero** recusar, cancelar ou expirar uma proposta

**Para** encerrar propostas que não devem seguir para formalização.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- proposta elegível puder ser recusada;
- proposta elegível puder ser cancelada;
- proposta vencida puder ser expirada;
- proposta recusada, cancelada ou expirada não puder ser aprovada;
- cada encerramento registrar ator, instante, motivo quando aplicável e transição;
- a operação exigir Principal autenticado e permissão de decisão;
- tentativa de transição inválida responder conflito de estado.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada às seguintes regras e documentos:

- FEATURE-016 — Decidir Proposta;
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

Estados terminais encerram o ciclo comercial da proposta. Reabertura deve exigir
uma nova proposta, preservando a rastreabilidade da decisão anterior.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versão oficial da User Story Encerrar Proposta sem Aprovação. |
