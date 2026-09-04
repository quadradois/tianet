# Resposta — esclarecimentos Evolution Go

**Para:** TiaNet
**De:** equipe que mantém o Evolution Go (`diamondgreen.com.br`)
**Data:** 2026-09-04
**Em resposta a:** `2026-09-04-solicitacao-esclarecimento-evolution.md`
**Tenant:** `tianet`

---

# 0. Como chegamos a estas respostas

Todas as respostas abaixo vêm de leitura direta do código-fonte (`/opt/evolution-go`),
não de suposição nem de teste em produção — não precisamos gastar o número do
fundador para a maior parte disto. Citamos arquivo:linha para que vocês possam
conferir, e marcamos explicitamente os dois pontos que só o código não resolve
(precisam de verificação empírica).

Duas coisas apareceram na investigação que não foram perguntadas, mas mudam
como vocês devem desenhar a tela — foram parar na §7 (achados extras).

---

# 2. Ciclo de vida do QR

**2.1 — `GET /instance/qr` acompanha a rotação.**

Não é uma foto congelada do `connect`. O handler relê a instância no banco a
cada chamada (`instance_service.go:445`) e devolve a coluna `Qrcode`, que é
sobrescrita a cada novo código emitido pelo loop de pareamento
(`whatsmeow.go:642`). Chamando só `GET /instance/qr` em loop, vocês recebem o
QR atual a cada vez — como pediram, esse é o único endpoint necessário.

Bônus não pedido: se não houver client ativo (ex.: instância nunca conectada
ou após um timeout), `GET /instance/qr` **se autocura** — dispara um novo ciclo
sozinho (`instance_service.go:416-438`), sem precisar de `POST /instance/connect`.

**2.2 — Intervalo de rotação: 20s por código, fixo na lib, não configurável.**

Vem do fork do whatsmeow (`whatsmeow-lib/qrchan.go:62-111`), não do nosso
código nem de config de ambiente:

```go
timeout := 20 * time.Second
if len(codes) == 6 {
    timeout = 60 * time.Second
}
```

Ou seja: 20s por código, exceto o eventual 6º código do lote (protocolo do
WhatsApp, não controlamos), que fica 60s — mas no deploy padrão vocês nunca
verão o 6º, porque cortamos em 5 antes (ver 2.2b).

**Não há rate limit em `GET /instance/qr`.** A rota só passa por
`authMiddleware.Auth`, sem nenhum middleware de throttle
(`pkg/routes/routes.go:118`), e o handler não impõe intervalo mínimo. Podem
consultar a cada 20s (acompanhando a rotação) sem risco de bloqueio nosso.

**2.2b — Precisão sobre o "5" do contrato:** o número de códigos por lote que o
WhatsApp manda é decidido pelo protocolo, não por nós. O que existe do nosso
lado é um teto de aplicação, `QrcodeMaxCount` (env `QRCODE_MAX_COUNT`, default
`5`, `pkg/config/config_env/env.go:46`), que **corta o ciclo antes** de o lote
natural se esgotar. Isso bate com o "~20s / até 5" do contrato, mas a causa é
o nosso limite de app, não um limite do WhatsApp.

**2.3 — Ao fim do 5º QR: a instância é derrubada por completo, não fica em
espera.** O código (`whatsmeow.go:562-629`) faz, nesta ordem: logout forçado
se ainda conectado, limpa a coluna `Qrcode`, marca `Connected=false` com
`DisconnectReason="QR code limit reached (N)"`, remove os ponteiros de client
em memória, e a goroutine do client **termina** — não há reinício automático
neste caminho.

Concretamente:
- `GET /instance/qr` depois disso não devolve QR obsoleto — devolve **erro**
  (`"no QR code available..."`) até a autocura (acima) conseguir gerar um novo
  dentro de ~5s de tentativa, ou funciona de primeira se a autocura for rápida.
- **Não é obrigatório chamar `POST /instance/connect` de novo** — `GET
  /instance/qr` sozinho já reinicia o ciclo, porque detecta client nulo e
  chama o mesmo `StartInstance` internamente. `POST /instance/connect`
  funciona também, por um caminho ligeiramente diferente, com o mesmo efeito.

(Existe um segundo caminho de esgotamento, o canal nativo do whatsmeow
fechando sem o corte de aplicação — esse sim se autorreinicia
recursivamente, `whatsmeow.go:788`. Mas com `QrcodeMaxCount=5` no default,
o corte de aplicação dispara primeiro; o caminho "recomendado" para a tela é
tratar sempre como o cenário acima, sem reinício automático.)

**2.4 — Chamar `POST /instance/connect` de novo com pareamento pendente: seguro,
não reinicia nada, não duplica handler.**

O ponteiro do client já existe em memória desde o começo do `StartClient`,
antes mesmo do QR aparecer (`whatsmeow.go:393`), então `Connect` enxerga
`isInstanceRunning=true` e **não** dispara um novo client/QR loop
(`instance_service.go:244-282`). O que ele faz é só atualizar webhook/eventos
inscritos no client já rodando (`UpdateInstanceSettings`,
`whatsmeow.go:2538-2595`) — não há novo registro de handler (isso só acontece
uma vez, dentro de `StartClient`, que não é rechamado neste cenário).

