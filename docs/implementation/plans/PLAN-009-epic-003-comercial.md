# PLAN-009 - Plano Tecnico do EPIC-003/Comercial

**ID:** PLAN-009

**Versao:** 1.1.0

**Status:** Implementado

---

# 1. Objetivo

Implementar o EPIC-003/Comercial no Credit Context, seguindo a Discovery e o
pacote Product ja materializados, para habilitar simulacoes, propostas, decisoes
comerciais e a saida controlada de proposta aprovada para Contratos futuro.

O escopo cobre dominio Comercial, persistencia, application services, API,
RBAC, auditoria, OpenAPI e suites de guardrail que impedem calculo financeiro
definitivo fora do Motor Financeiro.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-003-comercial-discovery.md`;
- `docs/product/credit/capabilities/PRODUCT-003-administrar-comercial.md`;
- `docs/product/credit/epics/EPIC-003-comercial-propostas-simulacao.md`;
- `docs/product/credit/features/FEATURE-013-simular-credito.md`;
- `docs/product/credit/features/FEATURE-014-criar-proposta-comercial.md`;
- `docs/product/credit/features/FEATURE-015-consultar-propostas.md`;
- `docs/product/credit/features/FEATURE-016-decidir-proposta.md`;
- `docs/product/credit/features/FEATURE-017-integrar-proposta-aprovada.md`;
- `docs/product/credit/user-stories/US-043-criar-simulacao-comercial.md`;
- `docs/product/credit/user-stories/US-044-consultar-simulacao-comercial.md`;
- `docs/product/credit/user-stories/US-045-criar-proposta-comercial.md`;
- `docs/product/credit/user-stories/US-046-validar-devedor-ativo-para-proposta.md`;
- `docs/product/credit/user-stories/US-047-consultar-proposta-por-id.md`;
- `docs/product/credit/user-stories/US-048-listar-propostas.md`;
- `docs/product/credit/user-stories/US-049-consultar-trilha-decisoes-comerciais.md`;
- `docs/product/credit/user-stories/US-050-aprovar-proposta.md`;
- `docs/product/credit/user-stories/US-051-encerrar-proposta-sem-aprovacao.md`;
- `docs/product/credit/user-stories/US-052-disponibilizar-proposta-aprovada-para-contratos.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`;
- `docs/foundation/FOUNDATION-006-arquitetura-multi-tenant.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/implementation/plans/PLAN-008-proximo-ciclo-pos-iam-p4.md`.

---

# 3. Situacao Atual

## Ja implementado - reutilizar

- IAM operacional com Principal autenticado, RBAC por permissao e contratos
  HTTP 401/403/404;
- Cadastro de Devedores com Carteira e Devedor como dependencias de origem;
- auditoria append-only e Unit of Work reutilizaveis;
- validacao reproduzivel de migrations e pipeline de qualidade P4;
- padroes REST de `presentation/api`, schemas Pydantic, dependencies e OpenAPI.

## Ainda nao implementado

- dominio Comercial: `SimulacaoComercial`, `PropostaComercial`,
  `DecisaoComercial`, estados e invariantes;
- ports e repositories comerciais;
- migration aditiva de tabelas comerciais;
- application services para simulacao, proposta, consulta, decisao e contrato
  logico de proposta aprovada;
- endpoints HTTP protegidos por IAM/RBAC;
- catalogo de permissoes comerciais;
- auditoria de escritas e transicoes;
- suites unitarias, integracao, API, OpenAPI e guardrail de Motor.

---

# 4. Decisoes Tecnicas

## DA-401 - Comercial como contexto de originação

O Comercial cria registros de simulacao e proposta, mas nao cria Contrato,
Emprestimo, Parcela, Pagamento nem memoria de calculo. Sua unica saida para o
roadmap financeiro e uma proposta aprovada consumivel pelo contexto Contratos.

## DA-402 - PropostaComercial como Aggregate Root do contexto

`PropostaComercial` e o Aggregate Root do EPIC-003. Ela protege estado,
parametros comerciais aprovaveis, referencias a Carteira/Devedor, decisoes e
imutabilidade apos aprovacao.

## DA-403 - SimulacaoComercial nao cria obrigacao

`SimulacaoComercial` e registro nao vinculante. Pode registrar parametros
informados e estimativas comerciais permitidas, mas qualquer calculo financeiro
definitivo deve falhar em testes de guardrail.

## DA-404 - Devedor ativo e mesma Carteira como pre-condicao

Criacao de simulacao e proposta exige Devedor ativo da Carteira autenticada. A
validacao consome Cadastro por referencia e recurso de outro Tenant/Carteira
responde 404.

## DA-405 - RBAC por permissoes comerciais

As operacoes comerciais nascem protegidas por IAM. Permissoes comerciais:
`comercial.simulacao.criar`, `comercial.proposta.criar`,
`comercial.proposta.ler`, `comercial.proposta.decidir` e
`comercial.proposta.integrar`.

## DA-406 - Auditoria apenas para escrita e decisao

Criacao de simulacao, criacao de proposta e decisoes comerciais geram auditoria
append-only. Consultas e listagens nao geram nova escrita de auditoria.

## DA-407 - API aninhada sob Carteira

Endpoints comerciais ficam sob `/credit/carteiras/{carteira_id}` para preservar
a fronteira operacional ja adotada no Cadastro e no IAM.

---

# 5. Modelo de Dados

Migration aditiva prevista:

- `simulacao_comercial`: id, tenant_id, carteira_id, devedor_id, parametros
  JSON, criada_por_usuario_id, criado_em;
- `proposta_comercial`: id, tenant_id, carteira_id, devedor_id,
  simulacao_id opcional, estado, parametros JSON, criada_por_usuario_id,
  aprovada_por_usuario_id opcional, aprovada_em opcional, validade_em opcional,
  criado_em, atualizado_em;
- `decisao_comercial`: id, proposta_id, usuario_id, tipo, estado_anterior,
  estado_posterior, motivo opcional, criado_em.

Constraints minimas:

- FKs para `tenant`, `carteira`, `devedor` e `usuario` quando aplicavel;
- indice por `carteira_id`, `devedor_id`, `estado` e `criado_em`;
- downgrade reversivel;
- nenhuma alteracao destrutiva em tabelas existentes.

---

# 6. API

Rotas implementadas do EPIC-003 nos IMP-120..122:

- `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais`
  cria simulacao comercial nao vinculante;
- `GET /credit/simulacoes-comerciais/{simulacao_id}` consulta simulacao por
  ID dentro do Tenant autenticado;
- `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais`
  cria proposta comercial, opcionalmente a partir de uma simulacao;
- `GET /credit/carteiras/{carteira_id}/devedores/{devedor_id}/propostas-comerciais`
  lista propostas comerciais do Devedor, com filtros e paginacao;
- `GET /credit/propostas-comerciais/{proposta_id}` consulta proposta por ID
  dentro do Tenant autenticado;
- `PATCH /credit/propostas-comerciais/{proposta_id}` atualiza parametros de
  proposta ainda nao terminal;
- `POST /credit/propostas-comerciais/{proposta_id}/enviar-para-analise`
  envia proposta para analise;
- `POST /credit/propostas-comerciais/{proposta_id}/aprovar` aprova proposta;
- `POST /credit/propostas-comerciais/{proposta_id}/recusar` recusa proposta;
- `POST /credit/propostas-comerciais/{proposta_id}/cancelar` cancela proposta;
- `POST /credit/propostas-comerciais/{proposta_id}/expirar` expira proposta;
- `GET /credit/propostas-comerciais/{proposta_id}/contrato-logico` retorna a
  saida logica de proposta aprovada para Contratos futuro.

Contratos de erro:

- 401 para token ausente, invalido ou expirado;
- 403 para Principal autenticado sem permissao comercial;
- 404 para Carteira/Devedor/Simulacao/Proposta inexistente ou de outro Tenant;
- 409 para transicao de estado invalida;
- 422 para entrada invalida.

---

# 7. Estrategia de Testes

- **Unit domain Comercial:** estados, invariantes, imutabilidade de proposta
  aprovada, decisao terminal e ausencia de calculo financeiro definitivo;
- **Unit application Comercial:** criacao, consulta, decisao, auditoria e
  validacao de Devedor ativo com ports fake;
- **Integration migrations:** ciclo upgrade/downgrade/upgrade e indices/FKs;
- **Integration repositories:** round-trip real de simulacao, proposta e
  decisoes por Tenant/Carteira;
- **Integration application:** UoW, auditoria, rollback, proposta aprovada como
  saida logica;
- **Integration API:** contratos HTTP 200/201/401/403/404/409/422, OpenAPI e
  RBAC;
- **Regression IAM/Cadastro:** cross-tenant, Devedor inativo, permissoes
  ausentes e healthcheck publico;
- **Guardrail Motor:** testes que falham se o Comercial criar Emprestimo,
  Parcela, Pagamento, Contrato ou executar calculo financeiro definitivo.

---

# 8. Ordem de Implementacao

1. Suites de dominio e guardrail antes do codigo de dominio;
2. dominio Comercial;
3. migrations e repositories;
4. application services;
5. catalogo RBAC e auditoria;
6. API e OpenAPI;
7. regressao, quality gates e recertificacao.

Cada tarefa inicia somente com suas dependencias concluidas e sua suite minima
definida.

---

# 9. Estrategia de Rollout

- migration aditiva, sem backfill obrigatorio;
- endpoints novos protegidos desde o nascimento;
- nenhum endpoint existente muda de contrato;
- rollback por downgrade das tabelas comerciais enquanto nao houver Contratos;
- release do EPIC-003 so ocorre apos suite completa e gates globais verdes.

---

# 10. Riscos

| Risco | Mitigacao |
|---|---|
| Comercial absorver Motor Financeiro | Guardrail Motor e DA-401/DA-403. |
| Proposta aprovada editavel | Invariante de imutabilidade e testes de estado. |
| Criar proposta para Devedor inativo | Validacao obrigatoria via Cadastro e regressao. |
| Vazamento cross-tenant | Dependencias IAM/Carteira e 404 indistinguivel. |
| Auditoria incompleta | Escritas e decisoes auditadas em application services. |
| API sem RBAC | Endpoints protegidos desde a primeira exposicao. |
| Plano implementar Contratos por acidente | Saida limitada a contrato logico; sem entidade Contrato no EPIC-003. |

---

# 11. Gates de Aceite

O EPIC-003 so pode ser considerado pronto quando:

- `uv run pytest` passar;
- `uv run ruff check .` passar;
- `uv run black --check .` passar;
- `uv run mypy src tests` passar;
- `npm run docs:validate` passar com 0 erros;
- `npm run docs:test` passar;
- endpoints comerciais sem token responderem 401;
- token valido sem permissao comercial responder 403;
- recurso de outro Tenant responder 404;
- transicao invalida responder 409;
- entrada invalida responder 422;
- proposta aprovada nao permitir alteracao de parametros;
- nenhuma suite, domain service ou application service comercial executar
  calculo financeiro definitivo.

---

# 12. Fora de Escopo

- Contratos de Credito;
- assinatura, liberacao ou documento contratual;
- Emprestimos, Parcelas e Pagamentos;
- Motor Financeiro;
- memoria de calculo, juros, amortizacao, saldo e quitacao;
- bureaus de credito, bancos, PIX, scoring externo ou IA;
- Event Bus externo ou mensageria.

---

# 13. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Plano tecnico inicial do EPIC-003/Comercial com dominio, migrations, application, API, RBAC, auditoria e suites de guardrail. |
