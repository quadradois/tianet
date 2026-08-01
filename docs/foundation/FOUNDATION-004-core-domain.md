# FOUNDATION-004 — Core Domain

**ID:** FOUNDATION-004

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Definir o Core Domain da plataforma.

O Core Domain representa o conjunto de capacidades que diferenciam o produto no mercado e concentram as principais regras de negócio da operação de crédito.

Todas as demais funcionalidades existem para apoiar ou consumir os resultados produzidos pelo Core Domain.

---

# 2. Contexto

O produto não tem como principal objetivo cadastrar clientes, registrar contratos ou enviar mensagens.

Seu principal objetivo é administrar operações de crédito de forma segura, previsível e automatizada.

O maior diferencial competitivo da plataforma é sua capacidade de interpretar regras financeiras e transformá-las em informações confiáveis para o Credor.

---

# 3. Definição do Core Domain

O Core Domain da plataforma é o **Motor Financeiro**.

Ele é responsável por interpretar todas as regras financeiras da operação de crédito.

Nenhum outro contexto poderá executar cálculos financeiros.

Todo cálculo deverá ser centralizado no Motor Financeiro.

---

# 4. Responsabilidades do Core Domain

O Motor Financeiro é responsável por:

- administrar empréstimos;
- interpretar contratos;
- calcular períodos financeiros;
- calcular juros;
- calcular juros por atraso;
- calcular amortizações;
- calcular saldo devedor;
- calcular valor para quitação;
- registrar pagamentos;
- identificar inadimplência;
- identificar quitação;
- processar renegociações;
- produzir memória de cálculo;
- produzir informações para os demais contextos.

---

# 5. Princípios do Core Domain

## Princípio 01

O sistema armazena fatos financeiros.

Nunca armazena valores financeiros derivados quando estes puderem ser calculados.

---

## Princípio 02

Todo pagamento deverá ser processado pelo Motor Financeiro antes de alterar qualquer operação.

---

## Princípio 03

Juros possuem prioridade sobre amortização.

Todo pagamento deverá primeiro quitar os juros devidos.

Somente o valor remanescente poderá amortizar o principal.

---

## Princípio 04

O cálculo financeiro deverá considerar períodos reais.

O sistema nunca assumirá períodos fixos.

Toda competência financeira deverá considerar a quantidade real de dias entre dois eventos financeiros.

---

## Princípio 05

O Motor Financeiro será a única fonte oficial para:

- saldo devedor;
- juros acumulados;
- valor atualizado;
- valor para quitação;
- memória de cálculo.

---

# 6. Eventos Produzidos

O Core Domain produzirá eventos para os demais contextos.

Exemplos:

- Empréstimo Criado;
- Pagamento Registrado;
- Juros Calculados;
- Parcela Gerada;
- Parcela Vencida;
- Empréstimo Quitado;
- Empréstimo Renegociado.

Os demais contextos apenas consomem esses eventos.

---

# 7. Critérios de Aprovação

Este documento será considerado aprovado quando:

- todas as responsabilidades do Core Domain estiverem definidas;
- todos os princípios estiverem formalizados;
- nenhum cálculo financeiro existir fora do Motor Financeiro.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Core Domain. |