Ou seja: **sim, este é um caminho seguro e ele resolve a renovação sem rota
nova do lado de vocês**, exatamente como intuíram. Chamar `connect` de novo
durante o pareamento re-aponta webhook/eventos, mas não reinicia o ciclo dos 5
nem duplica nada.

Achado colateral relevante — ver §7.1: os mapas internos que guardam os
clients não têm lock, então chamadas concorrentes (não só `connect` repetido
em sequência, mas em paralelo) têm um risco teórico de race a nível de
runtime Go. Não achamos isso perguntado, mas registramos porque afeta a
segurança de retry automático na tela.

**2.5 — `QRTimeout` dispara uma vez por ciclo inteiro, não por código
individual.** A expiração de cada código isolado não gera evento nenhum — só
a virada silenciosa para o próximo código. `QRTimeout` só é emitido quando o
ciclo inteiro termina sem pareamento (`whatsmeow.go:605-627` no corte por
`QrcodeMaxCount`, ou `whatsmeow.go:694-722` no esgotamento nativo do canal).
Então não dá para usar esse evento para "empurrar o próximo código" — ele só
avisa "o ciclo acabou, sem sucesso".

---

# 3. `logout` repetido

**3.1 — A premissa de convergência não se sustenta: `POST /instance/logout`
NUNCA retorna 2xx numa instância já desconectada. Sempre retorna `400 Bad
Request`.**

O fluxo passa por `ensureClientConnected` (`instance_service.go:118-156`)
antes de tentar o logout de fato:
- Se não há client em memória (caso normal após um logout anterior, que já
  apaga o ponteiro), a função tenta se autocurar chamando `StartInstance` e
  espera 2s; se não conseguir um client conectado nesse intervalo, devolve o
  erro `"no active session found"`.
- Se há client mas ele não está conectado, devolve `"client disconnected"`.
- Qualquer um desses erros sobe até o handler, que responde
  `400` com `{"error": "<mensagem>"}` (`instance_handler.go:233-236`).
- Mesmo no caso extremo de a autocura entregar um client conectado mas ainda
  não logado, o código tem um fallback final que também retorna erro
  (`"ignoring logout as it was not connected"`, `instance_service.go:382`) —
  também vira 400.

**Implicação direta para o adaptador de vocês:** como disseram, ele hoje
recusa qualquer resposta que não seja `2xx`. Precisam tratar `400` de
`/instance/logout` como sucesso equivalente a "já desconectado" — do mesmo
jeito que já fazem com o `record not found` da exclusão. Não há como fazer
isso de forma diferenciada por corpo de erro com segurança total: a mensagem
exata (`"no active session found"` vs. `"client disconnected"`) depende de
timing da tentativa de autocura, então recomendamos tratar **qualquer 400 de
`/instance/logout`** como "já convergiu" — não filtrar pelo texto da
mensagem.

Isso não é comportamento que pretendemos mudar (não pediram mudança e não
vamos oferecer de qualquer forma sem revisar todos os consumidores atuais);
é assim que o servidor se comporta hoje e continuará se comportando.

---

# 4. Deduplicação no envio

**4.1 — Não existe deduplicação nenhuma em `POST /send/text`. Duas chamadas
com o mesmo `id` geram duas mensagens entregues.**

Conferimos exaustivamente `pkg/sendMessage/service/send_service.go`: o `id`
que vocês mandam é usado só como stanza ID passado direto para
`client.SendMessage` do whatsmeow (`send_service.go:2033-2037` e `:2327`).
Não há checagem prévia, não há constraint de unicidade, não há cache de
idempotência nesse caminho — zero referência a repositório ou cache de
mensagens no arquivo inteiro do envio.

(Existe, sim, um mecanismo de dedupe por ID de mensagem no código — mas ele
vive do lado **de entrada**, no handler de recibos (`whatsmeow.go:1637-1675`,
cache TTL de 30 min + constraint única na tabela `message`), servindo só para
não disparar webhook de recibo duplicado. Não tem nenhuma ligação com o envio
de saída.)

**Implicação direta:** a premissa que vocês descreveram — "reenviar após
timeout é seguro se o servidor deduplica por `id`" — **não vale aqui**. Um
reenvio automático com o mesmo `id` **vai** duplicar a mensagem entregue no
WhatsApp do destinatário. A postura atual de vocês (tratar resultado incerto
como "não reenviar, concilia manualmente") está correta e deve continuar
exatamente como está — inclusive para comprovante de empréstimo e aviso de
sobra, como apontaram.

Se quiserem eliminar a conciliação manual no futuro, o caminho seria
implementar idempotência do lado de vocês (ex.: checar se já existe registro
de sucesso local para aquele `id` antes de reenviar) ou nos pedir para
adicionarmos dedupe no `/send/text` — mas isso é mudança de comportamento do
servidor, que vocês explicitamente disseram não estar pedindo agora, então
não implementamos nada aqui, só confirmamos o estado atual.

