# PRODUCT-008 - Capability Administrar Relatorios

**ID:** PRODUCT-008

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Objetivo

Esta Capability disponibiliza consultas e indicadores operacionais basicos no
Bounded Context Relatorios.

---

# 2. Valor de Negocio

Administrar Relatorios permite acompanhar carteira, vencimentos,
inadimplencia, pagamentos, encerramentos e fluxo de caixa sem controles
paralelos.

---

# 3. Responsabilidades

- consultar resumo da Carteira;
- consultar vencimentos e inadimplencia;
- consultar pagamentos e operacoes encerradas;
- consultar fluxo previsto e realizado;
- consolidar somente fatos oficiais dos contextos de origem;
- exibir Pagamentos brutos, estornos e liquido separadamente;
- distinguir quitacao, renegociacao, encerramento administrativo e cancelamento;
- aplicar IAM/RBAC e isolamento por Tenant/Carteira.

---

# 4. Contexto

Esta Capability pertence ao Bounded Context Relatorios. No EPIC-007, ela
consome Motor, Cobranca, Agenda e Comunicacao por contratos conformistas/read
models, sem comandar transicoes nos contextos de origem.

---

# 5. Limites

- nao calcula juros, mora, amortizacao, saldo ou quitacao;
- nao redefine inadimplencia;
- nao altera estado de negocio;
- nao inclui BI avancado, analytics preditivo ou exportacao CSV/PDF no MVP.

---

# 6. Dependencias

- FOUNDATION-007 - Product Map;
- FOUNDATION-009 - Capability Map;
- EPIC-005 - Motor Financeiro;
- EPIC-004 - Contratos de Credito;
- EPIC-006 - IAM;
- ADR-004 - Autenticacao e Autorizacao.

---

# 7. Epicos

- EPIC-007 - Operacao Diaria.

---

# 8. Criterios de Aprovacao

- consultas expoem periodo, Carteira e data de referencia;
- totais sao rastreaveis ate fatos oficiais;
- valores financeiros vem do Motor ou de read model reconstruivel;
- fluxo realizado soma `valor_efeito_realizado_assinado` fornecido pelo Motor;
- inadimplencia agrupa `SituacaoParcelaNaDataV1` sem regra temporal local;
- agregacoes `count`, `sum` e `group` sobre fatos oficiais sao permitidas;
- recalcular juros, mora, multa, amortizacao, saldo, quitacao, arredondamento ou
  memoria de calculo fora do Motor e proibido;
- nenhuma consulta altera estado de negocio;
- Tenant/Carteira e permissoes limitam todos os resultados.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Fronteira anti-Motor explicita para formulas financeiras adicionada. |
| 1.1.0 | 2026-08-10 | Estornos, encerramentos, situacao temporal e agregacoes permitidas formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao da Capability Administrar Relatorios para o EPIC-007. |
