# US-066 - Validar Periodos Financeiros Reais

**ID:** US-066

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** responsavel por auditoria financeira,
**quero** que os calculos usem periodos financeiros reais,
**para** evitar juros incorretos por mes fixo implicito.

---

# 2. Critérios de Aceitação

- todo calculo recebe data inicial e data final explicitas;
- a regra de periodo fica registrada na memoria de calculo;
- testes cobrem meses com quantidades diferentes de dias;
- o Motor nao usa periodo fixo implicito sem regra declarada.

---

# 3. Regras de Negócio Relacionadas

- periodo financeiro precisa ter datas explicitas;
- mes fixo implicito e proibido sem regra declarada.

---

# 4. Dependências

- FEATURE-024 - Gerar Plano de Parcelas;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Suites devem cobrir meses com quantidades diferentes de dias.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Validar Periodos Financeiros Reais. |
