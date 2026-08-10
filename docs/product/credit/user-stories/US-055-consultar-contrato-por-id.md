# US-055 - Consultar Contrato por ID

**ID:** US-055

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuario autorizado

**Quero** consultar um contrato de credito por ID

**Para** verificar suas condicoes, estado e origem comercial.

---

# 2. Critérios de Aceitação

- contrato existente do Tenant autenticado retorna dados publicos do contrato;
- contrato de outro Tenant/Carteira retorna 404;
- usuario sem permissao retorna 403;
- token ausente ou invalido retorna 401;
- resposta nao inclui dados internos de infraestrutura.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-019 - Consultar Contratos;
- EPIC-004 - Contratos de Credito.

---

# 4. Dependências

- FEATURE-019 - Consultar Contratos;
- EPIC-006 - IAM.

---

# 5. Observações Técnicas

A resposta deve expor DTO publico e nao objetos de ORM ou detalhes internos.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Consultar Contrato por ID. |
