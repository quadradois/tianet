# Contexto Externo

**Versao:** 1.9.0

**Status:** Vivo — mantido manualmente

---

# 1. Para que serve

Este documento registra o que existe **fora do repositorio** e que decisoes
tecnicas dependem: servicos contratados, integracoes de outros projetos,
infraestrutura, e decisoes tomadas em conversa que nunca viraram codigo.

Nenhuma analise de codigo descobre o que esta aqui. Sem este registro, uma
sessao nova conclui corretamente "isto nao existe no repositorio" e propoe
construir algo que a operacao ja tem.

**Regra de leitura:** antes de propor construir qualquer integracao, servico ou
infraestrutura, leia este documento. Se o assunto nao estiver aqui, pergunte
antes de assumir que nao existe.

**Regra de escrita:** quando algo for contratado, integrado ou decidido fora do
codigo, registre aqui na mesma hora. Um item errado e pior que um item ausente.

---

# 2. Integracoes disponiveis

## 2.1 API de WhatsApp — Evolution Go

**Contrato oficial:** `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`. Fonte da verdade,
auditada contra o codigo em producao. Leia antes de integrar qualquer coisa.

| Campo | Valor |
|---|---|
| Situacao | **Pronta e em uso em outros projetos do time** |
| Provedor | Evolution Go auto-hospedado, `https://diamondgreen.com.br` |
| Modelo | um tenant Evolution por Tenant da TiaNet |
| Autenticacao | tres niveis: Global (`/tenant/*`), Tenant (`/instance/*` de gestao), Instancia (envio e conexao) |
| Retry de webhook | 5 tentativas, 30s de intervalo, depois descarta — **nao existe replay** |
| Tamanho de payload | midia vem em base64; `HistorySync` ja foi observado com 5,6MB |
| Ambiente de teste | **Nao existe** — respondido em 2026-08-25. Validacoes controladas usam producao com o numero do fundador; ver §6.2 |

### Estado real do tenant `tianet` no provedor (lido em 2026-09-02)

Leitura ao vivo de `/instance/all` e `/instance/info/:id` com a chave de Tenant,
durante o IMP-368. **Uma unica instancia existe:**

| Campo | Valor |
|---|---|
| `name` | `adm_tianet` |
| `id` | `8a8c901f-16f9-4431-b19d-ed69cccc46c0` |
| Criada em | 2026-08-31 |
| `connected` | `false` — `disconnect_reason: "401: logged out from another device"` |
| `jid` | preenchido (`5562...`) **mesmo desconectada** |
| `webhook` | vazio |

O que cada linha ensina, e nao estava escrito em lugar nenhum:

- **A instancia e artefato de teste nosso.** O fundador confirmou em 2026-09-02
  que ela nasceu dos testes de comunicacao, nao de uma configuracao manual
  anterior ao sistema. O IMP-367 tinha registrado a premissa contraria no
  proprio codigo, e ela era falsa.
- **Apagar do celular NAO apaga a instancia.** Desparear pelo aparelho produz o
  `disconnect_reason` acima e a instancia continua existindo no provedor. So
  `DELETE /instance/delete/:id` a remove — e ate o IMP-368 nenhum codigo nosso
  chamava essa rota. E o motivo de a exclusao ter virado operacao propria.
- **O `jid` sobrevive a desconexao.** Ler o telefone do `jid` sem cruzar com
  `connected` mostraria "conectado no 6284290661" numa conexao caida.
- **O `webhook` vazio e proposital**, nao pendencia: a DR-006 apontou o webhook
  para o agente (§2.2), e mandar a URL da TiaNet roubaria os eventos dele.
- **`/instance/info` com id inexistente responde `500` com
  `{"error":"record not found"}`** — o status mente, o corpo nao. E por isso que
  o adapter trata a ausencia pelo texto do corpo, e nao pelo `500`.

**Consequencia operacional pendente:** a partir do IMP-368 a plataforma nomeia
as instancias como `tianet_{tenant_id}`, entao ela **nao vai adotar** a
`adm_tianet`. Essa instancia deve ser apagada (pela operacao nova, ou a mao no
diamondgreen) antes do primeiro `conectar` valer como definitivo — senao ela
fica para sempre como sessao morta, que e exatamente o acumulo que o fundador
pediu para evitar.

