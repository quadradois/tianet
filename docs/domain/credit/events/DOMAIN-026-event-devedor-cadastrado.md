# DOMAIN-026 — Domain Event Devedor Cadastrado

**ID:** DOMAIN-026

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Descrição

O evento Devedor Cadastrado representa a origem oficial de um novo cadastro de Devedor na plataforma.

Ele ocorre quando o cadastro é concluído com sucesso e o Devedor entra no estado Ativo.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- o cadastro do Devedor for validado (dados obrigatórios e unicidade);
- o Devedor for criado e vinculado à Carteira;
- o estado inicial Ativo for confirmado.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Devedor;
- Identificador da Carteira;
- Identificador do Tenant (via Carteira);
- Documento (CPF);
- Nome;
- Contatos;
- Data da criação.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Comercial (originação de propostas);
- Contratos (formalização futura);
- Relatórios;
- Search (futuro).

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do evento Devedor Cadastrado, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |