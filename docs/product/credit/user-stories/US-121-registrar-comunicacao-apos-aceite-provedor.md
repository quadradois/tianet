# US-121 - Registrar Comunicacao Apos Aceite do Provedor

**ID:** US-121

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. História

**Como** operador autorizado,
**quero** consultar o contato automatico aceito no historico de Comunicacao,
**para** compreender o acompanhamento realizado.

---

# 2. Critérios de Aceitação

- Comunicacao e registrada somente apos aceite confirmado pelo canal;
- registro e idempotente por `notification_id` e nao duplica em replay;
- registro distingue autoria sistemica de autoria humana;
- historico informa canal, template, instante e resultado sem contato em claro;
- falha ou resultado desconhecido nao marca Lembrete como `enviado`.

---

# 3. Regras de Negócio Relacionadas

- Notification guarda tentativa tecnica; Comunicacao guarda fato de negocio;
- aceite nao afirma entrega final ou leitura.

---

# 4. Dependências

- FEATURE-044 - Enviar Notificacoes Transacionais;
- PRODUCT-007 - Administrar Comunicacao;
- US-120 - Enviar Notificacao de Forma Idempotente.

---

# 5. Observações Técnicas

O caso de uso coordena a transicao oficial do Lembrete e o registro de
Comunicacao apos o resultado tipado do canal.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-08-11 | Primeira versao da User Story Registrar Comunicacao Apos Aceite do Provedor. |