### Custodia da `WHATSAPP_TOKEN_ENCRYPTION_KEY` (decidido em 2026-09-02)

**Onde mora:** o mesmo canal de `docs/credenciais/`, fora do git, entregue por
canal direto — ao lado do `evolution_api_key`. Sem cofre proprio, sem rotina de
rotacao. **Este documento nao carrega o valor**, so o lugar e o porque.

**Estado hoje:** a chave **nao existe** em lugar nenhum, nem no `.env` de
desenvolvimento. Ela nasce no IMP-359, com o provisionamento do VPS.

**Por que a protecao e proporcional, e nao maior.** Ela e a primeira chave
*decodificadora* do sistema — as outras sao substituiveis (`POSTGRES_PASSWORD`
se redefine, `JWT_SECRET_KEY` perdido so obriga todo mundo a logar de novo, e o
Evolution reemite a chave de Tenant por `/tenant/apikey/:id`). Isso legitima a
pergunta pelo backup, e ela foi feita.

Mas o que ela decodifica **tem segunda fonte**: `GET /instance/all`, com a chave
de Tenant, devolve o mesmo token da instancia em texto claro — verificado ao
vivo em 2026-09-02. Disso decorre a decisao: **a chave de cifra e estritamente
menos poderosa que a `EVOLUTION_API_KEY`**, que ja vive naquele canal. Quem tem
a segunda le o token direto do provedor sem precisar da primeira. Guardar a mais
fraca com mais cerimonia que a mais forte seria teatro.

O handoff de 2026-09-02 §5.1 registrava que perder a chave tornaria "todo token
persistido irrecuperavel". **Esta secao corrige isso**: e recuperavel, e sem QR
novo — a adocao por nome derivado (IMP-368) reencontra a instancia e regrava o
token.

**Custo real de perder a chave:** apagar a linha de `conexao_whatsapp` e chamar
`conectar`. Hoje esse apagar e **manual**, porque a unica operacao que remove o
registro local (`DELETE /platform/whatsapp/conexao/instancia`) apaga a instancia
no provedor junto — e ai o QR volta a ser necessario sem precisar. Uma operacao
que solte apenas o vinculo local esta anotada como candidata para depois do
deploy; ate la, o caminho e um `DELETE` no banco.

### Recorte para a TiaNet

O contrato descreve um CRM com clientes e corretores. Na TiaNet, `cliente` mapeia
para **Tenant**; **corretor nao existe** — o Credor opera sozinho
(`FOUNDATION-001 §3`). Portanto os Eventos 3 e 5 do contrato ficam fora de
escopo, e o Evento 6 corresponde a inativacao de Tenant ja existente.

### Achados que condicionam o desenho

- **O webhook nao tem autenticacao**: a URL e o unico segredo. Por isso o
  recebimento so pode criar um pre-cadastro pendente, nunca lancar financeiro —
  quem descobrisse a URL emitiria divida no sistema.
- **`consultar_status` da porta `NotificationChannel` nao tem endpoint
  correspondente**: o status chega por webhook (`Receipt`), nao por consulta. O
  adapter precisara ler recibos armazenados, ou a porta muda.
- **Conexao e pre-requisito das duas direcoes**: nao se envia nada sem instancia
  conectada, o que exige criar tenant, criar instancia e escanear o QR.
- **O formato de `POST /send/text` foi VALIDADO em 2026-08-31** (IMP-352). O
  contrato nao o descrevia, e o adapter usava `{number, text, id}` com aceite por
  `data.Info.ID` extrapolados da documentacao publica. **Nao divergia.** Corpo e
  resposta observados foram incorporados a secao 8.1 de
  `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`.

  O que a resposta real ensinou, e nao estava em lugar nenhum: **`data.Info.ID` e
  eco** do `id` que enviamos, nao identificador gerado pelo servidor.

  Isso **correlaciona** requisicao e resposta, e nao mais que isso: nao foi
  medido se o provedor suprime uma segunda mensagem com o mesmo `id`, entao um
  retry apos timeout, reset ou 5xx pode entregar duas vezes (§6.2). E **nao
  existe id do provedor**
  para consultar depois — entrega so se confirma por `Receipt`, que e o que
  `consultar_status` ja declarava.

