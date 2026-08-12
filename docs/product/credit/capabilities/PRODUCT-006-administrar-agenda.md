# PRODUCT-006 - Capability Administrar Agenda

**ID:** PRODUCT-006

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability organiza vencimentos financeiros oficiais, compromissos,
lembretes e retornos operacionais da carteira no Bounded Context Agenda.

---

# 2. Valor de Negocio

Administrar Agenda reduz perda de retornos e oferece ao operador uma visao
temporal do trabalho pendente, com automacao opcional e governada.

---

# 3. Responsabilidades

- consultar Agenda por periodo e responsavel;
- exibir `SituacaoParcelaNaDataV1` como vencimento financeiro somente leitura;
- criar compromissos e lembretes;
- reagendar, concluir e cancelar compromissos e lembretes;
- programar execucao automatica de lembretes por job duravel;
- cancelar atomicamente o job quando o lembrete deixar de ser elegivel;
- preservar historico de transicoes;
- integrar opcionalmente referencias de Devedor, Emprestimo ou Cobranca;
- aplicar IAM/RBAC e isolamento por Tenant/Carteira.

---

# 4. Contexto

Esta Capability pertence ao Bounded Context Agenda. No EPIC-007, ela integra o
contexto primario Cobranca por contrato conformista/ACL, sem depender do modelo
interno de Cobranca.

---

# 5. Limites

- nao altera vencimento ou estado financeiro;
- nao implementa Scheduler dentro do dominio Agenda;
- nao chama provedor de notificacao diretamente;
- nao cria obrigacao financeira.

---

# 6. Dependencias

- FOUNDATION-007 - Product Map;
- FOUNDATION-009 - Capability Map;
- EPIC-005 - Motor Financeiro como fonte de vencimentos;
- EPIC-002 - Cadastro de Devedores;
- PRODUCT-005 - Administrar Cobrancas, por contrato/ACL;
- EPIC-006 - IAM;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao.

---

# 7. Epicos

- EPIC-007 - Operacao Diaria.
- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes.

---

# 8. Criterios de Aprovacao

- Agenda funciona sem Scheduler;
- consulta exige `data_referencia` e distingue vencimento financeiro de item
  operacional;
- compromissos possuem responsavel, data, prioridade e estado validos;
- compromissos e lembretes compartilham transicoes e preservam historico;
- Lembrete e job correspondente sao persistidos ou cancelados atomicamente;
- Scheduler revalida a origem e nao decide regra de Agenda;
- referencias externas resolvem para a mesma cadeia por contrato/ACL;
- Tenant/Carteira e permissoes limitam todas as operacoes.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-11 | Automacao de lembretes por Scheduler externo ao dominio Agenda incorporada pelo EPIC-010. |
| 1.1.0 | 2026-08-10 | Agenda financeira, ciclo de lembretes e integridade referencial formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao da Capability Administrar Agenda para o EPIC-007. |
