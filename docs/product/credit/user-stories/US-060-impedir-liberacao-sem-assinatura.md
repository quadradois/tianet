# US-060 - Impedir Liberacao sem Assinatura

**ID:** US-060

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Sistema

**Quero** impedir liberacao de contrato sem assinatura ou formalizacao

**Para** evitar origem financeira sem acordo formal.

---

# 2. Critérios de Aceitação

- contrato rascunho nao pode ser liberado;
- contrato cancelado ou encerrado nao pode ser liberado;
- tentativa invalida retorna 409;
- a regra e coberta por teste de dominio e API;
- falha nao cria saida para Motor.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-021 - Liberar Contrato para Motor Financeiro;
- EPIC-004 - Contratos de Credito.

---

# 4. Dependências

- FEATURE-021 - Liberar Contrato para Motor Financeiro;
- US-057 - Registrar Assinatura Contratual.

---

# 5. Observações Técnicas

Esta regra deve existir no dominio e tambem ser exercitada pela API com retorno
409.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Impedir Liberacao sem Assinatura. |
