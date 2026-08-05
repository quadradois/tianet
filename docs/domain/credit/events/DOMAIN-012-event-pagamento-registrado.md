# DOMAIN-012 — Domain Event Pagamento Registrado

**ID:** DOMAIN-012

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Descrição

O evento Pagamento Registrado representa a conclusão do processamento financeiro de um pagamento.

Ele é publicado após o Motor Financeiro validar, processar e atualizar o estado da operação de crédito.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- um Pagamento for processado com sucesso;
- o Empréstimo for atualizado;
- a Memória de Cálculo for produzida;
- todas as regras financeiras forem aplicadas.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Pagamento;
- Identificador do Empréstimo;
- Identificador do Contrato de Crédito;
- Identificador da Carteira;
- Data do processamento;
- Valor recebido;
- Valor destinado aos juros;
- Valor destinado à amortização;
- Saldo principal atualizado;
- Situação atual do Empréstimo.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Cobrança;
- Comunicação;
- Agenda;
- Relatórios;
- Auditoria.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do evento Pagamento Registrado. |
