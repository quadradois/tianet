# DOMAIN-010 — Domain Service Motor Financeiro

**ID:** DOMAIN-010

**Versão:** 2.0.0

**Status:** Aprovado

---

# 1. Objetivo

O Motor Financeiro é o Domain Service responsável por executar todas as regras financeiras da plataforma.

Ele centraliza o processamento das operações financeiras e garante que todos os cálculos sejam realizados de forma consistente.

Nenhum cálculo financeiro poderá existir fora deste serviço.

---

# 2. Responsabilidades

O Motor Financeiro é responsável por:

- calcular juros do período;
- calcular juros por atraso;
- calcular amortizações;
- calcular saldo devedor;
- calcular valor para quitação;
- processar pagamentos;
- distribuir pagamentos entre juros, encargos e principal;
- registrar o excedente do pagamento e o estorno lançado sobre ele;
- atualizar o estado atual do Empréstimo;
- produzir a Memória de Cálculo;
- identificar inadimplência;
- identificar quitação;
- produzir eventos do domínio.

---

# 3. Entradas

O Motor Financeiro poderá receber, entre outras, as seguintes entradas:

- Contrato de Crédito;
- Empréstimo;
- Pagamento;
- Data de Processamento;
- Data de Referência.

---

# 4. Saídas

O Motor Financeiro produzirá:

- Empréstimo atualizado;
- Pagamento processado;
- Memória de Cálculo;
- Eventos do domínio.

---

# 5. Regras

## RN-001

Todo cálculo financeiro deverá ocorrer exclusivamente no Motor Financeiro.

---

## RN-002

O Motor Financeiro deverá respeitar as condições definidas pelo Contrato de Crédito.

---

## RN-003

Na modalidade Livre, os pagamentos deverão priorizar:

1. Juros devidos;
2. Amortização do principal.

---

## RN-004

Os pagamentos são distribuídos na ordem juros, encargos e principal, cada
destino recebendo no máximo o que está em aberto.

Quando o valor recebido excede o total devido, a diferença é registrada como
excedente e não fica sem contrapartida: o Credor é avisado e lança o estorno do
valor, devolvendo-o ao devedor por fora do sistema. Ver DOMAIN-006.

---

## RN-005

O cálculo de juros por atraso deverá considerar a quantidade real de dias transcorridos.

---

## RN-006

O Motor Financeiro deverá atualizar o estado atual do Empréstimo após cada processamento.

---

## RN-007

Todo processamento deverá produzir uma Memória de Cálculo auditável.

---

## RN-008

Todo processamento deverá preservar a consistência entre o histórico da operação e o estado atual do Empréstimo.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 2.0.0 | 23/08/2026 | Liquidacao de Parcelas removida das responsabilidades e dos produtos do Motor; RN-004 passa a descrever a distribuicao juros/encargos/principal e o tratamento do excedente (IMP-337). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Domain Service Motor Financeiro. |
