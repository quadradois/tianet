# PLAN-017 - Plano Tecnico do EPIC-009/Configuracoes Financeiras e Calendario Operacional

**ID:** PLAN-017

**Versao:** 1.0.0

**Status:** Planejado

---

# 1. Contexto

Este plano executa o EPIC-009/Configuracoes Financeiras e Calendario
Operacional apos a recertificacao dos EPICs de IAM, Comercial, Contratos,
Motor Financeiro, Operacao Diaria e Fundacao Operacional.

O objetivo e materializar o contexto responsavel por parametrizar modalidades,
taxas, politicas financeiras permitidas, vigencias, versoes e calendario
financeiro, sem criar regra de calculo definitiva fora do Motor Financeiro.

---

# 2. Referencias

- `docs/audits/discoveries/EPIC-009-configuracoes-financeiras-calendario-operacional-discovery.md`;
- `docs/product/credit/capabilities/PRODUCT-009-administrar-configuracoes-financeiras.md`;
- `docs/product/credit/epics/EPIC-009-configuracoes-financeiras-calendario-operacional.md`;
- `docs/product/credit/features/FEATURE-037-administrar-modalidades-financeiras.md`;
- `docs/product/credit/features/FEATURE-038-parametrizar-politicas-financeiras.md`;
- `docs/product/credit/features/FEATURE-039-administrar-calendario-financeiro-operacional.md`;
- `docs/product/credit/features/FEATURE-040-gerir-vigencias-configuracoes-financeiras.md`;
- `docs/product/credit/features/FEATURE-041-consultar-capturar-configuracao-financeira.md`;
- `docs/product/credit/user-stories/US-099-definir-modalidade-financeira-permitida.md`;
- `docs/product/credit/user-stories/US-100-validar-modalidade-por-tenant-carteira.md`;
- `docs/product/credit/user-stories/US-101-criar-configuracao-financeira-rascunho.md`;
- `docs/product/credit/user-stories/US-102-validar-parametros-financeiros-permitidos.md`;
- `docs/product/credit/user-stories/US-103-administrar-calendario-financeiro.md`;
- `docs/product/credit/user-stories/US-104-resolver-periodo-por-data-referencia.md`;
- `docs/product/credit/user-stories/US-105-aprovar-configuracao-financeira.md`;
- `docs/product/credit/user-stories/US-106-programar-ativacao-configuracao-financeira.md`;
- `docs/product/credit/user-stories/US-107-ativar-substituir-configuracao-sem-retroatividade.md`;
- `docs/product/credit/user-stories/US-108-auditar-historico-configuracao-financeira.md`;
- `docs/product/credit/user-stories/US-109-consultar-configuracao-vigente-data-referencia.md`;
- `docs/product/credit/user-stories/US-110-capturar-snapshot-configuracao-contratual.md`;
- `docs/product/credit/user-stories/US-111-impedir-regra-financeira-livre-apis.md`;
- `docs/product/credit/user-stories/US-112-impedir-calculo-financeiro-configuracoes.md`;
- `docs/implementation/plans/PLAN-013-epic-005-motor-financeiro.md`;
- `docs/implementation/plans/PLAN-015-epic-008-fundacao-operacional-observabilidade.md`;
- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/adrs/ADR-002-auditoria-independente-da-transacao.md`;
- `docs/architecture/adrs/ADR-004-autenticacao-e-autorizacao-iam.md`.

---

# 3. Situacao Atual

## Concluido e pronto para reutilizar

- IAM operacional com autenticacao, RBAC, respostas 401/403/404 e catalogo de
  permissoes;
- Comercial, Contratos e Motor Financeiro ja possuem fluxo funcional de
  proposta, contrato liberado logico, emprestimo, parcelas, pagamento, saldo,
  quitacao, renegociacao e memoria de calculo;
- Fundacao Operacional ja fornece gates, migrations reproduziveis, health,
  correlation ID, logs estruturados e contratos iniciais de eventos/projections;
- Product/EPIC/Features/User Stories do EPIC-009 foram materializados e
  revisados;
- Discovery do EPIC-009 definiu a fronteira obrigatoria: Configuracoes
  parametriza, Motor calcula.

## Pendencias para este plano

- suites de dominio e contratos documentais especificos do EPIC-009;
- guardrails anti-calculo e anti-regra financeira livre;
- dominio de configuracoes, modalidade, calendario, vigencia e snapshot;
- migration aditiva e persistencia de configuracoes financeiras;
- services de aplicacao para criacao, aprovacao, programacao, ativacao,
  consulta vigente e captura de snapshot;
- permissoes IAM, schemas, dependencies, rotas e OpenAPI;
- recertificacao completa do EPIC-009.

---

# 4. Decisoes Tecnicas

## D1 - Configuracoes parametriza, Motor calcula

Configuracoes Financeiras define parametros validos, vigentes, versionados e
auditaveis. O Motor Financeiro permanece a unica autoridade para calcular juros,
mora, multa, amortizacao, saldo, quitacao e memoria de calculo.

## D2 - Sem chamada direta Configuracoes -> Motor

Configuracoes nao chama o Motor para antecipar saldo, memoria ou qualquer
resultado financeiro. O Motor nao consulta Configuracoes diretamente: ele
consome parametros congelados no contrato liberado logico.

## D3 - Snapshot contratual e imutavel

`SnapshotConfiguracaoContratualV1` preserva configuracao, versao, parametros
normalizados, vigencia, origem, autoria de captura, data de captura e hash de
rastreabilidade. Alteracoes futuras em Configuracoes nao alteram snapshots ja
capturados.

## D4 - Escopo MVP de modalidade e aprovacao

O primeiro pacote implementavel aceita apenas modalidades e politicas ja
suportaveis pelo Motor atual. A ativacao no MVP exige usuario autenticado com
permissao administrativa especifica; aprovacao dupla fica fora deste ciclo.

## D5 - Vigencia deterministica

Toda consulta consumivel usa `data_referencia` explicita. Ausencia de
configuracao aplicavel retorna 404 logico; conflito ou ambiguidade de vigencia
retorna 409.

## D6 - Calendario define periodo, nao resultado

Calendario Financeiro pode resolver convencoes de periodo, dias corridos/dias
uteis basicos e datas de referencia. Ele nao calcula juros, inadimplencia,
saldo, mora, multa, amortizacao, quitacao ou memoria.

## D7 - APIs consumidoras nao aceitam regra livre

Comercial, Contratos e Motor nao devem aceitar payload financeiro arbitrario
como fonte oficial. Consumidores usam referencia governada ou snapshot
imutavel; validacoes de formato/faixa sao permitidas, calculo definitivo nao.

## D8 - Migracao aditiva

O EPIC-009 nao altera retroativamente proposta, contrato, emprestimo, parcela,
pagamento ou memoria existentes. A persistencia nova e aditiva e preserva
compatibilidade com snapshots contratuais atuais.

---

# 5. Modelo Tecnico Candidato

Componentes candidatos:

- aggregate `ConfiguracaoFinanceira`;
- entity `ModalidadeFinanceira`;
- entity `CalendarioFinanceiro`;
- entity `VersaoConfiguracaoFinanceira`;
- entity/evento `EventoConfiguracaoFinanceira`;
- value object `TaxaConfigurada`;
- value object `ParametroFinanceiro`;
- value object `JanelaVigencia`;
- value object `CodigoModalidade`;
- value object `PoliticaArredondamentoConfigurada`;
- contrato `ConfiguracaoFinanceiraVigenteV1`;
- contrato `SnapshotConfiguracaoContratualV1`;
- porta de repository para configuracoes, modalidades e calendarios;
- services de aplicacao de escrita, consulta e captura de snapshot;
- catalogo IAM `configuracoes_financeiras.*`;
- rotas REST sob `/credit/configuracoes-financeiras`.

Nenhum componente de Configuracoes Financeiras pode conter formula de calculo
definitivo ou duplicar memoria de calculo do Motor.

---

# 6. Persistencia

Migrations candidatas:

- `configuracoes_financeiras`;
- `configuracoes_financeiras_versoes`;
- `modalidades_financeiras`;
- `calendarios_financeiros`;
- `configuracoes_financeiras_eventos`;
- `snapshots_configuracao_contratual`, se o snapshot ficar materializado neste
  contexto antes de ser copiado por Contratos.

Restricoes minimas:

- escopo por tenant e carteira opcional;
- unicidade por tenant, carteira, modalidade, versao;
- indice por tenant, carteira, modalidade, estado, vigencia;
- ausencia de sobreposicao consumivel para mesma combinacao de escopo,
  modalidade e periodo;
- trilha auditavel de criacao, aprovacao, programacao, ativacao, substituicao e
  inativacao;
- downgrade/upgrade reproduzivel;
- nenhuma alteracao destrutiva em tabelas de Comercial, Contratos ou Motor.

---

# 7. API

Rotas candidatas:

- `POST /credit/configuracoes-financeiras/modalidades`;
- `GET /credit/configuracoes-financeiras/modalidades`;
- `POST /credit/configuracoes-financeiras/calendarios`;
- `GET /credit/configuracoes-financeiras/calendarios`;
- `POST /credit/configuracoes-financeiras`;
- `GET /credit/configuracoes-financeiras`;
- `GET /credit/configuracoes-financeiras/{configuracao_id}`;
- `POST /credit/configuracoes-financeiras/{configuracao_id}/aprovar`;
- `POST /credit/configuracoes-financeiras/{configuracao_id}/programar`;
- `POST /credit/configuracoes-financeiras/{configuracao_id}/ativar`;
- `POST /credit/configuracoes-financeiras/{configuracao_id}/inativar`;
- `GET /credit/configuracoes-financeiras/vigente`;
- `POST /credit/configuracoes-financeiras/snapshots`;

Todas as rotas de negocio devem ser protegidas por IAM/RBAC. Erros esperados:

- `400` para payload, filtro, data ou combinacao malformada;
- `401` para ausencia de autenticacao;
- `403` para principal sem permissao;
- `404` logico para recurso inexistente, inacessivel ou sem configuracao
  aplicavel;
- `409` para vigencia conflitante, estado invalido ou idempotencia divergente.

---

# 8. Estrategia de Testes

- **Docs/contratos:** Product, EPIC, Features, User Stories, PLAN, backlog e
  registry consistentes;
- **Dominio:** modalidade, parametros, calendario, vigencia, estados,
  transicoes e snapshots imutaveis;
- **Guardrails:** Configuracoes sem calculo financeiro, sem `float` monetario e
  sem regra financeira livre em APIs consumidoras;
- **Migrations:** upgrade/downgrade/upgrade, constraints, indices e ausencia de
  alteracao destrutiva em tabelas existentes;
- **Repositories:** round-trip, filtros por tenant/carteira/modalidade/data e
  conflitos de vigencia;
- **Application:** autorizacao, idempotencia, auditoria, 404 logico, 409 de
  conflito e captura de snapshot;
- **API:** contratos HTTP 200/201/400/401/403/404/409, RBAC, cross-tenant,
  paginacao/filtros e correlation ID;
- **OpenAPI:** schemas, security, erros e header `X-Correlation-ID`;
- **Recertificacao:** suite Python, qualidade, docs, migrations e revisao
  adversarial final.

---

# 9. Ordem de Implementacao

1. suites documentais, dominio e guardrails antes de codigo;
2. dominio de Configuracoes Financeiras;
3. persistencia, migrations, ORM e repositories;
4. integracao no UnitOfWork;
5. services de aplicacao;
6. IAM, schemas, dependencies, API e OpenAPI;
7. guardrails de integracao com Comercial, Contratos e Motor;
8. recertificacao completa do EPIC-009.

Cada tarefa inicia somente com dependencias satisfeitas no backlog.

---

# 10. Gates de Aceite

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:validate`;
- `npm run docs:test`;
- `npm run quality:migrations`;
- docs/contratos do EPIC-009 verdes;
- ausencia de calculo financeiro definitivo em Configuracoes;
- ausencia de regra financeira livre em APIs consumidoras;
- snapshots imutaveis com origem, versao, `capturado_em` e hash;
- Motor consumindo parametros apenas via contrato liberado logico;
- OpenAPI documentando rotas, security, 400/401/403/404/409 e correlation ID;
- revisao adversarial final sem achados bloqueantes.

---

# 11. Fora do Escopo Tecnico

- calculo definitivo de juros, mora, multa, saldo, amortizacao, quitacao ou
  memoria de calculo;
- alteracao retroativa de propostas, contratos, emprestimos, parcelas,
  pagamentos ou memorias existentes;
- aprovacao dupla ou workflow avancado;
- BACEN, PIX, boleto, banco ou terceiro externo;
- frontend administrativo;
- Scheduler, Notification, broker externo, outbox completa, BI avancado,
  dashboards APM externos ou IaC/cloud.

---

# 12. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Plano tecnico inicial do EPIC-009/Configuracoes Financeiras e Calendario Operacional. |
