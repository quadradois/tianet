# US-075 - Consultar Fila de Cobranca

**ID:** US-075

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** operador de cobranca autorizado,
**quero** consultar uma fila de operacoes que exigem acompanhamento,
**para** priorizar minhas acoes diarias.

---

# 2. Critérios de Aceitação

- a fila aceita filtros por periodo, estado oficial, responsavel e Carteira;
- a consulta exige `data_referencia` e consome `SituacaoParcelaNaDataV1`;
- cada item referencia Devedor, Emprestimo e Parcela quando aplicavel;
- datas, classificacao, estados e valores exibidos vem da projecao oficial do
  Motor, inclusive `regularizada_em` quando aplicavel;
- somente itens do Tenant/Carteira autorizados sao retornados;
- a consulta e paginada e possui ordenacao deterministica;
- filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- filtros visiveis de cadeias incompatíveis retornam `409`, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- Cobranca e downstream do Motor Financeiro;
- a fila organiza fatos oficiais e nao recalcula inadimplencia ou saldo.

---

# 4. Dependências

- FEATURE-028 - Gerir Cobranca Manual;
- EPIC-007 - Operacao Diaria;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

A estrategia de projecao e atualizacao da fila sera definida no PLAN tecnico.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 formalizado. |
| 1.1.0 | 2026-08-10 | Projecao temporal oficial e data de referencia formalizadas. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Fila de Cobranca. |
