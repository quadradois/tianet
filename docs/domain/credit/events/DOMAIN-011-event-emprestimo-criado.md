# DOMAIN-011 — Domain Event Empréstimo Criado

**ID:** DOMAIN-011

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Descrição

O evento Empréstimo Criado representa a origem oficial de uma nova operação de crédito na plataforma.

Ele ocorre após a formalização do Contrato de Crédito e a liberação do valor contratado.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- existir um Contrato de Crédito formalizado;
- o crédito for efetivamente liberado;
- o Empréstimo for criado com sucesso.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Empréstimo;
- Identificador do Contrato de Crédito;
- Identificador da Carteira;
- Identificador do Devedor;
- Data da criação;
- Valor originalmente contratado.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Agenda;
- Cobrança;
- Comunicação;
- Relatórios.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial do evento Empréstimo Criado. |