Consequencias ja incorporadas ao desenho:

- o envio de comprovante **nao** usa link `wa.me`; vai pela API;
- o adapter entra como implementacao de `NotificationChannel`
  (`src/emprestimo/domain/credit/automacao_ports.py`), ao lado do Resend;
- as conversas conduzidas pelo agente **nao** usam `RegistroComunicacao`
  (corrigido em 2026-08-27 pelo PLAN-033/IMP-358): `devedor_id` e obrigatorio
  naquela tabela, e uma conversa de pre-cadastro ainda nao tem Devedor. O agente
  tera modelo proprio de sessao e mensagem, com `devedor_id` opcional.
  `RegistroComunicacao` continua registrando comunicacoes ligadas a um Devedor
  existente, como o comprovante e o aviso de sobra ja fazem;
- `CanalComunicacao` **ja possui** o valor `whatsapp`, formalizado pela migration
  `0018` em 2026-08-20.

## 2.2 Agente de IA "TiaNet"

Atende pedidos que chegam pelo WhatsApp, registra o pre-cadastro e submete ao
Credor para aprovacao. E o segundo operador do sistema, conforme
`FOUNDATION-001 §3.1`.

| Campo | Valor |
|---|---|
| Situacao | desenhado — PLAN-033 v1.1.0 |
| Entra antes ou depois do wizard de emprestimo | *a preencher* |
| Topologia de recepcao | **Evolution -> agente -> endpoint autenticado da TiaNet** (decidido em 2026-08-25) |
| Contextos de conversa | **dois, isolados** (registrado em 2026-08-27): Operadora (allowlist de numeros, comeca so com o da Tia, unico com leitura de carteira) e Pre-cadastro (remetente desconhecido, zero acesso a dados). Nunca compartilham sessao, historico ou ferramenta. |
| Autenticacao do remetente | allowlist de numero **nao e autenticacao**: `Info.Sender` e forjavel por quem tiver a URL do webhook. O contexto Operadora so liga com prova de origem no reverse proxy; sem prova, fica desabilitado fail-closed (PLAN-033/IMP-359). |

**A TiaNet nao tera webhook publico.** A decisao foi pela topologia (b): o
agente recebe do Evolution e chama um endpoint autenticado da TiaNet, no mesmo
padrao de autenticacao que o resto do sistema ja usa.

O que isso evita, e por isso importa: a alternativa (a) exigiria uma rota **nao
autenticada aberta para a internet**, mais validacao de assinatura do Evolution,
mais uma peca para manter e mais superficie exposta. Nada disso e necessario
quando o agente ja e um cliente autenticado.

## 2.3 Resend (e-mail)

**E-mail esta fora do escopo do MVP.** Decisao do fundador em 2026-08-25: nao ha
conta Resend contratada, e o canal real da operacao e o WhatsApp.

| Campo | Valor |
|---|---|
| Conta contratada | **nao** |
| Dominio remetente verificado | nao se aplica |

`ResendNotificationChannel` continua no codigo, atras da porta
`NotificationChannel`. Se `RESEND_API_KEY` e `RESEND_FROM` existirem, ele e
usado; nada foi removido.

**O que mudou:** `APP_ENV=production` sem essas variaveis derrubava o worker na
subida. Isso bloqueava o deploy inteiro por causa de um canal que a operacao nao
usa. Agora o worker sobe.

**O que nao mudou, de proposito:** o canal ausente **nao** vira
`FakeNotificationChannel`. Aquele fake devolve `ACEITA` com um
`provider_message_id` sintetico — em teste e util, em producao seria mentira: a
trilha registraria como entregue um e-mail que nunca saiu. Em vez disso entra o
`CanalNaoConfiguradoNotificationChannel`, que recusa com
`FALHA_PERMANENTE` e codigo `canal_nao_configurado:email`. Terminal, porque
retry nao configura credencial, e **nomeado**, porque o operador precisa ver o
motivo na trilha.

