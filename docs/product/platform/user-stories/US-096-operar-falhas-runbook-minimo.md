# US-096 - Operar Falhas com Runbook Minimo

**ID:** US-096

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador da plataforma,

**Quero** um runbook minimo para falhas comuns,

**Para** saber quais comandos e sinais observar antes de escalar um incidente.

---

# 2. Critérios de Aceitação

- runbook cobre falha de banco, falha de migration, falha de pipeline e erro 500;
- cada sintoma possui comandos de diagnostico;
- runbook cita como localizar logs por correlation ID;
- runbook nao pede acesso a segredo em texto claro.

---

# 3. Regras de Negócio Relacionadas

- operacao previsivel e parte da seguranca do MVP;
- runbook nao substitui automacao futura de incidentes.

---

# 4. Dependências

- FEATURE-035 - Padronizar Logs e Erros Tecnicos;
- ADR-015 - CI/CD e Gates de Qualidade;
- ADR-016 - Observability, Logging e Correlation ID.

---

# 5. Observações Técnicas

O documento deve viver em `docs/operations/` e referenciar os comandos oficiais
de qualidade e migrations.

---

# 6. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story de runbook minimo. |
