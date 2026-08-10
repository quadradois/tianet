# EPIC-005 - Discovery/SDD de Emprestimos, Pagamentos e Motor Financeiro

**ID:** EPIC-005

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Objetivo

Este discovery prepara o ciclo do EPIC-005 - Emprestimos, Pagamentos e Motor
Financeiro.

O objetivo e definir escopo, fronteiras, eventos de entrada, riscos e criterios
de implementacao antes de criar codigo. O Motor Financeiro passa a ser a unica
autoridade operacional para criar operacoes financeiras, gerar parcelas,
processar pagamentos, apurar saldo, calcular valor de quitacao e produzir
memoria de calculo.

---

# 2. Autoridades Consultadas

- `docs/foundation/FOUNDATION-001-product-vision.md`;
- `docs/foundation/FOUNDATION-004-core-domain.md`;
- `docs/foundation/FOUNDATION-005-inventario-do-dominio.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md`;
- `docs/audits/discoveries/EPIC-004-contratos-discovery.md`;
- `docs/product/credit/features/FEATURE-021-liberar-contrato-para-motor-financeiro.md`;
- `docs/product/credit/user-stories/US-059-liberar-contrato-para-motor-financeiro.md`;
- `docs/domain/credit/services/DOMAIN-010-service-motor-financeiro.md`;
- `docs/domain/credit/entities/DOMAIN-004-entity-emprestimo.md`;
- `docs/domain/credit/entities/DOMAIN-005-entity-parcela.md`;
- `docs/domain/credit/entities/DOMAIN-006-entity-pagamento.md`;
- `docs/domain/credit/value-objects/DOMAIN-007-vo-dinheiro.md`.

---

# 3. Escopo

O EPIC-005 contempla:

- criar Emprestimo a partir de `ContratoLiberadoLogico`;
- impedir Emprestimo sem Contrato liberado;
- gerar plano de Parcelas;
- registrar Pagamento recebido;
- distribuir Pagamento entre juros, encargos, parcelas e amortizacao conforme
  regra oficial;
- consultar saldo devedor em data de referencia;
- produzir memoria de calculo auditavel;
- calcular valor de quitacao em data de referencia;
- quitar Emprestimo;
- preparar renegociacao como nova decisao financeira rastreavel;
- publicar eventos de dominio do Motor;
- expor API protegida por IAM/RBAC;
- documentar contratos OpenAPI e erros HTTP;
- manter guardrails que proíbem calculo financeiro definitivo fora do Motor.

---

# 4. Fora do Escopo

Este Epic nao contempla:

- criacao ou assinatura de Contrato de Credito;
- decisao comercial de aprovacao;
- cadastro de Devedor;
- cobranca ativa, agenda, comunicacao ou relatorios;
- integracao bancaria, PIX, boleto, conciliacao externa ou comprovante bancario;
- tabela regulatoria ou taxa externa nao fornecida pelo produto;
- scoring, IA ou decisao automatica de credito;
- contabilidade, livro fiscal ou calculo tributario oficial.

---

# 5. Fronteiras

| Contexto | Relacao com EPIC-005 | Regra de fronteira |
|---|---|---|
| Cadastro | Upstream | fornece Devedor ativo e isolado por Tenant/Carteira. |
| Comercial | Upstream indireto | gera proposta aprovada consumida por Contratos. |
| Contratos | Upstream direto | fornece `ContratoLiberadoLogico`; nao cria Emprestimo nem calcula saldo. |
| Motor Financeiro | Core Domain | unica autoridade de calculo financeiro definitivo. |
| Cobranca, Agenda, Comunicacao e Relatorios | Downstream | consomem eventos e saldos do Motor; nunca recalculam. |
| Configuracoes | Upstream futuro | fornece taxas, modalidades, regras e calendario financeiro. |

---

# 6. Entrada Principal

O evento/logical output de entrada e `ContratoLiberadoLogico`.

Campos minimos esperados:

- `tenant_id`;
- `carteira_id`;
- `devedor_id`;
- `contrato_id`;
- parametros financeiros aprovados;
- data de liberacao logica;
- usuario responsavel pela liberacao;
- versao/snapshot dos parametros contratuais.

O Motor deve tratar essa entrada como imutavel. Reprocessamento da mesma entrada
deve ser idempotente: um mesmo contrato liberado nao pode gerar dois Emprestimos
ativos no MVP.

---

# 7. Regras Financeiras Candidatas

## DA-601 - Motor e fonte oficial de calculo

