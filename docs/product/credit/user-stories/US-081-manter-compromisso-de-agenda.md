# US-081 - Manter Item de Agenda

**ID:** US-081

**Versao:** 1.3.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** reagendar, concluir ou cancelar um compromisso ou lembrete,
**para** manter a Agenda coerente com o trabalho realizado.

---

# 2. Critérios de Aceitação

- compromisso ou lembrete `aberto` pode ser reagendado, concluido ou cancelado;
- reagendamento exige nova data valida;
- reagendamento preserva data anterior/nova, responsavel e instante;
- conclusao e cancelamento registram responsavel e data;
- transicoes preservam historico;
- item concluido ou cancelado nao reabre; novo acompanhamento cria outro item;
- replay idempotente nao duplica historico;
- payload, data ou identificador malformado retorna `400`;
- transicao invalida, versao obsoleta ou chave com payload divergente retorna
  `409`;
- recurso inexistente ou cross-tenant retorna `404` logico.

---

# 3. Regras de Negócio Relacionadas

- compromisso concluido ou cancelado nunca retorna ao estado aberto; nova
  decisao de negocio cria outro item;
- manutencao da Agenda nao altera fatos financeiros.

---

# 4. Dependências

- FEATURE-029 - Administrar Agenda Operacional;
- US-080 - Criar Compromisso e Lembrete;
- EPIC-006 - IAM.

---

# 5. Observações Técnicas

As transicoes devem ser cobertas por testes de dominio antes da API.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.3.0 | 2026-08-10 | Regra de nao reabertura tornada inequívoca. |
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 completado. |
| 1.1.0 | 2026-08-10 | Ciclo de vida unificado de compromissos e lembretes formalizado. |
| 1.0.0 | 2026-08-10 | Primeira versao candidata da User Story Manter Compromisso de Agenda. |
