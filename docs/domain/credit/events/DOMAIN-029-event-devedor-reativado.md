# DOMAIN-029 — Domain Event Devedor Reativado

**ID:** DOMAIN-029

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Descrição

O evento Devedor Reativado representa a transição do Devedor do estado Inativo para o estado Ativo.

Ele comunica que o cadastro volta a originar novas operações, mantendo o mesmo documento e histórico.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- o Devedor Inativo for reativado;
- a transição de estado for confirmada com sucesso.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Devedor;
- Identificador da Carteira;
- Identificador do Tenant (via Carteira);
- Estado anterior (Inativo);
- Estado novo (Ativo);
- Data da reativação.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Comercial (retorno de elegibilidade);
- Cobrança (futuro);
- Relatórios.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do evento Devedor Reativado, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |