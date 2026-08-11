# FEATURE-030 - Registrar Comunicacao Manual

**ID:** FEATURE-030

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Objetivo

Registrar comunicacoes realizadas manualmente com o devedor e disponibilizar
um historico operacional rastreavel.

---

# 2. Valor de Negócio

Evita perda de contexto entre operadores e demonstra quando, como e com qual
resultado o devedor foi contatado.

---

# 3. Escopo

- registrar comunicacao manual;
- informar canal, data, responsavel e resultado do contato;
- referenciar Devedor e, quando aplicavel, Emprestimo ou Caso de Cobranca da
  mesma cadeia canonica;
- consultar historico cronologico de comunicacoes;
- proteger dados de contato por Tenant/Carteira e RBAC.

---

# 4. Fora do Escopo

- enviar WhatsApp, SMS, e-mail ou push;
- integrar provedores de mensageria;
- gerenciar templates ou filas de notificacao;
- automatizar campanhas.

---

# 5. User Stories

- US-082 - Registrar Comunicacao Manual;
- US-083 - Consultar Historico de Comunicacao.

---

# 6. Dependências

- EPIC-007 - Operacao Diaria;
- PRODUCT-007 - Administrar Comunicacao;
- EPIC-002 - Cadastro de Devedores;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- PRODUCT-005 - Administrar Cobrancas;
- FEATURE-028 - Gerir Cobranca Manual, por contrato/ACL;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- comunicacao registra canal, data, responsavel e resultado;
- historico e ordenado e filtrado pelo escopo autorizado;
- registro nao afirma entrega por provedor externo;
- referencias a Cobranca sao opcionais e consumidas por contrato/ACL;
- Emprestimo ou Cobranca opcional pertence ao Devedor, Tenant e Carteira;
- formato, filtro, data ou identificador malformado retorna `400`;
- cadeia visivel incompatível retorna `409`; recurso inexistente ou cross-tenant
  retorna `404` logico, conforme DA-719;
- dados de contato nao vazam entre Tenants/Carteiras;
- escrita idempotente nao cria comunicacao duplicada.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP 400/404/409 de DA-719 propagado para Comunicacao. |
| 1.1.0 | 2026-08-10 | Integridade da cadeia referencial e erros protegidos formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao da Feature Registrar Comunicacao Manual. |
