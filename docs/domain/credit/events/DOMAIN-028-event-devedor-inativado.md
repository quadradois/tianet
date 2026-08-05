# DOMAIN-028 — Domain Event Devedor Inativado

**ID:** DOMAIN-028

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Descrição

O evento Devedor Inativado representa a transição do Devedor do estado Ativo para o estado Inativo.

Ele comunica que o cadastro deixa de originar novas operações, preservando integralmente seu histórico.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- o Devedor Ativo for inativado;
- a transição de estado for confirmada com sucesso.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Devedor;
- Identificador da Carteira;
- Identificador do Tenant (via Carteira);
- Estado anterior (Ativo);
- Estado novo (Inativo);
- Data da inativação.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Comercial (bloqueio de novas propostas);
- Cobrança (futuro);
- Relatórios.

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do evento Devedor Inativado, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |