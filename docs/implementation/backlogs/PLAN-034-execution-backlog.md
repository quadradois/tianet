# PLAN-034 — Backlog de execução: conexão do WhatsApp na plataforma

**Versão:** 1.0.0

**Plano:** [PLAN-034](../plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md)

**Decisão de origem:** [DR-006](../../governance/decision-requests/DR-006-conexao-do-whatsapp-dentro-da-plataforma.md)

---

# 1. Estado do sistema hoje

Verificado em 2026-08-31, não presumido.

| Fato | Onde |
|---|---|
| Tenant `tianet` existe no Evolution | criado pela equipe que administra o servidor |
| Instância `adm_tianet` criada e pareada | manualmente, no fechamento do IMP-352 |
| `POST /instance/create` ecoa o token que o chamador envia | contrato §8.1 |
| `POST /instance/connect` aceita `webhookUrl` vazia | resposta `200` com `"webhookUrl": ""` |
| `Connected` e `LoggedIn` são estados distintos | `/instance/status` |
| Adapter de envio faz **só** `/send/text` | `infrastructure/notifications/whatsapp.py` |
| Nada de Evolution é persistido | o ORM não tem tabela nem coluna |
| `cryptography` **não** está instalado | `pyproject.toml` |

---

# 2. API

Idêntica à seção 6 do plano. O `contract-check` exige igualdade, não continência.

- `GET /platform/whatsapp/conexao` — estado da conexão. Permissão
  `whatsapp.conexao.ler`. `404` quando o registro existe e o token não decifra.
- `POST /platform/whatsapp/conexao` — cria a instância se necessário e inicia o
  pareamento. Permissão `whatsapp.conexao.gerir`. **Sem corpo e sem
  `Idempotency-Key`** — o porquê está na §3.1 do plano.
- `DELETE /platform/whatsapp/conexao` — encerra o pareamento (`logout`). A
  instância permanece. Permissão `whatsapp.conexao.gerir`.
- `DELETE /platform/whatsapp/conexao/instancia` — apaga a instância no provedor
  e o registro local. Permissão `whatsapp.conexao.gerir`. **Acrescentada no
  IMP-368** a pedido do fundador: sem ela nada no sistema remove instância
  abandonada, e o Evolution acumula sessão morta.

Inventário: **107 → 111 operações**, **135 → 137 schemas**. O plano previa
110/138 com três operações; a quarta reaproveita o DTO do `desconectar`.

---

# 3. Itens

### IMP-364 — Cifra do token de instância

- **Objetivo:** poder guardar o token sem guardá-lo em texto claro.
- **Escopo:** dependência `cryptography`; `CifraToken` sobre `Fernet`, com chave
  em `WHATSAPP_TOKEN_ENCRYPTION_KEY`; recusa nomeada no start quando
  `APP_ENV=production` e a variável falta.
- **Critério de pronto:** ida e volta preserva o token; chave ausente recusa em
  vez de degradar; o cifrado difere do claro em teste que falharia se alguém
  trocasse a cifra por identidade.

### IMP-365 — Persistência da conexão

- **Objetivo:** a conexão sobreviver a restart sem edição manual de `.env`.
- **Escopo:** migration aditiva `conexao_whatsapp`; ORM; repositório;
  `UNIQUE (tenant_id)`.
- **Limite:** migration aditiva; downgrade é `DROP TABLE`. Nenhuma tabela
  existente é tocada.
- **Critério de pronto:** ciclo `upgrade → downgrade → upgrade` verde; token
  gravado como `BYTEA` cifrado; leitura devolve o valor original.

### IMP-366 — Cliente de gestão do Evolution

- **Objetivo:** falar com `/instance/*` sem contaminar o adapter de envio.
- **Escopo:** `EvolutionInstanceClient` com `criar`, `conectar`, `qr`, `status` e
  `logout`. Auth de Tenant só no `criar`; as demais com token de instância.
