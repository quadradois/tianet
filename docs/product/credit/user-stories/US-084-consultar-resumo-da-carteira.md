# US-084 - Consultar Resumo da Carteira

**ID:** US-084

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** gestor autorizado,
**quero** consultar um resumo operacional da Carteira,
**para** acompanhar sua situacao em um periodo.

---

# 2. Critérios de Aceitação

- a consulta exige periodo e Carteira autorizada;
- o resumo apresenta contagens e totais derivados de fatos oficiais;
- valores financeiros vem do Motor ou de read model de seus fatos;
- vencimento e inadimplencia agrupam `SituacaoParcelaNaDataV1`;
- efeitos realizados somam `valor_efeito_realizado_assinado` do Motor;
- filtros e data de referencia ficam explicitos na resposta;
- a consulta nao altera estado de negocio;
- dados de outra Carteira nao sao agregados;
- filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- `409` nao se aplica enquanto a consulta nao combinar referencias
  independentes nem transicionar estado, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- Relatorios e contexto de leitura;
- o Motor permanece fonte oficial dos valores financeiros.

---

# 4. Dependências

- FEATURE-031 - Consultar Relatorios Operacionais;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-006 - IAM.

---

# 5. Observações Técnicas

O PLAN tecnico definira read model, atualizacao e estrategia de rebuild.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP aplicavel de DA-719 formalizado. |
| 1.1.0 | 2026-08-10 | Situacao temporal e efeitos assinados formalizados como fontes dos totais. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Resumo da Carteira. |
