# DOMAIN-004 — Entity Empréstimo

**ID:** DOMAIN-004

**Versão:** 1.0.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

O Empréstimo representa o estado atual de uma operação de crédito originada por um Contrato de Crédito.

Sua responsabilidade é refletir, a qualquer momento, a situação financeira da operação.

O Empréstimo não define regras financeiras.

As regras pertencem ao Contrato de Crédito.

Os cálculos pertencem ao Motor Financeiro.

O Empréstimo representa apenas o estado consolidado da operação após cada processamento.

---

# 2. Identidade

Um Empréstimo possui identidade única dentro da Carteira.

Todo Empréstimo é originado por exatamente um Contrato de Crédito.

Após sua criação sua identidade nunca poderá ser alterada.

---

# 3. Responsabilidades

O Empréstimo é responsável por manter o estado atual da operação.

Entre suas responsabilidades estão:

- manter o saldo principal atual;
- manter o status da operação;
- manter a data do último processamento financeiro;
- manter a data do último pagamento;
- manter o próximo vencimento;
- indicar se existe inadimplência;
- indicar se a operação está quitada;
- disponibilizar o estado atual para consultas.

O Empréstimo não calcula juros.

O Empréstimo não calcula amortizações.

O Empréstimo não processa pagamentos.

Essas responsabilidades pertencem exclusivamente ao Motor Financeiro.

---

# 4. Ciclo de Vida

## Aguardando Liberação

O contrato foi formalizado, porém o crédito ainda não foi liberado.

---

## Ativo

A operação encontra-se em execução.

Pode receber pagamentos.

Pode gerar juros.

Pode entrar em atraso.

---

## Quitado

O saldo principal foi totalmente amortizado.

A operação permanece disponível apenas para consulta histórica.

Não poderá receber novos pagamentos.

---

## Cancelado

A operação foi cancelada antes de sua conclusão.

Seu histórico permanece preservado.

---

# 5. Regras

## RN-001

Todo Empréstimo pertence exatamente a um Contrato de Crédito.

---

## RN-002

Todo Empréstimo pertence exatamente a uma Carteira.

---

## RN-003

Todo Empréstimo possui exatamente um estado atual.

---

## RN-004

Todo processamento financeiro deverá ser realizado pelo Motor Financeiro.

---

## RN-005

Todo pagamento recebido deverá atualizar o estado atual da operação.

---

## RN-006

Uma operação quitada não poderá receber novos pagamentos.

---

## RN-007

Uma operação cancelada não poderá voltar ao estado ativo.

---

## RN-008

O estado atual deverá representar fielmente o resultado do último processamento financeiro.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Contrato de Crédito (1)

↓

Empréstimo (1)

---

Empréstimo (1)

↓

Pagamento (0..N)

---

Empréstimo (1)

↓

Memória de Cálculo (0..N)

---

Motor Financeiro

↓

Atualiza

↓

Empréstimo

---

# 7. Invariantes

## INV-001

Todo Empréstimo possui exatamente um Contrato de origem.

---

## INV-002

Todo Empréstimo pertence exatamente a uma Carteira.

---

## INV-003

O estado atual deve ser consistente com o histórico da operação.

---

## INV-004

O saldo principal nunca poderá ser negativo.

---

## INV-005

Toda alteração do estado atual deverá ser consequência de um processamento realizado pelo Motor Financeiro.

---

# 8. Glossário

## Estado Atual

Fotografia consolidada da operação após o último processamento financeiro.

---

## Histórico da Operação

Conjunto de pagamentos, eventos, memórias de cálculo e demais registros produzidos durante toda a vida da operação.

---

## Processamento Financeiro

Execução das regras financeiras pelo Motor Financeiro com o objetivo de atualizar o estado atual da operação.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Empréstimo como estado atual da operação. |