- **Por que classe separada:** o contrato §0 registra incidente real por confundir
  chave de tenant com token de instância. Tipos distintos tornam a troca impossível
  por construção.
- **Critério de pronto:** as cinco rotas cobertas por fixtures com as respostas
  reais capturadas em 2026-08-31, incluindo `webhookUrl` vazia aceita e
  `Connected` sem `LoggedIn`. Nenhum teste toca a rede.

### IMP-367 — Casos de uso e permissões

- **Objetivo:** orquestrar consulta, conexão e desconexão sob RBAC.
- **Escopo:** `ConsultarConexaoWhatsApp`, `ConectarWhatsApp`,
  `DesconectarWhatsApp`; permissões `whatsapp.conexao.ler` e
  `whatsapp.conexao.gerir` no catálogo; `CATALOGO_PERMISSOES_VERSAO` sobe.
- **Critério de pronto:** instância inexistente, pendente e pareada distinguidas;
  `Connected` sem `LoggedIn` **não** conta como conectado; auditoria registra
  autoria conforme o IMP-361, sem o QR nos detalhes.

### IMP-368 — Endpoints e contrato

- **Objetivo:** expor as **quatro** operações da seção 2.
- **Escopo:** rotas, schemas, snapshot OpenAPI, contadores de superfície; o
  caso de uso `ExcluirConexaoWhatsApp` com `excluir_instancia` na porta e no
  adapter; e o nome da instância passando a ser derivado do Tenant.
- **Critério de pronto:** `api:check` verde; inventário em 111/137; RBAC
  coberto com 401, 403 e 404.
- **Decidido com o fundador em 2026-09-02** (protocolo socrático do handoff
  §5.1), e três respostas mudaram o desenho:
  1. **a instância é reconhecida por `instancia_id` guardado no banco**, não
     pelo nome. O nome continua existindo só como âncora de recuperação do
     `create` cuja resposta se perdeu, e por isso passou a ser **gerado**
     (`tianet_{tenant_id}`) em vez de recebido — um campo digitável
     transformaria erro de digitação em segunda instância não pareada;
  2. **excluir é operação distinta de desconectar**, com rota própria;
  3. a premissa escrita no IMP-367 — "a instância do TiaNet foi criada à mão
     antes desta tela existir" — **é falsa**. Ela nasceu dos testes de
     2026-08-31. A janela do `create` perdido, essa sim, continua real, e é o
     que mantém a adoção por nome viva.

### IMP-369 — Tela de conexão

- **Objetivo:** conectar o WhatsApp sem sair da plataforma.
- **Escopo:** tela com QR, polling de status, estados de erro e de QR expirado,
  e o número visível quando pareado.
- **Mudou no IMP-368:** o polling de status (`GET`) **não traz mais o QR** —
  buscá-lo custava uma ida ao provedor a cada volta do laço. O QR vem do `POST`,
  chamado quando alguém quer parear. A tela pede o QR uma vez e faz polling
  barato enquanto espera. Ver PLAN-034 §3.
- **Critério de pronto:** jornada Playwright cobre não conectado → QR → pareado;
  a11y sem violação crítica ou séria; **o QR não aparece em log, trilha nem
  métrica** — guardrail de teste, não convenção.

### IMP-371 — O que a resposta do Evolution mandou consertar

- **Objetivo:** fechar os dois defeitos e a corrida que a resposta do provedor
  revelou em 2026-09-04 (`docs/whatsapp/2026-09-04-resposta-esclarecimento-evolution.md`).
- **Nasceu depois do IMP-369 e por causa dele.** Nenhum dos três apareceu em
  review: apareceram quando perguntamos ao time que mantém o Evolution Go, e a
  resposta veio por leitura do código-fonte deles.
