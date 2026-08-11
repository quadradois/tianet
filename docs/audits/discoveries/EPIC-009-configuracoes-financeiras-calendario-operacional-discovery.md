# EPIC-009 - Discovery/SDD de Configuracoes Financeiras e Calendario Operacional

**ID:** EPIC-009

**Tipo:** Artefato de Discovery/SDD

**Versao:** 1.1.0

**Status:** Product materializado; pronto para PLAN tecnico

---

# 1. Objetivo

Este discovery prepara o ciclo do EPIC-009 - Configuracoes Financeiras e
Calendario Operacional.

O objetivo e definir o contexto responsavel por parametrizar modalidades,
taxas, politicas financeiras permitidas, vigencias e calendario financeiro,
sem implementar codigo neste ciclo de discovery. O EPIC-009 nao calcula juros,
saldo, amortizacao, quitacao ou memoria de calculo: ele fornece parametros
governados e versionados para que o Motor Financeiro continue sendo a unica
autoridade de calculo definitivo.

---

# 2. Autoridades Consultadas

- `docs/foundation/FOUNDATION-003-mapa-do-dominio.md`;
- `docs/foundation/FOUNDATION-005-inventario-do-dominio.md`;
- `docs/foundation/FOUNDATION-007-product-map.md`;
- `docs/foundation/FOUNDATION-008-mvp-scope.md`;
- `docs/foundation/FOUNDATION-009-capability-map.md`;
- `docs/architecture/ROADMAP-ALIGNMENT-PRODUCT-AMP.md`;
- `docs/architecture/amp/AMP-001-architecture-master-plan.md`;
- `docs/audits/discoveries/EPIC-005-motor-financeiro-discovery.md`;
- `docs/audits/discoveries/EPIC-007-operacao-diaria-discovery.md`;
- `docs/audits/discoveries/EPIC-008-fundacao-operacional-observabilidade-discovery.md`;
- `docs/implementation/plans/PLAN-013-epic-005-motor-financeiro.md`;
- `docs/product/platform/capabilities/PRODUCT-001-administrar-plataforma.md`;
- `docs/product/platform/user-stories/US-006-inicializar-configuracoes.md`.

---

# 3. Contexto

O backend ja possui a cadeia funcional principal do MVP:

1. Platform e IAM garantem tenant, usuario autenticado e RBAC.
2. Cadastro fornece Devedor.
3. Comercial cria simulacoes e propostas.
4. Contratos formaliza e libera logicamente a operacao.
5. Motor Financeiro cria Emprestimo, Parcelas, Pagamentos, Quitacao,
   Renegociacao e Memoria de Calculo.
6. Operacao Diaria organiza Cobranca, Agenda, Comunicacao manual e Relatorios.
7. Fundacao Operacional adiciona CI, migrations, healthcheck, correlation ID,
   logs estruturados e contratos iniciais de eventos/projections.

Os documentos de dominio ja reconhecem Configuracoes como contexto emergente
para taxas, modalidades, regras de calculo e calendario financeiro. O Motor
Financeiro, por sua vez, ja registrou que a regra financeira vem do contrato
liberado ou de Configuracoes financeiras futuras, nao de payload livre da API.

O EPIC-009 fecha essa lacuna de governanca: em vez de cada fluxo carregar
parametros livres ou hardcoded, o produto passa a ter um lugar explicito para
definir, versionar, consultar e congelar parametros financeiros antes de serem
interpretados pelo Motor.

---

# 4. Problema

Sem um contexto formal de Configuracoes Financeiras, o MVP fica exposto a
riscos de consistencia:

- parametros financeiros podem nascer duplicados em Comercial, Contratos ou
  Motor;
- requests podem carregar regra financeira arbitraria;
- contratos liberados podem congelar snapshots sem trilha de origem;
- mudanca de taxa ou modalidade pode afetar operacoes historicas por acidente;
- calendario financeiro pode ser inferido de forma diferente entre simulacao,
  contrato, parcela e relatorio;
- o Motor pode receber parametros validos tecnicamente, mas sem vigencia,
  autoria ou aprovacao de produto.

