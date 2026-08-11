# FEATURE-018 - Formalizar Contrato de Credito

**ID:** FEATURE-018

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Criar contrato de credito a partir de uma proposta comercial aprovada.

---

# 2. Valor de Negócio

Permite transformar a decisao comercial aprovada em um instrumento formal e
auditavel.

---

# 3. Escopo

- consumir proposta aprovada do EPIC-003;
- validar Tenant, Carteira, Devedor e proposta;
- criar snapshot contratual imutavel;
- registrar auditoria de criacao;
- impedir contrato para proposta nao aprovada.

---

# 4. Fora do Escopo

- calcular parcelas, juros ou saldo;
- criar Emprestimo;
- liberar dinheiro;
- assinar contrato.

---

# 5. User Stories

- US-053 - Criar Contrato a partir de Proposta Aprovada;
- US-054 - Validar Proposta Aprovada para Contrato.

---

# 6. Dependências

- EPIC-004 - Contratos de Credito;
- FEATURE-017 - Integrar Proposta Aprovada;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- contrato nasce apenas de proposta aprovada;
- snapshot preserva parametros aprovados;
- proposta invalida ou cross-tenant nao gera contrato;
- criacao e auditada.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Formalizar Contrato de Credito. |
