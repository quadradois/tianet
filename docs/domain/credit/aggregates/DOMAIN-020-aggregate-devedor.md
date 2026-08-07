# DOMAIN-020 — Aggregate Devedor

**ID:** DOMAIN-020

**Versão:** 1.0.0

**Status:** Proposto

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira (referência)

---

# 1. Objetivo

O Devedor é o Aggregate Root do contexto Cadastro.

Ele representa a Pessoa (DOMAIN-002) cadastrada pelo Credor como responsável por obrigações financeiras futuras ou existentes dentro da Carteira.

Seu papel é concentrar as informações cadastrais — documento, contatos e histórico — e garantir a identificação única do Devedor dentro da Carteira.

Na versão 1 do produto, o Devedor é sempre pessoa física (DOMAIN-002 RN-004).

---

# 2. Responsabilidades

O Devedor é responsável por:

- manter a identificação civil (documento) única e imutável;
- manter o conjunto de contatos;
- garantir a unicidade do documento dentro da Carteira;
- preservar o histórico cadastral;
- controlar o estado operacional (Ativo/Inativo);
- servir como origem para operações dos contextos downstream.

O Devedor não executa cálculos financeiros.

Valores, Parcelas e Pagamentos pertencem ao Empréstimo (DOMAIN-004).

---

# 3. Invariantes

## INV-001

Todo Devedor pertence exatamente a uma Carteira (DOMAIN-001 INV-001).

---

## INV-002

O documento do Devedor é único dentro da Carteira (DOMAIN-024).

---

## INV-003

O documento é imutável após a criação do cadastro.

---

## INV-004

O Devedor nunca perde seu histórico cadastral (DOMAIN-025).

---

## INV-005

Transições de estado ocorrem apenas entre Ativo e Inativo, conforme a máquina de estados (Ativo → Inativo; Inativo → Ativo).

---

## INV-006

Nenhum Devedor de um Tenant é acessível por outro Tenant (isolamento via Carteira — DOMAIN-019).

---

# 4. Entidades Filhas

O Devedor é composto pelas seguintes entidades:

- Contato (DOMAIN-021)

---

# 5. Value Objects

O Devedor utiliza os seguintes Value Objects:

- Documento (DOMAIN-022)

---

# 6. Eventos

O Devedor produz os seguintes eventos:

- Devedor Cadastrado (DOMAIN-026);
- Devedor Atualizado (DOMAIN-027);
- Devedor Inativado (DOMAIN-028);
- Devedor Reativado (DOMAIN-029).

---

# 7. Regras

## RN-001

Todo Devedor pertence exatamente a uma Carteira.

---

## RN-002

O documento (CPF) é único dentro da Carteira.

---

## RN-003

Somente pessoa física pode ser Devedor na versão 1.

---

## RN-004

Devedor com histórico financeiro nunca é excluído fisicamente — apenas inativado.

---

## RN-005

Devedor inativo não pode originar novas operações.

---

## RN-006

A inativação não altera o histórico cadastral nem financeiro.

---

# 8. Relacionamentos

## Aggregate

Referencia o Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Carteira (1)

↓

Devedor (0..N)

---

Devedor (1)

↓

Contato (0..N)

---

Devedor (1)

↓

Empréstimo (0..N)

No domínio Credit, o Devedor é entidade da fronteira da Carteira (DOMAIN-001 §4); no contexto Cadastro, ele é o Aggregate Root que administra os dados cadastrais.

---

## Identidade externa (ADR-018)

As duas leituras do parágrafo anterior não competem: descrevem planos distintos,
e a ADR-018 estabelece qual governa cada um.

**O Devedor permanece Aggregate Root do contexto Cadastro.** Ele protege suas
próprias invariantes (§3), possui identidade (`id`), ciclo de vida (Ativo/Inativo)
e entidade filha (Contato, §4) próprios, e é carregado e persistido como uma
unidade de consistência.

**A identidade externa, porém, pertence à Carteira.** Ser Aggregate Root é uma
propriedade da consistência transacional interna, não uma afirmação sobre como o
recurso é endereçado por um cliente externo. Como a Carteira é a fronteira de
consistência do domínio (DOMAIN-001 §114) e o isolamento entre Tenants se dá via
Carteira (§5), o Devedor não é endereçável de forma independente.

**A fronteira HTTP acompanha a Carteira.** A hierarquia oficial de endereçamento
é `Tenant → Carteira → Devedor`, e toda operação sobre o Devedor ocorre sob
`/credit/carteiras/{carteira_id}/devedores`. Um Devedor requisitado sob uma
Carteira à qual não pertence responde `404 devedor_nao_encontrado` — o mesmo
código de um identificador inexistente, para não revelar sua existência através
da fronteira.

Princípios registrados na ADR-018:

- Aggregate Root não determina identidade externa da API.
- Recursos subordinados podem possuir identidade própria no domínio e ainda assim
  possuir identidade contextualizada externamente.

Este esclarecimento define exclusivamente o endereçamento externo; nenhuma
invariante, regra de negócio ou relação de domínio deste documento é alterada
por ele.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do Aggregate Devedor, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |
| 1.1.0 | 07/08/2026 | Seção 9 (Identidade externa) — ambiguidade do §179 eliminada conforme ADR-018. Nenhuma regra de domínio alterada. |
