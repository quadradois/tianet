# DECISION REQUEST — DR-001 — Identidade externa do Devedor e forma dos endpoints

**Data:** 2026-08-07
**Solicitante:** Engenharia (sessão de execução do PLAN-003 — EPIC-002)
**Destinatário:** Arquitetura / Head de Produto
**Status:** **RESOLVIDA** — 2026-08-07, pela ADR-018
**Bloqueia:** —

---

> ## Resolução
>
> Decidida a **Opção A** (identidade externa contextualizada pela Carteira):
> o Devedor permanece Aggregate Root do contexto Cadastro, mas sua identidade
> externa pertence à Carteira. Todos os endpoints são aninhados sob
> `/credit/carteiras/{carteira_id}/devedores`.
>
> Devedor de outra Carteira responde **404 `devedor_nao_encontrado`**, mesmo
> código de identificador inexistente — a indistinguibilidade é intencional.
>
> **Decisão registrada em:** `docs/architecture/adrs/ADR-018-identidade-externa-do-devedor.md`
> (o identificador ADR-017, citado na TASK-089, está reservado a
> Billing/Subscriptions em AMP-001 §354).
>
> **Executada em:** TASK-089 — DOMAIN-020 §9, PLAN-003 §6, PLAN-003-EXEC
> IMP-058/059 e implementação HTTP alinhados.
>
> O conteúdo abaixo é preservado como registro da análise que motivou a decisão.

---

## 1. Objeto da decisão

**O Devedor possui identidade externa própria, endereçável de forma
independente, ou existe exclusivamente como parte interna do Aggregate
Carteira?**

Esta é uma decisão de modelagem, **não** de formato de URL. A forma dos
endpoints é consequência dela, não a questão em si.

---

## 2. Por que a decisão é necessária agora

Durante a implementação de IMP-057..IMP-059 constatou-se divergência entre
duas fontes oficiais quanto ao caminho dos endpoints de Devedor. A divergência
foi resolvida na implementação por escolha da Engenharia (seguiu-se o backlog
de execução), **o que foi um erro de processo**: a escolha pressupõe uma
definição de identidade que nenhuma fonte registra explicitamente.

A implementação **não foi alterada** e permanece como descrito na seção 4,
aguardando esta decisão.

---

## 3. Evidência documental — a ambiguidade é anterior à implementação

As fontes de domínio descrevem o Devedor de dois modos distintos, e o próprio
DOMAIN-020 registra a tensão de forma explícita.

### 3.1 Fontes que sugerem parte interna do Aggregate Carteira

| Fonte | Trecho |
|---|---|
| DOMAIN-001 §13 | "A Carteira representa o **Aggregate Root** do domínio de Operações de Crédito" |
| DOMAIN-001 §31 | "servir como **fronteira transacional** do domínio" |
| DOMAIN-001 §114 | "A Carteira estabelece a **fronteira de consistência** do domínio" |
| DOMAIN-001 §156 | Diagrama: `Carteira *-- Devedor : contém` (**composição**, não agregação) |
| DOMAIN-020 §9 | "**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira (referência)" |
| DOMAIN-020 §76 | "Nenhum Devedor de um Tenant é acessível por outro Tenant (isolamento **via Carteira**)" |

### 3.2 Fontes que sugerem identidade própria

| Fonte | Trecho |
|---|---|
| DOMAIN-020 §15 | "O Devedor é o **Aggregate Root** do contexto Cadastro" |
| DOMAIN-020 §19 | "concentrar as informações cadastrais — documento, contatos e histórico" |
| DOMAIN-020 | Possui `id` (UUID) próprio, ciclo de vida próprio (Ativo/Inativo) e entidade filha (Contato) |

### 3.3 A tensão já está registrada no próprio domínio

> **DOMAIN-020 §179:** "No domínio Credit, o Devedor é entidade da **fronteira
> da Carteira** (DOMAIN-001 §4); no contexto Cadastro, ele é o **Aggregate
> Root** que administra os dados cadastrais."

Esta frase descreve as duas leituras, mas **não decide** qual governa o
endereçamento externo. É exatamente essa lacuna que esta DR pede para fechar.

---

## 4. Estado atual da implementação (não alterado)

