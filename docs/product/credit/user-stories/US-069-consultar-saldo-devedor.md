# US-069 - Consultar Saldo Devedor

**ID:** US-069

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. História

**Como** operador autorizado de credito,
**quero** consultar saldo devedor em data de referencia,
**para** entender a posicao financeira atual ou historica da operacao.

---

# 2. Critérios de Aceitação

- saldo e calculado pelo Motor Financeiro;
- consulta exige data de referencia explicita ou regra padrao documentada;
- resposta separa principal, juros, encargos e total;
- usuario sem permissao recebe 403;
- recurso cross-tenant responde 404.

---

# 3. Regras de Negócio Relacionadas

- FEATURE-026 - Consultar Saldo e Memoria de Calculo;
- DOMAIN-010 - Service Motor Financeiro.

---

# 4. Dependências

- FEATURE-026 - Consultar Saldo e Memoria de Calculo;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro.

---

# 5. Observações Técnicas

Consulta de saldo deve receber data de referencia explicita ou padrao documentado.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da User Story Consultar Saldo Devedor. |