---

# 5. Escopo

O EPIC-009 contempla:

- definir modalidades de emprestimo permitidas no MVP;
- parametrizar taxas, encargos e politicas financeiras autorizadas;
- definir calendario financeiro operacional;
- controlar vigencia, versao e estado de uma configuracao financeira;
- permitir configuracao por tenant e, quando necessario, por carteira;
- consultar configuracoes vigentes em uma data de referencia;
- produzir snapshot imutavel para proposta e contrato; Contratos carrega esse
  snapshot no `ContratoLiberadoLogico` consumido pelo Motor Financeiro;
- validar que parametros financeiros pertencem ao tenant/carteira corretos;
- registrar autoria, motivo e historico de alteracao;
- expor contratos candidatos para Comercial, Contratos e Motor Financeiro;
- definir guardrails para impedir calculo financeiro dentro de Configuracoes;
- preparar suites de dominio, aplicacao, API, RBAC, OpenAPI e docs antes de
  qualquer implementacao.

---

# 6. Fora do Escopo

Este Epic nao contempla:

- calculo definitivo de juros, mora, multa, saldo, amortizacao, quitacao ou
  memoria de calculo;
- alteracao de Emprestimo, Parcela, Pagamento, Contrato ou Proposta ja
  existentes;
- retroatividade automatica sobre operacoes contratadas;
- tabela regulatoria externa, integracao com BACEN, PIX, boleto, banco ou
  provedor terceiro;
- precificacao comercial automatica, scoring, IA ou decisao de credito;
- simulacao financeira definitiva fora do Motor;
- workflow de aprovacao avancado para mudanca de parametro;
- frontend administrativo;
- Scheduler, Notification, broker externo, outbox completa ou BI avancado.

---

# 7. Fronteiras

| Contexto | Relacao com EPIC-009 | Regra de fronteira |
|---|---|---|
| Platform | Upstream transversal | fornece Tenant, Carteira e isolamento. |
| IAM | Upstream transversal | autentica usuario e autoriza gestao/consulta de configuracoes. |
| Configuracoes Financeiras | Contexto primario | define parametros validos, vigentes e versionados. |
| Comercial | Consumidor | consulta configuracoes para propostas e simulacoes, sem criar regra propria. |
| Contratos | Consumidor | congela snapshot contratual aprovado, sem recalcular. |
| Motor Financeiro | Consumidor protegido | interpreta parametros oficiais e executa calculos definitivos. |
| Operacao Diaria | Consumidor indireto | apenas exibe fatos do Motor e parametros de referencia quando necessario. |
| Relatorios | Consumidor indireto | pode reportar versao/origem da configuracao, sem reconstruir formula financeira. |

---

# 8. Modelo Candidato

## 8.1 Aggregate

- `PoliticaFinanceira`: raiz de configuracao versionada por tenant/carteira,
  modalidade, vigencia e estado.

## 8.2 Entities

- `ModalidadeEmprestimoConfigurada`;
- `RegraFinanceiraConfigurada`;
- `CalendarioFinanceiro`;
- `VersaoConfiguracaoFinanceira`;
- `EventoConfiguracaoFinanceira`.

## 8.3 Value Objects

- `TaxaConfigurada`;
- `ParametroFinanceiro`;
- `JanelaVigencia`;
- `CodigoModalidade`;
- `BasePeriodoFinanceiro`;
- `PoliticaArredondamentoConfigurada`.

## 8.4 Estados Candidatos

| Estado | Significado |
|---|---|
| `rascunho` | configuracao em preparo, nao consumivel por fluxos financeiros. |
| `ativa` | configuracao vigente e consumivel para novos snapshots. |
| `programada` | configuracao aprovada com inicio futuro. |
| `substituida` | configuracao encerrada por nova versao. |
| `inativa` | configuracao retirada sem novas emissoes. |

---

# 9. Decisoes de Discovery

## DA-901 - Configuracoes parametriza, Motor calcula

Configuracoes Financeiras define parametros validos, vigentes e versionados. O
Motor Financeiro interpreta esses parametros e continua sendo a unica autoridade
para calcular juros, mora, multa, amortizacao, saldo, quitacao e memoria de
calculo.

