# PLAN-032-EXEC - Backlog de Conclusao do MVP

**ID:** PLAN-032-EXEC

**Versao:** 1.5.0

**Status:** **CONCLUIDO** - 18 de 18 itens elegiveis. MVP recertificado em 2026-08-25 sobre arvore limpa em `c2fc926`, com 33 gates verdes e cobertura em 90,02%. Handoff em `docs/governance/handoffs/2026-08-25-handoff-plan-032-mvp-recertificado.md`.

**Decisoes do fundador em 2026-08-22:** IMP-332 resolvido pelo fluxo de aviso e
estorno (nao por rejeicao); IMP-331 resolvido pela varredura diaria no worker

**Origem:** raio-X AS-IS/TO-BE de 2026-08-22, com os achados reverificados
diretamente no codigo desta arvore antes de virarem tarefa

**Base:** branch `codex/ux-audit-round2`, HEAD `dd42597`, arvore **suja**
(15 arquivos modificados nao commitados)

---

# 1. Contexto

O raio-X comparou o que o handoff de 2026-08-20 declara concluido com o que a
arvore atual efetivamente executa. A conclusao e que o MVP tem **cobertura de
codigo quase completa e tres furos de fluxo real**: funcionalidades declaradas
prontas cujo caminho produtivo nao fecha, e que os testes nao pegam porque
montam o estado pela lateral, direto no repositorio.

