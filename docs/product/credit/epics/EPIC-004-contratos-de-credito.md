# EPIC-004 - Contratos de Credito

**ID:** EPIC-004

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Epic e responsavel por formalizar Contratos de Credito a partir de
propostas comerciais aprovadas.

Seu objetivo e criar a ponte rastreavel entre Comercial e Motor Financeiro,
registrando acordo formal, assinatura/formalizacao e liberacao logica para o
EPIC-005, sem criar Emprestimo, Parcela, Pagamento ou calculo definitivo.

---

# 2. Valor de Negócio

Contratos de Credito dao seguranca operacional ao credor: uma proposta aprovada
passa a ter um registro formal, imutavel nos pontos essenciais e auditavel antes
de qualquer execucao financeira.

---

# 3. Escopo

Este Epic contempla:

- criacao de contrato a partir de proposta aprovada;
- validacao de Tenant, Carteira, Devedor e proposta aprovada;
- preservacao de snapshot contratual;
- consulta de contrato por ID;
- listagem de contratos;
- registro de assinatura/formalizacao;
- consulta de historico contratual;
- liberacao logica de contrato para Motor Financeiro futuro;
- cancelamento de contrato ainda nao liberado;
- encerramento administrativo sem alterar operacao financeira;
- auditoria de escritas e transicoes;
- autorizacao por IAM/RBAC e isolamento por Tenant/Carteira.

---

# 4. Fora do Escopo

Este Epic nao contempla:

- criacao de Emprestimo, Parcela ou Pagamento;
- calculo de juros, amortizacao, saldo, atraso, quitacao ou memoria de calculo;
- execucao do Motor Financeiro;
- desembolso financeiro, banco, PIX ou boleto;
- assinatura digital externa;
- renegociacao de operacao em execucao;
- cobranca, agenda, comunicacao ou relatorios.

---

# 5. Features

Este Epic e composto pelas seguintes Features:

- FEATURE-018 - Formalizar Contrato de Credito;
- FEATURE-019 - Consultar Contratos;
- FEATURE-020 - Registrar Assinatura Contratual;
- FEATURE-021 - Liberar Contrato para Motor Financeiro;
- FEATURE-022 - Cancelar ou Encerrar Contrato.

---

# 6. Dependências

Este Epic depende de:

- PRODUCT-004 - Capability Administrar Operacoes de Credito;
- PRODUCT-003 - Capability Administrar Comercial;
- EPIC-003 - Comercial / Propostas / Simulacao;
- EPIC-006 - IAM;
- EPIC-002 - Cadastro de Devedores;
- FOUNDATION-008 - Escopo do MVP;
- FOUNDATION-009 - Capability Map;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao;
- DOMAIN-001 - Aggregate Carteira;
- DOMAIN-003 - Entity Contrato de Credito;
- DOMAIN-020 - Aggregate Devedor.

---

# 7. Critérios de Aprovação

Este Epic sera considerado concluido quando:

- todas as Features estiverem implementadas;
- contrato nascer somente a partir de proposta aprovada;
- proposta nao aprovada, inexistente ou cross-tenant responder conforme contrato;
- contrato puder ser formalizado/assinado e liberado logicamente para Motor;
- transicoes invalidas responderem `409`;
- recursos de outro Tenant/Carteira responderem `404`;
- endpoints protegidos responderem `401/403`;
- entrada invalida responder `400`;
- escritas e transicoes estiverem auditadas;
- Contratos nao executar nenhum calculo financeiro definitivo.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao oficial do EPIC-004 - Contratos de Credito. |