## 2.4 Mercado Pago — recebimento do acerto

**Decidido em 2026-09-03, sem desenho ainda.** Registrado aqui na primeira
mencao, antes de existir codigo, porque este documento so evita o erro que ele
descreve se for escrito na hora da decisao — nao depois.

| Campo | Valor |
|---|---|
| Situacao | **decidida a existencia; sem DR, sem ADR, sem codigo** |
| Fluxo do dinheiro | **Devedor paga o Credor** — quitacao do acerto mensal |
| Nao e | cobranca de assinatura do SaaS; a TiaNet nao cobra o Tenant por aqui |
| Conta / credencial | *a preencher* — nao verificado |
| Posicao na fila | **depois do IMP-359 (deploy)**, decidido pelo fundador |
| Toca | Motor Financeiro e a trilha ADR-002 — nao e integracao periferica |

**Por que vem depois do deploy, e nao e so preferencia:** notificacao de
pagamento do Mercado Pago precisa de um HTTPS publico e estavel para entregar.
Sem o IMP-359 feito nao existe esse endereco, entao integrar antes seria
construir contra um destino que ainda nao tem TLS nem dominio apontado.

### As duas colisoes com decisoes ja tomadas

Nenhuma das duas e impeditiva; as duas exigem decisao explicita antes do
desenho, e por isso estao escritas aqui e nao descobertas no meio da execucao.

1. **A TiaNet decidiu nao ter webhook publico** (§2.2), e o checklist do IMP-359
   diz *"rota publica somente para o ingress do agente; API e banco sem
   exposicao publica"*. Receber notificacao do Mercado Pago exige exatamente uma
   rota publica. Ou a decisao da §2.2 se abre para um segundo caso, ou o
   recebimento vira **polling** da API do provedor. **A diferenca em relacao ao
   Evolution e real e favorece o Mercado Pago:** o webhook do Evolution nao tem
   autenticacao nenhuma — a URL e o unico segredo —, enquanto o Mercado Pago
   assina a notificacao (`x-signature`), o que permite provar origem sem confiar
   no sigilo da URL. O argumento que fechou a §2.2 nao se transporta inteiro.
2. **A DR-004 acabou com o plano de parcelas.** O emprestimo e livre, com acerto
   mensal no dia combinado, e o valor devido so existe depois de o Motor
   calcular o trecho. Nao ha "parcela 3" para emitir com antecedencia: qualquer
   cobranca gerada e **do acerto apurado**, com validade curta, ou de valor
   aberto. Isso muda o que o desenho pode prometer.

**Ainda nao perguntado, e precisa ser antes da DR:** se o recebimento e por PIX,
link de pagamento ou os dois; se o Credor ja tem conta Mercado Pago com as
credenciais de producao; e o que acontece quando o devedor paga valor diferente
do apurado — que hoje o dominio ja trata como sobra, mas por lancamento manual.

---

---

# 3. Infraestrutura

## 3.1 Ambiente local

Documentado em `docs/operations/ambiente-local-docker.md`. Stack completa em
Docker, validada ponta a ponta.

## 3.2 Servidor de producao

| Campo | Valor |
|---|---|
| Situacao | **VPS provisionada em 2026-08-31.** Sem deploy ainda |
| Tipo | VPS |
| Dominio | `tianet.com.br` — ativo |
| TLS | *pendente* |
| Backup do PostgreSQL | *pendente* |
| CD e endurecimento | *pendentes* |

O insumo de **servidor** que bloqueava o **IMP-359** deixou de existir: a maquina
e o dominio estao disponiveis. Falta trabalho nosso — deploy, TLS, backup, CD e
endurecimento —, e a sequencia acordada com o fundador poe isso **depois** do
PLAN-034.

**O insumo de IA deixou de bloquear (respondido pelo fundador em 2026-09-03).**
O provedor BYOK da DR-005 **foi escolhido com o cliente e a chave existe**. Com
isso o IMP-359 fecha inteiro como esta escrito, sem precisar ser fatiado.

