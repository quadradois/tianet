# US-098 - Proteger Projections contra Verdade Paralela

**ID:** US-098

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** arquiteto financeiro,

**Quero** impedir que projections/read models recalculem valores financeiros,

**Para** preservar o Motor Financeiro como fonte unica da verdade.

---

# 2. Critérios de Aceitação

- projections sao reconstruiveis a partir de fatos oficiais;
- projection nao calcula juros, saldo, quitacao, amortizacao ou memoria;
- projection armazena `origem`, `versao` e `data_referencia` quando aplicavel;
- guardrail falha se evento, log ou projection introduzir calculo financeiro
  definitivo fora do Motor.

---

# 3. Regras de Negócio Relacionadas

- Motor Financeiro e unica autoridade de calculo definitivo;
- read model acelera leitura, mas nao cria verdade paralela.

---

# 4. Dependências

- FEATURE-036 - Preparar Eventos Internos e Projections;
- ADR-005 - Event Bus Interno e Eventos de Dominio;
- EPIC-005 - Motor Financeiro;
- US-074 - Impedir Calculo Financeiro fora do Motor;
- US-088 - Impedir Calculo Financeiro fora do Motor na Operacao Diaria.

---

# 5. Observações Técnicas

O PLAN deve prever teste de guardrail semelhante aos guardrails do Motor e da
Operacao Diaria, agora cobrindo eventos, logs e projections.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de protecao contra verdade paralela. |
