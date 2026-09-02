# FOUNDATION-008 — Escopo Oficial do MVP

**ID:** FOUNDATION-008

**Versão:** 1.2.0

**Status:** Aprovado

---

# 1. Objetivo

Este documento estabelece o escopo oficial da primeira versão (MVP) da plataforma.

Seu objetivo é definir claramente quais capacidades fazem parte da versão inicial e quais serão tratadas em versões futuras.

Toda funcionalidade deverá ser classificada como "Dentro do MVP" ou "Fora do MVP".

---

# 2. Contexto

O MVP representa o menor conjunto de capacidades necessário para permitir que um Credor administre suas operações de crédito de forma segura, previsível e auditável.

O escopo do MVP deverá permanecer estável durante todo o ciclo de desenvolvimento da versão 1.

---

# 3. Capacidades Incluídas no MVP

## Plataforma

- Isolamento por `tenant_id` — escopo estrutural, **não** multi-Tenant de produto
  (ver [ADR-003](../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md));
- Tenant;
- Usuários — **um operador humano** no v1, conforme a mesma ADR. O Copilot tem
  **identidade propria de servico**, com perfil minimamente privilegiado e
  revogavel (IMP-355), que nunca recebe `comercial.proposta.decidir` — e por isso
  o IMP-360 separou submeter de decidir. Um agente que age precisa ser
  identificavel na trilha (IMP-361); "um usuario" nunca significou "um Principal";
- Autenticação;
- Perfis de Acesso;
- Permissões.

---

## Cadastro

- Cadastro de Devedores;
- Histórico cadastral.

---

## Operações de Crédito

- Contratos de Crédito;
- Empréstimos;
- Pagamentos;
- Motor Financeiro;
- Memória de Cálculo;
- Juros;
- Juros por atraso;
- Amortização;
- Quitação;
- Situação da operação.

---

## Cobrança

- Acompanhamento de vencimentos;
- Identificação de inadimplência;
- Cobrança manual.

---

## Agenda

- Agenda financeira;
- Vencimentos;
- Lembretes.

---

## Comunicação

- Registro de contatos;
- Histórico de comunicação;
- Comunicação manual.

---

## Relatórios

- Relatórios operacionais;
- Relatórios financeiros;
- Indicadores básicos.

---

# 4. Capacidades Fora do MVP

> **Nota de 2026-09-01.** Duas entradas saíram desta lista porque o fundador as
> aprovou como escopo do v1, e mantê-las aqui permitiria rejeitar como "fora do
> MVP" dois ciclos em execução:
>
> - **Inteligência Artificial** — o Copilot é o segundo operador da plataforma
>   (FOUNDATION-001 §Visão) e está em execução no
>   [PLAN-033](../implementation/plans/PLAN-033-copilot-tianet.md);
> - **Integração com o WhatsApp** — decidida na
>   [DR-006](../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md)
>   e materializada no
>   [PLAN-034](../implementation/plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md),
>   com o canal já validado contra o provedor real.
>
> As demais integrações com terceiros seguem fora.

As funcionalidades abaixo não fazem parte da versão 1 da plataforma:

- Integrações bancárias;
- PIX automático;
- Cobrança automática;
- White Label;
- Marketplace;
- API pública;
- Aplicativo Mobile;
- Multi-Carteira operacional;
- Billing;
- Assinaturas;
- Integrações com terceiros **além do WhatsApp e do provedor de IA**. O Copilot
  opera em BYOK contra uma API compatível com OpenAI (DR-005, PLAN-033) — é
  integração de terceiro por definição, e está dentro do escopo aprovado;
- Automações avançadas.

---

# 5. Princípios

## Princípio 01

Toda funcionalidade deverá estar classificada neste documento antes de entrar no backlog.

---

## Princípio 02

Funcionalidades fora do MVP deverão ser direcionadas ao Roadmap do produto.

---

## Princípio 03

O escopo do MVP somente poderá ser alterado mediante decisão formal de produto.

---

## Princípio 04

O foco da versão 1 é validar o modelo de negócio, não atender todos os cenários possíveis.

---

## Princípio 05

Simplicidade, previsibilidade e estabilidade têm prioridade sobre quantidade de funcionalidades.

---

# 6. Critérios de Aprovação

Este documento será considerado aprovado quando:

- todas as capacidades do MVP estiverem definidas;
- as exclusões estiverem explícitas;
- Product e Development utilizarem este documento como referência oficial de escopo.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.2.0 | 01/09/2026 | Reconciliacao com decisoes aprovadas: Inteligencia Artificial e a integracao WhatsApp saem da lista de exclusoes, porque o PLAN-033 e o PLAN-034 estao aprovados e em execucao; "Multi-Tenant Nivel 1" vira isolamento estrutural por `tenant_id` (ADR-003); e "Usuarios" passa a dizer um operador humano, com o Copilot como identidade de servico propria (IMP-355). |
| 1.1.0 | 23/08/2026 | Parcelas removidas do escopo do MVP: revogadas pela DR-004 (IMP-337). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Escopo do MVP. |