- **Escopo, em três:**
  1. **`logout` repetido** — `DELETE /instance/logout` numa instância já
     desconectada **sempre** responde `400`, nunca `2xx`. O adapter recusava
     não-2xx, então a segunda desconexão falhava em produção. Agora qualquer
     `400` dessa rota é sucesso "já desconectado", **casado pelo status e não
     pela frase** (a mensagem depende do timing da autocura interna deles).
     ADR-019 v1.2.0 carrega o detalhe.
  2. **Renovação automática do QR** — o QR vive 20s e o provedor confirmou que
     repetir o `POST /instance/connect` é seguro: não reinicia o ciclo, não
     duplica handler, só re-aponta o webhook. **A rota nova que o IMP-369 ia
     propor não é necessária.** A tela renova sozinha a cada 20s, **quatro
     vezes** — cinco *tentativas* com a do clique, que é o tamanho de um ciclo
     do provedor; tentativas, e não códigos garantidos, porque uma delas pode
     voltar sem QR. Depois disso o botão volta a ser do operador. O limite
     existe contra a aba esquecida, não contra o provedor.

     O laço segue a **tentativa de pareamento**, não o QR na tela: o provedor
     responde `200` com `qrcode_base64: null` enquanto ainda gera, que é o
     caminho normal logo após o `connect`, e amarrar o laço ao QR fazia a
     renovação nunca começar justamente aí. Para o laço não renascer depois do
     logout, o estado da ação passou a dizer **qual** operação o produziu.
  3. **Debounce** — os mapas de client do provedor não têm lock, e disparar
     `connect`/`logout`/`qr` em paralelo para a mesma instância é corrida
     documentada por eles (§7.1). A renovação só dispara com a ação ociosa, que
     é a mesma condição que já desabilita o botão, e o polling de estado também
     para enquanto uma escrita corre.

     **A recomendação deles é literal, e foi seguida ao pé da letra.** Ela nomeia
     `connect`/`logout`/`qr`; `status` aparece na lista de handlers que tocam os
     mapas, mas fora da recomendação. Cheguei a desarmar o polling durante todo
     o laço — mais seguro no papel, e duas jornadas Playwright reprovaram na
     hora: sem ele, a tela leva até 20s para dizer "Conectado" depois do
     escaneamento, porque a única leitura de estado passa a ser o
     `revalidatePath` de cada renovação. O preço era do operador, e a
     recomendação não pedia isso. **Sobra** a janela de um `refresh` já em voo
     quando a escrita começa — não há como cancelá-lo do cliente, e ela fecha
     sozinha se o provedor puser o `sync.Mutex` por instância que ele mesmo
     cogita.
- **Critério de pronto:** testes de componente com temporizador falso provam o
  intervalo, o teto, o rearme no clique, o caminho "provedor ainda gerando", o
  debounce (nenhuma segunda chamada com a ação em curso) e o laço que não
  renasce depois do logout — e **falham se o React reclamar no console**, porque
  foi assim que a primeira versão passou verde despachando a ação fora de uma
  transição; testes de unidade fixam o `400` como sucesso **seja qual for a
  frase**; suíte Playwright do WhatsApp segue verde.
- **Fica de fora, decidido pelo fundador em 2026-09-04 — serialização por
  instância.** O debounce entregue é da **aba**, não da instância: `pendente` é
  estado local, e duas abas abertas na tela de conexão têm temporizadores
  independentes, podendo disparar `connect` no mesmo segundo. É exatamente o que
  o provedor pede para evitar (§7.1). **Aceito como caveat**, com o risco
  nomeado: se a corrida acontecer, o efeito é panic ou leitura corrompida no
  provedor — o canal de WhatsApp da operação cai junto.

  O que sustenta a decisão: a pré-condição é estreita (o operador precisaria de
  duas abas na tela de pareamento ao mesmo tempo, atividade rara e curta, com um
  operador só), e o provedor **já disse que avalia** pôr um `sync.Mutex` por
  instância do lado dele, o que fecharia a janela na origem.

  O fechamento do nosso lado, quando for a hora, é `pg_try_advisory_lock` por
  tenant em volta das chamadas externas de conectar/qr, devolvendo conflito à
  segunda tentativa em vez de deixá-la correr junto. Isso **muda o contrato**
  (novo status no `POST`) e o snapshot OpenAPI governado — é por isso que não
  entrou de carona neste item. O comentário em `whatsapp.client.tsx` diz o que
  a serialização de hoje alcança, e o que não alcança.

