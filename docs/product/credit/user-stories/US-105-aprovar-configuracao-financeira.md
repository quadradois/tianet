# US-105 - Aprovar Configuracao Financeira

**ID:** US-105

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** aprovador financeiro autorizado,
**quero** aprovar uma configuracao financeira valida,
**para** permitir sua ativacao imediata ou programada.

---

# 2. Critérios de Aceitação

- apenas configuracao `rascunho` valida pode ser aprovada;
- aprovacao exige Principal com permissao especifica;
- aprovacao registra autoria, data, motivo e versao;
- configuracao aprovada ainda respeita regras de vigencia antes de consumo.

---

# 3. Regras de Negócio Relacionadas

- configuracao nao validada nao pode ser ativada;
- aprovacao nao recalcula operacoes existentes.

---

# 4. Dependências

- FEATURE-040 - Gerir Vigencias de Configuracoes Financeiras;
- US-101 - Criar Configuracao Financeira em Rascunho;
- EPIC-006 - IAM.

---

# 5. Observações Técnicas

O PLAN deve definir se o MVP exige aprovacao simples por permissao administrativa
ou dupla aprovacao em ciclo futuro.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Aprovar Configuracao Financeira. |