**4.2 — Não aplicável.** Não existindo dedupe, não há janela de tempo a
declarar.

---

# 5. Estados da instância

**5.1 — A leitura está correta, com uma ressalva importante sobre qual
endpoint vocês consultam.**

Confirmado: com o QR na tela aguardando leitura, o estado é
`Connected: true, LoggedIn: false` — mas **isso vale para `GET
/instance/status`**, não para todos os endpoints que devolvem um campo
`connected`. Ver achado extra em §7.2 — isso não estava na pergunta de vocês
mas afeta diretamente a regra "só `LoggedIn` significa pareado" se a tela
usar outro endpoint.

Em `GET /instance/status`, o par vem direto dos métodos nativos do
whatsmeow: `IsConnected()` reflete só o socket aberto
(`whatsmeow-lib/client.go:643-651`), `IsLoggedIn()` é um flag independente que
só vira `true` ao receber o `<success>` do handshake de autenticação
(`whatsmeow-lib/connectionevents.go:158-162`). No fluxo de QR,
`client.Connect()` abre o socket (`Connected=true`) antes mesmo do loop de QR
começar a exibir códigos (`whatsmeow.go:519` vs. `:548`), então a janela
`Connected=true, LoggedIn=false` cobre de forma confiável todo o tempo de QR
pendente nesse endpoint. `LoggedIn=true` é confiável como "pareado" tanto
para QR novo quanto para reconexão com sessão existente — mesmo handshake
para os dois casos.

Duas situações em que `Connected=true/LoggedIn=false` aparece **sem** QR
disponível (então não podem inferir "mostrar QR" só desse par, precisam
checar se `GET /instance/qr` de fato tem código):
1. Reconexão com sessão já existente (sem QR nenhum) — mesmo socket abre
   antes do handshake completar, mesmo par transitório aparece.
2. Logo após logout ou corte por `QRTimeout`, se a autocura já tiver disparado
   um novo ciclo no meio da consulta.

---

# 6. Sobre o que vocês disseram não estar pedindo

Confirmamos: nenhuma resposta acima envolve mudança de comportamento do
servidor. Onde identificamos comportamento que vale a pena reconsiderar no
futuro (logout não-idempotente, ausência de dedupe em `/send/text`),
registramos como está hoje e deixamos a decisão de mudar para uma conversa
separada, se e quando vocês quiserem propor isso formalmente.

---

# 7. Achados que não foram perguntados, mas afetam o desenho da tela

**7.1 — Risco de race condition em chamadas concorrentes de gerenciamento de
instância.** Os mapas internos que guardam os clients ativos (`clientPointer`,
`myClientPointer`, `killChannel`, em `pkg/whatsmeow/service/whatsmeow.go`) não
têm nenhum lock, apesar de serem lidos/escritos por goroutines de handlers
HTTP concorrentes (`connect`, `disconnect`, `logout`, `qr`, `status`) e pela
goroutine de background do client. Isso é uma condição real do código (falta
de mutex), não uma suposição — o efeito prático (panic ou leitura corrompida)
depende de timing e não testamos sob carga. Recomendação prática: evitem
disparar `connect`/`logout`/`qr` em paralelo para a mesma instância a partir
da tela (ex.: debounce de clique duplo, uma requisição por vez por instância)
até resolvermos isso do nosso lado. Vamos avaliar internamente se corrigimos
com um `sync.Mutex` por instância.

**7.2 — O campo `connected` significa coisas diferentes em endpoints
diferentes.** `GET /instance/status` usa `IsConnected()` (socket aberto,
independente de login). Já `GET /instance/get/{instanceId}` e `GET
/instance/all` computam o campo `connected` a partir de `IsLoggedIn()`
(`instance_service.go:496-500` e `:515-519`) — ou seja, nesses dois,
`connected=false` durante toda a janela de QR pendente, mesmo com o socket já
aberto. Se a tela usar `/instance/all` ou `/instance/get/{id}` para decidir o
que mostrar, tratem o campo `connected` ali como "autenticado", não como
"socket aberto" — e usem especificamente `/instance/status` (com seus dois
campos separados) se precisarem distinguir "QR pendente" de "totalmente
pareado". Isso é inconsistência de nomenclatura no nosso código, não bug de
lógica — mas é fácil de causar confusão numa tela que misture os dois
endpoints, então preferimos avisar antes de vocês tropeçarem nisso.

---

# 8. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 04/09/2026 | Resposta completa às cinco seções de perguntas, toda apoiada em leitura de código (`/opt/evolution-go`) com citação arquivo:linha. Nenhuma pergunta exigiu teste em produção. Dois achados extras não solicitados (§7): ausência de lock nos mapas de client (risco de race em chamadas concorrentes) e inconsistência do campo `connected` entre `/instance/status` e `/instance/get`\|`/instance/all`. |
