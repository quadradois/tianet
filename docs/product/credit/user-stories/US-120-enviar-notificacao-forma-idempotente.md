# US-120 - Enviar Notificacao de Forma Idempotente

**ID:** US-120

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** sistema de notificacao,
**quero** enviar uma solicitacao idempotente por porta de canal,
**para** evitar duplicidade durante retries e recuperacoes.

---

# 2. Critérios de Aceitação

- chave deriva de Tenant, origem, versao e finalidade;
- adapter usa chave aceita pelo provedor ou consulta de status equivalente;
- aceite preserva identificador externo quando fornecido;
- timeout sem prova de rejeicao produz `resultado_desconhecido`;
- resultado desconhecido bloqueia reenvio automatico ate conciliacao.

---

# 3. Regras de Negócio Relacionadas

- `aceita` significa aceite do provedor, nao entrega ou leitura;
- canal nao abre transacao de dominio nem altera Lembrete diretamente.

---

# 4. Dependências

- FEATURE-044 - Enviar Notificacoes Transacionais;
- US-118 - Selecionar Contato Autorizado para Notificacao;
- US-119 - Renderizar Template Transacional Versionado.

---

# 5. Observações Técnicas

O contrato candidato e `ResultadoEnvioNotificacaoV1` do Discovery EPIC-010.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Enviar Notificacao de Forma Idempotente. |
