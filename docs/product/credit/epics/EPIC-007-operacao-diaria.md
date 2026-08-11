# EPIC-007 - Operacao Diaria

**ID:** EPIC-007

**Versao:** 1.5.0

**Status:** Proposto

---

# 1. Objetivo

Este Epic entrega a operacao diaria do credito por meio de Cobranca manual,
Agenda operacional, Comunicacao manual e Relatorios basicos.

Seu objetivo e transformar fatos oficiais de Cadastro e do Motor Financeiro em
rotinas rastreaveis de acompanhamento, sem recalcular ou alterar a verdade
financeira da operacao.

O contexto primario deste Epic e Cobranca, atendido por PRODUCT-005. Agenda,
Comunicacao e Relatorios sao contextos secundarios coordenados por
PRODUCT-006, PRODUCT-007 e PRODUCT-008, integrados por contratos
conformistas/ACL conforme a excecao de FOUNDATION-009 secao 10.2.

---

# 2. Valor de Negócio

O EPIC-007 fecha o ciclo operacional do MVP: a carteira deixa de ser apenas
registrada e calculada e passa a ser acompanhada diariamente por operadores e
gestores com uma visao consistente de vencimentos, contatos, promessas e
indicadores.

---

# 3. Escopo

Este Epic contempla:

- consultar fila de cobranca manual;
- registrar acao de cobranca e promessa de pagamento;
- acompanhar cumprimento ou descumprimento de promessas;
- consultar vencimentos financeiros oficiais e itens de Agenda por periodo;
- criar, reagendar, concluir e cancelar compromissos e lembretes;
- registrar comunicacao manual e consultar seu historico;
- consultar resumo de carteira, vencimentos, inadimplencia, pagamentos,
  operacoes encerradas e fluxo previsto/realizado;
- proteger operacoes por IAM/RBAC;
- preservar isolamento por Tenant/Carteira e trilha de auditoria;
- documentar contratos OpenAPI e erros HTTP;
- impedir calculo financeiro definitivo fora do Motor.

---

# 4. Fora do Escopo

Este Epic nao contempla:

- calculo de juros, mora, multa, amortizacao, saldo ou quitacao;
- alteracao de Contrato, Emprestimo, Parcela ou condicao financeira;
- renegociacao financeira fora do Motor;
- cobranca automatica ou workflow temporizado complexo;
- envio automatico ou integracao com provedor de mensagens;
- Scheduler, Notification ou Event Bus como dependencia obrigatoria;
- banco, PIX, boleto, conciliacao, protesto, negativacao ou cobranca juridica;
- BI avancado, data lake, machine learning ou exportacao CSV/PDF;
- frontend.

---

# 5. Features

Este Epic e composto pelas seguintes Features:

- FEATURE-028 - Gerir Cobranca Manual;
- FEATURE-029 - Administrar Agenda Operacional;
- FEATURE-030 - Registrar Comunicacao Manual;
- FEATURE-031 - Consultar Relatorios Operacionais.

---

# 6. Dependências

Este Epic depende de:

- PRODUCT-005 - Administrar Cobrancas (contexto primario);
- PRODUCT-006 - Administrar Agenda;
- PRODUCT-007 - Administrar Comunicacao;
- PRODUCT-008 - Administrar Relatorios;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-004 - Contratos de Credito, para encerramento administrativo;
- EPIC-006 - IAM;
- EPIC-002 - Cadastro de Devedores;
- FOUNDATION-008 - Escopo do MVP;
- FOUNDATION-009 - Capability Map;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao;
- DOMAIN-011 - Evento Emprestimo Criado;
- DOMAIN-012 - Evento Pagamento Registrado;
- DOMAIN-013 - Evento Emprestimo Quitado;
- [Discovery/SDD de Operacao Diaria](../../../audits/discoveries/EPIC-007-operacao-diaria-discovery.md).

---

# 7. Critérios de Aprovação

Este Epic sera considerado concluido quando:

- todas as Features e User Stories candidatas estiverem implementadas e
  recertificadas;
- fila de cobranca e Agenda consumirem `SituacaoParcelaNaDataV1` do Motor;
- vencimento e inadimplencia serem materializados pelo Motor para uma
  `data_referencia`, sem regra paralela nem dependencia de Scheduler;
- cada Feature permanecer sob sua Capability e seu Bounded Context;
- integracoes entre contextos usarem contratos conformistas/ACL;
- promessa de pagamento permanecer um fato operacional sem efeito financeiro;
- promessa somente ficar cumprida com Pagamentos oficiais nao estornados do
  mesmo Tenant, Carteira e Emprestimo, dentro da data e do valor declarados;
- valores apropriados a promessas nao serem reutilizados alem do valor elegivel
  de cada Pagamento;
- estorno identificado por `pagamento_id` e `estorno_id` reavaliar promessas e
  emitir `PromessaPagamentoCumprimentoInvalidado` apenas quando uma promessa
  cumprida perder esse estado;
- estados de promessa obedecerem a tabela normativa DA-718;
- apropriacao de Pagamento a promessa exigir `ApropriarPagamentoPromessa` e as
  transicoes sistemicas usarem `ReavaliarPromessaPagamento` sincronicamente apos
  apropriacao, estorno ou leitura vencida, sem descoberta automatica nem
  Scheduler obrigatorio;
- referencias opcionais formarem uma cadeia valida no mesmo Tenant, Carteira e
  Emprestimo, com Devedor derivado quando aplicavel;
- comunicacoes forem registradas manualmente com autoria e contexto;
- relatorios apresentarem dados derivados de fontes oficiais;
- pagamentos exibirem bruto, estornos e liquido separadamente, e o fluxo
  realizado somar apenas efeitos assinados fornecidos pelo Motor;
- encerramentos administrativos serem consumidos de Contratos e distinguidos de
  quitacao, renegociacao e cancelamento;
- endpoints sem token responderem `401`;
- Principal sem permissao responder `403`;
- recurso de outro Tenant/Carteira responder `404` logico;
- payload, formato, enum, data ou identificador malformado responder `400`;
- transicao proibida, referencias visiveis de cadeias diferentes, chave
  idempotente com payload divergente ou versao obsoleta responder `409`;
- replay da mesma chave idempotente e payload devolver o resultado original;
- escritas idempotentes nao criarem registros duplicados;
- OpenAPI documentar rotas protegidas e respostas de erro;
- agregacoes operacionais sobre fatos oficiais serem permitidas sem autorizar
  formula financeira definitiva fora do Motor.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.5.0 | 2026-08-10 | Reavaliacao deterministica de promessas sem Scheduler e cobertura HTTP por User Story formalizadas. |
| 1.4.0 | 2026-08-10 | Contratos upstream, estados de promessa, Agenda financeira, erros protegidos e guardrail de agregacao alinhados. |
| 1.3.0 | 2026-08-10 | Apropriacao exclusiva e reavaliacao de promessas apos estorno formalizadas. |
| 1.2.0 | 2026-08-10 | Elegibilidade do Pagamento para cumprimento de promessa formalizada apos recertificacao. |
| 1.1.0 | 2026-08-10 | Contexto primario Cobranca, Capabilities contextuais, rastreabilidade do discovery e semantica de promessa corrigidos apos revisao. |
| 1.0.0 | 2026-08-10 | Primeira versao formal do EPIC-007 - Operacao Diaria. |
