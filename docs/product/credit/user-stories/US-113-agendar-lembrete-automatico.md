# US-113 - Agendar Lembrete Automatico

**ID:** US-113

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** programar o envio automatico de um Lembrete,
**para** que o contato ocorra no horario definido pela Agenda.

---

# 2. Critérios de Aceitação

- Lembrete elegivel e job idempotente nascem na mesma transacao e UnitOfWork;
- falha em qualquer escrita desfaz ambos;
- job preserva Tenant, Carteira, origem, versao, horario e correlation ID;
- reagendamento invalida a programacao anterior sem perder historico;
- nenhum envio acontece durante a transacao de criacao.

---

# 3. Regras de Negócio Relacionadas

- Agenda decide horario e elegibilidade; Scheduler somente executa;
- programar Lembrete nao cria nem altera obrigacao financeira.

---

# 4. Dependências

- FEATURE-042 - Automatizar Lembretes Operacionais;
- US-080 - Criar Compromisso e Lembrete.

---

# 5. Observações Técnicas

O contrato candidato e `JobAgendadoV1` do Discovery EPIC-010.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Agendar Lembrete Automatico. |
