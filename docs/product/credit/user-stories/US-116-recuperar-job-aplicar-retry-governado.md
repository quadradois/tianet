# US-116 - Recuperar Job e Aplicar Retry Governado

**ID:** US-116

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operacao da plataforma,
**quero** recuperar jobs abandonados e repetir apenas falhas elegiveis,
**para** manter a automacao confiavel sem duplicar efeitos externos.

---

# 2. Critérios de Aceitação

- lease expirado permite nova reivindicacao e invalida token antigo;
- falha temporaria respeita limite e backoff definidos na ADR-007;
- falha permanente nao repete a mesma solicitacao;
- resultado externo desconhecido bloqueia reenvio automatico;
- recuperacao consulta idempotencia e, quando disponivel, status do provedor.

---

# 3. Regras de Negócio Relacionadas

- ausencia de confirmacao local nao prova ausencia de aceite externo;
- nova solicitacao apos falha permanente exige correcao e nova versao.

---

# 4. Dependências

- FEATURE-043 - Processar Jobs Duraveis;
- US-115 - Reivindicar e Executar Job com Lease.

---

# 5. Observações Técnicas

Tentativas, backoff e retencao devem estar fechados na ADR-007 antes do PLAN.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Recuperar Job e Aplicar Retry Governado. |
