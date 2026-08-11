# US-086 - Consultar Pagamentos e Operacoes Encerradas

**ID:** US-086

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** gestor autorizado,
**quero** consultar pagamentos e operacoes encerradas,
**para** acompanhar realizacoes e encerramentos da carteira.

---

# 2. Critérios de Aceitação

- a consulta aceita periodo, Carteira e tipo de encerramento;
- Pagamentos brutos, estornos e liquido sao exibidos separadamente;
- cada estorno preserva `estorno_id`, `pagamento_id`, apropriacoes revertidas,
  motivo, autoria e datas oficiais;
- o total realizado soma `valor_efeito_realizado_assinado` fornecido pelo Motor;
- quitacao, renegociacao, encerramento administrativo e cancelamento preservam
  contexto de origem, tipo, datas e referencias oficiais;
- a consulta nao cria, estorna ou altera Pagamento;
- apenas dados autorizados sao retornados;
- filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- `409` nao se aplica enquanto a consulta nao combinar referencias
  independentes nem transicionar estado, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- Motor Financeiro registra Pagamento e quitacao;
- Motor produz `PagamentoEstornadoV1` e os efeitos assinados;
- Contratos produz encerramento administrativo e cancelamento;
- Relatorios apenas consolida fatos oficiais.

---

# 4. Dependências

- FEATURE-031 - Consultar Relatorios Operacionais;
- DOMAIN-012 - Evento Pagamento Registrado;
- DOMAIN-013 - Evento Emprestimo Quitado.
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-004 - Contratos de Credito;
- US-062 - Encerrar Contrato sem Alterar Operacao.

---

# 5. Observações Técnicas

O contrato segue `EncerramentoOperacaoV1` e distingue `quitacao_financeira`,
`renegociacao_financeira`, `encerramento_administrativo` e
`cancelamento_contratual`.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP aplicavel de DA-719 formalizado. |
| 1.1.0 | 2026-08-10 | Semantica de estorno, efeito realizado e encerramentos por origem formalizada. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Pagamentos e Operacoes Encerradas. |