*Pendente de registro nesta tabela:* o **nome do provedor** e o **modelo**
(`LLM_BASE_URL` e `LLM_MODEL`). Ficam em branco de proposito ate serem
confirmados — este documento prefere lacuna a item errado. A `LLM_API_KEY` nao
entra aqui nem no git: vai pelo canal de `docs/credenciais/`, ao lado do
`evolution_api_key` e da `WHATSAPP_TOKEN_ENCRYPTION_KEY`.

**Nenhum insumo externo bloqueia mais o IMP-359.** O que falta e trabalho nosso.

Nao existe pipeline de CD no repositorio: `.github/workflows/quality.yml` e o
unico workflow e cobre apenas gates de qualidade.

---

# 4. Clientes e tenants

| Nome | Situacao |
|---|---|
| Ivonet | primeiro Tenant previsto; recebera a integracao de WhatsApp |

---

# 5. Ferramentas de apoio

## 5.1 Grafo de conhecimento (graphify)

`graphify-out/` e ignorado pelo git e vive apenas no disco de quem o gera.

**Estado em 2026-09-03:** construido em 2026-08-21 e atualizado em 2026-09-03 —
**10.768 nos, 25.809 arestas, 575 comunidades, 1.118 arquivos**. Cobre backend,
frontend, testes **e documentos**. Diretorios gerados (`playwright-report`,
`test-results`, `.next`) sao excluidos — sem isso, cerca de 1.200 nos de bundle
minificado poluem o grafo.

**A consulta ao grafo antes de alteracao arquitetural virou governanca:**
[SPEC-003](../governance/SPEC-003-pesquisa-no-grafo-antes-de-alteracao-arquitetural.md).
Ela define quando o gate dispara, exige verificar frescor antes de consultar, e
declara os limites abaixo como normativos.

**O grafo agora cobre documentos.** A extracao semantica foi executada em
2026-09-03 sobre 50 documentos e 4 imagens (handoffs, ADRs, DRs, PLANs,
FOUNDATION, o contrato Evolution e este arquivo), com 54 de 54 arquivos
gravados no cache — nenhum fragmento perdido. Consultas cruzam documento e
codigo na mesma resposta.

**O que ele continua nao cobrindo: o que esta fora do repositorio.** Servidor,
provedor, instancia, conta, cliente — a fonte e este arquivo, e o que ele nao
cobre so o fundador sabe. *"Nao achei no grafo"* significa *"nao existe no
codigo e nos documentos indexados"*, nunca *"nao existe"*.

**Correcao de tres erros que esta secao carregava ate a v1.8.0**, todos
verificados contra o disco em 2026-09-03: a data era 2026-08-21 e nao
2026-08-16; a contagem era 9.466 nos e nao 8.267; e o manifesto incremental
**existe** (`manifest.json`), de modo que `--update` re-extrai so o que mudou em
vez de reconstruir tudo. O terceiro erro era o mais caro: ele desencorajava a
atualizacao incremental, e o grafo passou treze dias parado.

---

# 6. Perguntas respondidas em 2026-08-25

As cinco perguntas que estavam abertas foram respondidas pelo fundador. Ficam
registradas com a resposta, para que ninguem as reabra como se fossem duvida.

| # | Pergunta | Resposta |
|---|---|---|
| 1 | Onde o agente recebe a mensagem? | **(b)** Evolution -> agente -> endpoint autenticado da TiaNet. Sem webhook publico. Ver §2.2. |
| 2 | Onde ficam `evolution_tenant_id` e `evolution_api_key`? | **Variavel de ambiente**, como ja e hoje (`EVOLUTION_INSTANCE_TOKEN`). Ver abaixo. |
| 3 | Ha ambiente de teste do Evolution? | **Nao.** A validacao sera em producao, com o numero do proprio fundador. Ver abaixo. |
| 4 | Ha conta Resend ativa? | **Nao.** E-mail fora do escopo do MVP. Ver §2.3. |
| 5 | Qual servidor recebe o deploy? | **VPS provisionada e dominio `tianet.com.br` ativo** desde 2026-08-31. Faltam deploy, TLS, backup, CD e endurecimento. Ver §3.2. |

## 6.1 Segredo do Evolution: variavel de ambiente

