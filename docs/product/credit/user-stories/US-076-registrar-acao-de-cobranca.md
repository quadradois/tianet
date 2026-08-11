# US-076 - Registrar Acao de Cobranca

**ID:** US-076

**Versao:** 1.1.0

**Status:** Proposto

---

# 1. História

**Como** operador de cobranca autorizado,
**quero** registrar uma acao realizada,
**para** manter o acompanhamento auditavel da operacao.

---

# 2. Critérios de Aceitação

- a acao informa tipo, data, responsavel e resultado;
- a acao recebe Emprestimo obrigatorio, deriva Devedor e pode receber Parcela
  pertencente ao mesmo Emprestimo;
- o Principal autenticado define a autoria do registro;
- a mesma chave idempotente nao cria acao duplicada;
- formato, payload, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- Parcela visivel de outro Emprestimo ou chave idempotente reutilizada com
  payload diferente retorna `409`.

---

# 3. Regras de Negócio Relacionadas

- uma acao de cobranca registra atividade operacional;
- registrar acao nao altera estado ou valor financeiro.

---

# 4. Dependências

- FEATURE-028 - Gerir Cobranca Manual;
- US-075 - Consultar Fila de Cobranca;
- EPIC-006 - IAM.
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

O contrato de escrita deve aceitar chave idempotente e correlation ID.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-10 | Devedor derivado, cadeia referencial e erros protegidos formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Registrar Acao de Cobranca. |
