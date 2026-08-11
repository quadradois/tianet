# FEATURE-040 - Gerir Vigencias de Configuracoes Financeiras

**ID:** FEATURE-040

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Controlar aprovacao, programacao, ativacao, substituicao e historico das
configuracoes financeiras.

---

# 2. Valor de Negócio

Permite mudar politicas financeiras sem afetar contratos e snapshots ja
emitidos, preservando rastreabilidade e previsibilidade operacional.

---

# 3. Escopo

- aprovar configuracao valida;
- programar inicio futuro;
- ativar configuracao de inicio imediato;
- substituir versao anterior conforme vigencia;
- manter historico append-only de alteracoes relevantes.

---

# 4. Fora do Escopo

- aplicar retroatividade automatica;
- migrar operacoes historicas;
- recalcular contratos ou emprestimos existentes.

---

# 5. User Stories

- US-105 - Aprovar Configuracao Financeira;
- US-106 - Programar Ativacao de Configuracao Financeira;
- US-107 - Ativar e Substituir Configuracao sem Retroatividade;
- US-108 - Auditar Historico de Configuracao Financeira.

---

# 6. Dependências

- EPIC-009 - Configuracoes Financeiras e Calendario Operacional;
- PRODUCT-009 - Administrar Configuracoes Financeiras;
- EPIC-006 - IAM;
- ADR-002 - Auditoria Independente da Transacao.

---

# 7. Critérios de Aprovação

- apenas configuracao valida pode ser aprovada;
- duas configuracoes `ativa` ou `programada` nao podem conflitar para o mesmo
  Tenant, Carteira, modalidade e vigencia;
- versao anterior pode ser marcada como `substituida` sem alterar snapshots
  antigos;
- historico preserva autoria, motivo, estado anterior e novo estado.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Gerir Vigencias de Configuracoes Financeiras. |
