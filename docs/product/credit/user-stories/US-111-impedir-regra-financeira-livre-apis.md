# US-111 - Impedir Regra Financeira Livre em APIs

**ID:** US-111

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** arquiteto da plataforma,
**quero** impedir regra financeira livre em APIs consumidoras,
**para** garantir que parametros oficiais venham de configuracao ou snapshot.

---

# 2. Critérios de Aceitação

- Comercial, Contratos e Motor nao aceitam regra financeira arbitraria como
  fonte oficial;
- APIs consumidoras usam referencia de configuracao aprovada ou snapshot
  imutavel validado;
- payload livre de taxa, politica ou calendario oficial e recusado;
- OpenAPI documenta o contrato permitido e os erros protegidos.

---

# 3. Regras de Negócio Relacionadas

- request livre nao define regra financeira;
- parametros financeiros pertencem ao Tenant e Carteira corretos.

---

# 4. Dependências

- FEATURE-041 - Consultar e Capturar Configuracao Financeira;
- EPIC-003 - Comercial;
- EPIC-004 - Contratos de Credito;
- EPIC-005 - Motor Financeiro.

---

# 5. Observações Técnicas

O PLAN deve prever guardrails e testes de contrato para payloads que tentem
contornar referencia ou snapshot oficial.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Impedir Regra Financeira Livre em APIs. |
