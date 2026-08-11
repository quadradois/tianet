# US-077 - Registrar Promessa de Pagamento

**ID:** US-077

**Versao:** 1.3.0

**Status:** Proposto

---

# 1. História

**Como** operador de cobranca autorizado,
**quero** registrar uma promessa de pagamento informada pelo devedor,
**para** planejar o proximo acompanhamento sem alterar a operacao financeira.

---

# 2. Critérios de Aceitação

- a promessa informa data futura e valor positivo declarado;
- a promessa recebe Emprestimo, deriva Devedor e pode referenciar Parcela do
  mesmo Emprestimo;
- o registro preserva responsavel, data e origem da informacao;
- a promessa nasce com estado `pendente` conforme DA-718;
- a mesma chave idempotente nao cria promessa duplicada;
- a promessa nao altera saldo, vencimento, Parcela, Emprestimo ou Contrato;
- payload, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- cadeia visivel incompatível ou chave idempotente reutilizada com payload
  diferente retorna `409`, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- valor prometido e declaratorio e nao substitui valor oficial do Motor;
- promessa de pagamento nao e renegociacao financeira.

---

# 4. Dependências

- FEATURE-028 - Gerir Cobranca Manual;
- US-076 - Registrar Acao de Cobranca;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

O modelo deve distinguir explicitamente valor declarado de valor financeiro
oficial.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.3.0 | 2026-08-10 | Conflito de chave idempotente com payload divergente formalizado. |
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 separado por causa. |
| 1.1.0 | 2026-08-10 | Estado inicial, Devedor derivado, integridade referencial e erros formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Registrar Promessa de Pagamento. |
