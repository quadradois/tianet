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

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do Aggregate Devedor, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |
