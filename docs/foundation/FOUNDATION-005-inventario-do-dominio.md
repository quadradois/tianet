# FOUNDATION-005 — Inventário do Domínio

**ID:** FOUNDATION-005

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Estabelecer o inventário oficial dos conceitos que compõem o domínio da plataforma.

Este documento representa a fonte oficial da Linguagem Ubíqua do projeto.

Todo novo conceito deverá ser registrado aqui antes de ser modelado como Aggregate, Entity, Value Object, Domain Service ou Domain Event.

---

# 2. Regras Gerais

- Cada conceito possui um único significado.
- Cada conceito pertence a um único Contexto de Negócio.
- Um conceito não pode possuir duas definições diferentes.
- Este documento é a referência oficial da linguagem utilizada em todo o projeto.

---

# 3. Participantes

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Credor | Proprietário da carteira que concede o crédito | Carteira |
| Devedor | Pessoa que recebe o crédito | Cadastro |

---

# 4. Operações

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Simulação | Estimativa financeira realizada antes da contratação | Comercial |
| Proposta | Oferta comercial apresentada ao Devedor | Comercial |
| Contrato de Crédito | Documento que estabelece as condições da operação | Contratos |
| Liberação | Ato de disponibilizar o valor contratado | Contratos |
| Empréstimo | Operação financeira em execução | Motor Financeiro |
| Renegociação | Alteração das condições de uma operação existente | Motor Financeiro |
| Quitação | Encerramento financeiro da operação | Motor Financeiro |

---

# 5. Financeiro

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Principal | Valor originalmente emprestado | Motor Financeiro |
| Saldo Devedor | Valor do principal ainda não amortizado | Motor Financeiro |
| Juros | Remuneração do capital emprestado | Motor Financeiro |
| Juros por Atraso | Juros proporcionais calculados sobre o atraso | Motor Financeiro |
| Amortização | Redução do saldo principal | Motor Financeiro |
| Pagamento | Registro de recebimento realizado pelo Devedor | Motor Financeiro |
| Período Financeiro | Intervalo utilizado para cálculo financeiro | Motor Financeiro |
| Memória de Cálculo | Demonstrativo completo dos cálculos realizados | Motor Financeiro |
| Valor para Quitação | Valor necessário para liquidar a operação em determinada data | Motor Financeiro |

---

# 6. Cobrança

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Cobrança | Processo de recuperação de crédito | Cobrança |
| Promessa de Pagamento | Compromisso assumido pelo Devedor | Cobrança |
| Inadimplência | Situação em que existe obrigação vencida e não paga | Cobrança |

---

# 7. Comunicação

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Mensagem | Comunicação enviada ao Devedor | Comunicação |
| Notificação | Aviso produzido por evento do domínio | Comunicação |
| Histórico de Comunicação | Registro das interações realizadas | Comunicação |

---

# 8. Agenda

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Vencimento | Data prevista para pagamento | Agenda |
| Lembrete | Aviso programado | Agenda |
| Compromisso | Atividade agendada pelo Credor | Agenda |

---

# 9. Configuração

| Conceito | Definição | Contexto |
|----------|-----------|----------|
| Taxa de Juros | Percentual aplicado ao principal | Configurações |
| Modalidade de Empréstimo | Define como a operação será amortizada (Livre ou Prazo Fixo) | Configurações |
| Regra de Cálculo | Estratégia utilizada pelo Motor Financeiro | Configurações |
| Calendário Financeiro | Regras para definição dos períodos financeiros | Configurações |

---

# 10. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Inventário do Domínio. |
