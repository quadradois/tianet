# US-073 - Renegociar Operacao

**ID:** US-073

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** renegociar uma operacao,
**para** registrar nova condicao financeira sem perder a trilha da operacao
original.

---

# 2. Critérios de Aceitação

- renegociacao preserva vinculo com Emprestimo original;
- condicoes antigas permanecem auditaveis;
- nova condicao financeira tem memoria de calculo;
- transicao invalida responde 409;
- replay com mesma `Idempotency-Key` e mesmo payload retorna a memoria original;
- replay com mesma `Idempotency-Key` e payload divergente responde conflito.

---

# 3. Regras de Negócio Relacionadas

- renegociacao preserva trilha da operacao original;
- nova condicao financeira deve ser auditavel.

---

# 4. Dependências

- FEATURE-027 - Quitar e Renegociar Operacao;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

O MVP pode limitar renegociacao a registro inicial rastreavel. A operacao deve
exigir `Idempotency-Key` para evitar duplicidade de memoria/evento em retries.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-10 | Especifica contrato de idempotencia da renegociacao. |
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Renegociar Operacao. |
