# FEATURE-044 - Enviar Notificacoes Transacionais

**ID:** FEATURE-044

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Enviar e-mail transacional de Lembrete por porta de canal, com contato
autorizado, template versionado e resultado tipado.

---

# 2. Valor de Negócio

Automatiza contatos operacionais previsiveis sem criar disparo arbitrario ou
perder controle sobre consentimento e autoria sistemica.

---

# 3. Escopo

- resolver contato de e-mail ativo e autorizado;
- bloquear opt-out antes de renderizar ou enviar;
- renderizar template de allowlist com parametros minimos;
- enviar com identidade idempotente no provedor;
- distinguir aceite, falhas e resultado desconhecido;
- registrar Comunicacao idempotente apos aceite.

A allowlist inicial contem apenas `lembrete_operacional_v1`, parametrizado por
`data_hora` e `canal_atendimento`.

---

# 4. Fora do Escopo

- WhatsApp, SMS, push, campanhas ou mensagens livres;
- declarar leitura ou entrega final sem receipt;
- armazenar corpo integral, contato em claro ou segredo em logs.

---

# 5. User Stories

- US-118 - Selecionar Contato Autorizado para Notificacao;
- US-119 - Renderizar Template Transacional Versionado;
- US-120 - Enviar Notificacao de Forma Idempotente;
- US-121 - Registrar Comunicacao Apos Aceite do Provedor.

---

# 6. Dependências

- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes;
- PRODUCT-007 - Administrar Comunicacao;
- EPIC-002 - Cadastro de Devedores;
- ADR-009 - Notifications / Channels.

---

# 7. Critérios de Aprovação

- somente e-mail autorizado e sem opt-out e elegivel;
- template inativo ou parametro fora da allowlist bloqueia envio;
- timeout sem prova externa vira resultado desconhecido;
- aceite externo cria no maximo um registro de Comunicacao.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da Feature Enviar Notificacoes Transacionais. |