- ~~**Fica de fora, e vira item próprio:** auditar o campo `connected`.~~
  **Auditado e fechado em 2026-09-04**, e o resultado é melhor que o esperado:
  chamamos os dois endpoints ambíguos — `buscar_instancia` usa `/instance/all`,
  `jid_da_instancia` usa `/instance/info/:id` — mas deles lemos apenas `name`,
  `id`, `token` e `jid`. O campo `connected` minúsculo **nunca é lido**. Todo
  estado de conexão vem de `/instance/status`, que entrega `Connected` (socket) e
  `LoggedIn` (autenticado) como campos separados, e a separação é preservada até
  a tela. O texto original do caveat segue abaixo, para quem precisar do contexto:
  auditar o campo `connected`, que
  significa **socket aberto** em `/instance/status` e **autenticado** em
  `/instance/all` e `/instance/get`. É leitura, não escrita, e não estava
  quebrando nada — mas ninguém verificou se o adapter mistura os dois.

### IMP-370 — Worker lê o token do repositório

- **Objetivo:** encerrar a dependência de `EVOLUTION_INSTANCE_TOKEN` no ambiente.
- **Escopo:** leitura pelo repositório, com o ambiente mantendo precedência
  enquanto existir.
- **Por que fase própria:** trocar origem do token junto com a criação da tela
  arriscaria deixar o worker sem canal, e worker sem canal é operação sem aviso.
- **Acrescentado em 2026-09-03 — o worker também grava o estado da conexão.** O
  `GET` de estado **vai ao provedor toda vez** (`_sincronizar`: o pareamento vem
  de leitura do provedor, nunca de inferência local). Um selo de status na barra
  lateral, lendo esse `GET`, faria uma chamada ao diamondgreen **por página
  aberta** — o mesmo defeito que o IMP-368 acabou de tirar do QR.

  Decisão do fundador em 2026-09-03: o selo do IMP-369 lê o **banco** (último
  estado conhecido, zero chamada externa), e o worker — que já roda de tempos em
  tempos e já vai passar por aqui para ler o token — passa a **perguntar ao
  provedor e gravar**. O selo fica fresco de graça, sem cache novo e sem número
  mágico de minutos.

- **E o aviso, porque selo sozinho não basta.** Se o WhatsApp cair no celular, um
  selo cinza no canto passa despercebido por dias — e o sintoma real aparece
  longe, quando o comprovante não sai. O fundador pediu **híbrido**: selo passivo
  mais aviso ativo. O aviso nasce aqui, quando o worker detecta a transição de
  conectado para desconectado — não no IMP-369, que não tem como saber.

- **Critério de pronto:** worker sobe com o token vindo do banco; com a variável
  presente, ela prevalece e o comportamento atual não muda; **o estado da conexão
  é gravado a cada varredura, e a queda gera aviso**.

---

### Candidato para depois do deploy — soltar o vinculo local

**Nao entra no PLAN-034.** Anotado em 2026-09-02, quando a custodia da chave de
cifra foi decidida: nao existe operacao que remova o registro local
**preservando** a instancia no provedor. A unica que apaga a linha
(`DELETE /platform/whatsapp/conexao/instancia`) apaga a instancia junto, e com
ela o pareamento.

Isso torna a recuperacao de uma chave de cifra perdida um `DELETE` no banco
feito a mao — quando poderia ser uma chamada. Custo baixo hoje (single-tenant,
um operador, e o caso ainda nao aconteceu), e por isso fica como candidato e nao
como item: construir agora seria antecipar uma operacao para um cenario que
ninguem viveu.