> **Superado em parte pela [DR-006](../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md)
> (2026-08-31).** O fundador decidiu que a conexao do WhatsApp passa a ter **tela
> de QR na plataforma**, porque quem opera nao tem conta no `diamondgreen.com.br`.
> Com isso o **token da instancia** passa a ser persistido **cifrado em repouso**
> no banco — sem isso a conexao nao sobrevive a um restart sem edicao manual do
> `.env`, que e o atrito que a tela elimina.
>
> O que **permanece** desta secao: `EVOLUTION_HOST` e as credenciais de **gestao**
> do tenant Evolution continuam em variavel de ambiente; a recusa de usar a
> entidade `Configuracao` continua valida, e pelo mesmo motivo — a DR-006 escolheu
> armazenamento cifrado justamente para nao repetir esse erro.
>
> O "limite declarado" abaixo previa que isso viraria tabela de segredos com
> criptografia quando cada Tenant tivesse instancia propria. A
> [ADR-003](../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md) decidiu que
> **nao havera segundo Tenant no v1** — a tabela chegou por outro caminho, o da
> ergonomia da conexao, e guarda um unico token.


O adapter ja recebe host e token por injecao, e `main()` os le de
`EVOLUTION_HOST` e `EVOLUTION_INSTANCE_TOKEN`. **Nada muda no codigo.**

Por que nao a entidade `Configuracao`: e tabela generica chave/valor, sem
criptografia em repouso, e exposta por endpoints de configuracao — o segredo
vazaria por leitura legitima, que e o pior tipo de vazamento porque nao parece
incidente.

**Limite declarado:** variavel de ambiente e uma instancia por processo. Serve
enquanto ha um credor e um Tenant. **No dia em que cada Tenant tiver instancia
propria do Evolution**, isso vira tabela de segredos com criptografia e
rotacao — escopo real, nao ajuste. Registrar agora evita descobrir no meio da
migracao.

## 6.2 Validacao do formato de envio: producao, com o numero do fundador

> **VALIDADO em 2026-08-31.** Envio real executado pela propria classe de
> producao (`EvolutionWhatsAppNotificationChannel`), para o numero do fundador,
> na instancia `adm_tianet`. Resultado: `ACEITA` / `accepted`.
>
> **O formato nao divergia.** `data.Info.ID` e o criterio correto — e a resposta
> revelou que ele e **eco do `id` enviado**, nao identificador gerado pelo
> servidor. O corpo e a resposta observados foram incorporados ao contrato, na
> secao 8.1 de `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`, que ate entao listava
> a rota sem fixar seu formato.
>
> Consequencia registrada: como o identificador e nosso, ele **correlaciona**
> requisicao e resposta. Nao foi medido se o provedor suprime uma segunda
> mensagem com o mesmo `id`, entao correlacionar nao e deduplicar. E **nao ha
> identificador do provedor** para consultar depois — entrega so se confirma por
> `Receipt`, o que o adapter ja declarava em `consultar_status`.

Nao ha ambiente de teste do Evolution — a validacao acima foi feita em producao,
para o numero do proprio fundador, sem que nenhum devedor real recebesse
mensagem. Esse continua sendo o unico caminho para conferencias futuras.

**O que ficou aberto, e foi corrigido em 2026-09-02.** A validacao
respondeu o formato, nao a deduplicacao. Mas a politica para esse caso **ja esta
decidida** na ADR-009: retry so quando ha **prova** de que o provedor nao
aceitou; na duvida — a ADR cita "timeout ou reset depois do envio de bytes" como
exemplo, nao como limite —, vale `resultado_desconhecido`, que **bloqueia retry
e concilia**.

Eram **tres pontos** no adapter, e os tres levavam a mesma consequencia
concreta:
o Scheduler reenvia sem prova de que o primeiro envio nao foi aceito. Se o
provedor nao deduplicar pelo `id` — nao medido —, o destinatario recebe duas
vezes. Hoje o adapter do WhatsApp esta ligado ao **comprovante do lancamento** do
emprestimo e ao **aviso de sobra de pagamento** (`enviar_lembrete` usa o canal de
e-mail), entao sao esses dois — dois comprovantes do mesmo emprestimo sugerem
dois emprestimos. Quando o lembrete migrar para o WhatsApp, alcanca cobranca.