| Operação | PLAN-003 §6 (aninhado) | Implementado | Diverge |
|---|---|---|---|
| Criar | `/carteiras/{cid}/devedores` | idem | não |
| Listar / por documento | `/carteiras/{cid}/devedores` | idem | não |
| Consultar por ID | `/carteiras/{cid}/devedores/{id}` | `/devedores/{id}` | **sim** |
| Atualizar | `/carteiras/{cid}/devedores/{id}` | `/devedores/{id}` | **sim** |
| Inativar | `/carteiras/{cid}/devedores/{id}/inativar` | `/devedores/{id}/inativar` | **sim** |
| Reativar | `/carteiras/{cid}/devedores/{id}/reativar` | `/devedores/{id}/reativar` | **sim** |
| Histórico | `/carteiras/{cid}/devedores/{id}/historico` | `/devedores/{id}/historico` | **sim** |

Prefixo comum: `/credit`. Fonte da forma adotada:
`docs/implementation/backlogs/PLAN-003-execution-backlog.md` §IMP-058/059.

Nenhum cliente externo consome a API hoje: a mudança, se decidida, é livre de
quebra de contrato.

---

## 5. Consequências práticas de cada opção

### 5.1 Isolamento multi-tenant (consequência principal)

Nenhum endpoint de Devedor valida hoje a que Tenant o recurso pertence — a
lacuna vale para toda a API, não só para as rotas divergentes. Quando a
autorização for implementada:

- **Aninhado:** a Carteira está na URL. A verificação "este Tenant é dono desta
  Carteira?" pode ocorrer **antes do acesso ao dado**, em um ponto único
  (dependência de rota), e toda rota aninhada a herda.
- **Plano:** é preciso carregar o Devedor, resolver Carteira e Tenant, e então
  decidir — **dentro de cada handler**. Uma rota esquecida é vazamento entre
  Tenants.

Contrapartida do aninhado: a URL passa a admitir par inconsistente
(Carteira A + Devedor da Carteira B). Isso **exige** validação de pertinência
explícita; sem ela, o aninhamento oferece garantia apenas aparente.

### 5.2 Semântica de erro

O PLAN-003 §106 prevê `404 carteira_nao_encontrada` **e**
`404 devedor_nao_encontrado`. O primeiro só é distinguível se a Carteira
estiver na URL. Na forma plana implementada, os dois casos são hoje
indistinguíveis.

### 5.3 Evolução do modelo

- Se o Devedor vier a ser referenciado por outros contextos (Contrato,
  Cobrança), a identidade própria tende a se confirmar e o caminho plano
  torna-se natural.
- Se o Devedor permanecer confinado à Carteira, o aninhamento expressa
  corretamente a dependência e evita sugerir uma autonomia inexistente.

---

## 6. Opções

**Opção A — Devedor como parte do Aggregate Carteira (endpoints aninhados).**
Alinha à fronteira de consistência de DOMAIN-001 e ao PLAN-003 §6 já escrito.
Torna a autorização multi-tenant estrutural. Exige validação de pertinência
Carteira↔Devedor em 5 rotas.

**Opção B — Devedor com identidade externa própria (endpoints planos).**
Mantém a implementação atual e alinha a DOMAIN-020 §15. Exige atualizar o
PLAN-003 §6 e assumir que a autorização será verificada handler a handler.

**Opção C — Híbrido: criação e listagem aninhadas; operações por ID planas.**
É a forma hoje implementada. Precisa ser assumida como decisão consciente e
documentada, não como resultado de divergência — caso contrário reaparece.

> **Observação da Engenharia:** não há recomendação nesta DR. A escolha depende
> da intenção de modelagem do domínio, que é atribuição de Arquitetura. As
> consequências técnicas de cada caminho estão na seção 5 para subsidiar a
> decisão.

---

## 7. Encaminhamento após a decisão

1. Registrar a decisão (ADR, se Arquitetura entender cabível);
2. Tornar explícita a definição em DOMAIN-020 §179, eliminando a leitura dupla;
3. Alinhar a implementação à decisão (Opções A ou C implicam alteração de rotas
   e validação de pertinência; a Opção B não altera código);
4. Atualizar o PLAN-003 §6 e o backlog de execução para que ambos expressem a
   mesma forma, eliminando a divergência de origem.

---

## 8. Decisão pedida (síntese)

1. O Devedor possui identidade externa própria (B), é parte do Aggregate
   Carteira (A), ou adota-se o híbrido (C)?
2. Confirmada a forma, autoriza-se o alinhamento da implementação e a
   atualização do PLAN-003 §6?

---

## 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 07/08/2026 | Abertura da Decision Request — identidade externa do Devedor. |
