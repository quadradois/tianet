# DOMAIN-002 — Entity Pessoa

**ID:** DOMAIN-002

**Versão:** 1.1.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

Pessoa representa um indivíduo com quem o proprietário da Carteira mantém, manteve ou poderá manter um relacionamento financeiro.

Ela representa o tomador dos empréstimos e concentra todas as informações necessárias para sua identificação, comunicação e histórico dentro da Carteira.

Uma Pessoa pode existir mesmo sem possuir empréstimos.

A Pessoa nunca representa uma empresa na versão 1 do produto.

---

# 2. Identidade

A identidade de uma Pessoa é única dentro de uma Carteira.

Uma Pessoa pertence obrigatoriamente a uma única Carteira.

Sua identidade permanece durante todo seu ciclo de vida, independentemente da quantidade de empréstimos realizados.

---

# 3. Responsabilidades

A Pessoa possui as seguintes responsabilidades:

- representar o tomador do empréstimo;
- manter seus dados cadastrais;
- disponibilizar informações de contato;
- manter o histórico de relacionamento financeiro;
- permitir consultas históricas.

A Pessoa não controla valores financeiros.

Valores pertencem ao Empréstimo.

Pagamentos pertencem ao Empréstimo.

---

# 4. Ciclo de Vida

## Criada

A Pessoa é cadastrada na Carteira.

---

## Ativa

Pode receber novos empréstimos.

Pode possuir empréstimos ativos.

Pode possuir empréstimos quitados.

---

## Inativa

Não poderá receber novos empréstimos.

Todo seu histórico permanece preservado.

---

# 5. Regras

## RN-001

Toda Pessoa pertence exatamente a uma Carteira.

---

## RN-002

Uma Pessoa pode existir sem possuir empréstimos.

---

## RN-003

Uma Pessoa pode possuir zero ou vários empréstimos.

---

## RN-004

Uma Pessoa nunca poderá representar uma empresa na versão 1.

---

## RN-005

Uma Pessoa com histórico financeiro nunca poderá ser excluída fisicamente.

---

## RN-006

A inativação não altera o histórico financeiro.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Pessoa (1)

↓

Empréstimo (0..N)

Uma Pessoa pode possuir nenhum, um ou vários empréstimos.

Todo Empréstimo pertence exatamente a uma Pessoa.

---

# 7. Invariantes

## INV-001

Pessoa sempre pertence a uma Carteira.

---

## INV-002

Pessoa nunca pertence a mais de uma Carteira.

---

## INV-003

Pessoa nunca perde seu histórico financeiro.

---

# 8. Glossário

## Pessoa

Indivíduo cadastrado na Carteira.

---

## Tomador

Pessoa que recebe um empréstimo.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|----------|------------|------------------------------|
| 1.1.0 | 23/08/2026 | Referencia a Parcelas removida: a entidade foi revogada pela DR-004 (IMP-337). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial. |
