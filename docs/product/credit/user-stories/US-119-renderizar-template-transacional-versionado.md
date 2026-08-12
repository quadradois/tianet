# US-119 - Renderizar Template Transacional Versionado

**ID:** US-119

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** responsavel por Comunicacao,
**quero** usar templates transacionais aprovados e versionados,
**para** controlar o conteudo enviado automaticamente.

---

# 2. Critérios de Aceitação

- a allowlist inicial contem `lembrete_operacional_v1` para e-mail, com
  `data_hora` e `canal_atendimento` como unicos parametros;
- template possui codigo, versao, canal, estado e parametros permitidos;
- somente template ativo e previamente aprovado pode ser renderizado;
- parametro fora da allowlist ou obrigatorio ausente bloqueia envio;
- alteracao de conteudo cria nova versao sem reescrever historico;
- template nao inclui segredo nem dado financeiro calculado pelo Scheduler.

---

# 3. Regras de Negócio Relacionadas

- templates sao exclusivamente operacionais e transacionais;
- ativacao registra autor, motivo e instante.

---

# 4. Dependências

- FEATURE-044 - Enviar Notificacoes Transacionais;
- ADR-009 - Notifications / Channels.

---

# 5. Observações Técnicas

A ADR-009 deve escolher armazenamento, provedor e sandbox antes do PLAN.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Renderizar Template Transacional Versionado. |
