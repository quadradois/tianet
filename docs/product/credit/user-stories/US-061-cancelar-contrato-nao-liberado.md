# US-061 - Cancelar Contrato nao Liberado

**ID:** US-061

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuario autorizado

**Quero** cancelar contrato ainda nao liberado

**Para** interromper formalizacao sem afetar operacao financeira inexistente.

---

# 2. Critérios de Aceitação

- contrato nao liberado pode ser cancelado conforme estado permitido;
- contrato liberado nao pode ser cancelado por esta Feature;
- motivo opcional, ator e instante sao registrados;
- transicao invalida retorna 409;
- cancelamento e auditado.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-022 - Cancelar ou Encerrar Contrato;
- EPIC-004 - Contratos de Credito.

---

# 4. Dependências

- FEATURE-022 - Cancelar ou Encerrar Contrato;
- US-053 - Criar Contrato a partir de Proposta Aprovada.

---

# 5. Observações Técnicas

Cancelamento de contrato liberado deve ficar fora deste fluxo para nao invadir
o EPIC-005.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Cancelar Contrato nao Liberado. |
