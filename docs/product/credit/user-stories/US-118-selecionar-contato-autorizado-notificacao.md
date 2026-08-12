# US-118 - Selecionar Contato Autorizado para Notificacao

**ID:** US-118

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** sistema de notificacao,
**quero** selecionar um contato autorizado,
**para** enviar somente e-mail transacional permitido.

---

# 2. Critérios de Aceitação

- primeiro incremento aceita apenas contato do tipo e-mail;
- contato deve estar ativo, autorizado e no mesmo Tenant/Carteira da origem;
- opt-out vigente bloqueia a solicitacao antes da renderizacao;
- ausencia ou ambiguidade de contato elegivel encerra sem envio;
- valor completo do contato nao entra em job, log ou resposta administrativa.

---

# 3. Regras de Negócio Relacionadas

- Cadastro permanece fonte de verdade do contato;
- Notification guarda referencia e representacao mascarada, nao copia Cadastro.

---

# 4. Dependências

- FEATURE-044 - Enviar Notificacoes Transacionais;
- EPIC-002 - Cadastro de Devedores.

---

# 5. Observações Técnicas

Politica de consentimento e opt-out e parte do contrato Product do EPIC-010.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Selecionar Contato Autorizado para Notificacao. |
