# US-123 - Conciliar Resultado Externo Desconhecido

**ID:** US-123

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** administrador operacional autorizado,
**quero** conciliar um resultado externo desconhecido,
**para** resolver a incerteza sem duplicar a notificacao.

---

# 2. Critérios de Aceitação

- notificacao desconhecida permanece bloqueada para reenvio automatico;
- conciliacao exige evidencia do provedor, motivo, autor e instante;
- aceite comprovado reconcilia estados sem nova chamada externa;
- rejeicao comprovada permite nova tentativa conforme politica;
- falta de evidencia mantem o bloqueio e o historico original.

---

# 3. Regras de Negócio Relacionadas

- ausencia de confirmacao local nunca autoriza reenvio;
- conciliacao nao reescreve tentativas anteriores.

---

# 4. Dependências

- FEATURE-045 - Operar e Reconciliar Automacao;
- US-120 - Enviar Notificacao de Forma Idempotente;
- US-122 - Administrar Job e Notificacao com RBAC.

---

# 5. Observações Técnicas

A antiga acao HTTP de `enviar` Lembrete fica restrita a este fluxo de
conciliacao auditada e nao pode chamar o provedor.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Conciliar Resultado Externo Desconhecido. |
