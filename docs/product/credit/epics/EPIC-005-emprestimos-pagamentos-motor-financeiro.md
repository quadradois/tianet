# EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro

**ID:** EPIC-005

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Epic implementa o Motor Financeiro como Core Domain operacional da
plataforma.

Seu objetivo e transformar contratos liberados logicamente em Emprestimos,
gerar Parcelas, registrar Pagamentos, calcular saldo, calcular quitacao e
produzir memoria de calculo auditavel.

---

# 2. Valor de Negócio

O EPIC-005 concentra o diferencial da plataforma: calculo financeiro unico,
auditavel, reproduzivel e protegido contra duplicacao em outros contextos.

---

# 3. Escopo

Este Epic contempla:

- criacao de Emprestimo a partir de contrato liberado;
- geracao de plano de Parcelas;
- registro e processamento de Pagamentos;
- consulta de saldo devedor;
- memoria de calculo;
- calculo de valor para quitacao;
- quitacao e encerramento financeiro;
- renegociacao inicial rastreavel;
- eventos financeiros;
- API protegida por IAM/RBAC;
- contratos OpenAPI;
- guardrails de precisao e exclusividade do Motor.

---

# 4. Fora do Escopo

Este Epic nao contempla:

- cadastro de Devedor;
- simulacao e proposta comercial;
- formalizacao, assinatura ou liberacao de contrato;
- cobranca ativa;
- agenda;
- comunicacao;
- relatorios gerenciais;
- conciliacao bancaria externa;
- PIX, boleto ou gateway de pagamento;
- calculo tributario/regulatorio oficial sem fonte normativa.

---

# 5. Features

Este Epic e composto pelas seguintes Features:

- FEATURE-023 - Criar Emprestimo a partir de Contrato Liberado;
- FEATURE-024 - Gerar Plano de Parcelas;
- FEATURE-025 - Registrar Pagamento;
- FEATURE-026 - Consultar Saldo e Memoria de Calculo;
- FEATURE-027 - Quitar e Renegociar Operacao.

---

# 6. Dependências

Este Epic depende de:

- PRODUCT-004 - Administrar Operacoes de Credito;
- EPIC-004 - Contratos de Credito;
- EPIC-006 - IAM;
- EPIC-002 - Cadastro de Devedores;
- FOUNDATION-004 - Core Domain;
- FOUNDATION-005 - Inventario do Dominio;
- FOUNDATION-009 - Capability Map;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao;
- DOMAIN-004 - Entity Emprestimo;
- DOMAIN-005 - Entity Parcela;
- DOMAIN-006 - Entity Pagamento;
- DOMAIN-007 - VO Dinheiro;
- DOMAIN-010 - Service Motor Financeiro.

---

# 7. Critérios de Aprovação

Este Epic sera considerado concluido quando:

- Emprestimo nascer somente de `ContratoLiberadoLogico`;
- contrato inexistente, nao liberado ou cross-tenant responder 404 logico;
- contrato ja consumido nao gerar Emprestimo duplicado;
- Parcelas forem geradas com periodos financeiros rastreaveis;
- Pagamentos forem processados pelo Motor antes de alterar estado financeiro;
- saldo, quitacao e memoria de calculo forem retornados pelo Motor;
- `float` estiver proibido em calculos financeiros;
- endpoints sem token responderem 401;
- Principal sem permissao responder 403;
- recursos cross-tenant responderem 404;
- transicoes financeiras invalidas responderem 409;
- entrada invalida responder 400;
- OpenAPI documentar rotas protegidas e erros;
- nenhum contexto fora do Motor executar calculo financeiro definitivo.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao oficial do EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro. |
