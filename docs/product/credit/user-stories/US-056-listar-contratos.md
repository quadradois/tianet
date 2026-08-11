# US-056 - Listar Contratos

**ID:** US-056

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** Usuario autorizado

**Quero** listar contratos da Carteira

**Para** acompanhar formalizacoes por Devedor, estado e periodo.

---

# 2. Critérios de Aceitação

- listagem e filtravel por Devedor, estado e periodo;
- paginacao e obrigatoria;
- ordenacao e deterministica;
- recursos ficam limitados ao Tenant/Carteira autenticados;
- leitura nao gera auditoria de escrita.

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

Listagem deve seguir o padrao de paginacao deterministica ja usado em Cadastro
e Comercial.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Listar Contratos. |
