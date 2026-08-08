# US-004 — Criar Carteira Padrão

**ID:** US-004

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. História

**Como** Administrador da Plataforma

**Quero** que uma Carteira padrão seja criada junto com a organização

**Para** que o Tenant já nasça apto a receber cadastros e operações de crédito.

---

# 2. Critérios de Aceitação

A User Story será considerada concluída quando:

- toda organização provisionada possuir exatamente uma Carteira no MVP;
- a Carteira for criada na mesma transação do provisionamento;
- o vínculo Tenant→Carteira for obrigatório e garantido por chave estrangeira;
- a criação da Carteira ocorrer através da fronteira entre contextos, sem que o Platform Context acesse o modelo interno do Credit Context;
- a falha na criação da Carteira impedir o provisionamento inteiro.

---

# 3. Regras de Negócio Relacionadas

Esta User Story está relacionada aos seguintes documentos:

- DOMAIN-001 — Aggregate Carteira;
- DOMAIN-017 — Aggregate Tenant;
- DOMAIN-019 — Toda Carteira pertence exatamente a um Tenant;
- PRODUCT-001 — Capability Administrar Plataforma;
- EPIC-001 — Gerenciar Tenant;
- FEATURE-001 — Criar Tenant.

---

# 4. Dependências

Esta User Story depende de:

- FEATURE-001 — Criar Tenant;
- US-001 — Criar Tenant;
- US-003 — Validar Unicidade.

---

# 5. Observações Técnicas

A integração entre Platform e Credit ocorre por camada anticorrupção (AD-003): o
Platform Context solicita a criação e não conhece o modelo interno da Carteira.

A transação única (AD-001) garante que Tenant e Carteira sejam persistidos juntos
ou nenhum dos dois.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 08/08/2026 | Materialização da User Story, referenciada pela FEATURE-001 desde 01/08/2026 e implementada no EPIC-001. |
