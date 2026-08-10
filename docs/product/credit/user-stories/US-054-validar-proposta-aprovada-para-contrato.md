# US-054 - Validar Proposta Aprovada para Contrato

**ID:** US-054

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Sistema

**Quero** validar que a proposta esta aprovada e pertence ao contexto autenticado

**Para** impedir contratos indevidos ou vazamento cross-tenant.

---

# 2. Critérios de Aceitação

- proposta nao aprovada nao cria contrato;
- proposta inexistente ou de outro Tenant/Carteira retorna 404 indistinguivel;
- Devedor inativo bloqueia criacao;
- tentativa duplicada para a mesma proposta e tratada por regra explicita;
- falhas sao auditadas quando aplicavel.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-018 - Formalizar Contrato de Credito;
- EPIC-003 - Comercial / Propostas / Simulacao;
- EPIC-006 - IAM.

---

# 4. Dependências

- US-052 - Disponibilizar Proposta Aprovada para Contratos;
- FEATURE-018 - Formalizar Contrato de Credito.

---

# 5. Observações Técnicas

A validacao deve preservar 404 indistinguivel para recursos fora do Tenant ou
Carteira autenticados.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Validar Proposta Aprovada para Contrato. |
