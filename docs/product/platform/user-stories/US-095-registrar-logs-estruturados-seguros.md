# US-095 - Registrar Logs Estruturados Seguros

**ID:** US-095

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** responsavel por operacao,

**Quero** logs estruturados com campos minimos e mascaramento,

**Para** diagnosticar falhas sem vazar informacao sensivel.

---

# 2. Critérios de Aceitação

- logs possuem timestamp, level, logger, correlation ID, metodo, rota,
  status_code e duracao quando aplicavel;
- tokens, credenciais, documentos pessoais e payloads sensiveis sao mascarados;
- logs nao substituem audit log da ADR-002;
- testes negativos procuram vazamento de termos sensiveis.

---

# 3. Regras de Negócio Relacionadas

- observabilidade tecnica nao e trilha de auditoria de negocio;
- dados sensiveis nao devem aparecer em logs.

---

# 4. Dependências

- FEATURE-035 - Padronizar Logs e Erros Tecnicos;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 5. Observações Técnicas

O PLAN deve preferir logging padrao configurado de forma estruturada, salvo se
uma dependencia nova for explicitamente justificada.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de logs estruturados seguros. |
