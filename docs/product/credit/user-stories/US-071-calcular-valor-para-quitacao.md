# US-071 - Calcular Valor para Quitacao

**ID:** US-071

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** calcular valor para quitacao,
**para** informar quanto encerra a operacao em uma data de referencia.

---

# 2. Critérios de Aceitação

- valor de quitacao e calculado pelo Motor;
- data de referencia e obrigatoria ou documentada por regra padrao;
- resposta inclui memoria de calculo;
- calculo nao altera estado do Emprestimo.

---

# 3. Regras de Negócio Relacionadas

- valor de quitacao e calculado pelo Motor Financeiro;
- calculo de quitacao nao altera estado por si so.

---

# 4. Dependências

- FEATURE-027 - Quitar e Renegociar Operacao;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Comando de quitacao deve ser separado de consulta de valor para quitacao.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Calcular Valor para Quitacao. |
