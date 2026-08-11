# FEATURE-041 - Consultar e Capturar Configuracao Financeira

**ID:** FEATURE-041

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Permitir que consumidores autorizados consultem a configuracao financeira
vigente e capturem snapshots imutaveis para proposta e contrato.

---

# 2. Valor de Negócio

Garante que Comercial, Contratos e Motor usem parametros oficiais, congelados e
rastreaveis, sem aceitar regra financeira livre em requests.

---

# 3. Escopo

- consultar configuracao vigente por Tenant, Carteira, modalidade e
  `data_referencia`;
- retornar exatamente uma configuracao ou erro protegido;
- capturar snapshot contratual imutavel;
- preservar `capturado_em`, origem, versao e hash de parametros;
- impedir regra financeira livre e calculo financeiro em Configuracoes.

---

# 4. Fora do Escopo

- calcular valores de simulacao, saldo, quitacao ou memoria;
- chamar Motor para antecipar resultado financeiro;
- alterar snapshot ja capturado.

---

# 5. User Stories

- US-109 - Consultar Configuracao Vigente por Data de Referencia;
- US-110 - Capturar Snapshot de Configuracao Contratual;
- US-111 - Impedir Regra Financeira Livre em APIs;
- US-112 - Impedir Calculo Financeiro em Configuracoes.

---

# 6. Dependências

- EPIC-009 - Configuracoes Financeiras e Calendario Operacional;
- PRODUCT-009 - Administrar Configuracoes Financeiras;
- EPIC-003 - Comercial;
- EPIC-004 - Contratos de Credito;
- EPIC-005 - Motor Financeiro;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- consulta exige ou deriva `data_referencia` explicita;
- ausencia de configuracao aplicavel retorna `404` logico;
- ambiguidade de vigencia retorna `409`;
- snapshot exclui `consultada_em` e usa `capturado_em` como marco temporal da
  captura;
- APIs consumidoras usam referencia ou snapshot oficial;
- guardrail bloqueia juros, mora, multa, amortizacao, saldo, quitacao e memoria
  de calculo fora do Motor.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Consultar e Capturar Configuracao Financeira. |
