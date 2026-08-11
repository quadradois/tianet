# US-085 - Consultar Vencimentos e Inadimplencia

**ID:** US-085

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** gestor ou operador autorizado,
**quero** consultar vencimentos e inadimplencia por periodo,
**para** planejar o acompanhamento da carteira.

---

# 2. Critérios de Aceitação

- a consulta agrupa `SituacaoParcelaNaDataV1` em futuras, vencidas,
  regularizadas e canceladas;
- estados, valores e `regularizada_em` sao obtidos do Motor;
- `data_referencia` e obrigatoria e os filtros ficam explicitos;
- resultados podem ser filtrados por Carteira e situacao;
- a resposta e paginada quando listar operacoes;
- o relatorio nao aplica formula propria de mora ou atraso;
- filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- `409` nao se aplica enquanto a consulta nao combinar referencias
  independentes nem transicionar estado, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- classificacao financeira e produzida pelo Motor para a data de referencia;
- Relatorios nao redefine inadimplencia.

---

# 4. Dependências

- FEATURE-031 - Consultar Relatorios Operacionais;
- US-084 - Consultar Resumo da Carteira;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Indices e projecoes devem sustentar filtros por periodo sem recalculo financeiro.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP aplicavel de DA-719 formalizado. |
| 1.1.0 | 2026-08-10 | Contrato SituacaoParcelaNaDataV1 e historico de regularizacao formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Vencimentos e Inadimplencia. |
