# US-107 - Ativar e Substituir Configuracao sem Retroatividade

**ID:** US-107

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador financeiro autorizado,
**quero** ativar nova configuracao e substituir a versao anterior,
**para** preservar evolucao de parametros sem alterar contratos historicos.

---

# 2. Critérios de Aceitação

- configuracao aprovada com inicio imediato passa a `ativa`;
- versao anterior aplicavel pode passar a `substituida`;
- snapshots antigos permanecem imutaveis;
- retroatividade automatica e proibida.

---

# 3. Regras de Negócio Relacionadas

- nova configuracao afeta apenas snapshots futuros;
- migracao ou reprocessamento historico exige decisao de produto e plano proprio.

---

# 4. Dependências

- FEATURE-040 - Gerir Vigencias de Configuracoes Financeiras;
- US-106 - Programar Ativacao de Configuracao Financeira.

---

# 5. Observações Técnicas

O PLAN deve tratar ativacao como transicao de estado auditavel e idempotente.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Ativar e Substituir Configuracao sem Retroatividade. |