### Caveat registrado — a janela entre o efeito externo e o commit

**Aberto pelo review do Codex no IMP-368 (2026-09-02), fechado como caveat e nao
como defeito.** O revisor apontou tres pontos — `desconectar`, `excluir` e
`criar` — e os tres sao o mesmo pedido: gravar um registro duravel de "operacao
pendente" **antes** de cada efeito externo, para que um crash entre a chamada e
o commit deixe rastro conciliavel.

Isso e um outbox/saga, e a **ADR-001 o adia por decisao**: "Repository Pattern +
Unit of Work: transacao unica (AD-001), *evolucao futura para Saga*". A janela
descrita nao e propria deste item — e a mesma de todo efeito externo do sistema,
incluindo o codigo do IMP-367 que ja passou por dezenove rodadas de review.

O que foi verificado antes de fechar:

- **a alegacao de violacao do contrato nao se sustenta hoje.** O
  `CRM_EVOLUTION_CONTRACT.md` §5.4 exige guardar a intencao antes do `logout`
  para nao reconectar por engano — mas a regra e **condicional** a acionar a
  reconexao do Evento 4, e `grep` em `src/` nao encontra nenhum consumidor de
  `LoggedOut` nem qualquer reconexao. A exigencia passa a valer no dia em que
  alguem construir o reator; ate la nao ha o que violar;
- **a exclusao ja converge sozinha:** o adapter trata `record not found` do
  provedor como sucesso, entao repetir o `DELETE` fecha a divergencia;
- **a criacao ja tem mitigacao registrada** (caveat 3.9 do handoff de
  2026-09-02): a adocao pelo nome derivado reencontra a instancia orfa na
  proxima tentativa.

**Quando isto deixa de ser caveat:** quando existir mais de um operador
concorrente, ou quando algum componente passar a reagir a `LoggedOut`. Ai a
conciliacao deixa de ser "repetir a chamada" e passa a exigir estado.

---

# 4. Ordem e dependências

| Ordem | Item | Depende de |
|---|---|---|
| 1 | IMP-364 | — |
| 2 | IMP-365 | IMP-364 |
| 3 | IMP-366 | — |
| 4 | IMP-367 | IMP-365, IMP-366 |
| 5 | IMP-368 | IMP-367 |
| 6 | IMP-369 | IMP-368 |
| 7 | IMP-370 | IMP-365 |
| 8 | IMP-371 | IMP-369 |

O IMP-366 não depende de nada e pode andar em paralelo com 364/365.

---

# 5. Fora de escopo

- **Receber mensagens.** É a Fase C do PLAN-033 (IMP-356), e depende do agente,
  que não existe.
- **Webhook apontando para a TiaNet.** A DR-006 decidiu apontar para o agente,
  preservando o `contexto-externo.md` §2.2.
- **Múltiplas instâncias por Tenant.** A ADR-003 fixou o escopo single-tenant;
  `UNIQUE (tenant_id)` expressa isso no banco.
- **Rotação da chave de cifra.** Vira item próprio quando houver segundo segredo
  cifrado. **Reconectar nao regenera o token**: o reconnect preserva o valor da instancia, entao recuperar de chave perdida exige criar instancia nova e reparear.

---

# 6. Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.1.0 | 2026-09-04 | Acrescenta o IMP-371, que nao existia quando o plano foi escrito: ele e a lista de consertos que a resposta do time do Evolution Go produziu — `logout` repetido, renovacao automatica do QR e debounce. Vale registrar como o item nasceu: perguntar ao provedor rendeu tres achados que quatro rodadas de review no IMP-369 nao produziram. |
| 1.0.0 | 2026-08-31 | Sete itens materializando o PLAN-034, com o estado do sistema verificado contra o servidor real em vez de presumido. |