## DA-902 - Configuracao vigente vira snapshot imutavel

Quando uma proposta ou contrato usar uma configuracao financeira, o consumidor
deve persistir um snapshot com `configuracao_id`, `versao`, parametros
normalizados, vigencia usada, autoria e data de captura. Alteracoes futuras na
configuracao nao mudam snapshots ja emitidos.

## DA-903 - Vigencia e data de referencia sao obrigatorias

Toda consulta de configuracao financeira deve informar ou derivar uma
`data_referencia` explicita. O sistema nao escolhe silenciosamente uma taxa ou
calendario quando houver ambiguidade de vigencia.

## DA-904 - Request livre nao define regra financeira

APIs de Comercial, Contratos ou Motor nao devem aceitar regra financeira
arbitraria como fonte oficial. Elas podem receber referencia a configuracao
aprovada ou snapshot imutavel validado.

## DA-905 - Tenant e Carteira delimitam parametros

Toda configuracao pertence a um Tenant e pode ser especializada por Carteira.
Configuracao de outro Tenant ou Carteira inacessivel deve ser tratada como 404
logico na borda HTTP.

## DA-906 - Alteracao nao e retroativa por padrao

Nova taxa, modalidade, politica ou calendario afeta apenas snapshots futuros,
salvo decisao explicita de produto e plano tecnico proprio para migracao ou
reprocessamento historico.

## DA-907 - Calendario define periodo, nao resultado

Calendario Financeiro define regras de periodo, dias uteis/corridos,
feriados parametrizados e convencoes temporais. Ele nao calcula juros nem
classifica inadimplencia definitiva.

## DA-908 - Auditoria de configuracao e obrigatoria

Criacao, ativacao, substituicao e inativacao de configuracao financeira sao
acoes de negocio auditaveis, com usuario, motivo, timestamp, tenant, carteira
quando aplicavel e versao anterior/nova.

## DA-909 - Convivencia com snapshot contratual existente

O EPIC-009 deve preservar compatibilidade com os snapshots contratuais do MVP ja
usados pelo Motor. A migracao para referencia oficial de configuracao deve ser
aditiva e nao pode invalidar operacoes existentes.

## DA-910 - Guardrail anti-calculo em Configuracoes

O pacote deve incluir teste negativo para impedir formulas financeiras
definitivas dentro de modulos de Configuracoes. Validacoes de faixa, escala,
vigencia e enum sao permitidas; calculo de saldo, juros, mora, multa,
amortizacao, quitacao e memoria permanece proibido.

## DA-911 - Configuracoes Financeiras nasce como PRODUCT-009

Configuracoes Financeiras atende aos criterios de nova Capability em
FOUNDATION-009: possui linguagem propria, ciclo de vida proprio, ownership
funcional distinto de Operacoes de Credito e fronteira explicita com Platform.
Por isso, o Product do EPIC-009 foi materializado como `PRODUCT-009 -
Administrar Configuracoes Financeiras`, e nao como extensao de `PRODUCT-004` ou
`PRODUCT-001`.

---

# 10. Contratos de Integracao Candidatos

## 10.1 Configuracoes -> Comercial

Contrato minimo `ConfiguracaoFinanceiraVigenteV1`:

- `tenant_id`;
- `carteira_id` opcional;
- `configuracao_id`;
- `versao`;
- `modalidade`;
- `vigente_de`;
- `vigente_ate` opcional;
- `taxas_configuradas`;
- `politicas_permitidas`;
- `calendario_id`;
- `politica_arredondamento`;
- `consultada_em`;
- `origem`.

Comercial pode usar esse contrato para montar simulacao/proposta candidata, mas
nao pode alterar a regra recebida nem calcular resultado financeiro definitivo.

## 10.2 Configuracoes -> Contratos

Contrato minimo `SnapshotConfiguracaoContratualV1`:

