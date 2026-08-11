# FEATURE-031 - Consultar Relatorios Operacionais

**ID:** FEATURE-031

**Versao:** 1.2.0

**Status:** Proposto

---

# 1. Objetivo

Disponibilizar consultas operacionais basicas da carteira a partir de fatos e
valores oficiais dos contextos de origem.

---

# 2. Valor de Negócio

Permite que gestores acompanhem carteira, vencimentos, inadimplencia,
pagamentos, encerramentos e fluxo de caixa sem montar controles paralelos.

---

# 3. Escopo

- consultar resumo da carteira;
- consultar vencimentos e inadimplencia por periodo;
- consultar pagamentos e operacoes encerradas;
- consultar fluxo previsto e realizado;
- filtrar por periodo, Carteira e escopo autorizado;
- impedir qualquer recalculo financeiro fora do Motor.

---

# 4. Fora do Escopo

- BI avancado, data lake ou analytics preditivo;
- exportacao CSV/PDF;
- dashboards frontend;
- definicao paralela de juros, saldo ou inadimplencia;
- comandos que alterem estado de negocio.

---

# 5. User Stories

- US-084 - Consultar Resumo da Carteira;
- US-085 - Consultar Vencimentos e Inadimplencia;
- US-086 - Consultar Pagamentos e Operacoes Encerradas;
- US-087 - Consultar Fluxo Previsto e Realizado;
- US-088 - Impedir Calculo Financeiro fora do Motor na Operacao Diaria.

---

# 6. Dependências

- EPIC-007 - Operacao Diaria;
- PRODUCT-008 - Administrar Relatorios;
- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-004 - Contratos de Credito;
- EPIC-002 - Cadastro de Devedores;
- EPIC-006 - IAM.

---

# 7. Critérios de Aprovação

- consultas respeitam periodo, Tenant, Carteira e permissao do Principal;
- valores financeiros sao consumidos do Motor ou de projecoes de seus fatos;
- vencimento e inadimplencia agrupam `SituacaoParcelaNaDataV1`;
- Pagamentos brutos, estornos e liquido sao exibidos separadamente;
- fluxo realizado soma `valor_efeito_realizado_assinado` fornecido pelo Motor;
- encerramentos preservam tipo e contexto de origem, incluindo Contratos;
- `count`, `sum` e `group` sobre campos oficiais sao agregacoes permitidas e
  reproduziveis;
- dados de Cobranca, Agenda e Comunicacao entram por contratos opcionais;
- consultas nao alteram estado de negocio;
- guardrails permitem agregacoes operacionais e falham diante de juros, mora,
  multa, amortizacao, saldo, quitacao, arredondamento ou memoria de calculo;
- formato, filtro, periodo, data ou identificador malformado retorna `400`;
- recurso inexistente ou cross-tenant retorna `404` logico; `409` nao se aplica
  enquanto a consulta nao combinar referencias independentes nem transicionar
  estado, conforme DA-719;
- OpenAPI documenta filtros, paginacao e erros protegidos.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-10 | Contrato HTTP aplicavel de DA-719 propagado para Relatorios. |
| 1.1.0 | 2026-08-10 | Contratos de situacao, estorno, encerramento e guardrail de agregacao formalizados. |
| 1.0.0 | 2026-08-10 | Primeira versao da Feature Consultar Relatorios Operacionais. |
