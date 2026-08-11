# US-057 - Registrar Assinatura Contratual

**ID:** US-057

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuario autorizado

**Quero** registrar a assinatura ou formalizacao do contrato

**Para** preparar o contrato para liberacao logica ao Motor Financeiro futuro.

---

# 2. Critérios de Aceitação

- assinatura registra ator e instante;
- contrato em estado invalido nao pode ser assinado;
- transicao invalida retorna 409;
- assinatura e auditada;
- integracao externa de assinatura permanece fora do MVP.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-020 - Registrar Assinatura Contratual;
- EPIC-004 - Contratos de Credito.

---

# 4. Dependências

- FEATURE-020 - Registrar Assinatura Contratual;
- US-053 - Criar Contrato a partir de Proposta Aprovada.

---

# 5. Observações Técnicas

No MVP, assinatura e registro interno de formalizacao; provedor externo fica
fora do escopo.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Registrar Assinatura Contratual. |
