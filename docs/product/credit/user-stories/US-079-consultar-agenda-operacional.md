# US-079 - Consultar Agenda Operacional

**ID:** US-079

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** consultar minha Agenda operacional,
**para** visualizar vencimentos financeiros, compromissos, lembretes e retornos
por periodo.

---

# 2. Critérios de Aceitação

- a Agenda reune `vencimento_financeiro`, `compromisso` e `lembrete`;
- a consulta exige periodo e `data_referencia` e aceita responsavel, prioridade,
  tipo e estado como filtros;
- `vencimento_financeiro` vem de `SituacaoParcelaNaDataV1` e apresenta Parcela,
  Emprestimo, Devedor, data, classificacao, estado e valores oficiais;
- itens sao ordenados por data/hora, tipo e identificador;
- cada item apresenta sua referencia operacional quando houver;
- apenas itens do Tenant/Carteira autorizados sao retornados;
- a consulta nao depende de Scheduler para funcionar;
- filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- filtros visiveis de cadeias incompatíveis retornam `409`, conforme DA-719.

---

# 3. Regras de Negócio Relacionadas

- Agenda organiza trabalho e nao altera vencimento financeiro;
- agir sobre vencimento cria item operacional separado;
- visibilidade segue o Principal autenticado e suas permissoes.

---

# 4. Dependências

- FEATURE-029 - Administrar Agenda Operacional;
- EPIC-007 - Operacao Diaria;
- EPIC-006 - IAM.
- EPIC-005 - Motor Financeiro como fonte de vencimentos.

---

# 5. Observações Técnicas

O PLAN tecnico definira paginacao, ordenacao padrao e indices de consulta.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 formalizado. |
| 1.1.0 | 2026-08-10 | Agenda financeira, data de referencia e ordenacao deterministica formalizadas. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Agenda Operacional. |
