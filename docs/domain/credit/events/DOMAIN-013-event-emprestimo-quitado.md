# DOMAIN-013 — Domain Event Empréstimo Quitado

**ID:** DOMAIN-013

**Versão:** 1.1.0

**Status:** Aprovado

---

# 1. Descrição

O evento Empréstimo Quitado representa a conclusão financeira de uma operação de crédito.

Ele é publicado quando o Motor Financeiro identifica que o saldo principal da operação foi integralmente amortizado e não existem obrigações financeiras pendentes.

A partir deste momento, o Empréstimo passa para o estado **Quitado**.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- o saldo principal da operação atingir zero;
- os juros do período em aberto estiverem cobertos;
- todas as regras financeiras forem satisfeitas;
- o Empréstimo for atualizado para o estado Quitado.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Empréstimo;
- Identificador do Contrato de Crédito;
- Identificador da Carteira;
- Identificador do Devedor;
- Data da quitação;
- Valor total amortizado;
- Valor total de juros pagos;
- Quantidade de pagamentos realizados;
- Situação final da operação.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Comunicação;
- Relatórios;
- Agenda;
- Auditoria.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.1.0 | 23/08/2026 | Condicao de parcelas pendentes substituida pelos juros do periodo em aberto, conforme o emprestimo livre da DR-004 (IMP-337). |
| 1.0.0 | 01/08/2026 | Primeira versão oficial do evento Empréstimo Quitado. |
