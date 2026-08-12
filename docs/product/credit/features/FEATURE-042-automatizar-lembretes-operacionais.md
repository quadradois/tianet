# FEATURE-042 - Automatizar Lembretes Operacionais

**ID:** FEATURE-042

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Converter a programacao de um Lembrete elegivel em trabalho duravel, mantendo a
Agenda como autoridade sobre horario, estado e cancelamento.

---

# 2. Valor de Negócio

Reduz esquecimentos operacionais sem comprometer a consistencia entre a Agenda
e a fila de execucao.

---

# 3. Escopo

- agendar job idempotente junto com o Lembrete;
- reagendar substituindo a intencao anterior de forma auditavel;
- cancelar job pendente quando a origem for concluida ou cancelada;
- revalidar origem, Tenant, Carteira, horario e contato antes do envio.

---

# 4. Fora do Escopo

- calcular vencimento ou inadimplencia;
- chamar provedor a partir do dominio Agenda;
- reabrir Lembrete terminal.

---

# 5. User Stories

- US-113 - Agendar Lembrete Automatico;
- US-114 - Cancelar Trabalho de Lembrete Inelegivel.

---

# 6. Dependências

- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes;
- PRODUCT-006 - Administrar Agenda;
- FEATURE-029 - Administrar Agenda Operacional.

---

# 7. Critérios de Aprovação

- Lembrete e job compartilham transacao e UnitOfWork;
- falha em qualquer escrita desfaz ambas;
- job obsoleto termina sem efeito;
- operacao permanece isolada por Tenant e Carteira.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Automatizar Lembretes Operacionais. |