- **Resposta 5xx** (`_classificar_resposta`, codigo `provider_5xx`) — a tabela
  da ADR nomeia `5xx` como o primeiro item de `resultado_desconhecido`; o adapter
  devolve `FALHA_TEMPORARIA`. Nenhum 5xx prova recusa: um 502 pode ser o gateway
  sem alcancar o upstream, mas tambem pode chegar depois de ele ter aceitado; um
  504 so diz que o gateway desistiu de esperar;
- **Transporte indistinto** (o `except` de `enviar`) — o `except` unico devolve
  `FALHA_TEMPORARIA` para todo `TimeoutException` e todo `TransportError`,
  varrendo junto o que prova nao-aceitacao (`ConnectTimeout`, `ConnectError`) e o
  que nao prova nada (`ReadTimeout`, `ReadError`, `WriteError`, `CloseError`,
  `RemoteProtocolError`);
- **`DecodingError` escapava** (o mesmo `except`, nos dois adapters) — ela e
  `RequestError`, nao `TransportError`, entao o `except` nao a captura; sobe do
  adapter, e o `SchedulerWorker` converte qualquer excecao do handler em
  `FALHA_TEMPORARIA`. Como o decoding falha lendo o **corpo da resposta**, a
  requisicao ja foi enviada. Em `consultar_status` a mesma
  excecao nao vira retry: vira erro nao tratado na conciliacao administrativa.

A correcao nao e uma lista maior de excecoes, e inverter o padrao. "Depois de
transmitir bytes" nao e verificavel a partir da excecao — um `WriteError` pode
estourar na primeira escrita, sem nenhum byte na rede. O criterio da ADR e a
**prova**: retry so quando ha prova de que o provedor nao aceitou; na duvida,
`resultado_desconhecido`. Entao: reenviam apenas `ConnectTimeout`,
`ConnectError` e `PoolTimeout`, onde a requisicao nao chegou a existir na rede
(o `PoolTimeout` estoura esperando conexao do pool, antes de haver requisicao);
**todo o resto**, `5xx` incluido, e desconhecido — inclusive uma excecao nova da
biblioteca, que assim cai no lado seguro sozinha.

**O telefone da conta pareada existe, e vem por `/instance/info/:id`.** Ate
2026-09-02 o codigo supunha que `/instance/status` era a unica fonte de estado —
e ele traz `Name`, que e o push name, nao o numero. O fundador apontou que o CRM
exibe o numero conectado; a leitura ao vivo confirmou o campo `jid`
(`556299999999:74@s.whatsapp.net`) na rota autenticada por **Tenant**. Detalhes e
armadilhas no contrato §4.4 — em especial que `@lid` tambem e so digitos e nao e
telefone.

**Estado atual: corrigido.** O adapter do WhatsApp aplica essa allowlist, seu
`5xx` virou `DESCONHECIDO`, e nos **dois** adapters o `except` passou a capturar
`RequestError`, que engloba `DecodingError`. O do Resend continua mais restrito
de proposito: manda **toda** falha de transporte para desconhecido, inclusive as
tres que a ADR permitiria reenviar. Bloquear retry demais e seguro, e e-mail esta
fora do escopo do MVP — quem reativar o canal deve esperar zero retry
automatico ali, nao a allowlist do WhatsApp. Os testes cobrem os tres caminhos anteriores ao
envio e os sete que nao provam nada. O que **continua aberto** e a pergunta de
fundo: nao foi medido se o Evolution deduplica pelo `id`. Enquanto nao for, cada
`resultado_desconhecido` vira conciliacao humana — o custo real de nao ter
medido.

