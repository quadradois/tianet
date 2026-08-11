# US-110 - Capturar Snapshot de Configuracao Contratual

**ID:** US-110

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador de contratos,
**quero** capturar um snapshot imutavel da configuracao financeira,
**para** preservar os parametros usados na proposta ou contrato.

---

# 2. Critérios de Aceitação

- snapshot inclui campos materiais da configuracao vigente, exceto
  `consultada_em`;
- snapshot registra `capturado_em`, autor, motivo, origem, versao e hash de
  parametros;
- snapshot capturado nao muda quando a configuracao original evolui;
- Contratos carrega o snapshot no `ContratoLiberadoLogico` consumido pelo Motor.

---

# 3. Regras de Negócio Relacionadas

- configuracao vigente vira snapshot imutavel;
- Motor consome parametros congelados via contrato liberado, nao chamada direta
  de Configuracoes.

---

# 4. Dependências

- FEATURE-041 - Consultar e Capturar Configuracao Financeira;
- EPIC-004 - Contratos de Credito;
- EPIC-005 - Motor Financeiro.

---

# 5. Observações Técnicas

O contrato candidato e `SnapshotConfiguracaoContratualV1`, conforme discovery do
EPIC-009.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Capturar Snapshot de Configuracao Contratual. |
