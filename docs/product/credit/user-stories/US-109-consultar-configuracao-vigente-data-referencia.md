# US-109 - Consultar Configuracao Vigente por Data de Referencia

**ID:** US-109

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** consumidor autorizado,
**quero** consultar a configuracao financeira vigente em uma data de referencia,
**para** usar parametros oficiais na proposta, contrato ou operacao.

---

# 2. Critérios de Aceitação

- consulta usa Tenant, Carteira opcional, modalidade e `data_referencia`;
- sistema retorna exatamente uma configuracao vigente ou erro protegido;
- ausencia de configuracao aplicavel retorna `404` logico;
- conflito de vigencia retorna `409`;
- resposta inclui origem, versao e `consultada_em`.

---

# 3. Regras de Negócio Relacionadas

- consulta nao escolhe taxa silenciosamente quando houver ambiguidade;
- Configuracoes retorna parametros, nao resultado financeiro.

---

# 4. Dependências

- FEATURE-041 - Consultar e Capturar Configuracao Financeira;
- US-107 - Ativar e Substituir Configuracao sem Retroatividade.

---

# 5. Observações Técnicas

O contrato candidato e `ConfiguracaoFinanceiraVigenteV1`, conforme discovery do
EPIC-009.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Consultar Configuracao Vigente por Data de Referencia. |
