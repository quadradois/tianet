# US-099 - Definir Modalidade Financeira Permitida

**ID:** US-099

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador financeiro autorizado,
**quero** definir modalidades financeiras permitidas,
**para** que propostas e contratos usem somente modalidades governadas.

---

# 2. Critérios de Aceitação

- modalidade possui codigo, descricao, Tenant e vigencia;
- modalidade pode ter escopo de Carteira quando necessario;
- modalidade indisponivel nao pode ser usada em nova configuracao;
- criacao registra autoria e motivo.

---

# 3. Regras de Negócio Relacionadas

- modalidade e parametro governado, nao resultado financeiro;
- modalidade de outro Tenant deve responder `404` logico na borda HTTP.

---

# 4. Dependências

- FEATURE-037 - Administrar Modalidades Financeiras;
- EPIC-009 - Configuracoes Financeiras e Calendario Operacional.

---

# 5. Observações Técnicas

O PLAN deve prever unicidade por Tenant, Carteira opcional, codigo e janela de
vigencia aplicavel.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Definir Modalidade Financeira Permitida. |
