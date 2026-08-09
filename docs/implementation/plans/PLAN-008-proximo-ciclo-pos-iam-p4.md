# PLAN-008 - Plano Tecnico do Proximo Ciclo Pos-IAM/P4

**ID:** PLAN-008

**Versao:** 1.0.0

**Status:** Proposto

---

# 1. Contexto

Este plano fecha o IMP-081 do PLAN-004 e define a transicao apos:

- backend recuperado e recertificado;
- EPIC-006/IAM formalmente encerrado;
- P4 operacional concluido com CI e validacao reproduzivel de migrations.

A decisao central e nao iniciar diretamente Contratos ou Motor Financeiro. O
roadmap oficial coloca **Epico 003 - Comercial / Propostas / Simulacao** antes de
Epico 004 Contratos e Epico 005 Emprestimos/Pagamentos/Motor Financeiro.

---

# 2. Fontes de Autoridade

- `ROADMAP-ALIGNMENT` e documento oficial de transicao: AMP-001 como
  roadmap estrategico; Epico 003 = Comercial; Epico 004 = Contratos; Epico 005 =
  Emprestimos/Pagamentos/Motor Financeiro.
- `AMP-001` v1.1.0: corrige a ambiguidade historica de Epico 003 e separa
  Comercial, Contratos e Motor Financeiro.
- `FOUNDATION-009`: nenhum elemento pula a hierarquia
  `Capability -> Bounded Context -> Discovery -> EPIC -> Feature -> User Story`;
  PRODUCT N nasce somente quando houver necessidade real no Discovery.
- `PLAN-004`: P4 fecha a base operacional; IMP-081 prepara o pacote seguinte.

---

# 3. Decisao de Escopo

O proximo ciclo deve ser **Discovery/SDD do Epico 003 - Comercial**, nao
implementacao direta de codigo.

## Dentro do IMP-081

- Consolidar o plano de transicao pos-IAM/P4.
- Definir a ordem recomendada para o proximo SDD.
- Registrar fronteiras entre Comercial, Contratos e Motor Financeiro.
- Definir suites de teste que deverao nascer antes da implementacao do Epico 003.

## Fora do IMP-081

- Criar Product/EPIC/Feature/User Story finais do Epico 003.
- Implementar codigo de propostas, contratos, emprestimos, parcelas ou pagamentos.
- Criar migrations de dominio financeiro.
- Alterar `FOUNDATION-009` ou `ROADMAP-ALIGNMENT`.

---

# 4. Fronteiras do Proximo Ciclo

| Contexto | Papel no roadmap | Pode entrar no proximo SDD? | Observacao |
|---|---|---:|---|
| Comercial | Simulacoes, propostas, analise e aprovacao comercial | Sim | Epico 003; downstream de Cadastro e upstream de Contratos. |
| Contratos | Formalizacao, contrato de credito, assinatura, liberacao | Nao | Epico 004; depende de proposta aprovada. |
| Motor Financeiro | Juros, amortizacao, pagamentos, quitacao, memoria de calculo | Nao | Epico 005; calculos financeiros ficam exclusivamente aqui. |
| Configuracoes Financeiras | Taxas, modalidades, regras de calculo, calendario financeiro | Apenas discovery de dependencia | Deve ser tratado como dependencia upstream, sem misturar com Comercial. |

---

# 5. Ordem Recomendada

## P5.1 - Discovery do Epico 003 Comercial

Resultado esperado: pacote de descoberta que confirma linguagem ubiqua,
capability aplicavel, limites, atores, eventos, regras e dependencias.

Entregaveis:

1. Discovery do Epico 003 Comercial.
2. Decisao explicita sobre PRODUCT N aplicavel, conforme FOUNDATION-009 BR 006.
3. Lista inicial de Features e User Stories de Comercial.
4. Mapa de dependencias com Cadastro, IAM e futuras Configuracoes Financeiras.

## P5.2 - Plano de Implementacao do Epico 003

Resultado esperado: plano tecnico com domain, persistence, application, API,
migrations e suites antes de codigo.

Entregaveis:

1. Plano de implementacao do Epico 003.
2. Backlog de execucao com novos IMPs.
3. Matriz de endpoints e contratos HTTP se houver API.
4. Estrategia de testes por camada.

## P5.3 - Execucao do Epico 003

Resultado esperado: implementar somente depois do SDD aprovado e validado.

---

# 6. Suites Previstas

| Suite | Objetivo |
|---|---|
| Unit domain Comercial | Proposta, Simulacao, estado comercial e invariantes sem banco. |
| Property/table tests | Cenarios de simulacao sem assumir calculo financeiro definitivo fora do Motor. |
| Integration repositories | Persistencia de proposta/simulacao com Tenant, Devedor e Carteira. |
| Integration application | Criacao, consulta, aprovacao/reprovacao e auditoria de propostas. |
| API contract | Contratos HTTP, 401/403/404/409/422 e OpenAPI. |
| Authorization regression | RBAC por permissao comercial e bloqueio cross-tenant. |
| Migration cycle | Upgrade/downgrade/upgrade das migrations do Epico 003. |

---

# 7. Riscos e Guardrails

| Risco | Severidade | Guardrail |
|---|---:|---|
| Pular Comercial e iniciar Contratos/Motor | Alta | IMP-081 fixa Epico 003 como proximo SDD. |
| Calculo financeiro aparecer em Comercial | Alta | Comercial pode simular cenarios, mas a regra financeira final pertence ao Motor Financeiro. |
| Criar Product antes do Discovery | Media | Seguir FOUNDATION-009 BR 006 e BR 008. |
| Reabrir numeracao antiga de Epico 003 como Perfis | Alta | ROADMAP-ALIGNMENT e AMP-001 v1.1.0 sao fonte de autoridade. |
| Misturar Configuracoes Financeiras com Comercial | Media | Registrar como dependencia futura/upstream, nao como escopo principal. |

---

# 8. Definicao de Pronto

O proximo ciclo so deve sair do planejamento para implementacao quando:

- Discovery do Epico 003 existir e passar em `npm run docs:validate`;
- Product/EPIC/Features/User Stories tiverem sido criados no nivel correto;
- plano e backlog de execucao do Epico 003 existirem;
- suites de dominio, aplicacao, API, autorizacao e migrations estiverem
  previstas antes da implementacao;
- P4 continuar verde com CI e rotina de migrations reproduzivel.

---

# 9. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | IMP-081 define o proximo ciclo pos-IAM/P4 como Discovery/SDD do Epico 003 Comercial antes de Contratos e Motor Financeiro. |