- campos materiais de `ConfiguracaoFinanceiraVigenteV1`, exceto `consultada_em`;
- `proposta_id`;
- `contrato_id` quando existir;
- `capturado_em`;
- `capturado_por_usuario_id`;
- `motivo_captura`;
- `hash_parametros` para rastreabilidade;
- payload normalizado congelado.

Contratos congela o snapshot aprovado. Depois da liberacao logica, esse snapshot
entra no contrato que o Motor consome.

## 10.3 Contratos -> Motor Financeiro

Contrato minimo esperado no `ContratoLiberadoLogico` apos o EPIC-009:

- `configuracao_financeira_id`;
- `configuracao_financeira_versao`;
- `snapshot_configuracao`;
- `data_referencia_configuracao`;
- `parametros_financeiros_aprovados`;
- `calendario_financeiro`;
- `politica_arredondamento`;
- `origem_snapshot`.

O Motor recebe parametros congelados e decide o calculo. Configuracoes nao
chama o Motor para antecipar saldo ou memoria.

---

# 11. Fluxos Candidatos

## 11.1 Criar Configuracao Financeira

1. Usuario autorizado informa modalidade, taxas, calendario, vigencia e motivo.
2. Aplicacao valida tenant/carteira, formato, faixas permitidas e sobreposicao de
   vigencia.
3. Configuracao nasce como `rascunho`, ainda nao consumivel por fluxos
   financeiros.
4. Auditoria registra autoria e parametros normalizados.

## 11.2 Aprovar, Programar ou Ativar Nova Versao

1. Usuario autorizado aprova configuracao valida e define ativacao imediata ou
   inicio futuro.
2. Sistema impede duas configuracoes `ativa` ou `programada` conflitantes para a
   mesma combinacao tenant/carteira/modalidade/vigencia.
3. Configuracao aprovada com inicio futuro passa a `programada`; configuracao
   com inicio imediato passa a `ativa`.
4. Versao anterior pode ser marcada como `substituida` a partir da nova vigencia.
5. Snapshots antigos permanecem imutaveis.

## 11.3 Consultar Configuracao Vigente

1. Consumidor informa tenant, carteira, modalidade e data de referencia.
2. Sistema retorna exatamente uma configuracao vigente ou erro protegido.
3. Ambiguidade ou conflito de vigencia retorna `409`.
4. Ausencia de configuracao aplicavel retorna `404` logico.

## 11.4 Capturar Snapshot para Proposta/Contrato

1. Comercial ou Contratos solicita configuracao vigente.
2. Sistema devolve parametros normalizados e versao.
3. Consumidor persiste snapshot imutavel.
4. Mudancas futuras de configuracao nao alteram o snapshot capturado.

---

# 12. Plano Inicial de Testes

## 12.1 Dominio

- criar politica financeira valida;
- rejeitar taxa negativa, escala invalida, moeda incompativel ou vigencia
  incompleta;
- impedir sobreposicao de vigencias para a mesma modalidade e escopo;
- aprovar, programar e ativar configuracao em etapas separadas;
- substituir configuracao sem alterar snapshots existentes;
- consultar configuracao vigente por data de referencia;
- preservar imutabilidade da versao emitida.

## 12.2 Guardrails

- falhar se Configuracoes calcular juros, mora, multa, saldo, amortizacao,
  quitacao ou memoria de calculo;
- falhar se usar `float` em parametro monetario/percentual;
- permitir validacao de faixa, escala, enum, vigencia e calendario;
- garantir que requests de Comercial, Contratos e Motor nao aceitam regra
  financeira arbitraria como fonte oficial.

## 12.3 Aplicacao

- services exigem principal autenticado;
- comandos de escrita sao auditados e idempotentes quando expostos por API;
- consultas respeitam tenant/carteira;
- conflitos de vigencia retornam erro de dominio mapeavel para `409`;
- configuracao inexistente ou inacessivel retorna `None`/erro mapeavel para
  `404`.

## 12.4 Persistencia

- migrations aditivas para politicas, versoes, calendarios e eventos;
- constraints de unicidade por tenant/carteira/modalidade/vigencia;
- indices por tenant, carteira, modalidade, estado e vigencia;
- downgrade/upgrade reversivel;
- nenhum dado historico de contrato ou emprestimo alterado.

