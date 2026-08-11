# US-104 - Resolver Periodo por Data de Referencia

**ID:** US-104

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** consumidor autorizado de configuracoes,
**quero** resolver o calendario por uma data de referencia explicita,
**para** usar periodos consistentes sem inferencia silenciosa.

---

# 2. Critérios de Aceitação

- consulta informa ou deriva `data_referencia` explicita;
- ausencia de calendario aplicavel retorna `404` logico;
- conflito de calendario aplicavel retorna `409`;
- resolucao de periodo nao calcula juros, saldo, quitacao ou memoria.

---

# 3. Regras de Negócio Relacionadas

- vigencia e data de referencia sao obrigatorias;
- calendario define periodo, Motor calcula resultado.

---

# 4. Dependências

- FEATURE-039 - Administrar Calendario Financeiro Operacional;
- US-103 - Administrar Calendario Financeiro.

---

# 5. Observações Técnicas

O resultado deve ser rastreavel por calendario, versao, origem e
`data_referencia`.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Resolver Periodo por Data de Referencia. |
