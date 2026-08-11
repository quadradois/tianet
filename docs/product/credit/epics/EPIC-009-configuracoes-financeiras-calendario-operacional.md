# EPIC-009 - Configuracoes Financeiras e Calendario Operacional

**ID:** EPIC-009

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este Epic materializa o contexto de Configuracoes Financeiras para parametrizar
modalidades, taxas, politicas permitidas, vigencias e calendario financeiro sem
criar um Motor paralelo.

O EPIC-009 define parametros governados e versionados. O Motor Financeiro segue
como unica autoridade para juros, mora, multa, amortizacao, saldo, quitacao e
memoria de calculo.

---

# 2. Valor de Negócio

O Epic permite que propostas, contratos e operacoes financeiras usem parametros
oficiais, rastreaveis e congelaveis, reduzindo divergencia entre simulacao,
contrato liberado e processamento financeiro.

---

# 3. Escopo

Este Epic contempla:

- modalidades financeiras permitidas no MVP;
- parametros, taxas e politicas financeiras autorizadas;
- calendario financeiro operacional;
- vigencia, versao e estados de configuracao;
- configuracao por Tenant e, quando necessario, por Carteira;
- consulta de configuracao vigente por data de referencia;
- captura de snapshot imutavel para proposta e contrato;
- autoria, motivo e historico de alteracao;
- contratos de integracao com Comercial, Contratos e Motor;
- guardrail para impedir calculo financeiro dentro de Configuracoes.

---

# 4. Fora do Escopo

Este Epic nao contempla:

- calculo definitivo de juros, mora, multa, saldo, amortizacao, quitacao ou
  memoria de calculo;
- alteracao de proposta, contrato, emprestimo, parcela ou pagamento existente;
- retroatividade automatica sobre operacoes contratadas;
- scoring, decisao de credito, precificacao automatica ou IA;
- integracao com BACEN, PIX, boleto, banco ou terceiro;
- frontend.

---

# 5. Features

Este Epic e composto pelas seguintes Features:

- FEATURE-037 - Administrar Modalidades Financeiras;
- FEATURE-038 - Parametrizar Politicas Financeiras;
- FEATURE-039 - Administrar Calendario Financeiro Operacional;
- FEATURE-040 - Gerir Vigencias de Configuracoes Financeiras;
- FEATURE-041 - Consultar e Capturar Configuracao Financeira.

---

# 6. Dependências

Este Epic depende de:

- PRODUCT-009 - Administrar Configuracoes Financeiras;
- PRODUCT-001 - Administrar Plataforma;
- PRODUCT-003 - Administrar Comercial;
- PRODUCT-004 - Administrar Operacoes de Credito;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-006 - IAM;
- FOUNDATION-007 - Product Map;
- FOUNDATION-008 - Escopo do MVP;
- FOUNDATION-009 - Capability Map;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao;
- [Discovery/SDD do EPIC-009](../../../audits/discoveries/EPIC-009-configuracoes-financeiras-calendario-operacional-discovery.md).

---

# 7. Critérios de Aprovação

Este Epic sera considerado pronto para implementacao quando:

- Product, Features e User Stories estiverem consistentes com o Discovery/SDD;
- configuracoes nascerem como `rascunho` e so forem consumiveis quando
  aprovadas e `ativa` ou `programada` conforme vigencia;
- o sistema impedir conflitos de vigencia por Tenant, Carteira, modalidade e
  periodo;
- consulta de configuracao vigente exigir ou derivar `data_referencia`
  explicita;
- ausencia de configuracao aplicavel responder `404` logico;
- ambiguidade ou conflito de vigencia responder `409`;
- snapshot contratual preservar parametros materiais, origem, versao,
  `capturado_em` e hash de rastreabilidade;
- request livre nao puder definir regra financeira oficial;
- calendario definir periodo operacional sem calcular resultado financeiro;
- nenhuma funcionalidade em Configuracoes calcular juros, mora, multa, saldo,
  amortizacao, quitacao ou memoria de calculo.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Primeira versao formal do EPIC-009 - Configuracoes Financeiras e Calendario Operacional. |