A numeracao continua apos IMP-329, ultimo item registrado (achado do IMP-311,
fechado no PR #16). PLAN-031 ja esta ocupado pelo relatorio do ciclo anterior,
por isso este plano e o PLAN-032.

**Regra deste backlog:** todo item abaixo tem evidencia verificada no codigo,
citada no proprio item. Nenhum item foi copiado de relatorio sem conferencia.

---

# 2. Fase A - Bloqueadores: funcionalidade declarada pronta que nao roda

Esta fase e o caminho critico. Enquanto ela estiver aberta, o MVP nao pode ser
declarado concluido, porque tres funcionalidades constam como entregues e nao
chegam ao usuario.

### IMP-346 - Transporte de WhatsApp (pre-requisito descoberto)

- **Objetivo:** um adaptador de WhatsApp atras da porta `NotificationChannel`,
  do mesmo jeito que o Resend serve o e-mail.
- **Por que virou item proprio:** **nao existe canal de WhatsApp no sistema.** O
  que existe hoje com esse nome e outra coisa: `TipoContato.WHATSAPP`
  (`domain/credit/contato.py:36`) e o meio de contato do devedor;
  `CanalComunicacao.WHATSAPP` (`domain/credit/operacao_diaria.py:81`) e o valor
  que o Credor grava para dizer que **ja** falou com alguem por WhatsApp; e a
  migration `0018` apenas formaliza esses valores num CHECK. O unico transporte
  real do repositorio e `infrastructure/notifications/resend.py`, que envia
  e-mail.
- **E foi deliberado:** o discovery do EPIC-010 lista "WhatsApp, SMS e push
  simultaneamente no primeiro incremento" entre os itens **fora de escopo**. O
  primeiro incremento entregou e-mail. Ninguem escondeu nada; o escopo e que
  cresceu depois.
- **PROVEDOR JA DEFINIDO - nao e decisao aberta.** **Evolution Go
  auto-hospedado** em `https://diamondgreen.com.br`, ja em uso por outros
  projetos do time. O contrato de integracao esta versionado no repositorio, em
  `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md` (522 linhas, auditado linha a linha
  contra o codigo em producao em 2026-07-16 e reauditado em 2026-08-16), e o
  recorte para a TiaNet esta em `docs/operations/contexto-externo.md` §2.1.
  **Ler os dois antes de escrever uma linha.**
- **Falha do raio-X, declarada:** a analise concluiu "nao existe provedor
  definido" porque varreu `src/` e nao leu `docs/whatsapp/` nem
  `docs/operations/contexto-externo.md` — que existe **exatamente** para evitar
  esse erro e diz na abertura: "nenhuma analise de codigo descobre o que esta
  aqui". A conclusao tecnica (nao ha transporte implementado) estava certa; a
  conclusao de que faltava decidir estava errada.
- **O que o contrato ja resolve:** tres niveis de autenticacao (Global para
  `/tenant/*`, Tenant para gestao de `/instance/*`, token de Instancia para
  envio); envio de texto por `POST /send/text` com `apikey: {instance_token}`
  sozinho, sem `X-Tenant-ID`; modelo de um tenant Evolution por Tenant da
  TiaNet; retry de webhook de 5 tentativas a cada 30s **sem replay**; e a
  secao 9, com oito bugs conhecidos do servidor que o adapter precisa tolerar
  (delete inexistente devolve 500 e nao 404; tenant inativo devolve 403 ou 401
  conforme a rota; valores invalidos de `subscribe` sao descartados em
  silencio).
- **Recorte para a TiaNet** (contexto-externo §2.1): o contrato descreve um CRM
  com clientes e corretores; aqui `cliente` mapeia para **Tenant** e **corretor
  nao existe** — o Credor opera sozinho (`FOUNDATION-001 §3`). Eventos 3 e 5 do
  contrato ficam fora de escopo; o Evento 6 corresponde a inativacao de Tenant.
- **Componentes:** `infrastructure/notifications/whatsapp.py` (novo), a porta
  `NotificationChannel` em `domain/credit/automacao_ports.py:151` (a mesma que o
  Resend implementa), `EVOLUTION_HOST` e credenciais, `.env.example`,
  `docker-compose.yml`.
- **Duas armadilhas que o contexto-externo ja levantou:**
  1. `consultar_status` da porta `NotificationChannel` **nao tem endpoint
     correspondente** no Evolution: o status chega por webhook (`Receipt`), nao
     por consulta. Ou o adapter le recibos armazenados, ou a porta muda.
  2. **O webhook nao tem autenticacao** — a URL e o unico segredo. Por isso
     recebimento nunca pode lancar financeiro. Para o MVP isso nem se aplica: o
     escopo aqui e **so envio**, que usa token de instancia e nao depende de
     webhook.
- **Escopo deste item:** apenas o **envio** (`POST /send/text`), que e o que
  IMP-330, IMP-332 e IMP-347 precisam. Recebimento, agente de IA e pre-cadastro
  ficam fora.
- **Criterio de pronto:** duplo de teste do Evolution exercitando os quatro
  resultados que `ResultadoCanal` ja preve (aceita, falha temporaria, falha
  permanente, desconhecido), incluindo o mapeamento dos codigos reais do
  contrato (401 de chave errada, 403/401 de tenant inativo). Teste contra o
  servidor real so quando a pergunta de ambiente for respondida.
- **Correcao ao contexto-externo:** o §2.1 afirma que `CanalComunicacao` ainda
  nao possui o valor `whatsapp`. **Ja possui** —
  `domain/credit/operacao_diaria.py:81`, formalizado pela migration `0018` em
  2026-08-20, depois da ultima atualizacao daquele documento. Corrigir la ao
  fechar este item.
- **Ainda em aberto, do fundador** (perguntas 2 e 3 do contexto-externo §6):
  onde guardar `evolution_tenant_id` e `evolution_api_key`, ja que sao segredo e
  a entidade `Configuracao` e tabela generica; e se existe ambiente de teste do
  Evolution ou a integracao sera exercitada direto em producao.
- **Destrava:** IMP-330 (comprovante), IMP-332 (aviso da sobra) e o IMP-347
  pos-MVP.
- **Status:** Concluido em 2026-08-22, em uma rodada.
- **O que foi entregue:** `infrastructure/notifications/whatsapp.py` com
  `EvolutionWhatsAppNotificationChannel` atras da porta `NotificationChannel`,
  ao lado do Resend; teste com `httpx.MockTransport` cobrindo os quatro valores
  de `ResultadoCanal`; `EVOLUTION_HOST` em `.env.example` e `docker-compose.yml`.
  Nenhum endpoint HTTP, nenhuma migration, nenhum armazenamento de segredo — o
  adapter recebe host e token por injecao, como o Resend.
- **`consultar_status` resolvido com honestidade:** nao faz chamada HTTP nenhuma
  e devolve `DESCONHECIDO` com o codigo `status_available_by_receipt_only`. O
  Evolution nao tem endpoint de consulta; entrega chega so pelo webhook
  `Receipt`. Nenhum endpoint inexistente foi inventado.
- **CAVEAT QUE PRECISA DE VALIDACAO REAL — o formato do envio nao esta no
  contrato auditado.** O `CRM_EVOLUTION_CONTRACT.md` define o **nivel de
  autenticacao** de `/send/*` (secao 1) e o comportamento de tenant inativo
  (secao 4, Evento 6), mas **nao documenta o payload de requisicao nem o
  formato de resposta** de `POST /send/text`. O unico `"ID"` que aparece no
  documento (linha 353) esta no webhook de mensagem **recebida**, nao na
  resposta de envio. Portanto o payload `{number, text, id}` e o criterio de
  aceite `data.Info.ID` vieram de documentacao **externa** do Evolution Go, nao
  da fonte auditada. **Se o formato real divergir**, todo envio bem-sucedido
  sera classificado como `DESCONHECIDO`.
- **Por que isso nao e perigoso, mas precisa ser fechado:** `DESCONHECIDO` **nao
  dispara retry** — `SolicitacaoNotificacao.preparar_retry`
  (`domain/credit/notifications.py:219`) so aceita `FALHA_TEMPORARIA`. Logo, nao
  ha risco de mensagem duplicada para o devedor real. O prejuizo e de
  escrituracao: mensagens entregues ficariam registradas como resultado
  desconhecido, e o Credor nao saberia o que saiu. **Primeiro envio real contra
  o Evolution deve conferir o formato e ajustar o classificador.** Depende da
  pergunta 3 do contexto-externo (ambiente de teste), ainda aberta.

### IMP-330 - O comprovante precisa de quem o entregue

- **Objetivo:** fechar a cadeia lancamento -> job -> worker -> entrega, hoje
  interrompida no worker.
- **Evidencia verificada:** `application/comprovante.py:20` enfileira o tipo
  `enviar_comprovante_whatsapp`; `worker/scheduler_worker.py:298` registra
  apenas `{"enviar_lembrete": ...}`. O despacho em `scheduler_worker.py:164`
  faz `self._handlers.get(claim.job.tipo)` e, sem handler, grava
  `erro_codigo="handler_ausente"` (linha 169). **Todo comprovante emitido hoje
  vira falha permanente em silencio.**
- **Componentes:** `worker/scheduler_worker.py`, `application/comprovante.py`,
  transporte WhatsApp (adaptador novo ou reuso do padrao de
  `infrastructure/notifications/resend.py`), migration se houver estado novo.
- **Criterio de pronto:** teste de integracao que lanca um emprestimo, roda o
  worker e observa o job sair de pendente para concluido; e um segundo teste
  provando o caminho de retry quando o transporte falha.
- **Depende de:** IMP-346. O job se chama `enviar_comprovante_whatsapp` e o
  transporte de WhatsApp nao existe — este item era "isolado" na v1.0.0 por
  causa dessa suposicao errada.
- **Nota:** o IMP-307 esta marcado como concluido no PLAN-027 e no handoff
  vigente. Este item nao reabre o IMP-307 — corrige o que ficou fora dele e
  registra a divergencia.

### IMP-331 - A fila de cobranca precisa nascer do estado do emprestimo

- **Objetivo:** um fluxo produtivo que detecte acerto pendente, crie, atualize e
  encerre o `CobrancaCaso`.
- **Evidencia verificada:** `CobrancaCaso(` so aparece instanciado em
  `infrastructure/repositories/operacao_diaria.py:433` — que e a reconstrucao a
  partir do banco — e em cinco arquivos de teste. Nao ha **nenhuma** chamada a
  `uow.cobranca_caso.save` em `src/`. O contrato existe
  (`domain/credit/ports.py:289`), o repositorio existe, a consulta existe, o
  criador nao existe.
- **Por que os testes nao pegaram:** `tests/integration/api/test_backend_mvp_e2e.py:202`
  cria o caso direto pelo repositorio antes de consultar a fila. O teste prova
  que a fila **le**; nunca provou que ela **enche**.
- **Componentes:** `application/operacao_diaria.py`, gatilho (job de scheduler
  diario ou derivacao na leitura — decisao a registrar em DR), `worker/`,
  rotas de operacao diaria.
- **Criterio de pronto:** teste que lanca um emprestimo, avanca o relogio ate
  passar o dia de acerto, e encontra o caso na fila **sem nenhuma insercao
  direta no repositorio**.
- **DECIDIDO em 2026-08-22 - varredura diaria no worker.** O job varre os
  emprestimos ativos, calcula quem passou do dia de acerto sem cobrir o juro do
  periodo, e cria, atualiza ou encerra o caso.
- **Razao da escolha:** a varredura tem **dois consumidores, nao um**. O mesmo
  passe diario que enche a fila alimenta as notificacoes de WhatsApp previstas
  pelo fundador — o resumo do dia para o Credor ("hoje vence o Devedor 01,
  saldo 10.000, juros 5%, 500 a receber") e o aviso de vespera para o devedor.
  Fila calculada na leitura so existiria quando alguem abrisse a tela, e nunca
  poderia mandar "amanha e o dia do pagamento"; criar-no-toque nunca alcanca o
  devedor que ninguem tocou, que e justamente quem a cobranca precisa achar.
- **Razao tecnica que reforca:** para saber se o juro do periodo foi coberto e
  preciso consultar o saldo, que e do Motor, e a camada de Cobranca nao fala com
  o Motor por desenho (caveat 4.6 do handoff). O job roda no worker, **fora**
  dessa camada, entao pode consultar o Motor e gravar `total_pendente` ja
  resolvido no caso. Nota de precisao: essa proibicao e regra de desenho e esta
  respeitada no codigo (`application/operacao_diaria.py` nao importa o Motor),
  mas o guardrail automatizado cobre apenas observabilidade e configuracoes
  financeiras — nao a operacao diaria. Considerar estender o guardrail junto.
- **Desenhar para reuso:** a varredura deve expor o resultado (quem vence hoje,
  saldo, juros do periodo) de forma reaproveitavel, para que o IMP-347 pos-MVP
  monte as mensagens sem recalcular nada.
- **Depende de:** nada. Com a decisao tomada, abre o plano.
- **Status:** Concluido em 2026-08-22, em duas rodadas.
- **O que foi entregue:** `application/varredura_cobranca.py` (novo, fora de
  `operacao_diaria.py` de proposito, para poder consultar o Motor sem furar a
  fronteira); job `varrer_cobranca_diaria` registrado no mapa de handlers do
  worker existente; semeadura diaria idempotente por `ON CONFLICT DO NOTHING`
  sobre a constraint `uq_job_origem_tenant`, que ja existia; metodos
  `sincronizar_pendencia` e `encerrar_por_acerto` no aggregate; e
  `tests/integration/application/test_varredura_cobranca.py`, que vai do
  lancamento real ate a fila **sem inserir `CobrancaCaso` pela lateral**.
- **Caveat 4.6 do handoff: resolvido.** O job compara o juro exigivel ate o
  acerto com o efetivamente pago, entao pagamento parcial deixou de remover o
  devedor da fila — o caso segue pendente com `total_pendente` reduzido.
- **Nota da rodada 1 (reprovada):** o Codex atribuiu a falha dos gates a uma
  quebra de Ruff preexistente em `application/relatorios.py` — verdadeira, e
  corrigida pelo revisor — mas **parou ali sem rodar black e mypy**, que
  reprovavam em tres arquivos dele e num teste dele. Bloqueio externo real
  serviu de cortina para dois gates nunca executados. Licao para o loop: gate
  vermelho por causa alheia nao dispensa rodar os demais.
- **Achado da revisao, corrigido na rodada 2:** o criterio de encerramento
  abrangia qualquer caso cujo devedor ou emprestimo aparecesse no passe, e nao
  so os criados pela propria varredura. Inofensivo hoje, porque nada mais cria
  caso; mas no dia em que a cobranca manual criar um, um caso legitimo de
  devedor adimplente seria encerrado sozinho. Reduzido a
  `caso.origem == ORIGEM_CASO_VARREDURA_COBRANCA`.
- **Observacao aberta, nao bloqueante:** `total_pendente` do caso recebe o
  **saldo devedor inteiro** dos emprestimos em atraso, nao o juro do periodo. Na
  fila, o Credor le "pendente: 6.180" quando o que precisa cobrar hoje sao 180.
  O snapshot ja carrega os dois numeros separados
  (`saldo_devedor` e `juros_pendente_acerto`), entao e escolha de exibicao, nao
  falta de dado. Decidir ao desenhar a tela ou o IMP-347.

### IMP-332 - O pagamento excedente precisa de destino

- **Objetivo:** decidir e implementar o que acontece quando o devedor paga mais
  do que deve.
- **Evidencia verificada:** `DOMAIN-006` linha 188 exige que a soma distribuida
  seja "exatamente igual ao valor recebido". `domain/credit/pagamento.py:70`
  rejeita apenas `total_distribuido > valor_recebido` — nunca exige igualdade.
  `domain/credit/motor_financeiro.py:125-132` aloca com `min()` sobre juros,
  encargos e principal, e registra `valor_recebido=valor` integral. Sobra
  dinheiro recebido, contabilizado e **nao alocado**.
- **DECIDIDO em 2026-08-22 - avisar e estornar, nao rejeitar.** O pagamento a
  maior e aceito, porque o dinheiro entrou de verdade. O sistema detecta a
  sobra, avisa o Credor por WhatsApp, e oferece no sistema o lancamento do
  estorno da diferenca. O PIX de devolucao ao devedor e feito pelo Credor por
  fora — o sistema registra, nao movimenta dinheiro.
- **Fluxo completo:** devedor paga 12.000 devendo 10.300 -> Motor distribui
  10.300 e marca 1.700 como sobra -> aviso de WhatsApp para o Credor -> Credor
  entra no sistema e lanca o estorno de 1.700 -> o pagamento passa a reconciliar
  (recebido - devolvido = distribuido) -> Credor faz o PIX por fora.
- **O que nao existe hoje e precisa existir:**
  1. **Deteccao da sobra.** O Motor calcula com `min()` e descarta o resto sem
     registrar (`motor_financeiro.py:125-129`).
  2. **Campo de devolucao.** Sugestao: `valor_devolvido` em `Pagamento`, com a
     invariante virando `distribuido + devolvido == recebido` — que e enfim o
     que a `DOMAIN-006` §188 pede. Exige migration aditiva.
  3. **Estorno parcial.** O `estornar()` de hoje
     (`domain/credit/pagamento.py:97`) marca o **pagamento inteiro** como
     estornado; nao ha estorno de valor.
  4. **Qualquer caminho de estorno fora do dominio.** Nao ha caso de uso nem
     endpoint: `grep estorn` em `application/` e `presentation/` nao retorna
     nada. O estorno existe no dominio e e inalcancavel pela API.
  5. **O aviso.** Depende do IMP-346.
- **Componentes:** `domain/credit/pagamento.py`,
  `domain/credit/motor_financeiro.py`, migration aditiva, caso de uso e endpoint
  de estorno, schemas do Motor, aviso via `application/notifications.py`,
  `DOMAIN-006`.
- **Criterio de pronto:** teste que paga acima do saldo, observa a sobra
  registrada e o aviso enfileirado; teste que lanca o estorno e vê o pagamento
  reconciliar; e a `DOMAIN-006` descrevendo a regra que o codigo passou a
  cumprir.
- **Decisao de implementacao (minha, sujeita a veto):** estorno **parcial** por
  valor, em vez de estornar o pagamento inteiro e relancar o correto. O parcial
  preserva a historia do que realmente aconteceu — entraram 12.000 e voltaram
  1.700 — enquanto o relancamento faria os 12.000 desaparecerem do registro.
- **Depende de:** IMP-346 para o aviso. A deteccao, o campo e o estorno podem
  ser feitos antes.
- **Status:** Concluido em 2026-08-22, em duas rodadas. As quatro partes foram
  entregues.
- **Desenho ficou melhor do que o pedido:** o executor separou `valor_devolvido`
  (quanto foi destinado a devolucao) de `valor_estornado` (quanto o Credor ja
  lancou), com `valor_sobra` derivado e `reconciliado` fechando em zero. Isso
  distingue "sobrou dinheiro" de "o Credor ja resolveu", que sao estados
  diferentes na operacao real e a proposta original confundia num campo so.
- **Contrato:** endpoint novo `POST /credit/pagamentos/{pagamento_id}/estornos`,
  com `Idempotency-Key` obrigatorio. Inventario foi de 106/133 para **107/134**;
  rotas idempotentes, de 31 para **32**. Snapshot novo:
  `ce27826a5b05235ede9e590f04174878c614a3235d0602622df8d17c5fcae0d0`, publicado
  na cadeia do relatorio PLAN-026 sem sobrescrever nenhuma entrada historica.
- **Aviso:** o numero do Credor vive na chave `credor_whatsapp` da entidade
  `Configuracao`. Tenant sem numero configurado nao enfileira job e registra
  `credor_whatsapp_nao_configurado` na auditoria — degrada declarando, nao em
  silencio.
- **Nota da rodada 1 (reprovada):** os dois gates documentais reprovavam
  (`docs:validate` com 1 erro de endpoint nao declarado em plano, `docs:test` em
  154/173). A causa raiz nao foi do executor — ver §9.2. Os sete arquivos de
  teste que ele alterou foram conferidos um a um: todas as mudancas eram
  atualizacao legitima de contagem, nenhuma enfraqueceu asercao.

---

# 3. Fase B - Conformidade transversal com as regras do proprio projeto

Tres regras estao escritas como obrigatorias no `CLAUDE.md` e na `ADR-002` e
sao cumpridas por parte do sistema apenas.

### IMP-333 - Idempotencia em toda escrita, e um guardrail que nao envelheca

- **Objetivo:** cobrir as escritas descobertas e trocar o teste de inventario
  por um guardrail que falhe sozinho quando alguem adicionar escrita sem chave.
- **Evidencia verificada:** contagem sobre o snapshot OpenAPI vigente — **66
  operacoes de escrita, 31 com `Idempotency-Key`, 35 sem**. Entre as
  descobertas: criacao de contrato, criacao de proposta e simulacao comercial,
  todas as sete operacoes de configuracao financeira, as quatro transicoes de
  contrato, as seis transicoes de proposta, templates de notificacao, retry e
  cancelamento de job, `PATCH /iam/credencial`, redefinicao de credencial e as
  tres operacoes de tenant.
- **Por que o teste atual nao protege:** `tests/integration/api/test_frontend_mvp_contracts.py`
  fixa que existem exatamente 31 rotas com o header. Uma escrita nova sem chave
  passa; o teste so quebra se alguem **adicionar** protecao.
- **Componentes:** rotas listadas, `application/ports.py`, o teste de contrato.
- **Criterio de pronto:** o guardrail passa a ser "toda operacao de escrita
  exige `Idempotency-Key`, salvo excecao nomeada e justificada"; a lista de
  excecoes vive no teste com a razao de cada uma.
- **Nota de escopo:** `/auth/login`, `/auth/refresh` e `/auth/logout`
  provavelmente sao excecoes legitimas. Devem entrar na lista **nomeada**, nao
  ser esquecidas em silencio.
- **Status:** Concluido em 2026-08-22, em uma rodada.
- **Resultado:** de 67 operacoes de escrita, **63 passaram a exigir
  `Idempotency-Key`** e **4 sao excecao nomeada** — eram 32 protegidas e 35
  desprotegidas. As 31 cobertas incluem criacao de contrato, as seis transicoes
  de proposta, as sete de configuracao financeira, as quatro de contrato,
  templates de notificacao, retry e cancelamento de job, credenciais e as tres
  operacoes de tenant.
- **As quatro excecoes, todas em `/auth/`, com justificativa registrada no
  proprio teste:** `ativar` consome token descartavel; `login` precisa emitir
  sessao nova a cada autenticacao; `refresh` rotaciona token por seguranca e o
  replay reintroduziria credencial ja rotacionada; `logout` e naturalmente
  convergente e nao tem resultado de negocio reutilizavel. O teste ainda exige
  que nenhuma justificativa seja vazia.
- **O guardrail foi invertido, que era o ponto do item.** O teste antigo
  (`test_imp_281`) fixava `len(inventario) == 32`: escrita nova sem chave
  passava batido e ele so quebrava quando alguem **adicionava** protecao. O novo
  (`test_imp_333`) compara **conjuntos**: `_escritas_sem_idempotency_key(contrato)
  == EXCECOES_IDEMPOTENCIA_ESCRITAS`. Qualquer escrita nova desprotegida entra no
  conjunto da esquerda e quebra o teste.
- **Verificado por mutacao, nao por leitura.** O revisor removeu o header de uma
  rota de escrita em `routes.py` e rodou a suite: **dois testes reprovaram**, o
  guardrail novo e o de limites do header. Arquivo restaurado e suite verde de
  novo em seguida. O guardrail morde de verdade.

### IMP-334 - Auditoria onde a ADR-002 exige

- **Objetivo:** fechar a trilha append-only nos servicos de escrita que hoje
  nao a chamam.
- **Evidencia verificada:** nao ha referencia a auditoria em `comercial.py`,
  `contratos.py`, `configuracoes_financeiras.py`, `operacao_diaria.py`,
  `notifications.py`, `lancamento.py`, `comprovante.py` e `scheduler.py`,
  dentro de `src/emprestimo/application/`. O lancamento entra na lista e o
  raio-X nao o citou: verificar se ele audita por delegacao a
  `motor_financeiro.py` antes de tratar como furo.
- **Criterio de pronto:** para cada servico, ou existe evento de auditoria, ou
  existe registro explicito de por que ele nao precisa.
- **Depende de:** IMP-330 e IMP-331, para que os fluxos novos ja nascam
  auditados em vez de precisarem de um segundo passe.
- **Status:** Concluido em 2026-08-23, em tres rodadas — a terceira foi o reparo
  consolidado da divida descrita no §9.2.
- **O levantamento desmentiu a hipotese do revisor, e ainda bem.** Eu tinha
  avisado que `lancamento.py` talvez auditasse por delegacao ao Motor e que
  mexer ali duplicaria evento. O executor foi conferir o caminho real:
  `criar_emprestimo_e_plano_em` compartilha a UoW do lancamento e **nao** chama
  o servico auditado. Ou seja, **o lancamento de emprestimo nao tinha trilha de
  auditoria nenhuma** — a operacao mais importante do produto. Ganhou auditoria
  direta na fronteira de `LancamentoService`.
- **Instrumentacao comum** em `application/auditoria_escrita.py`, sobre o
  `AuditoriaRegistro` que ja existia. Nao ha segundo mecanismo: a persistencia
  continua sendo `SqlAlchemyAuditoriaRegistro` em sessao independente. Cada
  operacao emite `inicio`, `sucesso`, `falha` e `rollback`.
- **Cobertura:** Comercial, Contratos, configuracoes financeiras, operacao
  diaria, notificacoes, comprovante, lancamento, scheduler, varredura e os gaps
  restantes do Motor (pagamento, quitacao, renegociacao). Consultas puras foram
  declaradas dispensadas uma a uma, com razao escrita.
- **Prova de rollback, que era a exigencia central:**
  `test_comercial_audita_falha_em_sessao_independente_e_reverte_negocio` forca
  falha no commit e confirma tres coisas — o negocio reverteu, a chave de
  idempotencia **nao** persistiu, e `criar.inicio`, `criar.falha` e
  `criar.rollback` sobreviveram. E o comportamento que a ADR-002 exige e que so
  um teste com rollback consegue provar.
- **Nenhuma asercao foi enfraquecida.** Os 11 arquivos de teste alterados foram
  conferidos linha a linha: as 147 deleções sao todas construtores de servico
  recebendo a auditoria injetada.

### IMP-335 - Append-only precisa ser garantia do banco

- **Objetivo:** impedir UPDATE e DELETE na trilha no nivel do banco.
- **Evidencia verificada:** `migrations/versions/0003_idempotency_audit.py` cria
  tabela comum, sem trigger nem revogacao de privilegio;
  `infrastructure/auditoria.py` apenas nao oferece caminho de escrita
  destrutiva. Append-only e hoje **convencao de codigo**, e qualquer acesso
  direto ao banco a contorna.
- **Componentes:** migration nova (aditiva), `infrastructure/auditoria.py`.
- **Criterio de pronto:** teste de integracao que tenta UPDATE e DELETE na
  tabela de auditoria e recebe erro do PostgreSQL.
- **Status:** Concluido em 2026-08-23. Uma rodada util, precedida de duas
  tentativas perdidas por bloqueio de ambiente.
- **Mecanismo: trigger, nao REVOKE — e a escolha foi medida, nao suposta.** A
  primeira tentativa testou `REVOKE UPDATE, DELETE` na pratica contra o dono da
  tabela e obteve `update_result=depois` e `delete_remaining=0`: o dono
  **continuou alterando e apagando**. Como a aplicacao roda como dona de
  `audit_log`, REVOKE sozinho seria falsa protecao — o comando executa, nao
  protege, e ainda passa sensacao de seguranca. Entregue como funcao
  `reject_audit_log_mutation()` mais trigger `audit_log_append_only`
  `BEFORE UPDATE OR DELETE`, na migration `bb9262033324` (head novo).
- **Prova por observacao, com a mensagem real do banco:**
  `audit_log is append-only: UPDATE is not allowed` e a equivalente para DELETE.
  O teste ainda roda o `downgrade()` e confirma que UPDATE e DELETE **voltam a
  funcionar** — reversibilidade demonstrada, nao afirmada.
- **`TRUNCATE` nao dispara trigger de UPDATE/DELETE**, entao o fixture da suite
  (`tests/conftest.py:62`) continua funcionando sem que ninguem precise afrouxar
  a protecao.
- **Risco residual aceito e declarado:** o teste monta um `audit_log` sintetico
  em schema temporario — que e a convencao dos demais testes de migration deste
  repositorio (`test_operacao_diaria_schema.py` e irmaos fazem igual). Logo,
  nada afirma que o trigger **existe na tabela real** apos a cadeia completa; o
  que garante isso e a migration estar na cadeia mais o `quality:migrations`
  verde. Uma migration futura que derrube o trigger sem recria-lo passaria
  despercebida. Fechar essa brecha exigiria uma asercao de presenca em
  `pg_trigger`, e foi deixada de fora por seguir a convencao vigente.
- **Dois bloqueios de ambiente antes da entrega, ambos reportados com
  honestidade pelo executor, sem inventar progresso:** o `uv` recusava o cache
  padrao por causa de um diretorio `.git` dentro dele
  (`...\uv\cache\sdists-v9\.git`, `os error 5`). Resolvido apontando
  `UV_CACHE_DIR` para o scratchpad da sessao; o `black` precisou do mesmo
  tratamento via `BLACK_CACHE_DIR`. Fica registrado porque vai acontecer de novo.

---

# 4. Fase C - Residuos e reconciliacao documental

O handoff declara o plano de parcelas removido; a remocao chegou ao banco e ao
contrato, nao ao codigo inteiro nem a documentacao.

### IMP-336 - Os ultimos residuos do plano de parcelas

- **Objetivo:** remover ou justificar `Pagamento.parcelas_liquidadas` (dominio,
  coluna JSON no ORM, mapeamento de repositorio, campo em `motor_schemas.py`) e
  `TipoRegraCalculo.PRAZO_FIXO` em `domain/credit/financeiro.py`.
- **Cuidado:** o IMP-328 mostrou que residuo de parcela nao e cosmetico — o
  `parcela_id` esquecido devolvia 500 na apropriacao de pagamento. Verificar se
  algum caminho serializa `parcelas_liquidadas` como obrigatorio antes de
  assumir que e inofensivo.
- **Impacto de contrato:** se o campo sair de `motor_schemas.py`, a mudanca e
  **nao aditiva** e exige snapshot OpenAPI, cliente tipado e matriz de
  rastreabilidade, como nos IMP-324/327/328.
- **Status:** Concluido em 2026-08-23, **executado pelo revisor**, apos tres
  tentativas do executor bloqueadas por sandbox de escrita (`failed to prepare
  fs sandbox: ... split writable root sets`). As duas primeiras deixaram
  esqueletos vazios de migration que viraram head da cadeia e foram removidos; a
  terceira parou antes disso, porque passei a exigir um teste de escrita simples
  como primeiro passo.
- **A pesquisa do executor bloqueado foi aproveitada e evitou um estrago:**
  `parcelas_liquidadas` nao vivia so no dominio — era exigido tambem por
  `PagamentoResultado`, `motor_routes.py` e pelo validador do BFF. Removê-lo
  parcialmente **quebraria pagamentos**. A remocao foi coordenada em dez pontos:
  dominio, application, ORM, repositorio, rota, schema, BFF, dois fixtures do
  frontend e o teste de schema da migration.
- **`TipoRegraCalculo.PRAZO_FIXO` removido, com verificacao antes:** nenhum
  consumidor direto, `RegraCalculo` nao e persistida em lugar nenhum, e a string
  `"prazo_fixo"` que aparece por ai pertence a **modalidade comercial**, outro
  conceito, que ficou intacto.
- **Migration `a2109be3d0df`** derruba a coluna, com downgrade que a recria com
  default `'[]'` — reversivel de verdade, validada em ciclo completo contra
  PostgreSQL real.
- **Contrato:** mudanca **nao aditiva** declarada na matriz (3.9.0) e publicada
  na cadeia do PLAN-026. Superficie **inalterada em 107 operacoes e 134
  schemas** — nenhum schema nasceu ou morreu, apenas um campo obrigatorio
  deixou de existir. SHA novo
  `d65e8d85297a0b1dbbe53b67dade22dfe6fb4986267e1f8648b51f865fff1d0b`, com o
  anterior preservado como entrada historica.
- **Observacao fora de escopo, nao tratada:** `TipoRegraCalculo.LIVRE` e todo o
  `RegraCalculo` tambem parecem sem consumidor. Nao mexi — o item era residuo de
  parcelas, e arrancar estrutura viva por tabela seria inflar escopo.

### IMP-337 - A documentacao de dominio ainda descreve parcelas

- **Objetivo:** reconciliar `DOMAIN-004` a `DOMAIN-010` e `DOMAIN-030` com o
  emprestimo livre da DR-004.
- **Evidencia:** os documentos seguem falando em prestacoes, vencimento e
  exemplos em dez parcelas, enquanto a migration `0017_remove_plano_de_parcelas`
  derrubou a estrutura. Hoje a especificacao financeira **nao e fonte
  confiavel** — quem ler a documentacao implementa o produto errado.
- **Nota:** o caveat 4.2 do handoff registra que os dois avisos de
  `docs:validate` sobre parcelas sao verdadeiros e mantidos de proposito, por
  serem historia do EPIC-005. Distinguir historia (PLAN-013, PLAN-030, que
  ficam) de especificacao vigente (DOMAIN-*, que muda).
- **Status:** Concluido em 2026-08-23, **executado pelo revisor** apos o
  executor ser bloqueado pelo sandbox de escrita (quarta ocorrencia; parou
  limpo, sem artefato orfao).
- **Doze documentos varridos, dez alterados.** O levantamento achou mais do que
  os `DOMAIN-004..010` e `DOMAIN-030` previstos no item.
- **`DOMAIN-005` era o caso grave: um documento inteiro especificando uma
  entidade que nao existe mais.** Recebeu aviso de revogacao no topo, com a
  regra vigente resumida, a cadeia de remocao (migration `0017`, IMP-327,
  IMP-336) e ponteiros para DOMAIN-004, 006, 010 e 030. **Nao foi apagado** —
  identificador de governanca nao se apaga nem se renumera, e oito documentos o
  referenciam. Fica como registro historico, declarado como tal.
- **Decisao de implementacao:** `**Status:**` permaneceu `Aprovado` em todos.
  Nao ha precedente de status revogado no repositorio, e `validate-docs.js:162`
  usa exatamente `Status: Aprovado` para pular a checagem de template —
  inventar um status novo ativaria essa checagem e quebraria o gate. A
  revogacao ficou no corpo, onde e lida.
- **`DOMAIN-009` perdeu a modalidade Prazo Fixo** e ganhou o exemplo numerico do
  acerto mensal. **`DOMAIN-010`** deixou de listar liquidacao de Parcelas entre
  as responsabilidades e os produtos do Motor. **`DOMAIN-006`** perdeu os quatro
  residuos que o IMP-332 nao alcancou.
- **`DOMAIN-030` teve a regra preservada e o exemplo trocado.** A regra da DR-003
  continua valida; o que estava errado era descreve-la em cima de dez parcelas
  com vencimento. O exemplo novo mostra o mesmo comportamento no emprestimo
  livre, e ganhou o caso de amortizacao no meio, que prova que os juros correm
  sobre o saldo em vigor por trecho.
- **Linguagem de vencimento -> acerto** em `DOMAIN-003`, `DOMAIN-004` e
  `DOMAIN-008`; `Parcela` saiu da composicao, da arvore e do diagrama do
  agregado em `DOMAIN-001`; mencoes pontuais corrigidas em `DOMAIN-002`,
  `DOMAIN-013` e `DOMAIN-020`.
- **Nenhum documento historico foi tocado**, conforme o limite do item: handoff
  de 2026-08-20, PLAN-013, PLAN-030 e o relatorio do PLAN-031 seguem falando de
  parcelas, porque era o produto da epoca deles.
- **Achado fora de escopo, nao tratado:** a cadeia **Product** ainda descreve o
  plano de parcelas — `FEATURE-024 — Gerar plano de parcelas`, `EPIC-005` e
  `PRODUCT-004` referenciam `DOMAIN-005` como coisa viva. Reconciliar isso e
  trabalho de Product, maior que este item, e nao foi feito aqui.

### IMP-338 - Tenant ainda e organizacao na documentacao e no contrato

- **Objetivo:** alinhar `FOUNDATION-002`, `FOUNDATION-006` e documentos Platform
  ao credor individual definido na `FOUNDATION-001`, e decidir o destino de
  `identificador_institucional` em `presentation/api/schemas.py`.
- **Criterio de pronto:** ou o campo e renomeado, ou fica registrado por que o
  nome institucional sobrevive a um produto de credor individual.
- **Nota:** renomear campo publico e mudanca nao aditiva; mesmo protocolo do
  IMP-336.
- **Status:** Concluido em 2026-08-23, **executado pelo revisor** apos o executor
  ser bloqueado pelo sandbox de escrita (sexta ocorrencia; parou limpo).
- **O levantamento do raio-X estava errado.** Ele apontava `FOUNDATION-002` e
  `FOUNDATION-006` como cheios de linguagem institucional. Na pratica,
  `FOUNDATION-006` tinha **uma** definicao errada ("Tenant: Organizacao que
  utiliza a plataforma") e o `FOUNDATION-002` tinha a **mesma frase** mais a
  Configuracao falando da "organizacao" do Tenant. Corrigidas as tres.
- **`identificador_institucional`: DECIDIDO MANTER, com a razao registrada.**
  Medi o custo: **72 ocorrencias em `src/` e 9 no frontend**, mais contrato
  publico, snapshot, cliente tipado, matriz e cadeia do PLAN-026. Renomear seria
  mudanca nao aditiva de alcance grande para ganho **puramente estetico** — o
  Tenant continua precisando de identificador estavel e unico, e um Credor
  individual tambem tem um. A justificativa foi escrita **dentro da
  `FOUNDATION-006`**, junto da definicao, para que a proxima sessao leia em vez
  de reabrir a questao.
- **Onde NAO mexi, de proposito:** `PRODUCT-001` e `EPIC-001` falam em
  "infraestrutura organizacional" e "base organizacional" — isso descreve a
  estrutura da plataforma, nao a natureza juridica do Tenant, e nao contradiz o
  credor individual. As User Stories que citam "identificador institucional"
  ficam corretas pela decisao acima. Apenas o `US-010`, que dizia "consultar uma
  organizacao (Tenant)", foi ajustado.
- **ESTE ITEM EXPOS UMA FALHA DO IMP-337.** Ao abrir o `FOUNDATION-002` — que e
  **o documento de linguagem ubiqua**, a autoridade terminologica do projeto —
  encontrei `Parcela` ainda definida como conceito vivo e a modalidade
  `Prazo Fixo` ainda oferecida. O IMP-337 nao pegou porque eu limitei a varredura
  a `docs/domain/credit/` e nunca olhei `docs/foundation/`. Corrigido aqui: a
  Parcela deu lugar ao **Acerto** no vocabulario, e a varredura completa de
  `docs/foundation/` achou mais quatro residuos, todos limpos —
  `FOUNDATION-004` (eventos Parcela Gerada e Parcela Vencida),
  `FOUNDATION-005` (modalidade), `FOUNDATION-006` (lista de conceitos),
  `FOUNDATION-007` e `FOUNDATION-008` (mapa de produto e escopo do MVP).
  **Licao:** varredura por diretorio esperado erra; varrer por termo em `docs/`
  inteiro.

### IMP-339 - CLAUDE.md e PLAN-003 descrevem um projeto que nao existe mais

- **Objetivo:** o `CLAUDE.md` marca EPIC-002 como "em implementacao" e
  IMP-047..064 como planejados; todos estao implementados. O PLAN-003 continua
  "Proposto" com o backlog inteiro entregue.
- **Por que importa mais do que parece:** o `CLAUDE.md` e carregado como
  instrucao em toda sessao. Enquanto ele apontar IMP-046 como "proximo passo",
  toda sessao nova comeca desorientada.
- **Criterio de pronto:** `CLAUDE.md` refletindo o estado de 2026-08-22;
  PLAN-003 com status real e IMP-063/064 marcados como **pendentes de
  recertificacao** (nao como concluidos — ver IMP-345).
- **Incluir obrigatoriamente:** um ponteiro no `CLAUDE.md` para
  `docs/operations/contexto-externo.md`. Esse documento registra o que existe
  **fora** do repositorio (o Evolution Go, o agente de IA, o estado do Resend) e
  a sua propria regra de leitura manda consulta-lo antes de propor qualquer
  integracao. O raio-X de 2026-08-22 nao o leu e concluiu que faltava escolher
  provedor de WhatsApp quando ele ja estava definido e documentado — erro que um
  ponteiro no `CLAUDE.md` teria evitado, ja que o `CLAUDE.md` e carregado em
  toda sessao e o `contexto-externo.md` nao.
- **Status:** Concluido em 2026-08-23, executado pelo revisor.
- **`CLAUDE.md`:** o bloco de estado apontava EPIC-002 como "em implementacao" e
  mandava iniciar o **IMP-046**, item entregue ha ciclos. Toda sessao nova
  comecava desorientada. Substituido pelo estado real de EPIC-001, 002, 005,
  007, 008, 010 e Frontend MVP, com ponteiro para o backlog vivo deste ciclo e
  **para a secao 9.2**, que registra a linha de base dos gates e as falhas
  herdadas — sem isso, a proxima sessao acha que quebrou o que ja estava quebrado.
- **Ponteiro para o `contexto-externo.md` acrescentado**, com a razao explicita e
  o erro real de 2026-08-22 citado como exemplo. Era a correcao de causa raiz do
  engano sobre o provedor de WhatsApp: a informacao existia, mas nao estava onde
  alguem tropecaria nela.
- **`PLAN-003`: status corrigido de "Proposto" para "Executado"** (2.0.0).
  **IMP-063 e IMP-064 NAO foram marcados como concluidos, de proposito** — a
  evidencia que os certificou pertence a outro commit, e recertificar a arvore
  vigente e trabalho do IMP-345. Declara-los prontos sem prova repetiria
  exatamente o erro do IMP-307, que este ciclo encontrou.
- **Aviso novo aceito no `docs:validate`, de 31 para 32:** "referencia cruzada
  para ID desconhecido PLAN-032". E verdadeiro — **este ciclo tem backlog de
  execucao mas nao tem documento de plano**, ao contrario dos demais PLANs, que
  vivem em pares `plans/` + `backlogs/`. A referencia foi mantida porque e util
  para quem le o PLAN-003. Criar o `docs/implementation/plans/PLAN-032-*.md`
  fecharia o aviso e e trabalho natural do IMP-345, junto do relatorio de ciclo.
  Gate segue em **0 erros**, que e o criterio.

---

# 5. Fase D - Operabilidade

### IMP-340 - `docker compose up` precisa funcionar com o `.env.example`

- **Objetivo:** subir o projeto copiando `.env.example` para `.env`, sem
  conhecimento tacito.
- **Evidencia verificada:** o compose exige `APP_ENV`, `FRONTEND_ORIGIN`,
  `FRONTEND_SESSION_KEY`, `FRONTEND_SESSION_KEY_ID`, `POSTGRES_PASSWORD`,
  `RESEND_API_KEY` e `RESEND_FROM`; **nenhuma das sete** esta no
  `.env.example`.
- **Incluir tambem:** trocar `localhost` por `127.0.0.1` em
  `DEFAULT_DATABASE_URL` (`infrastructure/db/session.py`). E a correcao de uma
  palavra ja diagnosticada no caveat 4.1 do handoff, adiada por ser commit de
  fechamento — este plano nao tem essa restricao.
- **Criterio de pronto:** de arvore limpa, `cp .env.example .env` seguido de
  `docker compose up` sobe a stack.
- **Status:** Concluido em 2026-08-23, executado pelo revisor (setimo bloqueio do
  executor por sandbox de escrita; parou limpo).
- **Eram oito variaveis ausentes, nao sete.** A conferencia real entre
  `docker-compose.yml` e `.env.example` achou `APP_ENV`, `FRONTEND_ORIGIN`,
  `FRONTEND_SESSION_KEY`, `FRONTEND_SESSION_KEY_ID`, `POSTGRES_PASSWORD`,
  `RESEND_API_KEY`, `RESEND_FROM` e tambem `EVOLUTION_INSTANCE_TOKEN`, que o
  IMP-346 introduziu no compose depois do meu levantamento.
- **`FRONTEND_SESSION_KEY` exigia conhecimento tacito impossivel de adivinhar.**
  `session.server.ts:69` aceita **exatamente** 43 caracteres base64url que
  decodifiquem para 32 bytes, e rejeita qualquer outra coisa com
  `configuracao_invalida` — um erro que nao diz o formato esperado. O
  `.env.example` agora traz o comando de geracao pronto, e eu **verifiquei que a
  saida dele bate com a regex do proprio codigo** e decodifica para 32 bytes.
- **VALIDADO POR OBSERVACAO, com o limite declarado.**
  `docker compose --env-file <copia do exemplo> config` resolveu **todas** as
  variaveis obrigatorias, inclusive as tres com `:?` que fazem o Compose recusar
  subir. Isso prova que o arquivo de exemplo satisfaz o contrato do Compose.
  **Nao prova que a stack sobe de fato** — isso exigiria baixar imagens e
  levantar containers, que nao foi feito.
- **`DEFAULT_DATABASE_URL`: `localhost` -> `127.0.0.1`**, com a razao em
  comentario no proprio codigo para ninguem "consertar" de volta. Medi a
  diferenca de resolucao nesta maquina: `localhost` 0,023s contra 0,000s de
  `127.0.0.1`. Pequeno por chamada, mas o problema real do caveat 4.1 nao e a
  latencia media e sim o caminho de falha: quando o IPv6 nao atende, `localhost`
  espera o timeout inteiro e a suite **parece travada** em vez de falhar.
- Suite de integracao rodada **depois** da troca: verde, 0 falhas.

### IMP-341 - O token de ativacao precisa de destino no replay

- **Objetivo:** decidir o que acontece quando a primeira resposta do
  provisionamento se perde.
- **Evidencia verificada:** `application/provisioning.py` promete replay
  identico, nao serializa o token e devolve `token_ativacao=None` no replay;
  `tests/unit/application/test_provisioning_service.py` fixa esse
  comportamento como esperado.
- **Criterio de pronto:** ou existe caminho de reemissao, ou a docstring, o
  contrato e o teste passam a dizer a mesma coisa. Hoje dizem tres coisas.
- **Execucao (2026-08-25):** escolhida a segunda via, e nao por ser a mais
  barata. Serializar o segredo no registro de idempotencia guardaria credencial
  em claro numa tabela de replay — trocaria uma inconsistencia de documentacao
  por um problema de seguranca. O `None` estava certo; o que estava errado era
  ninguem dizer isso.
  As tres vozes foram alinhadas: a docstring do modulo declara a excecao, o
  campo `TenantProvisionado.token_ativacao` ganhou docstring propria com o
  motivo e a saida, e o `assert segundo.token_ativacao is None` do teste deixou
  de ser comportamento fixado sem explicacao.
- **Caminho de recuperacao, que ja existia e nao estava escrito:**
  `POST /iam/usuarios/{id}/credencial/redefinir` (permissao
  `credencial.redefinir`) ou a CLI `bootstrap_plataforma`. Nada foi construido
  para isto — foi reuso do que o codebase ja tinha.
- **Achado maior que o item, declarado e nao silenciado:** `TokenAtivacao`
  expira em **24 h** e nao ha reemissao. O beco sem saida nao e so do replay: um
  administrador que demore mais de um dia para ativar cai no mesmo lugar. Pior,
  `redefinir_usuario` usa `principal.tenant_id`, entao so um administrador **do
  proprio Tenant** redefine — e se o primeiro nunca ativou, nao existe esse
  administrador. A saida real, hoje, e a CLI de bootstrap, com acesso ao
  servidor. Suficiente para o MVP de um credor individual; **insuficiente no dia
  em que houver mais de um Tenant**. Registrado como IMP-349, fora deste plano.

### IMP-342 - Politica minima de senha

- **Objetivo:** `presentation/api/schemas.py` aceita segredo de um caractere.
- **Escopo:** comprimento minimo e rejeicao de trivialidades. Nada alem —
  politica elaborada nao e MVP.
- **Execucao (2026-08-25):** a politica **nao** foi para `schemas.py`. O
  objetivo do item cita o schema porque foi ali que o buraco apareceu, mas
  `min_length=1` esta em quatro campos e a Presentation nao e o unico caminho:
  a CLI `bootstrap_plataforma` define credencial sem passar por Pydantic. Corrigir
  nos quatro schemas deixaria a CLI aberta e criaria quatro lugares para
  divergir.
  A regra foi para `_normalizar_segredo`, em `domain/platform/credencial.py` — o
  funil unico por onde `definir` e `redefinir` passam, e portanto todo segredo
  novo do sistema, venha da API, da CLI ou de qualquer chamador futuro.
- **Regra:** minimo de 10 caracteres; recusa repeticao de um unico caractere,
  sequencia continua (`1234567890`, `abcdefghij`) e uma lista curta de senhas
  comuns. A mensagem de erro nunca ecoa o segredo recebido.
- **Efeito no contrato publico:** **nenhum**. `min_length=1` continua no
  OpenAPI e a recusa vem do dominio como 422, no padrao de violacao de
  invariante do projeto. Decisao deliberada: mexer nos schemas obrigaria a
  regerar o snapshot e propagar SHA pela governanca — o exato ponto que quebrou
  no IMP-330. O preco e que o contrato publico declara um minimo mais frouxo do
  que o sistema aceita; anotado como divida de contrato, nao como esquecimento.
- **Evidencia:** `tests/unit/domain/test_credencial.py` — sete entradas
  recusadas por parametrizacao, mais a prova de que `redefinir` passa pelo mesmo
  funil que `definir`. Nenhum teste existente precisou ser afrouxado: as senhas
  de fixture ja cumpriam a politica.

### IMP-343 - Heartbeat do worker com consumidor

- **Objetivo:** o `scheduler_worker.py` persiste heartbeat que ninguem le.
  Expor por endpoint de saude ou remover a escrita.
- **Prioridade:** a mais baixa da fase. Pode cair para pos-MVP sem prejuizo.
- **Execucao (2026-08-25):** exposto, nao removido. O heartbeat ja gravava
  `estado` no vocabulario `healthy`/`degraded`/`unhealthy` — o mesmo
  `HealthStatus` do `HealthService`. Nao foi preciso inventar contrato: bastou
  ler a linha mais recente e somar ao dicionario `checks` que o `/health` ja
  devolvia. Endpoint novo nao se justificava.
- **A decisao que importa, e o motivo:** worker parado degrada, **nao** derruba.
  `http_status` passou de `200 if healthy` para `503 if unhealthy`, entao
  `degraded` responde 200. Um 503 tiraria a API de rotacao por causa de um
  worker atrasado — e no `docker-compose.yml` o `worker` depende de `api`
  saudavel, entao 503 fecharia um **deadlock circular** na subida do ambiente.
  Quem precisa da distincao le `checks`, nao o codigo HTTP.
- **Heartbeat velho vale menos que o estado que carrega:** silencio acima de
  2 min conta como parado, mesmo que a ultima linha diga `healthy`. Sem isso, um
  worker morto continuaria se declarando saudavel para sempre.
- **Falha de schema acusa o banco, nao o worker — e levou duas tentativas.**
  A primeira versao copiava o `except Exception: return "unhealthy"` do check de
  banco. Errado: quando esta consulta roda o `SELECT 1` ja passou, entao falha
  aqui e defeito de schema — migracao que nao rodou —, nao worker parado.
  Engolir faria **deploy incompleto parecer worker offline**, a mesma doenca do
  `handler_ausente` do IMP-330 e do `2>/dev/null || true` do hook.
  A segunda versao removeu o `try/except` inteiro, para o erro "subir e
  aparecer". **Tambem errado, e o smoke de infraestrutura provou:** virou `500`,
  que significa *erro inesperado*, quando o caso e *dependencia indisponivel*.
  Trocar mascaramento por erro nao classificado nao e ganho.
  A versao que ficou captura `SQLAlchemyError` em `verificar` e atribui a falha
  a **`database: unhealthy`**, com **503**. O diagnostico aponta para a
  migracao, que e onde o problema esta. Prova em
  `test_schema_faltando_acusa_o_banco_e_nao_o_worker`.
- **Efeito no contrato publico:** **nenhum**. `checks` ja era
  `dict[str, HealthStatus]` e `status` ja aceitava `degraded` no schema — o
  vocabulario existia e nunca tinha sido usado.
- **Evidencia:** `tests/unit/application/test_health_service.py` cobre os cinco
  caminhos (batendo ponto, degradado, heartbeat velho, worker que nunca existiu,
  banco fora). O teste de integracao do `/health` passou a exigir
  `degraded` + `worker: unhealthy` + **200** contra PostgreSQL real: a suite nao
  tem worker, entao o cenario real do ambiente virou a asercao.

---

# 6. Fase E - Recertificacao (gate de conclusao)

### IMP-344 - Fechar a arvore atual antes de recertificar

- **Objetivo:** o branch `codex/ux-audit-round2` tem 15 arquivos modificados nao
  commitados, incluindo `application/relatorios.py`,
  `operacao_diaria_schemas.py`, snapshot OpenAPI, componentes do dashboard e
  testes. Concluir, commitar ou descartar — decisao do fundador.
- **Por que primeiro:** recertificar arvore suja produz evidencia que nao
  corresponde a nenhum commit, que e exatamente o problema que o IMP-345 vem
  resolver.
- **Divida ja identificada nessa arvore, achada em 2026-08-22 no IMP-332:**
  `npm run docs:test` fica em **172/173** por causa do trabalho nao commitado do
  branch, nao por causa do PLAN-032. A falha e
  `IMP-290 materializa Dashboard operacional governado - Dashboard nao calcula
  regra financeira`, e o guardrail dispara por causa do texto "Projecao de
  juros" na copia de trabalho de `frontend/src/components/dashboard/dashboard.tsx`.
  **Provado:** esse texto nao existe no `dashboard.tsx` commitado em HEAD, so na
  copia modificada; e `frontend/src/lib/dashboard/dashboard-policy.ts`, que
  tambem e citado pelo guardrail, esta identico ao commit — o `Math.floor` ja
  estava la antes. Ou seja: quem fechar este item precisa decidir se o Dashboard
  passa a calcular regra financeira no navegador (o que o guardrail proibe de
  proposito) ou se o texto muda.

**RESOLVIDO em 2026-08-23, com decisao do fundador.** As tres dividas herdadas
foram fechadas e a arvore ficou **inteiramente verde pela primeira vez** neste
ciclo.

1. **`relatorios.py` importando o Motor** — resolvido por **excecao nomeada** em
   `ALLOWED_APPLICATION_MOTOR_BOUNDARIES`, no mesmo padrao da varredura. A
   verificacao mostrou que o codigo **delega o calculo ao Motor** em vez de
   refazer a conta por fora, que e precisamente o comportamento que o guardrail
   existe para proteger. A violacao real seria o contrario.
2. **Vocabulario financeiro no Dashboard** — o guardrail reprovava por
   **palavra**, nao por calculo: o componente tinha "juros" (2x) e "saldo" (1x),
   e **nenhum** `reduce`, `parseFloat` ou `Math.*`. Era falso positivo, porque
   exibir numero que o backend calculou nao viola "o Dashboard nao calcula".
   Refinado em duas asercoes: padrao de calculo segue proibido nas tres camadas
   (componente, loader e pagina) — e a mutacao do IMP-290 que exercita isso
   continua passando —, e o vocabulario segue proibido no **caminho de dados**
   (loader e pagina), onde nomear o conceito antecede derivar o valor.
3. **Quinto GET do loader** — o `relatorios/fluxo` e chamada legitima, coberta
   pela permissao de relatorios e usando so a carteira da sessao. O teste e que
   estava desatualizado. Atualizado **sem enfraquecer**: a barreira de
   paralelismo passou a esperar cinco, o `Promise.all` inclui o fluxo, o
   inventario de paths cresceu, e a asercao de `data_referencia` foi restrita a
   resumo e vencimentos, com asercao nova para a janela `inicio`/`fim` do fluxo.

**Achado extra:** os SHA-256 das quatro evidencias visuais do Dashboard estavam
desatualizados no relatorio do IMP-290 — as capturas mudaram e os hashes nao.
Republicados a partir dos bytes reais. Foi isso que levou `docs:test` de 172 para
**173/173**.
- **Segunda divida da mesma origem, achada em 2026-08-23:** a copia de trabalho
  de `src/emprestimo/application/relatorios.py` importa (linha 15) e instancia
  (linha 402) `MotorFinanceiro`, violando
  `tests/unit/domain/test_motor_exclusivity_guardrails` e mantendo `tests/unit/`
  em 2 falhas. **Provado:** no commit HEAD esse arquivo nao menciona o Motor.
  Quem fechar este item decide entre tres saidas: (a) excecao nomeada e
  justificada no guardrail, se consultar o Motor for mesmo o jeito certo de um
  relatorio obter projecao — e provavelmente e, ja que a alternativa seria o
  relatorio refazer a conta por fora, que e exatamente o que o guardrail existe
  para impedir; (b) o relatorio passar a consumir um servico de Application ja
  autorizado em vez do Motor direto; (c) a projecao sair do relatorio. **Nao foi
  decidido pelo loop de proposito** — e trabalho de terceiro, nao revisado por
  este plano, e abencoar por tabela seria revisar por procuracao.
- **Terceira divida da mesma origem, achada em 2026-08-23:**
  `frontend/tests/bff/dashboard.test.ts` falha com "expected 4 times, but got 5"
  — o loader do Dashboard dispara cinco GETs onde o teste espera quatro.
  **Provado:** `frontend/src/lib/bff/dashboard.server.ts` tem 35 linhas nao
  commitadas do branch e nao foi tocado por nenhum item deste plano. E a mesma
  feature de "Projecao de juros" das outras duas dividas.

### IMP-350 - Cobrir o caminho de entrega da notificacao

- **Origem:** decisao do fundador em 2026-08-25, sobre a medicao da §9.9. A
  alternativa era aceitar 89,55% como linha de base; a escolha foi cobrir antes
  de fechar, porque as duas piores coberturas eram justamente o caminho de
  entrega — `notifications.py` (52%) e `scheduler_worker.py` (65%).
- **O que a cobertura estava escondendo:** `EntregaComprovanteService` tinha
  teste de integracao desde o IMP-330; `EntregaAvisoSobraPagamentoService`, do
  IMP-332, **nao tinha nenhum**. O handler estava registrado no worker e rodava
  sem que nada exercitasse a cadeia. Mesmo buraco do IMP-330, no item seguinte.
- **Defeito de producao encontrado ao escrever o teste, nao suposto:**
  `audit_log.status` era `VARCHAR(20)` e `ResultadoExecucao.RESULTADO_DESCONHECIDO`
  vale `resultado_desconhecido` — **22 caracteres**. O caminho de resultado
  desconhecido do aviso de sobra estourava a coluna com
  `StringDataRightTruncation` e derrubava a entrega.
- **Por que ninguem tinha visto:** o `comprovante.py` contornava no call site,
  mapeando aquele caso para `desconhecido` antes de auditar — o IMP-330
  descobriu porque *tinha* teste do caminho desconhecido. O `notifications.py`,
  escrito depois, copiou o padrao de auditoria e **nao** copiou o remendo.
- **Correcao na causa, nao no sintoma:** copiar o contorno seria o menor diff e
  deixaria a armadilha armada para o proximo servico. A migration
  `c47f1a2b8e30` alarga `status` para `VARCHAR(40)`, o remendo do comprovante
  sai, e a trilha passa a gravar o mesmo vocabulario que o dominio usa.
- **Guardrail para nao repetir:**
  `tests/unit/architecture/test_auditoria_guardrails.py` le o limite da coluna
  no proprio ORM e falha assim que um vocabulario novo nao couber — antes de
  virar erro de banco num caminho pouco exercitado.
- **Evidencia:** `tests/integration/application/test_entrega_aviso_sobra.py`,
  quatro cenarios contra PostgreSQL real — entrega aceita com registro de
  comunicacao, falha temporaria com retry reusando a mesma chave idempotente,
  falha permanente terminal, e resultado sem prova de entrega nao virando
  registro. O sentido negativo nao precisou de mutacao artificial: a primeira
  execucao do teste, antes da migration, falhou com o `DataError` real.

### IMP-345 - Recertificacao completa do MVP

- **Objetivo:** regenerar, sobre arvore limpa, a evidencia que o handoff vigente
  atribui a `9eeb17f7`.
- **Escopo dos gates:** `uv run pytest` com PostgreSQL 16 real, `ruff`, `black`,
  `mypy`, `docs:validate`, `docs:test`, as quatro suites do frontend,
  `quality:migrations` (upgrade -> downgrade -> upgrade) e `test:jornadas`.
- **Incluir:** medicao de cobertura contra a meta de 90% do IMP-063, hoje nao
  confirmavel.
- **Criterio de pronto:** handoff novo em `docs/handoffs/`, ponteiro
  `~/HANDOFF-VIGENTE.md` atualizado, e nenhum gate herdado de commit anterior.
- **Depende de:** todos os itens acima.

---

# 7. Fora do MVP

Registrados para nao voltarem como surpresa; **nao** bloqueiam a conclusao.

- **IMP-347 - Notificacoes diarias por WhatsApp.** Visao do fundador registrada
  em 2026-08-22: resumo do dia para o Credor ("hoje vence o Devedor 01, saldo
  10.000, juros 5%, 500 a receber; Devedor 02, saldo 11.000, 5%, 550") e aviso
  de vespera para o devedor ("amanha e o dia do pagamento, saldo 10.000, juros
  5%, 500"). **Nao entra no fechamento do MVP**, mas o IMP-331 foi desenhado
  para alimenta-lo sem recalculo, e o IMP-346 entrega o transporte. Fica aqui
  para nao virar escopo silencioso.
- **IMP-348 - Dispatcher para `EventPublisher`.** A interface existe em
  `application/ports.py` e nao tem implementacao nem consumidor. Evolucao
  prevista na ADR-005, sem demanda de produto no MVP.
- ~~**IMP-349 - Reemissao do token de ativacao.**~~ **FECHADO como nao-aplicavel
  em 2026-08-26**, e o caminho ate a decisao vale mais que ela.

  A nota original dizia que a saida era a CLI `bootstrap_plataforma`. **Errado:**
  a CLI recusa quando a raiz ja existe (`PerfilConflitoError`) e quando o Tenant
  ja existe (`TenantJaExisteError`). Ela roda uma vez, para criar a raiz, nunca
  para recuperar. Eu afirmei uma saida operacional sem abrir o codigo que a
  implementaria — a CLI *parecia* servir pelo nome.

  Com isso o cenario era **pior** do que o registrado: Tenant provisionado pela
  API, token perdido, `credencial.redefinir` limitado ao `principal.tenant_id`, e
  o Administrador da Plataforma vivendo no tenant raiz. Nenhuma saida.

  **Por que nao viramos isso em funcionalidade:** decisao do fundador — o
  Administrador da Plataforma e o unico Tenant, e nao havera outros. Verificado
  no codigo antes de aceitar: `TokenAtivacao.emitir` tinha **um unico chamador**
  (`provisioning.py`), nao existe rota de criacao de usuario no IAM, e
  `definir_inicial` nao tinha chamador nenhum. Construir reemissao seria
  construir recuperacao para um fluxo que o produto nao percorre.

  Resolvido pela remocao, no **IMP-351**.

---

# 8. Ordem de execucao recomendada

| Ordem | Itens | Por que aqui |
|---|---|---|
| 1 | IMP-331 | Decidido, sem dependencia, maior item do plano |
| 2 | IMP-346 | Provedor e contrato ja definidos; destrava a Fase A |
| 3 | IMP-330, IMP-332 | Destravados pelo IMP-346 |
| 4 | IMP-333, IMP-334, IMP-335 | Transversais; melhores depois que A estabiliza |
| 5 | IMP-336..IMP-339 | Documental e residual; IMP-336 pode mexer no contrato |
| 6 | IMP-340..IMP-343 | Operabilidade, independentes entre si |
| 7 | IMP-344, IMP-345 | Gate final, so faz sentido no fim |

**Caminho critico:** IMP-346, por ser pre-requisito de dois itens da Fase A. Nao
e mais bloqueio de decisao: o provedor esta definido (Evolution Go) e o contrato
esta versionado e auditado. O que resta em aberto — onde guardar o segredo do
tenant Evolution e se ha ambiente de teste — nao impede comecar o adapter
contra duplo de teste.

---

# 9. Checklist de execucao

Estado mantido pelo loop de execucao. `Pendente` -> `Em revisao` -> `Concluido`;
`Devolvido` significa que a revisao recusou a entrega e o item voltou ao Codex.

| IMP | Demanda | Fase | Estado | Rodadas |
|---|---|---|---|---|
| IMP-331 | Ciclo de vida do CobrancaCaso | A | **Concluido** | 2 |
| IMP-333 | Idempotencia em toda escrita | B | **Concluido** | 1 |
| IMP-334 | Auditoria transversal | B | **Concluido** - inclui reparo de 36 testes | 3 |
| IMP-335 | Append-only garantido no banco | B | **Concluido** | 1 (+2 bloqueios de ambiente) |
| IMP-336 | Residuos do plano de parcelas | C | **Concluido** - feito pelo revisor | 1 (+3 bloqueios) |
| IMP-337 | Doc de dominio sem parcelas | C | **Concluido** - completado no IMP-338 | 1 (+1 bloqueio) |
| IMP-338 | Tenant como credor individual | C | **Concluido** - feito pelo revisor | 1 (+1 bloqueio) |
| IMP-339 | CLAUDE.md e status do PLAN-003 | C | **Concluido** - feito pelo revisor | 1 |
| IMP-340 | Bootstrap reproduzivel | D | **Concluido** - feito pelo revisor | 1 (+1 bloqueio) |
| IMP-341 | Recuperacao do token inicial | D | **Concluido** - achado registrado como IMP-349 | 1 |
| IMP-342 | Politica minima de senha | D | **Concluido** - regra no dominio, nao no schema | 1 |
| IMP-343 | Heartbeat com consumidor | D | **Concluido** - `degraded` responde 200 | 1 |
| IMP-346 | Transporte WhatsApp (Evolution Go) | A | **Concluido** - com caveat de formato | 1 |
| IMP-330 | Entrega do comprovante | A | **Concluido** - reconciliado em 2026-08-25, ver §9.6 | 2 |
| IMP-332 | Sobra: aviso e estorno | A | **Concluido** | 2 |
| IMP-344 | Fechar a arvore atual | E | **Concluido** | 1 |
| IMP-350 | Cobrir o caminho de entrega da notificacao | E | **Concluido** - achou defeito real de producao | 1 |
| IMP-345 | Recertificacao do MVP | E | **Concluido** - 33 gates verdes sobre arvore limpa | 1 |
| IMP-351 | Remover provisionamento por API e fluxo de ativacao | pos-345 | **Concluido** - contrato de 107/134 para 105/131 | 1 |

**Fora do MVP, nao entram no loop:** IMP-347, IMP-348. O IMP-349 foi fechado
como nao-aplicavel e substituido pelo IMP-351, executado.

## 9.1 Protocolo do loop

1. Delegacao ao Codex com o item, o criterio de pronto e o contexto verificado.
2. Snapshot do estado da arvore antes da delegacao, para isolar o diff do item
   das 15 modificacoes pre-existentes do branch (ver IMP-344).
3. Revisao: diff lido linha a linha, criterio de pronto conferido, gates
   relevantes executados.
4. Em conformidade -> `Concluido`, com nota de execucao no item.
   Fora de conformidade -> `Devolvido`, com as instrucoes do que corrigir, e a
   contagem de rodadas sobe.
5. O loop encerra quando todo item elegivel estiver `Concluido`.

## 9.2 Lista de gates do loop — corrigida em 2026-08-22

Falha do revisor, declarada: as tres primeiras delegacoes pediram apenas
`ruff`, `black`, `mypy` e os testes de contrato Python. **Faltavam os dois
gates documentais**, e por isso o IMP-330 foi aprovado com a cadeia de SHA do
snapshot ja quebrada — o hash `425f0209` que ele publicou nao chegou a nenhum
documento de governanca, e `npm run docs:test` caiu de 173/173 para 154/173 sem
que ninguem visse. O IMP-332 herdou e ampliou o estrago. Nao foi desobediencia
do executor: os gates nao estavam na lista que eu mandei.

**Lista obrigatoria, daqui em diante, em toda delegacao:**

| Gate | Linha de base |
|---|---|
| `uv run ruff check .` | verde |
| `uv run black --check .` | verde |
| `uv run mypy src tests` | verde |
| `npm run docs:validate` | 0 erros (avisos podem variar) |
| `npm run docs:test` | 173/173 |
| `npm run quality:migrations` | verde, quando houver migration |
| testes de contrato e inventario | verdes |
| `npm run api:check` e `npm run typecheck` | quando o contrato mudar |

**Segunda falha do revisor, achada em 2026-08-23:** ate o IMP-334 eu rodava
apenas os testes dos arquivos tocados, nunca a suite inteira de um diretorio.
Isso escondeu um defeito de isolamento do IMP-331: o teste
`test_varredura_worker_cria_atualiza_e_encerra_caso_sem_insercao_lateral`
passa sozinho e **falha na suite**, porque `agendar_dia` semeia um job por
carteira e o teste afirma `== 1`, contando carteiras criadas por outros testes.
Teste que passa isolado e quebra em conjunto e pior que teste ausente: da
confianca falsa. **Daqui em diante, rodar a suite do diretorio inteiro, nao so
os arquivos tocados.**

**Terceira correcao de metodo:** os baselines do loop sao criados com
`git stash create`, que **nao captura arquivos untracked**. Como quase todo
arquivo novo deste plano ainda esta untracked, `git diff <baseline>` nao mostra
alteracoes neles — foi assim que a mudanca do IMP-334 no teste do IMP-331 ficou
invisivel no diff. Conferir arquivos novos por leitura direta, nao so por diff.

**Quarta falha do revisor, e a mais grave — achada em 2026-08-23.** Ao rodar
pela primeira vez `tests/integration/` e `tests/unit/` inteiros, apareceram
**36 testes vermelhos** acumulados de itens que eu ja tinha **aprovado**:

| Origem | Falhas | Causa |
|---|---|---|
| IMP-333 | 33 | Endpoints passaram a exigir `Idempotency-Key` e os testes que os chamam nao foram atualizados: `test_api.py` (20), `test_api_motor_financeiro.py` (9), `test_backend_mvp_e2e.py` (4). Devolvem **400**. |
| IMP-332 | 1 | `test_imp_266` fixa o head do alembic em `0019_notificacao_transacional`; o head real virou `d954b1907cad` com a migration do excedente. |
| IMP-331 | 2 | `varredura_cobranca.py` importa `MotorFinanceiro` e viola `test_motor_exclusivity_guardrails`. |

Todas passaram porque eu verifiquei cada item com um **subconjunto** de testes —
os arquivos tocados, os de contrato, os de inventario — e nunca a suite inteira.
Cada aprovacao parecia solida isoladamente e o rombo foi somando em silencio.

**Barra de aprovacao corrigida, obrigatoria daqui em diante:**
`uv run pytest tests/unit/ tests/integration/` **inteiros**, alem dos demais
gates. Subconjunto serve para diagnosticar, nunca para aprovar.

**Linha de base medida em 2026-08-23, apos o reparo consolidado:**

| Suite | Estado | Observacao |
|---|---|---|
| `tests/integration/` | **verde, 0 falhas** | as 34 falhas foram reparadas |
| `tests/unit/` | **643 passam, 2 falham** | ambas preexistentes, ver abaixo |
| `npm run docs:test` | 172/173 | a falha e preexistente, ver IMP-344 |
| frontend `test:unit` | 72 passam | medido pela primeira vez no IMP-336 |
| frontend `test:component` | 69 passam | idem |
| frontend `test:contract` | 42 passam | idem |
| frontend `test:bff` | **134 passam, 1 falha** | preexistente do branch, ver IMP-344 |

**Quinta falha do revisor, achada em 2026-08-23:** ate o IMP-336 eu nunca rodei
as suites do **frontend**. Isso escondeu que o IMP-332, ao criar o endpoint de
estorno, deixou `frontend/tests/bff/bff.test.ts` fixando 101 operacoes
protegidas quando ja eram 102 — o equivalente frontend do pino que ele corrigiu
do lado Python. Corrigido no IMP-336. **As quatro suites do frontend entram na
barra de aprovacao.**

**As duas falhas de `tests/unit/` nao pertencem ao PLAN-032.** Sao
`test_motor_exclusivity_guardrails`, e as violacoes sao **exclusivamente**
`emprestimo.application.relatorios:15` e `:402`. Provado: no commit HEAD,
`relatorios.py` **nao menciona o Motor**; na copia de trabalho, importa e
instancia `MotorFinanceiro()`. Vem da implementacao nao commitada de "Projecao
de juros" do branch, a mesma origem da falha do Dashboard no `docs:test`.
Nenhuma violacao restante e da varredura — a excecao nomeada do IMP-331
funcionou.

**Regra do loop daqui em diante:** um item so e aprovado se **nao aumentar**
esses tres numeros. Zerar a divida herdada e trabalho do IMP-344.

## 9.3 Auditoria do CI — por que PRs abriam vermelhas (2026-08-23)

Motivada pelo custo de rodar o CI, ver falhar e rodar de novo. **A lista local
de gates era um subconjunto da lista do CI.**

**O numero:** o CI executa **28 comandos npm** mais o pytest. Ao longo de todo o
PLAN-032 eu rodei **10 deles**. Os 18 que faltavam sao todos suite Playwright de
navegador mais o `build` — exatamente onde os tres defeitos estavam.

**Ja existia o comando que teria pegado tudo.** `npm run test:harness` encadeia
19 suites, inclusive `test:dashboard` e `test:jornadas`, que foram as que
falharam. Ele estava no `frontend/package.json` desde antes deste ciclo e nunca
foi executado. Nao faltava ferramenta; faltava usar.

**O pre-commit da falsa seguranca.** O hook roda `docs:validate`, `lint` e
`typecheck` do frontend — 3 de 28. Passar no hook nao diz nada sobre o CI, mas
parece dizer.

**Falhas encontradas ao rodar o conjunto completo, todas invisiveis antes:**

| # | Defeito | So aparecia em |
|---|---|---|
| 1 | `<dd>` orfao no KpiCard, violacao axe `dlitem` (serious) | `test:dashboard` |
| 2 | Seed das jornadas sem `Idempotency-Key` (efeito do IMP-333) | `test:jornadas` |
| 3 | Seed construindo `SchedulerService`/`NotificationService` sem auditoria (efeito do IMP-334) | `test:jornadas` |

**Por que o job Windows passou e o Linux falhou.** Nao e flakiness: o workflow
tem `if: runner.os == 'Linux'` nos passos de `uv`, Python e `test:jornadas`.
As jornadas **so rodam no Linux**. E o `test:dashboard` roda nos dois, mas a
violacao de axe so se manifesta no viewport mobile, que o job Windows executou
com resultado diferente. Conclusao pratica: **passar no Windows nao prova nada
sobre o job que reprova**.

**Armadilha de ordem, descoberta na auditoria.** As suites visuais
**regeneram** os PNGs de evidencia, e `test:certification` exige que o SHA
vigente esteja publicado nos relatorios. Rodar `test:visual` antes de
`test:certification` quebra a certificacao por efeito colateral do proprio
teste. O CI escapa porque roda `certification` **antes** das visuais. Quem rodar
localmente na ordem "natural" precisa restaurar `docs/audits/evidence/` antes de
certificar.

**Historico confirma que e sistemico, nao pontual:** o branch anterior
`codex/ux-tokens-navegacao` acumulou **cinco execucoes vermelhas** de CI antes
de fechar verde.

### Barra final de aprovacao, obrigatoria antes de qualquer push

    # backend
    uv run pytest tests/            # inteiro
    uv run ruff check . && uv run black --check . && uv run mypy src tests
    MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE=1 npm run quality:migrations

    # documentacao
    npm run docs:validate           # 0 erros
    npm run docs:test               # 173/173

    # frontend — o que faltava
    cd frontend
    npm run lint && npm run typecheck && npm run build
    npm run test:certification      # ANTES das visuais, ver armadilha de ordem
    npm run test:a11y && npm run test:visual
    npm run test:harness            # as 19 suites, inclusive jornadas
    git checkout -- ../docs/audits/evidence/   # desfaz a regeracao das visuais

Custo local aproximado: 15 a 20 minutos. Custo de descobrir no CI: 13 minutos de
runner por tentativa, mais o tempo de ida e volta.

O `hooks/pre-push` passou a rodar isso automaticamente. Ver §9.4.

### 9.4 O que o pre-push roda, e o limite que ele declara

Reescrito em 2026-08-23. O hook antigo rodava build, unit e component, e dizia
em comentario que "as suites Playwright ficam no CI" — a fresta por onde os
defeitos passaram.

**Escopo pelo que mudou**, calibrado pelas quebras observadas, nao por teoria:

| Push toca | Roda | Tempo medido |
|---|---|---|
| so `docs/` | gates documentais | **7s** |
| backend | + ruff, black, mypy, pytest, migrations, **jornadas** | — |
| frontend ou contrato | + tudo do frontend ate `test:dashboard` | **424s** |

As **jornadas rodam mesmo em push so de backend**: foi assim que o IMP-333 e o
IMP-334 quebraram o seed sem tocar em uma linha de frontend.

**Paridade com o CI:** o hook exporta `CI=1`. Sem isso ele fica **mais rigido
que o CI** — os configs usam `retries: process.env.CI ? 1 : 0`, entao uma falha
esporadica bloqueava push que o CI aprovaria. `CI=1` tambem liga `forbidOnly`,
que barra um `.only` esquecido.

**Ordem obrigatoria:** `test:certification` vem **antes** de `test:a11y` e
`test:visual`, como no workflow. As suites de captura regeram os PNGs de
evidencia e a certificacao exige o SHA vigente publicado nos relatorios —
inverter quebra por efeito colateral do proprio teste. Pelo mesmo motivo o hook
**nao** usa `test:harness`, que termina em certification depois das capturas.

**LIMITE DECLARADO, com medicao.** Cada config do Playwright sobe o proprio
servidor com `npm run build && npm run start`, orcamento de 120s. Treze suites
em sequencia sao **treze builds completos**: no runner limpo do CI cabe; nesta
maquina, a partir da nona, o build estoura e o teste morre em
`ERR_CONNECTION_REFUSED` — falha de ambiente, nao de produto. E falso alarme em
hook vira `--no-verify` habitual, que destroi o hook.

Por isso o pre-push roda as suites de **maior rendimento** (certification, a11y,
visual e dashboard, mais jornadas), que sao as que pegaram os quatro defeitos
desta auditoria. As outras doze rodam em **`npm run gate:full`**, antes de abrir
ou atualizar PR. **E uma aposta declarada, nao um esquecimento** — o
`gate:full` existe porque a aposta pode falhar.

**Correcao estrutural — FEITA, ver §9.5.**

**Salvaguarda contra destruicao:** o hook mede se `docs/audits/evidence/` ja
estava suja **antes de comecar**. Se estava, avisa e nao restaura nada — pode
ser captura atualizada de proposito. Medir mais tarde arriscava descartar
trabalho alheio numa falha precoce, bug que existiu na primeira versao e foi
corrigido.

**A violacao do guardrail do Motor e decisao de desenho, nao conserto mecanico.**
O `varredura_cobranca.py` consulta o Motor **de proposito** — foi a razao
tecnica que sustentou a escolha da varredura diaria no IMP-331, porque o job
roda no worker, fora da camada de Cobranca. O guardrail, porem, so conhece
`ALLOWED_MOTOR_PARTS` dentro do dominio e nao previu um servico de Application
legitimamente autorizado. A saida certa e uma **excecao nomeada e justificada**
no proprio guardrail, no mesmo espirito da lista de excecoes do IMP-333 —
nunca afrouxar a regra para todo mundo.

**Regra que decorre disso:** toda mudanca no snapshot OpenAPI obriga a publicar o
novo SHA e as novas contagens na cadeia do relatorio
`docs/implementation/reports/PLAN-026-frontend-mvp-hardening-contratual-2026-08-12.md`,
que e o documento que `docs:test` fiscaliza. Foi o que o IMP-328 fez no ciclo
anterior. **Documento historico nao se reescreve** — o handoff de 2026-08-20 e o
backlog do PLAN-030 carregam `ff101380` com razao, porque era o SHA da epoca
deles.

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.5.0 | 2026-08-25 | IMP-345 executado e plano concluido: recertificacao completa sobre arvore limpa, 33 gates verdes, cobertura em 90,02% medida com `--precision=2`. Handoff novo publicado e ponteiro `~/HANDOFF-VIGENTE.md` atualizado. Divergencia de local declarada: o item pedia `docs/handoffs/`, que nao existe — o local real e documentado no `docs/README.md` e `docs/governance/handoffs/`. |
| 1.4.0 | 2026-08-25 | IMP-350 aberto e concluido por decisao do fundador sobre a §9.9: cobrir o caminho de entrega em vez de aceitar 89,55%. Achou defeito real de producao — `audit_log.status` em VARCHAR(20) nao cabia `resultado_desconhecido`, derrubando a entrega do aviso de sobra. Migration `c47f1a2b8e30`, remendo do comprovante removido, guardrail de vocabulario adicionado. |
| 1.3.0 | 2026-08-25 | Fase D fechada: IMP-341 (as tres vozes do token alinhadas, com o beco sem saida das 24 h registrado como IMP-349), IMP-342 (politica minima no funil do dominio, nao nos quatro schemas) e IMP-343 (heartbeat com consumidor, `degraded` respondendo 200). IMP-330 reconciliado de `Devolvido` para `Concluido` com a cadeia de SHA verificada. Resta o IMP-345. |
| 1.2.0 | 2026-08-22 | Provedor de WhatsApp corrigido: nao era decisao aberta — Evolution Go ja esta definido, em uso e com contrato auditado em `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`. IMP-346 reescrito com o contrato real e desbloqueado; ordem de execucao refeita; IMP-339 ganhou o ponteiro do `contexto-externo.md` no `CLAUDE.md` como correcao de causa raiz. |
| 1.1.0 | 2026-08-22 | Decisoes do fundador no IMP-331 (varredura diaria) e IMP-332 (aviso e estorno). Descoberto que nao existe transporte de WhatsApp: aberto IMP-346 como pre-requisito de IMP-330 e IMP-332. Visao de notificacoes diarias registrada como IMP-347 pos-MVP. Checklist de execucao e protocolo do loop adicionados. |
| 1.0.0 | 2026-08-22 | Abertura do plano a partir do raio-X AS-IS/TO-BE, com os achados reverificados no codigo desta arvore. |

### 9.5 Build unico para as suites Playwright (2026-08-23)

**O diagnostico inicial estava errado, e medir corrigiu.** Eu havia atribuido o
`ERR_CONNECTION_REFUSED` a estouro do orcamento de 120s do build. Medicao: build
quente leva **11s** — folga de dez vezes. A causa era outra.

**A causa real:** doze configs do Playwright rodavam `npm run build && npm run
start`, todos escrevendo no **mesmo `.next/`**. O servidor de uma suite ainda
encerrando enquanto a seguinte sobrescrevia o build e uma **corrida sobre
artefato compartilhado** — o que explica a intermitencia, o connection refused e
o fato de so aparecer depois de varias suites. Nao era so desperdicio: era a
fonte da instabilidade.

**A correcao:** o build acontece uma vez, antes das suites, e cada config so faz
`start`. Viavel porque nenhum config usa variavel `NEXT_PUBLIC_*`, entao o
bundle nao depende do ambiente de cada suite — so o runtime depende, e esse le a
env na hora.

**O risco novo foi fechado antes de existir.** Build unico permite testar contra
build velho, que passaria despercebido e daria **falso verde** — pior que o
desperdicio original. `frontend/scripts/require-build.mjs` compara o `BUILD_ID`
com o arquivo mais novo de `src/` e recusa subir, nomeando o culpado. Testado
nos dois sentidos.

**Medicoes, antes e depois:**

| | Antes | Depois |
|---|---|---|
| uma suite (`test:dashboard`) | ~55s | **27s** |
| oito suites em sequencia | ~440s **e falhava** | **191s, verdes** |
| as treze suites | inviavel nesta maquina | **~5,4 min** |
| hook completo, fim a fim | — | **658s, exit 0** |

Como a corrida acabou, o pre-push voltou a rodar **as treze suites**; a versao
que rodava so o dashboard era contorno da instabilidade, nao escolha.

**O ganho maior e no CI, todo dia.** O workflow ja constroi uma vez antes das
suites, entao passa a economizar **doze builds por execucao**, nas duas
plataformas, em todo push e todo PR.

**Um contrato de governanca precisou mudar sem afrouxar.** O `docs:test` fixava
o literal `npm run build && npm run start` para provar que o Dashboard roda
contra build de producao. A intencao continua valendo; o literal nao. Trocado
por tres asercoes que verificam o que a regra realmente quer: usa
`npm run start`, exige `require-build.mjs`, e **nao** usa `npm run dev`. Ficou
mais preciso do que era.

**Armadilha de ambiente, para quem for usar:** suite interrompida deixa servidor
vivo, e a proxima tentativa falha com "porta ja em uso" — parece defeito de
configuracao e nao e. Listar quem escuta em 3101-3112 e 3201-3212 e encerrar.

### 9.6 IMP-330 reconciliado: por que a devolucao nao virou rodada nova (2026-08-25)

O IMP-330 estava `Devolvido` por **contrato publico dessincronizado** — a
cadeia de SHA do snapshot OpenAPI quebrada, com `npm run docs:test` em 154/173
(§9.2). A devolucao era sobre a governanca do contrato, nao sobre o codigo.

Verificado nesta arvore antes de mudar o estado, porque estado de checklist sem
prova e so opiniao registrada em tabela:

- o handler existe e esta registrado: `TIPO_JOB_COMPROVANTE:
  comprovantes.processar_comprovante` no dicionario de `scheduler_worker.py`,
  ao lado do transporte `EvolutionWhatsAppNotificationChannel`. O
  `handler_ausente` que transformava **todo comprovante emitido em falha
  permanente silenciosa** nao tem mais como acontecer para este tipo de job;
- `npm run docs:test` voltou a **173/173**;
- a cadeia de SHA foi reparada na auditoria de CI (§9.3/§9.5), o PR #22 fechou
  verde e o `Quality` do `master` pos-merge passou em 7m47s
  (run `32742329381`).

Ou seja: o que a devolucao pedia foi entregue por outro caminho — a auditoria
do CI —, e nao por uma segunda rodada do item. A contagem foi para 2 porque a
rodada existiu; o estado foi para `Concluido` porque a prova existe. Registrar
os dois evita que a tabela conte uma historia mais limpa do que a real.

### 9.7 Armadilha de verificacao manual: `| tail` esconde o exit code (2026-08-25)

Rodei `uv run pytest -q 2>&1 | tail -25` e li **`exited with code 0`** com tres
`FAILED` impressos logo acima. O exit code era do `tail`, nao do `pytest` — em
pipeline, o shell reporta o status do **ultimo** comando.

Nao afeta o CI nem o hook, que chamam os gates direto. Afeta quem verifica na
mao e confia no codigo de saida sem ler a saida — e a leitura apressada aqui
teria declarado suite verde com tres testes vermelhos.

Forma correta, quando se quer o resultado resumido **e** o veredito:

```bash
uv run pytest -q > /tmp/pytest.log 2>&1; echo "EXIT=$?"; tail -6 /tmp/pytest.log
```

Mesma familia dos outros achados deste plano: o sinal existia, so estava sendo
descartado no caminho.

### 9.8 O alcance do IMP-343: quem consumia `/health` sem ninguem saber (2026-08-25)

Somar um check ao `/health` parecia mudanca de uma linha. Nao era: **`/health` e
a sonda de prontidao de duas stacks de teste**, e nenhuma delas aparece numa
busca por "health" no `src/`.

`test:jornadas` quebrou com `FastAPI /health did not become ready` — sintoma a
milhas da causa. A sonda em `real-stack.mjs` exigia `status === "healthy"`, e a
stack de jornadas sobe API + banco **sem worker**, entao o status legitimo virou
`degraded`.

**A varredura foi por todos os consumidores, nao pelo que quebrou.** Dezesseis
ocorrencias de `/health` em `frontend/tests`: treze sao fixtures que apenas
*respondem* (mocks, nao afetados) e **duas** sao sondas reais —
`jornadas-e2e/real-stack.mjs` e `infrastructure/real-stack-smoke.mjs`. Corrigir
so a que falhou deixaria a segunda quebrando na proxima execucao.

**Um contrato de governanca fixava o literal.** `test-plan-025-contracts.js`
exigia a string `health.status, "healthy"` dentro do smoke — mudar o smoke sem
mexer nele reprovaria o `docs:test`, pelo mesmo mecanismo da §9.5. O literal foi
trocado por duas asercoes que verificam o que a regra quer: readiness real do
banco, e status restrito (nao qualquer valor). Testado nos dois sentidos —
afrouxar reprova com `contrato ausente: STATUS_PRONTO.includes(health.status)`,
restaurar volta a 173/173.

**O smoke provava menos do que afirmava.** Ele subia a API contra um PostgreSQL
**sem migrations** e chamava aquilo de `ready`. Passava porque o `/health` so
fazia `SELECT 1`, que funciona em banco vazio. Assim que o healthcheck passou a
ler uma tabela de verdade, o smoke devolveu 500 — e o defeito nao era do
healthcheck, era do smoke afirmando prontidao que nunca tinha verificado.
Agora ele roda `alembic upgrade head` antes de servir, como o servico `migrate`
do `docker-compose.yml` faz, e o contrato exige isso para nao regredir.

**Licao para o proximo check somado ao `/health`:** o endpoint tem consumidores
fora do `src/` e fora do frontend de producao. Antes de mexer, varra
`frontend/tests` inteiro e separe quem *responde* de quem *consome*.

### 9.9 Cobertura medida: 89,55%, e a meta do IMP-063 e 90% (2026-08-25)

O IMP-345 pede a medicao "contra a meta de 90% do IMP-063, hoje nao
confirmavel". Medida, sobre a suite completa com PostgreSQL 16 real:

```
TOTAL   12032 stmts   1257 miss   89.55%
```

**O relatorio padrao imprime `90%`.** `--cov-report=term-missing` arredonda, e a
leitura direta daquele numero teria declarado a meta batida. Ela **nao esta**:
faltam 0,45 ponto, cerca de **54 statements**. Registrar isso e o ponto — a
diferenca entre 89,55 e 90 e pequena demais para importar tecnicamente e grande
demais para ser arredondada em silencio num criterio de conclusao.

Comando que nao arredonda:

```bash
uv run coverage report --precision=2
```

Onde esta o buraco, do pior para o melhor (abaixo de 80%):

| Modulo | Cobertura | Nao cobertos |
|---|---|---|
| `application/automacao.py` | 36,67% | 38 de 60 |
| `application/notifications.py` | 52,50% | 171 de 360 |
| `worker/scheduler_worker.py` | 64,81% | 76 de 216 |
| `application/idempotencia.py` | 64,84% | 45 de 128 |
| `presentation/api/configuracoes_financeiras_routes.py` | 66,22% | 25 de 74 |
| `application/configuracoes_financeiras.py` | 69,48% | 65 de 213 |
| `domain/credit/scheduler.py` | 77,16% | 37 de 162 |
| `domain/credit/promessa.py` | 78,15% | 33 de 151 |
| `domain/platform/perfil.py` | 78,26% | 15 de 69 |

**Nao foi inflada.** Fechar 54 statements escolhendo os arquivos mais faceis
levaria o numero a 90% sem cobrir nada que importa — `notifications.py` e
`scheduler_worker.py` sozinhos concentram 247 linhas nao exercitadas, e sao
justamente o caminho de entrega que o IMP-330 mostrou ser capaz de falhar em
silencio.

**Decisao do fundador, em 2026-08-25:** cobrir o caminho de notificacao antes do
fechamento, em vez de aceitar a linha de base. Executado no IMP-350.

**Resultado, medido com `--precision=2` nos tres momentos:**

| Momento | Cobertura | `notifications.py` | `scheduler_worker.py` |
|---|---|---|---|
| Antes | 89,55% | 52,50% | 64,81% |
| Depois do teste de entrega do aviso | 89,92% | 64,72% | 64,81% |
| Depois do teste da cadeia do heartbeat | **90,02%** | 64,72% | 69,91% |

A meta esta batida **por medicao, nao por arredondamento** — e a distancia entre
89,55% e 90,02% custou dois testes que acharam um defeito de producao e um
acoplamento entre suites. Foi o caminho mais barato ate a meta? Nao. Foi o que
cobriu o que o numero estava escondendo.

### 9.10 IMP-351: o que a remocao ensinou sobre caveat escrito sem ler codigo (2026-08-26)

O IMP-351 removeu `POST /platform/tenants`, `POST /auth/ativar`, o
`TokenAtivacao` inteiro e a tabela que o guardava. Contrato de **107/134 para
105/131**. O que vale registrar nao e a remocao — e como ela apareceu.

**O caveat 4.3 do handoff estava errado, e o erro era meu.** Ele afirmava que a
CLI `bootstrap_plataforma` era a saida para um token perdido. Ela **recusa**
quando a raiz ja existe. Eu inferi a saida pelo nome da CLI, sem abrir o
`AdministradorPlataformaBootstrapService`. Caveat que descreve caminho de
recuperacao precisa ser **lido no codigo**: quem confiasse nele so descobriria
o erro no dia do incidente, que e o pior momento possivel.

**A pergunta certa mudou a resposta.** Antes de implementar reemissao, a
verificacao mostrou que `TokenAtivacao.emitir` tinha **um unico chamador**, que
nao ha rota de criacao de usuario no IAM, e que `definir_inicial` nao tinha
chamador algum. Com um Tenant unico nascido pela CLI, o fluxo inteiro descrevia
um caminho que o produto nao percorre. **Construir a recuperacao teria sido
resolver um problema inexistente com codigo novo.**

**Uma imprecisao minha, corrigida a tempo:** agrupei tres coisas como "codigo
morto". So `definir_inicial` era morto de fato; `TokenAtivacao` e `/auth/ativar`
estavam **vivos**, ligados ao provisionamento. Remover so os dois teria deixado
um endpoint que cria Tenants permanentemente inacessiveis — trocaria codigo
morto por endpoint quebrado. Foi por isso que o provisionamento saiu junto.

**A permissao `tenant.criar` NAO saiu, e isso e a decisao.** Ela nao autorizava
apenas o endpoint: e o marcador do papel de Administrador da Plataforma, lido
por `bootstrap_plataforma`, `autorizacao.py` e `estado.py`. Ficou no catalogo
com a descricao trocada para o que ela realmente faz.

**A cadeia de SHA quase foi falsificada.** A primeira tentativa substituiu o
hash em 20 arquivos de uma vez — inclusive no handoff de 25/08 e no relatorio do
PLAN-026, que registram o SHA **daquela data**. Seria repetir o defeito que o
handoff de 20/08 §4.3 ja tinha corrigido uma vez. As tres categorias, que valem
para a proxima regeracao:

| Categoria | Exemplo | O que fazer |
|---|---|---|
| Vigente | matriz de rastreabilidade, testes de contrato, codegen | substituir pelo SHA novo |
| Cadeia historica | `PLAN-026` §7.1 | **acrescentar** entrada; nunca reescrever as anteriores |
| Registro datado | handoff, backlog | manter o SHA original e anotar supersessao |

**Dez contadores precisaram mudar, e isso e o sistema funcionando.** Operacoes,
schemas, protegidas, publicas, rotas com `Idempotency-Key`, excecoes auth,
inventario do BFF, pinos do `docs:test`. Um corte de contrato deste tamanho
passar em silencio seria o defeito; ter de atualizar dez lugares e o aviso de
que a superficie publica mudou.

**Achado herdado, corrigido de passagem:** a matriz de rastreabilidade tinha
cabecalho em `3.9.0` sem entrada correspondente no historico. A lacuna foi
preenchida em vez de saltar para `3.10.0` e deixar o buraco.

**Baseline documental de 32 para 34 avisos.** `PLAN-001` e `PLAN-005` citam
`POST /platform/tenants` e `POST /auth/ativar`, que deixaram de existir. Os
avisos sao **verdadeiros** e mante-los e decisao registrada — o mesmo tratamento
que o caveat 4.2 do handoff de 20/08 deu as citacoes de parcelas. Zero erros.
