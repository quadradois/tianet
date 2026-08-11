# FEATURE-039 - Administrar Calendario Financeiro Operacional

**ID:** FEATURE-039

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Administrar calendario financeiro operacional usado para interpretar periodos,
dias corridos, dias uteis e referencias de vigencia.

---

# 2. Valor de Negócio

Evita que cada contexto interprete datas e periodos de forma diferente ao
preparar proposta, contrato, parcela ou relatorio.

---

# 3. Escopo

- cadastrar calendario financeiro por Tenant e Carteira quando aplicavel;
- definir regras operacionais de periodo permitidas no MVP;
- resolver periodo para uma `data_referencia`;
- disponibilizar calendario para snapshots de configuracao.

---

# 4. Fora do Escopo

- calcular juros por atraso;
- calcular saldo ou quitacao;
- integrar calendario regulatorio externo;
- executar Scheduler ou jobs temporizados.

---

# 5. User Stories

- US-103 - Administrar Calendario Financeiro;
- US-104 - Resolver Periodo por Data de Referencia.

---

# 6. Dependências

- EPIC-009 - Configuracoes Financeiras e Calendario Operacional;
- PRODUCT-009 - Administrar Configuracoes Financeiras;
- EPIC-005 - Motor Financeiro.

---

# 7. Critérios de Aprovação

- calendario possui origem, vigencia e escopo de Tenant/Carteira;
- resolucao de periodo e deterministica para a data de referencia;
- ausencia ou conflito de calendario aplicavel retorna erro protegido;
- calendario nao calcula valor financeiro definitivo.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Administrar Calendario Financeiro Operacional. |
