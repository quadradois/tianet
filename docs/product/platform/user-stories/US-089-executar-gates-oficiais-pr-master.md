# US-089 - Executar Gates Oficiais em PR e Master

**ID:** US-089

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** mantenedor da plataforma,

**Quero** que todo PR e atualizacao de `master` execute os gates oficiais,

**Para** impedir regressao silenciosa antes de merge ou continuidade do ciclo.

---

# 2. Critérios de Aceitação

- pipeline executa testes, lint, formatacao, typecheck e validacao documental;
- falha em qualquer gate obrigatorio bloqueia o resultado;
- comandos executados no CI possuem equivalente local documentado;
- resultado do gate fica rastreavel por commit ou PR.

---

# 3. Regras de Negócio Relacionadas

- qualidade operacional e pre-condicao do MVP;
- pipeline nao substitui revisao humana nem altera regra de negocio.

---

# 4. Dependências

- FEATURE-032 - Automatizar Pipeline de Qualidade;
- EPIC-008 - Fundacao Operacional e Observabilidade;
- ADR-015 - CI/CD e Gates de Qualidade.

---

# 5. Observações Técnicas

A matriz minima deve incluir `uv run pytest -q`, `uv run ruff check .`,
`uv run black --check .`, `uv run mypy src tests`, `npm run docs:test` e
`npm run docs:validate` e `npm run quality:migrations`.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de gates oficiais. |
