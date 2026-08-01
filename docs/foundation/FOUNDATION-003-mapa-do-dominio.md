# FOUNDATION-003 — Mapa do Domínio

**ID:** FOUNDATION-003

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Definir os limites do domínio do Sistema de Gestão de Operações de Crédito.

Este documento estabelece os principais contextos de negócio da plataforma, suas responsabilidades e a relação entre eles.

Seu objetivo é garantir que cada contexto possua uma única responsabilidade de negócio, reduzindo acoplamento e facilitando a evolução do produto.

---

# 2. Contexto

O produto não é apenas um sistema para registrar empréstimos.

Ele é uma plataforma para administrar toda a operação de crédito de um Credor, desde o cadastro do Devedor até a quitação da dívida e o relacionamento posterior.

Todo o sistema está organizado em Contextos de Negócio (Business Contexts).

---

# 3. Contextos do Domínio

## 3.1 Carteira

Responsável pela administração da carteira do Credor.

Principais responsabilidades:

- administração da carteira;
- indicadores gerais;
- visão consolidada da operação.

---

## 3.2 Cadastro

Responsável pelos cadastros do domínio.

Inclui:

- Devedores;
- informações cadastrais;
- contatos;
- documentos.

---

## 3.3 Comercial

Responsável pela origem da operação.

Inclui:

- simulações;
- propostas;
- análise comercial;
- aprovação.

---

## 3.4 Contratos

Responsável pela formalização da operação.

Inclui:

- contrato;
- assinatura;
- liberação do crédito.

---

## 3.5 Motor Financeiro (Core Domain)

É o principal contexto do sistema.

Responsável por:

- empréstimos;
- períodos financeiros;
- cálculo de juros;
- amortizações;
- pagamentos;
- saldo devedor;
- quitação;
- renegociação;
- memória de cálculo.

Todo cálculo financeiro da plataforma deverá ocorrer exclusivamente neste contexto.

Nenhum outro contexto poderá calcular juros, saldo ou amortizações.

---

## 3.6 Cobrança

Responsável pela recuperação de crédito.

Inclui:

- cobranças;
- acordos;
- promessas de pagamento;
- acompanhamento da inadimplência.

---

## 3.7 Comunicação

Responsável pelo relacionamento com o Devedor.

Inclui:

- WhatsApp;
- SMS;
- E-mail;
- histórico de comunicações.

Este contexto nunca executa cálculos financeiros.

Ele apenas consome eventos produzidos pelo Motor Financeiro.

---

## 3.8 Agenda

Responsável pelos compromissos da operação.

Inclui:

- vencimentos;
- retornos;
- visitas;
- lembretes.

---

## 3.9 Relatórios

Responsável pela consolidação das informações.

Inclui:

- fluxo de caixa;
- carteira ativa;
- inadimplência;
- juros recebidos;
- desempenho da operação.

---

## 3.10 Configurações

Responsável pelas parametrizações do sistema.

Inclui:

- taxas padrão;
- modelos de contrato;
- regras operacionais;
- parâmetros financeiros.

---

# 4. Relação entre os Contextos

O fluxo principal do sistema é:

Cadastro

↓

Comercial

↓

Contratos

↓

Motor Financeiro

↓

Cobrança

↓

Comunicação

↓

Relatórios

Todos os demais contextos dependem das informações produzidas pelo Motor Financeiro.

---

# 5. Princípios

- Cada contexto possui responsabilidade única.
- O Motor Financeiro é o Core Domain da plataforma.
- Nenhum cálculo financeiro poderá existir fora do Motor Financeiro.
- Comunicação nunca altera dados financeiros.
- Relatórios apenas consolidam informações.

---

# 6. Critérios de Aprovação

Este documento será considerado aprovado quando:

- todos os contextos estiverem definidos;
- cada contexto possuir responsabilidade única;
- não existirem sobreposições de responsabilidade.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do Mapa do Domínio. |
