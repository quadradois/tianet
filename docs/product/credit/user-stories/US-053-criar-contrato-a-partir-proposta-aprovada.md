# US-053 - Criar Contrato a partir de Proposta Aprovada

**ID:** US-053

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Credor

**Quero** criar um contrato de credito a partir de uma proposta aprovada

**Para** formalizar a decisao comercial antes de qualquer operacao financeira.

---

# 2. Critérios de Aceitação

- contrato nasce apenas de proposta aprovada;
- contrato preserva Tenant, Carteira, Devedor e proposta de origem;
- parametros aprovados sao copiados para snapshot contratual;
- criacao e auditada;
- nenhuma entidade financeira e criada.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-018 - Formalizar Contrato de Credito;
- EPIC-004 - Contratos de Credito;
- FEATURE-017 - Integrar Proposta Aprovada.

---

# 4. Dependências

- US-052 - Disponibilizar Proposta Aprovada para Contratos;
- FEATURE-018 - Formalizar Contrato de Credito.

---

# 5. Observações Técnicas

O contrato deve copiar os parametros aprovados e nao manter dependencia mutavel
da proposta comercial.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Criar Contrato a partir de Proposta Aprovada. |