## 12.5 API/RBAC/OpenAPI

- permissoes especificas para administrar e consultar configuracoes financeiras;
- contratos HTTP `200/201/400/401/403/404/409`;
- endpoint de consulta vigente por data de referencia;
- endpoint de captura ou resposta de snapshot;
- testes cross-tenant;
- OpenAPI documentando schemas, erros e security.

## 12.6 Docs

- Product/EPIC/Features/User Stories consistentes;
- PLAN tecnico e execution backlog com suites antes do codigo;
- registry atualizado ao emitir PRODUCT, EPIC, FEATURE, US e PLAN;
- docs:validate e docs:test verdes.

---

# 13. Riscos

| Risco | Impacto | Mitigacao |
|---|---|---|
| Configuracoes virar Motor paralelo | divergencia financeira | DA-901 e guardrail anti-calculo. |
| Parametro retroativo acidental | contratos historicos mudam de sentido | snapshots imutaveis e DA-906. |
| Vigencias sobrepostas | consumidor escolhe taxa errada | constraint e consulta deterministica. |
| Ambiguidade Plataforma x Financeiras | escopo errado no Product | nomear como Configuracoes Financeiras e referenciar PRODUCT-001. |
| Payload livre em APIs | regra financeira sem governanca | referencia/snapshot obrigatorio. |
| Calendario calcular resultado | duplicacao de regra temporal | calendario define periodo; Motor calcula. |
| Falta de auditoria | mudanca de taxa sem rastreabilidade | auditoria obrigatoria por DA-908. |
| Quebra de operacoes existentes | regressao no Motor/Contratos | migracao aditiva e compatibilidade DA-909. |

---

# 14. Perguntas Abertas

- Quais modalidades entram no primeiro pacote implementavel: livre, prazo fixo,
  PRICE, SAC ou somente as ja usadas pelo Motor atual?
- Qual politica oficial de arredondamento monetario sera permitida no MVP?
- O calendario financeiro tera feriados nacionais/municipais parametrizados no
  MVP ou apenas dias corridos/dias uteis basicos?
- A ativacao de configuracao exige aprovacao dupla ou apenas usuario com
  permissao administrativa no MVP?
- Havera configuracao global por tenant com override por carteira?

---

# 15. Criterios de Pronto para PLAN

O EPIC-009 esta pronto para PLAN tecnico porque:

- `PRODUCT-009 - Administrar Configuracoes Financeiras` foi criado;
- EPIC formal, Features e User Stories foram materializados;
- escopo e fora do escopo deste discovery permanecem governados;
- fronteira "parametriza vs calcula" foi aceita como regra bloqueante;
- contratos candidatos com Comercial, Contratos e Motor foram preservados;
- perguntas de modalidade, arredondamento, calendario e aprovacao viram decisoes
  do PLAN tecnico, nao bloqueios para Product;
- backlog tecnico pode nascer com suites de dominio e guardrails antes de
  qualquer implementacao.

---

# 16. Recomendacao de Sequencia

1. Fazer revisao adversarial documental da camada Product materializada.
2. Criar o proximo PLAN tecnico sequencial e o respectivo execution backlog.
3. Implementar em macro-loop controlado somente apos Product/PLAN aprovados.

---

# 17. Parecer

O proximo EPIC recomendado e o EPIC-009 - Configuracoes Financeiras e Calendario
Operacional.

Ele deve vir antes de Scheduler/Notification porque reduz ambiguidade upstream
do Motor Financeiro e impede que novos fluxos operacionais dependam de
parametros livres. O pacote tambem prepara o backend para evoluir regras
financeiras com rastreabilidade, sem quebrar a autoridade do Motor nem alterar
operacoes ja contratadas.

---

# 18. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.1.0 | 2026-08-11 | Capability PRODUCT-009, EPIC formal, Features e User Stories materializados; discovery atualizado para pronto para PLAN tecnico. |
| 1.0.0 | 2026-08-11 | Discovery/SDD inicial do EPIC-009 - Configuracoes Financeiras e Calendario Operacional. |
