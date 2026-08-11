# US-083 - Consultar Historico de Comunicacao

**ID:** US-083

**Versao:** 1.3.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** consultar o historico de comunicacoes de um devedor ou operacao,
**para** compreender os contatos anteriores antes de agir.

---

# 2. Critérios de Aceitação

- o historico aceita filtros por Devedor, Emprestimo, periodo e canal;
- registros sao ordenados cronologicamente de forma deterministica;
- autoria, data, canal e resultado sao exibidos;
- apenas dados do Tenant/Carteira autorizados sao retornados;
- filtro, periodo ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- filtros visiveis de cadeias diferentes retornam `409`, conforme DA-719;
- a resposta e paginada.

---

# 3. Regras de Negócio Relacionadas

- historico de comunicacao e imutavel como registro de atividade;
- dados de contato sao expostos somente a Principals autorizados.

---

# 4. Dependências

- FEATURE-030 - Registrar Comunicacao Manual;
- US-082 - Registrar Comunicacao Manual;
- EPIC-006 - IAM.
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- PRODUCT-005 - Administrar Cobrancas.

---

# 5. Observações Técnicas

Politicas de retencao e mascaramento detalhadas serao tratadas no PLAN tecnico.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.3.0 | 2026-08-10 | Recurso inexistente incluido explicitamente no contrato 404. |
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 completado. |
| 1.1.0 | 2026-08-10 | Dependencias e validacao da cadeia de filtros formalizadas. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Consultar Historico de Comunicacao. |
