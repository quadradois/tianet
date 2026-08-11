# US-103 - Administrar Calendario Financeiro

**ID:** US-103

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador financeiro autorizado,
**quero** administrar calendario financeiro operacional,
**para** padronizar periodos usados por propostas, contratos e operacoes.

---

# 2. Critérios de Aceitação

- calendario possui Tenant, Carteira opcional, codigo, vigencia e regras de
  periodo permitidas no MVP;
- calendario pode ser associado a configuracao financeira;
- calendario indisponivel ou de outro escopo nao pode ser usado;
- alteracao de calendario nao altera snapshots ja capturados.

---

# 3. Regras de Negócio Relacionadas

- calendario define periodo, nao resultado financeiro;
- Configuracoes nao executa Scheduler nem jobs temporizados.

---

# 4. Dependências

- FEATURE-039 - Administrar Calendario Financeiro Operacional;
- EPIC-009 - Configuracoes Financeiras e Calendario Operacional.

---

# 5. Observações Técnicas

O calendario MVP deve ficar limitado ao recorte definido no PLAN tecnico, sem
integracao regulatoria externa.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Administrar Calendario Financeiro. |
