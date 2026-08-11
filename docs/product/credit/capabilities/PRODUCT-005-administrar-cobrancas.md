# PRODUCT-005 - Capability Administrar Cobrancas

**ID:** PRODUCT-005

**Versao:** 1.5.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability administra o acompanhamento manual de cobrancas da carteira de
credito no MVP.

Ela transforma fatos oficiais do Motor Financeiro em fila de trabalho, acoes de
cobranca e promessas de pagamento, sem assumir responsabilidade por calculo
financeiro definitivo.

---

# 2. Valor de Negocio

Administrar Cobrancas permite que operadores priorizem vencimentos e registrem
o acompanhamento de recuperacao de credito com rastreabilidade e isolamento por
Tenant/Carteira.

---

# 3. Responsabilidades

Esta Capability e responsavel por:

- organizar a fila de cobranca manual;
- registrar acoes de cobranca;
- registrar e acompanhar promessas de pagamento;
- receber Emprestimo como referencia canonica, derivar Devedor e validar Parcela;
- auditar escritas conforme ADR-002;
- aplicar IAM/RBAC e isolamento por Tenant/Carteira;
- consumir valores e estados financeiros oficiais do Motor.

---

# 4. Contexto Primario

Esta Capability pertence ao Bounded Context Cobranca, contexto primario do
EPIC-007. Agenda, Comunicacao e Relatorios participam do mesmo ciclo por
Capabilities proprias e contratos conformistas/ACL, sem compartilhar modelo de
dominio com Cobranca.

---

# 5. Limites

Esta Capability nao e responsavel por:

- calcular juros, multa, mora, amortizacao, saldo ou quitacao;
- alterar Contrato, Emprestimo ou plano de Parcelas;
- executar renegociacao financeira fora do Motor;
- administrar Agenda ou historico de Comunicacao;
- produzir Relatorios;
- enviar WhatsApp, SMS, e-mail ou push automaticamente;
- depender de Scheduler, Notification ou Event Bus no MVP;
- integrar bancos, PIX, boleto, conciliacao, protesto ou negativacao;
- produzir BI avancado, analytics preditivo ou exportacao CSV/PDF;
- implementar frontend operacional.

---

# 6. Dependencias

Esta Capability depende de:

- FOUNDATION-007 - Product Map;
- FOUNDATION-008 - Escopo do MVP;
- FOUNDATION-009 - Capability Map;
- ROADMAP-ALIGNMENT - roadmap oficial de transicao;
- AMP-001 - Architecture Master Plan;
- PRODUCT-002 - Administrar Cadastro;
- PRODUCT-004 - Administrar Operacoes de Credito;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-006 - IAM;
- ADR-002 - Auditoria Independente da Transacao;
- ADR-004 - Autenticacao e Autorizacao.

---

# 7. Epicos

Esta Capability sera atendida inicialmente por:

- EPIC-007 - Operacao Diaria.

---

# 8. Criterios de Aprovacao

Esta Capability sera considerada concluida no MVP quando:

- operadores autorizados puderem consultar a fila e registrar acoes manuais;
- fila consumir `SituacaoParcelaNaDataV1` sem recalcular vencimento ou
  inadimplencia;
- promessas preservarem autoria, data, valor declarado e referencias;
- cumprimento de promessa exigir Pagamentos oficiais nao estornados do mesmo
  Tenant, Carteira e Emprestimo, dentro da data e do valor declarados;
- apropriacoes de Pagamento entre promessas serem rastreaveis e nao excederem o
  valor elegivel recebido;
- estornos invalidarem apropriacoes e reavaliarem as promessas afetadas sem
  alterar fatos financeiros;
- `PromessaPagamentoCumprimentoInvalidado` ser emitido somente quando promessa
  cumprida perder esse estado;
- estados de promessa seguirem a tabela normativa DA-718;
- apropriacao ocorrer por `ApropriarPagamentoPromessa` e a reavaliacao usar
  `ReavaliarPromessaPagamento` depois de apropriacao, estorno ou leitura vencida,
  com `data_referencia` e sem descoberta automatica ou Scheduler obrigatorio;
- todas as operacoes respeitarem Tenant e Carteira do Principal autenticado;
- escritas forem auditadas conforme ADR-002;
- nenhum modulo de Cobranca executar calculo financeiro definitivo.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.5.0 | 2026-08-10 | Gatilhos sincronicos e deterministas de reavaliacao de promessa formalizados. |
| 1.4.0 | 2026-08-10 | Estados de promessa, invalidacao condicional e referencias canonicas alinhados. |
| 1.3.0 | 2026-08-10 | Apropriacao exclusiva e efeito de estorno sobre promessas formalizados. |
| 1.2.0 | 2026-08-10 | Elegibilidade do Pagamento para cumprimento de promessa formalizada. |
| 1.1.0 | 2026-08-10 | Capability corrigida para representar exclusivamente o contexto Cobranca, primario do EPIC-007. |
| 1.0.0 | 2026-08-10 | Primeira versao da Capability coordenadora do EPIC-007 - Operacao Diaria. |
