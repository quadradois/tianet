# PRODUCT-007 - Capability Administrar Comunicacao

**ID:** PRODUCT-007

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability registra e consulta comunicacoes manuais ou transacionais
aceitas por provedor com o devedor no Bounded Context Comunicacao.

---

# 2. Valor de Negocio

Administrar Comunicacao preserva o contexto dos contatos entre operadores e
dos envios transacionais governados, sem misturar fila tecnica com historico.

---

# 3. Responsabilidades

- registrar canal, data, responsavel, resumo e resultado do contato;
- consultar historico cronologico de comunicacoes;
- registrar de forma idempotente o aceite de notificacoes transacionais;
- governar consentimento, opt-out e templates operacionais versionados;
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

- nao envia diretamente: usa Notification por porta de canal;
- nao afirma entrega final quando o provedor confirma apenas aceite;
- nao executa campanhas, marketing em massa ou jornada comercial;
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
- EPIC-010 - Automacao Operacional, Scheduler e Notificacoes.

---

# 8. Criterios de Aprovacao

- comunicacao manual preserva autoria, canal, data e resultado;
- historico e paginado e respeita o escopo autorizado;
- escrita idempotente nao cria duplicidade;
- referencias opcionais pertencem ao Devedor, Tenant e Carteira canonicos;
- envio transacional exige contato autorizado, consentimento vigente e ausencia
  de opt-out para o canal;
- aceite do provedor cria um unico registro de Comunicacao e nao equivale a
  leitura ou entrega final;
- Tenant/Carteira e permissoes limitam todas as operacoes.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-11 | Notificacao transacional por componente tecnico e governanca de consentimento incorporadas pelo EPIC-010. |
| 1.1.0 | 2026-08-10 | Dependencias e validacao da cadeia referencial formalizadas. |
| 1.0.0 | 2026-08-10 | Primeira versao da Capability Administrar Comunicacao para o EPIC-007. |