O proprio adapter ja classifica **2xx malformado** como desconhecido, que e a
linha vizinha da mesma tabela — os tres pontos acima sao omissao, nao desenho.
Corrigir isso e item de codigo, nao de documentacao.

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.9.0 | 2026-09-03 | A §5.1 estava errada em tres pontos ao mesmo tempo — data, contagem de nos e a afirmacao de que o manifesto nao fora salvo. O terceiro era o mais caro: desencorajava o `--update`, e o grafo ficou treze dias parado, escondendo cifra, persistencia e rotas da conexao de WhatsApp. Corrigidos contra o disco, o grafo atualizado (10.768 nos) e a extracao semantica executada: ele passa a **cobrir documentos**, o que a versao anterior declarava impossivel. A consulta antes de alteracao arquitetural virou governanca na SPEC-003. |
| 1.8.0 | 2026-09-03 | O provedor de IA foi escolhido e a chave existe: o ultimo insumo externo do IMP-359 caiu, e o deploy passa a depender so de trabalho nosso. Mercado Pago entra como §2.4 na primeira mencao — devedor paga o Credor, depois do deploy —, com as duas colisoes nomeadas antes de virarem descoberta no meio da execucao: a decisao de nao ter webhook publico (§2.2), cujo argumento nao se transporta inteiro porque o Mercado Pago assina a notificacao e o Evolution nao, e o fim do plano de parcelas (DR-004), que impede emitir cobranca antes de o Motor apurar o acerto. |
| — | — | *Lacuna conhecida: as versoes 1.6.0 e 1.7.0 subiram o cabecalho sem deixar linha aqui. Nao reconstruidas — inventar a descricao seria pior que registrar a falta.* |
| 1.5.0 | 2026-09-02 | O telefone da conta pareada e obtivel: `jid` em `/instance/info/:id`, autenticado por Tenant — nao por instancia, que e o motivo de ele parecer inexistente. Verificado ao vivo. |
| 1.4.0 | 2026-09-02 | Os tres defeitos da §6.2 foram corrigidos no mesmo dia em que acabaram de ser descritos: os adapters aplicam a allowlist, o `5xx` do WhatsApp virou desconhecido e o `except` passou a capturar `RequestError`, que engloba `DecodingError`. O que continua aberto e a premissa — ninguem mediu se o Evolution deduplica pelo `id`, e por isso cada resultado desconhecido vira conciliacao humana. |
| 1.3.1 | 2026-09-02 | A §6.2 registrava so um terco do problema. Alem do timeout indistinto: **resposta 5xx** vira `FALHA_TEMPORARIA` e a tabela da ADR-009 poe `5xx` em `resultado_desconhecido`; e **`DecodingError` escapa** do `except` (e `RequestError`, nao `TransportError`) direto para o retry do Scheduler. Sao tres pontos, nao um. E a receita mudou de forma: em vez de enumerar excecoes "de depois do envio" — enumeracao que faltou uma em cada tentativa —, a regra vira allowlist. So `ConnectTimeout`, `ConnectError` e `PoolTimeout` provam que a requisicao nao chegou a existir na rede; todo o resto e desconhecido por omissao, `5xx` incluido. "Depois de transmitir bytes" nao e verificavel a partir da excecao. Registrado tambem o que de fato pode duplicar hoje: comprovante do lancamento e aviso de sobra, nao cobranca — o lembrete usa o canal de e-mail. |
| 1.3.0 | 2026-08-27 | Reconciliacoes do PLAN-033/IMP-358: conversas do agente saem de `RegistroComunicacao` (devedor_id obrigatorio impede) e ganham modelo proprio; contextos Operadora/Pre-cadastro e o limite da allowlist registrados na §2.2. |
| 1.2.0 | 2026-08-25 | As cinco perguntas em aberto foram respondidas pelo fundador e a secao §6 deixou de ser duvida para virar registro. E-mail saiu do escopo do MVP e o worker deixou de ser derrubado por falta de conta Resend — com recusa nomeada no lugar do fake que fingia entrega. Topologia do agente decidida sem webhook publico. Segredo do Evolution fica em variavel de ambiente, com o limite de uma instancia por processo declarado. |
| 1.1.0 | 2026-08-16 | WhatsApp preenchido a partir do contrato Evolution Go versionado em `docs/whatsapp/`: modelo de tenant, tres niveis de autenticacao, limites de retry e payload, recorte para a TiaNet e achados que condicionam o desenho. |
| 1.0.0 | 2026-08-16 | Criado apos a sessao identificar que decisoes de desenho foram tomadas sem conhecer integracoes existentes fora do repositorio. |