Nenhum contexto fora do Motor Financeiro calcula juros, saldo, amortizacao,
valor de quitacao ou memoria de calculo.

## DA-602 - Dinheiro e calculado com Decimal

Valores monetarios usam `Decimal` e politica explicita de arredondamento. `float`
e proibido em regras financeiras.

## DA-603 - Periodos financeiros sao reais

Calculos usam datas reais e periodo de referencia explicito. O EPIC-005 nao
assume mes fixo quando a regra contratual exigir dias corridos ou uteis.

## DA-604 - Pagamento prioriza juros antes de amortizacao

O pagamento e processado pelo Motor antes de alterar estado de Emprestimo ou
Parcela. A distribuicao prioriza juros/encargos vencidos antes de amortizar
principal, salvo regra contratual futura explicita.

## DA-605 - Memoria de calculo e obrigatoria

Todo calculo observavel deve produzir memoria de calculo com entradas, regra,
periodo, valores intermediarios, arredondamentos e resultado.

## DA-606 - Fatos financeiros prevalecem sobre derivados

O sistema persiste fatos financeiros e snapshots necessarios. Saldos derivados
devem ser recomputaveis ou possuir trilha que explique sua origem.

## DA-607 - Configuracoes financeiras podem nascer como snapshot contratual

Enquanto o contexto de Configuracoes financeiras nao existir, o MVP pode usar os
parametros congelados do contrato liberado. A decisao evita dependencia falsa e
mantem rastreabilidade.

---

# 8. Modelo Candidato

- Aggregate: `Emprestimo`;
- Entities: `Parcela`, `Pagamento`, `MemoriaCalculo`;
- Value Objects: `Dinheiro`, `PeriodoFinanceiro`, `TaxaJuros`,
  `RegraCalculo`, `ValorQuitacao`;
- Domain Service: `MotorFinanceiro`;
- Eventos: `EmprestimoCriado`, `ParcelasGeradas`, `PagamentoRegistrado`,
  `SaldoCalculado`, `ValorQuitacaoCalculado`, `EmprestimoQuitado`,
  `EmprestimoRenegociado`.

---

# 9. Fluxos Candidatos

1. Contratos libera logicamente um contrato.
2. Motor consome `ContratoLiberadoLogico`.
3. Motor cria Emprestimo idempotente.
4. Motor gera Parcelas conforme parametros congelados.
5. Operacao recebe Pagamentos.
6. Motor distribui cada Pagamento e registra memoria.
7. Consultas de saldo e quitacao usam data de referencia explicita.
8. Quitacao encerra a operacao quando nao houver obrigacao financeira pendente.
9. Renegociacao encerra/relaciona condicoes antigas e cria nova trilha
   financeira conforme regra aprovada.

---

# 10. Riscos

| Risco | Impacto | Mitigacao |
|---|---|---|
| Uso de `float` | erro financeiro silencioso | guardrail AST e testes de precisao. |
| Mes fixo indevido | juros incorretos | `PeriodoFinanceiro` com datas reais. |
| Calculo fora do Motor | quebra do Core Domain | guardrail anti-Motor em Comercial, Contratos e downstreams. |
| Duplicidade por contrato | duas operacoes para o mesmo contrato | idempotencia e constraint unica por contrato liberado. |
| Memoria insuficiente | impossibilidade de auditoria | memoria obrigatoria em toda operacao financeira. |
| Pagamento duplicado | saldo indevido | chave idempotente de pagamento e auditoria. |
| Configuracoes incompletas | regras ambiguas | snapshot contratual no MVP e DR futura para Configuracoes. |
| Retroatividade | divergencia de saldo historico | fatos imutaveis e recalculo com data de referencia. |

---

# 11. Perguntas Abertas

- Qual sera a politica oficial de arredondamento monetario por moeda?
- Quais modalidades de amortizacao entram no MVP?
- Haverá chave idempotente externa para pagamentos ou apenas identificador
  interno no MVP?
- Renegociacao cria novo Emprestimo ou altera condicoes do Emprestimo original
  mantendo versoes?
- Configuracoes financeiras serao EPIC proprio ou subciclo posterior de
  Operacoes de Credito?

---

# 12. Resultado do Discovery

O EPIC-005 pode avancar para Product/Features/User Stories e plano tecnico, com
uma premissa central: Motor Financeiro e a unica superficie autorizada a
produzir calculo financeiro definitivo.

---

# 13. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Discovery/SDD inicial do EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro. |
