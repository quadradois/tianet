# DOMAIN-027 — Domain Event Devedor Atualizado

**ID:** DOMAIN-027

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Descrição

O evento Devedor Atualizado representa a alteração dos dados cadastrais de um Devedor existente.

Ele ocorre quando nome ou contatos são alterados; o documento e o vínculo com a Carteira nunca são alterados.

---

# 2. Quando Ocorre

O evento deverá ser publicado quando:

- o nome do Devedor for atualizado;
- contatos forem adicionados, alterados ou removidos;
- o contato preferencial for alterado.

---

# 3. Dados Publicados

O evento deverá disponibilizar, no mínimo:

- Identificador do Devedor;
- Identificador da Carteira;
- Identificador do Tenant (via Carteira);
- Campos alterados (antes/depois);
- Data da alteração.

---

# 4. Consumidores

Exemplos de consumidores deste evento:

- Relatórios;
- Comunicação (futuro);
- Search (futuro).

---

# 5. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial do evento Devedor Atualizado, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |