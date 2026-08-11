# FEATURE-029 - Administrar Agenda Operacional

**ID:** FEATURE-029

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Objetivo

Organizar vencimentos financeiros oficiais, compromissos, lembretes e retornos
relacionados ao acompanhamento manual da carteira.

---

# 2. Valor de Negócio

Reduz perda de retornos e da ao operador uma visao temporal consistente do
trabalho pendente, sem depender de automacao no primeiro ciclo.

---

# 3. Escopo

- consultar vencimentos financeiros e itens operacionais por periodo,
  `data_referencia`, responsavel, prioridade e estado;
- criar compromisso e lembrete;
- associar item a Devedor, Emprestimo ou Caso de Cobranca;
- reagendar, concluir ou cancelar compromisso ou lembrete;
- registrar autoria e historico das transicoes.

---

# 4. Fora do Escopo

- executar Scheduler, cron ou batch;
- disparar notificacao externa;
- alterar vencimento financeiro;
- criar obrigacao financeira.

---

# 5. User Stories

- US-079 - Consultar Agenda Operacional;
- US-080 - Criar Compromisso e Lembrete;
- US-081 - Manter Item de Agenda.

---

# 6. Dependências

- EPIC-007 - Operacao Diaria;
- PRODUCT-006 - Administrar Agenda;
- EPIC-005 - Motor Financeiro como fonte de vencimentos;
- PRODUCT-005 - Administrar Cobrancas;
- FEATURE-028 - Gerir Cobranca Manual, por contrato/ACL;
- EPIC-002 - Cadastro de Devedores;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- Agenda filtra itens pelo periodo e escopo autorizado;
- vencimento financeiro e somente leitura de `SituacaoParcelaNaDataV1`;
- compromisso possui responsavel, data e prioridade validos;
- compromisso e lembrete nascem `aberto` e somente itens abertos podem ser
  reagendados, concluidos ou cancelados;
- item concluido ou cancelado nao reabre; novo acompanhamento cria outro item;
- reagendamento preserva historico;
- referencias a Cobranca sao opcionais e consumidas por contrato/ACL;
- Scheduler e notificacao externa nao sao requisitos do MVP;
- formato, filtro, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico;
- transicao proibida ou referencias visiveis incompatíveis retornam `409`,
  conforme DA-719.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 propagado para Agenda. |
| 1.1.0 | 2026-08-10 | Vencimentos financeiros, ciclo completo de lembretes e ACL formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao da Feature Administrar Agenda Operacional. |
