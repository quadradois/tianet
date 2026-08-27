# PLAN-033-EXEC - Copilot TiaNet

**ID:** PLAN-033-EXEC

**Versao:** 1.3.0

**Status:** Redesenhado - bloqueado pela pre-execucao

**Origem:** decisao do fundador em 2026-08-26 de dar forma ao segundo operador
previsto no `docs/foundation/FOUNDATION-001-product-vision.md`, sobre a base
recertificada do PLAN-032

**Base:** `origin/master` em `6fe7861` (merge do PR #27)

> **A execucao deste backlog deve seguir obrigatoriamente o
> AGENT-LOOP-EXECUTION-PROTOCOL (ALP-001), em
> `docs/governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md`.**

---

# 1. Veredito do redesenho

O PLAN-033 continua valido como direcao de produto, mas a versao 1.0.0 nao era
executavel com seguranca. Esta versao substitui premissas por trabalho explicito:

- pre-cadastro passa a ser um Aggregate novo; `Devedor` nao ganha estado pendente;
- proposta comercial sai do fluxo conversacional v1;
- submissao e decisao comercial passam a ter permissoes tecnicamente separadas;
- o Motor ganha uma leitura agregada por Devedor; o LLM nunca soma dinheiro;
- o resumo diario usa o snapshot da varredura, nao a fila persistida;
- o agente ganha inbox duravel, deduplicacao, dois contextos isolados, limites,
  auditoria propria e operacao de producao declarada;
- governanca, PII, Evolution, servidor e ponteiros documentais sao fechados antes
  da primeira mudanca de codigo.

O plano nao fixa prazo, headcount ou valor mensal do provedor de IA porque essas
restricoes ainda nao existem em fonte oficial. O teto mensal e uma decisao de
fundador que bloqueia a Fase C e sera registrado pelo IMP-358.

Pessoas e dados afetados: a Tia como operadora, o Credor como decisor, remetentes
desconhecidos em pre-cadastro, Devedores ja cadastrados, a carteira financeira e a
operacao que guarda chaves, monitora o agente e restaura o servico.

---

# 2. Estado real que condiciona o plano

Toda afirmacao desta secao foi conferida no arquivo indicado.

| Fato atual | Evidencia | Consequencia para este plano |
|---|---|---|
| `Devedor` so possui `ativo` e `inativo`, e nasce `ativo` | `src/emprestimo/domain/credit/devedor.py` | pre-cadastro nao pode reutilizar `Devedor`; IMP-357 cria Aggregate proprio |
| proposta nasce `rascunho` e exige `parametros` nao vazios | `src/emprestimo/domain/credit/proposta_comercial.py` | proposta sai do fluxo v1; a Tia continua a cria-la manualmente |
| enviar proposta para analise e aprovar usam `comercial.proposta.decidir` | `src/emprestimo/presentation/api/comercial_routes.py` e `src/emprestimo/application/iam_catalogo.py` | IMP-360 separa `submeter` de `decidir` antes de qualquer versao futura |
| a API lista emprestimos e consulta saldo por emprestimo, sem saldo agregado por Devedor | `src/emprestimo/presentation/api/motor_routes.py` | IMP-362 cria a leitura agregada no Motor |
| a varredura produz snapshot com `vence_hoje`; caso persistido nasce para item em atraso | `src/emprestimo/application/varredura_cobranca.py` | IMP-353 consome a mesma leitura da varredura, nunca `CobrancaCaso` como fonte de vencimento do dia |
| eventos de cadastro de Devedor nao carregam `usuario_id` em todos os detalhes | `src/emprestimo/application/cadastro_devedor.py` | IMP-361 faz o retrofit de autoria das escritas disparadas pelo copilot |
| `audit_log` nao tem coluna de ator; possui `detalhes` | `src/emprestimo/infrastructure/db/orm.py` | autoria entra em `detalhes`; nao se inventa coluna sem decisao de schema |
| `RegistroComunicacaoORM.devedor_id` e obrigatorio | `src/emprestimo/infrastructure/db/orm.py` | conversa e mensagem pertencem ao servico do agente, nao a `RegistroComunicacao` |
| Perfil e entidade por Tenant; o catalogo fechado contem permissoes, nao perfis | `src/emprestimo/domain/platform/perfil.py` e `src/emprestimo/application/iam_catalogo.py` | perfil `copilot` nasce por operacao administrativa idempotente por Tenant |
| `PreferenciaNotificacao` guarda estado, evidencia e origem por contato | `src/emprestimo/domain/credit/notifications.py` e `src/emprestimo/infrastructure/db/orm.py` | IMP-354 consulta a preferencia real antes de enfileirar WhatsApp |
| o lembrete por e-mail consulta a preferencia e nao envia quando ela nao permite | `src/emprestimo/application/notifications.py` | esse e o precedente de consentimento; o aviso de sobra nao e precedente |
| o aviso de sobra monta texto em codigo | `src/emprestimo/application/notifications.py` | os textos deterministas da Fase A seguem esse padrao e nao usam `TemplateNotificacao` |
| access token dura 15 minutos e refresh token dura 7 dias | `src/emprestimo/application/autenticacao.py` e `src/emprestimo/domain/platform/sessao.py` | IMP-356 implementa login, refresh, revogacao e recuperacao de sessao |
| `httpx` existe, mas nao ha cliente de LLM nem dependencia de provedor | `pyproject.toml` | IMP-356 usa a API compativel com OpenAI via `httpx` contra endpoint BYOK; sem SDK de provedor |
| o compose nao possui processo do agente e publica API apenas em loopback | `docker-compose.yml` | IMP-359 e IMP-356 incluem servico, ingress, reverse proxy e operacao |
| o adapter Evolution recebe um token de instancia por processo | `docker-compose.yml`, `.env.example` e `docs/operations/contexto-externo.md` secao 6.1 | v1 opera um Tenant por processo; multi-Tenant exige desenho de segredos fora deste ciclo |

---

# 3. Regras inviolaveis

1. **O copilot nunca calcula dinheiro.** Saldo agregado vem do IMP-362 e os
   demais valores vem do Motor. O agente repete campos tipados da API.
2. **O copilot nao pode aprovar proposta.** A garantia e tecnica: o IMP-360 cria
   `comercial.proposta.submeter`, mantem `comercial.proposta.decidir` separado e
   prova que o perfil `copilot` nao recebe `decidir`. Proposta esta fora do v1,
   mas o split bloqueia uma regressao futura.
3. **So o contexto Operadora acessa carteira.** Ele e aberto apenas para numero
   na allowlist e usa ferramentas GET explicitamente permitidas.
4. **Remetente desconhecido usa contexto Pre-cadastro separado.** Ele tem zero
   ferramentas de leitura de carteira. Depois de confirmar nome, documento e
   contato, pode chamar apenas a escrita idempotente de pre-cadastro pendente.
5. **Os contextos nunca compartilham sessao, historico, cache, tool-call ou
   resposta.** Uma resposta a remetente desconhecido nunca contem dado de
   terceiro, ainda que o prompt peca, simule autoridade ou cite um Devedor real.
6. **Escrita financeira por chat nao entra no v1.** Pagamento, estorno,
   renegociacao, contrato, emprestimo e decisao comercial nao sao ferramentas.
7. **Pre-cadastro nao e Devedor.** Devedor so nasce quando o Credor aprova, por
   `DevedorCadastroService`, e a aprovacao e idempotente.
8. **Toda escrita do copilot identifica o ator.** Seus eventos ADR-002 incluem
   `usuario_id` em `detalhes`. Leituras continuam fora da trilha ADR-002.
9. **Tool-calls tem trilha propria no agente.** Entrada, ferramenta, campos
   autorizados, resultado resumido, latencia e correlacao sao registrados com
   mascaramento da ADR-016, sem corpo integral, segredo ou PII desnecessaria.
10. **Falha do LLM e fechada.** Em indisponibilidade, timeout, limite de custo ou
    resposta invalida, o agente envia mensagem fixa de indisponibilidade; nunca
    inventa resposta e nunca troca automaticamente de provedor ou modelo.

---

# 4. Fase 0 - Pre-execucao obrigatoria

Nenhum item de codigo das Fases A-D comeca antes do GATE-E1.
Esta fase tambem fecha as decisoes externas.

### IMP-352 - Validar o formato real de envio do Evolution

- **Objetivo:** fechar o caveat 4.1 do handoff vigente. O contrato auditado em
  `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md` nao fixa o corpo e a resposta de
  `POST /send/text`; o adapter em
  `src/emprestimo/infrastructure/notifications/whatsapp.py` usa o formato ainda
  nao observado no servidor.
- **Execucao:** fazer um unico envio real para o numero do fundador, pois
  `docs/operations/contexto-externo.md` secao 6.2 registra que nao existe ambiente
  de teste. Capturar a resposta sem segredo e conferir o identificador aceito.
- **Dependencias externas:** numero do fundador, `EVOLUTION_HOST` e
  `EVOLUTION_INSTANCE_TOKEN` de producao.
- **Criterio de pronto:** formato observado incorporado ao contrato Evolution;
  classificador coberto por teste; sucesso, falha e resultado desconhecido
  continuam sem duplicacao.

### IMP-358 - Congelar governanca e decisoes abertas

- **Objetivo:** criar e aprovar os artefatos upstream exigidos antes de executar
  um backlog que introduz Aggregate, canal bidirecional, fornecedor de IA e PII.
- **Escopo obrigatorio:**
  1. revisar ADR-009 para admitir WhatsApp, envio e webhook, sem apagar a decisao
     historica de e-mail inicial;
  2. revisar pontualmente ADR-002 para registrar que leituras da API continuam
     nao auditadas e tool-calls pertencem ao log proprio do agente;
  3. abrir DR com o fundador para PII enviada ao provedor de IA: campos permitidos,
     minimizacao, mascaramento, retencao, exclusao, regiao, uso para treino,
     revisao humana e resposta a incidente;
  4. fixar na mesma DR o provedor/modelo BYOK aprovado e o teto mensal em moeda, com
     responsavel por alterar o teto;
  5. materializar e congelar Foundation/Product/Domain/Architecture necessarios
     para `PreCadastro`, agente e canal antes do primeiro IMP de codigo;
  6. reconciliar `docs/operations/contexto-externo.md` secao 2.1, que hoje manda
     registrar conversas em `RegistroComunicacao`, com o modelo proprio do agente;
  7. reconciliar o handoff vigente secao 4.1, que ainda trata o ambiente Evolution
     como pergunta, com `docs/operations/contexto-externo.md` secao 6, que responde
     que nao existe ambiente de teste;
  8. corrigir no ciclo de execucao os ponteiros vencidos de `CLAUDE.md`: ciclo
     PLAN-032, caminho antigo do ALP-001 e handoff de 2026-08-05;
  9. registrar que somente a Operadora recebe respostas com acesso a carteira;
     desconhecido recebe apenas o fluxo isolado de pre-cadastro;
  10. decidir retencao e descarte de inbox, sessao, mensagem e tool-call.
- **Condicao de parada:** se a DR proibir os campos necessarios ao provedor, a
  coleta vira formulario determinista ou para para novo desenho; PII nao segue
  para o fornecedor contra a decisao.
- **Criterio de pronto:** ADRs aceitas; DR decidida; artefatos upstream
  congelados; divergencias reconciliadas; GATE-E1 lista hashes e confirma o plano.

### IMP-359 - Fechar prontidao de producao e limite de tenancy

- **Objetivo:** substituir a premissa de servidor provisionado por evidencia
  operacional verificavel.
- **Checklist:** servidor endurecido; dominio e DNS; TLS; reverse proxy; rota
  publica somente para o ingress do agente; API e banco sem exposicao publica;
  backup automatico e restore do PostgreSQL; CD com rollback; healthcheck;
  restart; rotacao de segredos; logs, metricas, alertas e runbooks do provedor de IA e
  Evolution.
- **Segredos:** provisionar `LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`, credencial do
  usuario copilot, refresh token, `COPILOT_OPERATOR_ALLOWLIST`, `EVOLUTION_HOST`
  e `EVOLUTION_INSTANCE_TOKEN`. A allowlist inicial contem somente o numero da
  Tia. Nenhum segredo entra em log, banco generico, imagem ou Git.
- **Limite de tenancy:** `docs/operations/contexto-externo.md` secao 6.1 limita a
  uma instancia Evolution por processo. O v1 opera o primeiro Tenant. Um segundo
  Tenant exige processo isolado ou cofre de segredos com criptografia e rotacao;
  nao e ajuste de configuracao.
- **Divergencia tecnica registrada:** allowlist de numero nao autentica um JSON
  recebido por webhook sem assinatura. Quem descobrir a URL pode forjar
  `Info.Sender` com o numero da Tia. Antes de habilitar ferramentas da Operadora,
  o reverse proxy deve provar a origem por controle verificavel compativel com o
  Evolution, como allowlist de rede estavel confirmada em producao. Se isso nao
  for possivel, o contexto Operadora fica desabilitado e somente o contexto
  desconhecido, sem leitura de carteira, opera. A decisao do fundador por
  allowlist e mantida, mas nao e chamada de autenticacao criptografica.
- **Criterio de pronto:** checklist demonstrado em producao; restore e rollback
  ensaiados; processo ligado a uma unica instancia/Tenant; controle de origem ou
  bloqueio fail-closed do contexto Operadora provado.

---

# 5. Fase A - O sistema fala primeiro, sem IA

Nenhum item usa LLM. Textos sao montados por funcoes em codigo, seguindo
`montar_texto_aviso_sobra` de `src/emprestimo/application/notifications.py`.
`TemplateNotificacao` nao e usado: sua allowlist atual em
`src/emprestimo/domain/credit/notifications.py` aceita apenas os campos do
lembrete operacional por e-mail.

### IMP-353 - Resumo diario ao Credor a partir da varredura

- **Objetivo:** enviar ao `credor_whatsapp` os Devedores que vencem hoje com os
  valores devolvidos pelo Motor.
- **Fonte:** extrair e reutilizar a mesma leitura que hoje produz
  `VarreduraCobrancaResultado` e seus itens `vence_hoje` em
  `src/emprestimo/application/varredura_cobranca.py`. A fila persistida de
  `CobrancaCaso` nao e fonte do resumo.
- **Ordem obrigatoria:** o seed diario cria varredura antes de resumo, e o resumo
  da data so fica elegivel depois do sucesso da varredura da mesma data. Isso
  evita corrida e preserva quem vence hoje sem ainda estar em atraso.
- **Escopo real:** tipo e origem de job; snapshot datado; ordenacao determinista;
  handler e wiring no worker; saldos do Motor; texto em codigo; destino; envio
  Evolution; idempotencia por Tenant/data; resultado; retry/conciliacao;
  auditoria e observabilidade.
- **Criterio de pronto:** integracao semeia varredura e resumo, prova a
  dependencia, inclui `vence_hoje` sem `em_atraso`, observa um unico envio em
  replay e prova que nenhum valor foi calculado fora do Motor. Dia vazio nao envia.

### IMP-354 - Aviso de vespera ao Devedor com consentimento

- **Objetivo:** avisar no WhatsApp que o acerto ocorre amanha, usando
  `proximo_acerto_em` e valores do Motor.
- **Consentimento:** o seed localiza o contato WhatsApp preferencial e consulta
  `PreferenciaNotificacao` antes do job, pelo mesmo principio do caminho de
  e-mail em `src/emprestimo/application/notifications.py`. Ausencia, `opt_out`
  ou revogacao nao enviam e geram evento com codigo proprio, por exemplo
  `vespera_whatsapp_sem_consentimento`.
- **Correcao de precedente:** `enfileirar.ignorado` do aviso de sobra trata falta
  de `credor_whatsapp`; nao prova consentimento de Devedor e nao e precedente.
- **Escopo real:** data/timezone; snapshot de calendario; contato preferencial;
  preferencia/evidencia; texto em codigo; job; idempotencia por emprestimo/data;
  handler/wiring; Evolution; resultado; retry/conciliacao; auditoria e metricas.
- **Criterio de pronto:** testes cobrem vespera, outra data, consentido, ausente,
  opt-out, revogado, contato ausente, replay e retry. Sem `PERMITIDO`, nao ha envio.

---

# 6. Fase B - Identidade, RBAC e autoria

### IMP-355 - Provisionar usuario e perfil copilot por Tenant

- **Objetivo:** dar ao agente identidade propria, revogavel e minima, sem usar a
  identidade da Tia nem superusuario.
- **Estado atual:** `src/emprestimo/presentation/api/iam_routes.py` possui gestao
  de perfis e credenciais, mas nao rota de criacao de Usuario.
- **Escopo real:** servico e `POST /iam/usuarios`; `Idempotency-Key`; permissao
  administrativa nova; credencial na criacao; Tenant; estados/erros; auditoria;
  schemas; OpenAPI; snapshot, matriz e contadores; contrato, integracao,
  cross-tenant e replay.
- **Perfil:** operacao administrativa idempotente faz seed do perfil `copilot` em
  cada Tenant e o atribui ao Usuario. Nao existe perfil no catalogo:
  `src/emprestimo/application/iam_catalogo.py` cataloga permissoes e
  `src/emprestimo/domain/platform/perfil.py` modela Perfil por Tenant.
- **Permissoes v1:** somente GETs necessarios, `pre_cadastro.criar` e nenhum
  comando financeiro. `pre_cadastro.decidir`, `comercial.proposta.decidir`, IAM,
  configuracao, contrato, pagamento, estorno e renegociacao ficam ausentes.
- **JWT:** o seed nao gera token eterno. A credencial usa login normal; o ciclo
  operacional e implementado no IMP-356.
- **Criterio de pronto:** replay converge para um Usuario, Perfil e atribuicao;
  suite negativa prova 403 nas operacoes proibidas e 404 neutro cross-tenant;
  ator administrativo fica auditado.

### IMP-360 - Separar submeter de decidir proposta no RBAC

- **Objetivo:** tornar tecnica a separacao entre quem submete e quem decide.
- **Escopo:** adicionar `comercial.proposta.submeter` ao catalogo e migration;
  proteger `enviar-para-analise` com `submeter`; manter aprovar, recusar e
  cancelar com `comercial.proposta.decidir`; migrar perfis atuais sem perda;
  atualizar contrato, matriz e testes.
- **Futuro:** proposta esta fora do v1. Em versao futura, copilot pode receber
  `submeter`, mas nunca `decidir`.
- **Criterio de pronto:** somente submeter nao decide; somente decidir nao
  submete; ambas fazem ambos; nenhuma recebe 403. Copilot falha em aprovar por API.

### IMP-361 - Registrar autoria das escritas disparadas pelo copilot

- **Objetivo:** toda escrita do agente identifica o Usuario copilot em ADR-002.
- **Escopo:** retrofit de `DevedorCadastroService` em
  `src/emprestimo/application/cadastro_devedor.py` e novos fluxos de pre-cadastro
  para incluir `usuario_id` em `detalhes` de inicio, passos, sucesso, falha,
  rollback e replay; guardrail para futuras ferramentas de escrita.
- **Limite:** GETs continuam fora da ADR-002. Tool-calls usam o log proprio do
  agente no IMP-356, com retencao e mascaramento do IMP-358/ADR-016.
- **Criterio de pronto:** sucesso, falha, rollback e replay tem o mesmo
  `usuario_id` do Principal; PII, token, prompt e resposta integral nao aparecem.

---

# 7. Fase C - Copilot conversacional de leitura

### IMP-362 - Expor saldo agregado por Devedor calculado no Motor

- **Objetivo:** responder quanto o Devedor deve sem o LLM somar saldos de varios
  emprestimos.
- **Escopo:** caso de uso no Motor, query por Tenant/Carteira/Devedor, soma com a
  precisao e regras do Motor, DTO tipado, GET protegido por `motor.saldo.ler`,
  OpenAPI, snapshot, matriz e testes multi-emprestimo.
- **Contrato:** resposta traz valor total, referencia temporal e itens de origem;
  o total oficial e campo do backend. O agente nao deriva, arredonda ou completa.
- **Criterio de pronto:** dois emprestimos produzem o total do Motor; Devedor sem
  emprestimo tem semantica explicita; escopo divergente e neutro; o agente copia
  o total sem operacao aritmetica local.

### IMP-356 - Servico de conversa com contextos e ferramentas restritas

- **Objetivo:** responder a Operadora no WhatsApp com dados dos GETs da TiaNet e
  conduzir remetente desconhecido apenas pelo pre-cadastro isolado.
- **Topologia:** processo novo no mesmo repositorio e compose. Evolution chama o
  ingress publico do agente; o agente chama a TiaNet com Usuario copilot. A API
  TiaNet continua sem webhook publico, conforme
  `docs/operations/contexto-externo.md` secao 2.2.
- **Dependencias (BYOK, decisao do fundador em 2026-08-27):** o cliente traz a
  propria chave do provedor de IA. O agente fala a API compativel com OpenAI
  (chat completions + function calling) contra `LLM_BASE_URL` configuravel —
  isso cobre OpenRouter, NVIDIA NIM e os demais provedores compativeis com um
  unico cliente `httpx`, sem SDK. `LLM_API_KEY` por secret/env; `LLM_MODEL`,
  `LLM_TIMEOUT_SECONDS` e `LLM_MAX_RETRIES` aprovados no IMP-358; teto mensal duro;
  `httpx` ja existente; login/refresh do copilot; IMP-352, IMP-355, IMP-359,
  IMP-361 e IMP-362.
- **Degradacao:** indisponibilidade, timeout, resposta invalida ou teto atingido
  produz mensagem fixa. Nao ha resposta inventada, fallback de modelo ou provedor.

#### Entrega 356-A - Ingress duravel, classificacao e deduplicacao

- Endpoint valida envelope `Message`, identifica por `instanceId` e usa chave
  unica `(instanceId, data.Info.ID)`.
- O evento aceito entra em inbox persistente antes do `2xx`; processamento e
  assincrono. Replay responde `2xx` sem repetir LLM, ferramenta ou resposta.
- `IsFromMe`, grupo, evento nao suportado e mensagem sem ID sao descartados com
  motivo seguro. Numero na allowlist entra em Operadora; numero desconhecido,
  LID ou identidade nao resolvida entra em Pre-cadastro, nunca em Operadora.
- Chave de sessao inclui Tenant, instancia, classe e remetente normalizado. Nao
  existe promocao automatica nem memoria compartilhada entre contextos.
- **Criterio de pronto:** replay de `Info.ID`, duas instancias com o mesmo ID,
  crash depois do commit da inbox e crash depois do tool-call nao duplicam efeito
  nem resposta. Remetente nao autorizado nunca obtem contexto Operadora.

#### Entrega 356-B - Limites de payload e descarte de midia

- Definir `AGENT_WEBHOOK_MAX_BYTES` a partir da medicao do IMP-352, acima do maior
  `HistorySync` aceito. Testes usam o valor configurado, nao literal escondido.
- Somente texto e metadados minimos seguem para inbox e LLM. Base64, binarios,
  citacao com midia e campos nao usados sao descartados antes da persistencia.
  `HistorySync` e eventos nao conversacionais recebem `2xx` e descarte auditado,
  pois o Evolution repete inclusive `4xx` cinco vezes.
- **Criterio de pronto:** payload abaixo/acima do limite, midia e `HistorySync`
  grande nao derrubam o processo, nao entram no prompt e nao causam retry. Metricas
  contam bytes e descartes sem armazenar conteudo.

#### Entrega 356-C - Rate limiting e teto de custo

- Limites independentes por instancia, remetente e contexto, com teto global de
  concorrencia. Desconhecido tem quota menor e nao consome fila da Operadora.
- Antes de chamar o provedor, reservar custo estimado; depois, reconciliar uso.
  Ao atingir o teto mensal do IMP-358, bloquear chamadas e responder mensagem
  fixa. Alteracao do teto e administrativa e auditada.
- **Criterio de pronto:** rajada por remetente, distribuida, concorrencia, virada
  do periodo e teto atingido sao testados. Corrida nao ultrapassa o limite.

#### Entrega 356-D - Cliente LLM BYOK e tool-use restrito

- Cliente via `httpx` falando a API compativel com OpenAI contra `LLM_BASE_URL`,
  com modelo fixo, timeout e retry aprovados no IMP-358, validacao de schema e
  sem fallback. Trocar de provedor e trocar configuracao, nunca codigo — e a
  troca e decisao registrada, jamais automatica (regra inviolavel 10). Segredo
  nunca aparece em erro ou log. Function calling e requisito do provedor
  escolhido; provedor sem tool-use confiavel nao e elegivel.
- Operadora recebe allowlist nominal de GETs, incluindo saldo do IMP-362.
  Pre-cadastro recebe zero ferramentas de leitura de carteira e somente
  `pre_cadastro.criar` apos confirmacao explicita dos dados pelo remetente.
- Argumentos sao montados do contexto autenticado; o modelo nao escolhe Tenant,
  Carteira, Usuario, permissao ou URL. A saida e filtrada pelo schema permitido.
- Prompt, saida e tool result sao nao confiaveis. Instrucao do remetente nao
  altera allowlist, contexto, Tenant, politica ou confirmacao.
- **Criterio de pronto:** suite adversarial cobre remetente nao autorizado,
  pedido para ignorar regras, exfiltracao de outro Devedor/Tenant, URL arbitraria,
  ferramenta inexistente, escrita financeira, dinheiro sem tool-call e campo
  extra. Todos falham fechados.

#### Entrega 356-E - Egress pelo canal existente

- Reusar `EvolutionWhatsAppNotificationChannel` de
  `src/emprestimo/infrastructure/notifications/whatsapp.py`, com o formato do
  IMP-352. Nao criar segundo adapter.
- Resposta tem chave idempotente derivada da entrada e indice. Resultado
  desconhecido nao e reenviado automaticamente.
- Mensagem de indisponibilidade e texto fixo em codigo. Resposta a desconhecido
  passa por politica que proibe qualquer fato de carteira.
- **Criterio de pronto:** aceite, falha temporaria, permanente, desconhecido e
  replay sao cobertos; crash parcial nao duplica envio; token nao cruza Tenant.

#### Entrega 356-F - Sessao, JWT, auditoria propria e observabilidade

- Criar modelos proprios para sessao, mensagem, inbox e tool-call. `devedor_id`
  e opcional; `RegistroComunicacao` nao e usado.
- O agente faz login como copilot, guarda refresh em secret store, renova access
  antes dos 15 minutos, respeita refresh de 7 dias, trata revogacao/401 sem loop
  e nunca persiste token em mensagem ou log. Os prazos estao em
  `src/emprestimo/application/autenticacao.py` e
  `src/emprestimo/domain/platform/sessao.py`.
- Logs ADR-016 correlacionam inbox, sessao, provedor de IA, tool-call, TiaNet e egress.
  Documento, telefone, prompt, resposta, corpo de ferramenta, token e segredo
  sao mascarados ou omitidos conforme a DR do IMP-358.
- Metricas: idade/backlog da inbox, dedup, descarte, latencia, erro, tokens,
  custo reservado/real, rate limit, falha JWT, tool negada e egress.
- **Criterio de pronto:** GET nao cria `audit_log`; o log proprio reconstrui qual
  ferramenta/schema foi usado sem PII; testes cobrem refresh, revogacao, 401
  unico, mascaramento, retencao e correlacao.

#### Suite obrigatoria do IMP-356

A suite inclui: remetente nao autorizado; prompt injection; exfiltracao; dois
Tenants e dois Devedores; replay de `Info.ID`; payload grande; midia; crash
parcial antes/depois de efeitos; rate limit; teto de custo; indisponibilidade
do provedor; refresh/revogacao JWT; tentativa de aprovar proposta; escrita
financeira; auditoria propria e ausencia de PII/segredo em logs.

O IMP-356 exige as seis entregas verdes. Transcript feliz isolado nao certifica
o agente.

---

# 8. Fase D - Pre-cadastro conversacional

### IMP-357 - Criar Aggregate PreCadastro e aprovacao humana

- **Objetivo:** colher nome, documento e contato sem transformar o remetente em
  Devedor antes da decisao do Credor.
- **Dominio novo:** `PreCadastro` e Aggregate proprio com estados `pendente`,
  `aprovado` e `rejeitado`; Tenant, Carteira, dados, origem, autoria, timestamps,
  motivo de rejeicao e `devedor_id` final. Nao reutiliza estado de Devedor ou proposta.
- **Persistencia:** migration aditiva/reversivel; ORM; repository; porta no UoW;
  unicidade; concorrencia; idempotencia; auditoria com `usuario_id`.
- **Endpoints:** criar pendente; listar/consultar para o Credor; aprovar; rejeitar.
  Criacao exige `pre_cadastro.criar`; decisao exige `pre_cadastro.decidir`, ausente
  no perfil copilot. Escritas exigem `Idempotency-Key`; OpenAPI, snapshot, matriz
  e contadores seguem o rito vigente.
- **Aprovacao:** somente o Credor aprova. O orquestrador chama
  `DevedorCadastroService` com chave determinista ligada ao pre-cadastro,
  persiste o `devedor_id` e fecha como aprovado. Replay ou crash recupera o mesmo
  resultado e nunca cria segundo Devedor. Rejeicao nunca chama o cadastro.
- **Interface:** incluir fila para a Tia revisar dados, aprovar ou rejeitar. O
  agente nao decide pela interface nem por chat.
- **Proposta fora do v1:** aprovacao cria somente Devedor. Proposta continua
  manual da Tia, pois nasce `rascunho` e exige parametros que a conversa nao
  colhe, conforme `src/emprestimo/domain/credit/proposta_comercial.py`.
- **Confirmacao do remetente:** antes de `pre_cadastro.criar`, apresentar nome,
  documento mascarado e contato. Correcao exige nova confirmacao; silencio nao confirma.
- **Criterio de pronto:** jornada cobre conversa, confirmacao, pendente, revisao,
  aprovacao, um Devedor via `DevedorCadastroService`, dois atores e nenhuma
  proposta. Cobrir rejeicao, CPF invalido, duplicidade, replay, concorrencia,
  crash, cross-tenant e tentativa do copilot de decidir.

---

# 9. Resposta nominal aos cinco bloqueadores da revisao adversarial

| Bloqueador aceito | Resposta desta versao | Evidencia exigida |
|---|---|---|
| 1. RBAC nao separa submissao de aprovacao | IMP-360 cria `comercial.proposta.submeter`, preserva `decidir` e exclui proposta do v1 | quatro combinacoes e copilot com 403 ao aprovar |
| 2. Remetente humano nao e autenticado | IMP-356-A usa allowlist/separacao; IMP-359 registra que allowlist nao autentica webhook e exige prova de origem ou desabilita Operadora | remetente, spoof de envelope e ingress em producao |
| 3. Estado pendente nao existe em Devedor | IMP-357 cria `PreCadastro`, migration, endpoints e UI; Devedor nasce na aprovacao | jornada e crash/replay criando um Devedor |
| 4. GET-only nao impede exfiltracao | IMP-356 separa memoria, schema e ferramentas; desconhecido tem zero leitura de carteira | prompt injection, outro Devedor/Tenant e campo extra |
| 5. IMP-356 omitia durabilidade, dedup, limite, auditoria e operacao | IMP-356-A..F e IMP-359 criam entregas verificaveis | seis entregas, restore, metricas, replay e crash |

Nenhum bloqueador fecha por intencao textual. O Gate precisa observar o comportamento.

---

# 10. Fora do escopo, declarado

- proposta comercial pelo copilot no v1;
- pagamento, estorno, renegociacao, contrato ou emprestimo por chat;
- aprovacao de pre-cadastro ou decisao comercial por agente;
- Resend/e-mail; `docs/operations/contexto-externo.md` secao 2.3 registra que nao
  ha conta contratada e o canal real e WhatsApp;
- segundo Tenant no mesmo processo Evolution; exige desenho de segredos;
- audio, imagem, documento, OCR e download de midia;
- troca automatica de modelo ou provedor de IA;
- IMP-348, dispatcher de `EventPublisher`, sem consumidor neste plano;
- **memoria de longo prazo do agente** (preferencias da operadora, padroes por
  Devedor): o v1 tem memoria de sessao (Entrega 356-F, retencao na DR-005) e
  nada alem. Candidata a v2 sobre o modelo de sessao ja persistido;
- **RAG e base de conhecimento**: a fonte de conhecimento do copilot e a API
  viva, por tool-use — RAG sobre dado operacional serviria chunk potencialmente
  velho com confianca, exatamente o que "o Motor e a autoridade" impede. RAG so
  entra quando existir um corpus de politicas escritas da operacao, que hoje
  nao existe;
- **autonomia alem do reativo**: nenhum loop autonomo de planejar-agir-observar
  no v1. O agente responde mensagem; a proatividade e deterministica e sem LLM
  (Fase A). Autonomia nova cresce por fase com gate proprio, nunca por acumulo
  silencioso de capacidade.

---

# 11. Ordem, dependencias e Execution Gates

| Ordem | Fase | Item | Depende de |
|---|---|---|---|
| 1 | 0 | IMP-352 | acesso Evolution e numero do fundador |
| 2 | 0 | IMP-358 | revisao aceita e decisoes do fundador |
| 3 | 0 | IMP-359 | IMP-352, IMP-358 e servidor contratado |
| 4 | A | IMP-353 | IMP-352 e GATE-E1 |
| 5 | A | IMP-354 | IMP-352 e GATE-E1 |
| 6 | B | IMP-355 | GATE-E1 |
| 7 | B | IMP-360 | GATE-E1 |
| 8 | B | IMP-361 | IMP-355 |
| 9 | C | IMP-362 | GATE-E2 |
| 10 | C | IMP-356 | IMP-352, IMP-355, IMP-359, IMP-361, IMP-362 |
| 11 | D | IMP-357 | IMP-356 e permissoes do IMP-355 |

Execution Gates conforme ALP-001:

| Gate | IMPs | Justificativa | Condicao para seguir |
|---|---|---|---|
| GATE-E1 | IMP-352, IMP-358, IMP-359 | bloco curto de pre-execucao | ADRs/DR congeladas, Evolution observado e producao pronta |
| GATE-E2 | IMP-353, IMP-354, IMP-355, IMP-360, IMP-361 | cinco IMPs de fala deterministica, identidade e conformidade | Fase A/B, contrato e RBAC verdes |
| GATE-E3 | IMP-362, IMP-356 | bloco curto porque IMP-356 contem seis entregas | seis entregas, suite adversarial e operacao verdes |
| GATE-E4 | IMP-357 | gate final isolado pelo novo Aggregate | dominio, migration, API, UI e jornada verdes |

Todo Gate responde: IMPs executadas, testes, cobertura, qualidade, pendencias,
riscos, plano continua valido e pode seguir. Nova ADR, Foundation, Capability,
Bounded Context, decisao irreversivel ou conflito oficial para e escala conforme
ALP-001.

---

# 12. Criterios finais de aprovacao do PLAN-033

O plano so fecha quando:

1. GATE-E1 a GATE-E4 estao aprovados e encadeados;
2. os cinco bloqueadores da secao 9 possuem evidencia observada;
3. OpenAPI, snapshot, matriz e contadores estao reconciliados;
4. migrations fazem upgrade, downgrade e novo upgrade em PostgreSQL real;
5. suites unitarias, integracao, contrato, seguranca e stack real estao verdes;
6. prompt injection, exfiltracao, replay, payload grande e crash falham fechados;
7. custo, PII, retencao e operacao possuem responsavel e runbook;
8. arvore final nao contem segredo, PII real ou evidencia gerada solta.

---

# 13. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.3.0 | 2026-08-27 | Escopo negativo ampliado a pedido do fundador: memoria de longo prazo, RAG/base de conhecimento e autonomia alem do reativo declarados fora do v1, cada um com o porque e o gatilho de entrada futura. |
| 1.2.0 | 2026-08-27 | BYOK por decisao do fundador: o cliente nao usa Anthropic; o agente fala a API compativel com OpenAI contra endpoint configuravel (OpenRouter, NVIDIA NIM e similares), com LLM_BASE_URL/LLM_API_KEY/LLM_MODEL. Nenhuma outra mudanca de desenho. |
| 1.1.0 | 2026-08-27 | Reescrita integral apos a revisao adversarial do PLAN-033, aceita pelo fundador: corrige dominio/RBAC, cria PreCadastro, retira proposta do v1, decompoe o agente, ancora seguranca/operacao e adiciona pre-execucao por ALP-001. |
| 1.0.0 | 2026-08-26 | Desenho inicial: quatro fases sobre os ativos do PLAN-032, IMP-347 absorvido pela Fase A, regras inviolaveis herdadas do ciclo e escopo negativo declarado. |
