# PRODUCT-007 - Capability Administrar Comunicacao

**ID:** PRODUCT-007

**Versao:** 1.1.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability registra e consulta comunicacoes realizadas manualmente com o
devedor no Bounded Context Comunicacao.

---

# 2. Valor de Negocio

Administrar Comunicacao preserva o contexto dos contatos entre operadores sem
introduzir provedores externos ou automacao no MVP.

---

# 3. Responsabilidades

- registrar canal, data, responsavel, resumo e resultado do contato;
- consultar historico cronologico de comunicacoes;
- referenciar Devedor e opcionalmente Emprestimo ou Cobranca da mesma cadeia;
- proteger dados por IAM/RBAC e Tenant/Carteira;
- auditar escritas conforme ADR-002.

---

# 4. Contexto

Esta Capability pertence ao Bounded Context Comunicacao. No EPIC-007, ela
integra Cobranca e Cadastro por contratos conformistas/ACL, sem depender de seus
modelos internos.

---

# 5. Limites

- nao envia WhatsApp, SMS, e-mail ou push;
- nao integra provedores de mensageria;
- nao confirma entrega externa;
- nao altera dados cadastrais ou financeiros.

---

# 6. Dependencias

- FOUNDATION-007 - Product Map;
- FOUNDATION-009 - Capability Map;
- EPIC-002 - Cadastro de Devedores;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- PRODUCT-005 - Administrar Cobrancas, por contrato/ACL;
- EPIC-006 - IAM;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao.

---

# 7. Epicos

- EPIC-007 - Operacao Diaria.

---

# 8. Criterios de Aprovacao

- comunicacao manual preserva autoria, canal, data e resultado;
- historico e paginado e respeita o escopo autorizado;
- escrita idempotente nao cria duplicidade;
- referencias opcionais pertencem ao Devedor, Tenant e Carteira canonicos;
- nenhuma integracao externa e exigida no MVP;
- Tenant/Carteira e permissoes limitam todas as operacoes.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-10 | Dependencias e validacao da cadeia referencial formalizadas. |
| 1.0.0 | 2026-08-10 | Primeira versao da Capability Administrar Comunicacao para o EPIC-007. |
