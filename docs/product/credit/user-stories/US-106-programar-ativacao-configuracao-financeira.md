# US-106 - Programar Ativacao de Configuracao Financeira

**ID:** US-106

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador financeiro autorizado,
**quero** programar a ativacao futura de uma configuracao aprovada,
**para** trocar parametros em uma data prevista sem ambiguidade.

---

# 2. Critérios de Aceitação

- configuracao aprovada com inicio futuro passa a `programada`;
- sistema impede conflito com configuracao `ativa` ou `programada` no mesmo
  Tenant, Carteira, modalidade e vigencia;
- conflito de vigencia retorna `409`;
- programacao nao altera snapshots antigos.

---

# 3. Regras de Negócio Relacionadas

- alteracao nao e retroativa por padrao;
- vigencia conflitante nao pode ser resolvida silenciosamente.

---

# 4. Dependências

- FEATURE-040 - Gerir Vigencias de Configuracoes Financeiras;
- US-105 - Aprovar Configuracao Financeira.

---

# 5. Observações Técnicas

O PLAN deve prever constraint ou servico de dominio para detectar sobreposicao
de vigencia.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Programar Ativacao de Configuracao Financeira. |
