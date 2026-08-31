# DR-006 — Decision Request — Conexao do WhatsApp dentro da plataforma

**Data:** 2026-08-31
**Solicitante:** Arquitetura (a pedido do fundador, sessao de 2026-08-31)
**Destinatario:** Fundador
**Status:** **RESOLVIDA** — 2026-08-31
**Efeito:** **reverte** a decisao de `contexto-externo.md` §6.1 (segredo do
Evolution em variavel de ambiente) no que toca ao token da instancia.

---

## Resolucao — 2026-08-31

| Pergunta | Decisao do fundador |
|---|---|
| 1. Quem conecta, e de onde? | **Tela de QR na plataforma.** |
| 2. Onde ficam os segredos? | **Token da instancia cifrado em repouso**, no banco. |
| 3. Para onde aponta o `webhookUrl`? | **Para o agente**, via variavel configuravel — vazia hoje. Preserva §2.2. |
| 4. Quando? | **Ciclo proprio** — revisto em 2026-08-31: **antes do deploy**, nao depois do PLAN-033. Ver nota abaixo. |

### Revisao da Pergunta 4 — 2026-08-31

A resposta original era *"ciclo proprio, depois do PLAN-033 e depois do
IMP-352"*. O fundador reviu no mesmo dia: **a tela entra antes do deploy**, junto
com o resto do que precisa estar pronto.

O que mudou entre a resposta e a revisao, e justifica a mudanca:

- o **IMP-352 fechou** — formato de envio validado contra o provedor real;
- o **VPS foi liberado** e o dominio `tianet.com.br` existe, entao o deploy
  deixou de ser hipotese e virou o proximo marco;
- o tenant e a instancia passaram a existir, tornando a tela construivel de fato.

A parte "ciclo proprio" **permanece**: a tela nao vira emenda ao PLAN-033. Ela
ganhou plano proprio, o [PLAN-034](../../implementation/plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md),
pelo mesmo motivo registrado na resposta original — emendar um desenho que ja foi
refutado por revisao adversarial, sem revisa-lo de novo, repete o erro que aquela
revisao pegou.

O que mudou foi **a ordem**, nao o instrumento.

### O que a ADR-003 simplificou antes desta resolucao

A [ADR-003](../../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md), emitida
no mesmo dia, decidiu o escopo single-tenant do v1. Com isso:

- a opcao "tela por Tenant" da Pergunta 1 caiu sozinha — com um unico usuario,
  "restrita ao administrador" e "o usuario" sao a mesma pessoa;
- a tabela de segredos **por Tenant** deixou de ser necessaria. A
  `evolution_api_key` de gestao continua no ambiente; a plataforma persiste
  apenas o token da instancia que ela mesma criar.

### Por que o token e persistido, e por que cifrado

Se a tela existe, o token **tem** de ir para o banco: sem isso a conexao nao
sobrevive a um restart sem alguem editar o `.env` na mao — que e exatamente o
atrito que a tela vem eliminar.

Cifrado porque esse token nao vaza *informacao*, vaza **capacidade de agir**:
quem o tiver envia, le e desconecta em nome do Credor. O mesmo banco ja guarda
CPF e telefone em texto claro, entao cifrar o token nao muda o perfil de risco do
dump inteiro — protege a diferenca que importa.

### Correcao a este proprio documento

A Pergunta 3 classificava "conectar sem webhook agora" como a pior das tres
opcoes, por deixar "uma janela em que a instancia esta conectada e ninguem recebe
mensagem". **Isso foi escrito antes de confirmar que o agente ainda nao existe.**

Receber e a Fase C (IMP-356), bloqueada. A tal janela e a realidade de hoje, nao
um risco que a opcao cria. A opcao A resolvida — URL configuravel, vazia hoje —
incorpora aquela terceira opcao em vez de descarta-la.

### Fatos externos registrados nesta sessao

- **Dominio:** `tianet.com.br`. **VPS em provisionamento** em 2026-08-31 — o
  IMP-359 deixa de estar bloqueado, e com ele o GATE-E1b.
- Ter dominio proprio torna a opcao B da Pergunta 3 *possivel*, nao mais segura:
  o §2.2 decidiu pela topologia por **superficie de ataque**, nao por falta de
  endereco. Um webhook publico aceita `POST` de qualquer origem, e o proprio
  `contexto-externo.md` registra que `Info.Sender` e forjavel por quem souber a
  URL.
- **Nao verificado:** se o `/instance/connect` aceita `webhookUrl` vazia. O
  contrato nao diz. Uma instancia recem-criada nasce com `"webhook": ""`, o que
  sugere que vazio e representavel — mas isso e inferencia sobre sistema externo,
  a mesma classe de suposicao que produziu o caveat 8.1. **Vira item de
  verificacao junto com o IMP-352**, que exige a mesma ida ao Evolution.

### Ordem acordada

1. **IMP-352** — validar o formato de envio. E o caveat de maior risco, e a tela
   seria construida sobre ele.
2. **IMP-359** — producao, agora destravado pelo VPS.
3. Retomada do PLAN-033 (Fases A e C).
4. **Ciclo proprio da tela de QR**, com o escopo desta resolucao.

### Aviso operacional para o deploy

Com `APP_ENV=production` e sem `EVOLUTION_INSTANCE_TOKEN`, o worker **recusa
subir** (`scheduler_worker.py:342`). Recusa nomeada, de proposito — mas o deploy
precisa do token antes de o worker funcionar.

---

## O pedido

> "Precisamos que o tenant faca um login pelo QR code dentro da nossa
> plataforma, pois o usuario nao tem acesso direto ao diamondgreen."

A justificativa e operacional e correta: se quem opera a TiaNet nao tem conta no
servidor Evolution, mandar essa pessoa escanear o QR **la** nao e um fluxo, e um
impedimento. Hoje conectar um numero exige acesso ao `diamondgreen.com.br`.

Esta DR existe porque atender o pedido **reverte uma decisao ja registrada** e
cria capacidade que nao existe em nenhuma camada — nao porque o pedido seja
questionavel.

---

## O que existe hoje — evidencia, nao memoria

| Camada | Estado verificado em 2026-08-31 |
|---|---|
| Adapter `infrastructure/notifications/whatsapp.py` | so `/send/text` e consulta de status. **Envia**; nao provisiona nem conecta |
| Endpoints backend | nenhum `/instance/create`, `/instance/connect`, `/instance/qr`, `/instance/status` |
| ORM (`infrastructure/db/orm.py`) | nao guarda nada de Evolution — nem `tenant_id`, nem `api_key`, nem token de instancia |
| Frontend | nenhuma tela, nenhum QR. As unicas ocorrencias de "whatsapp" sao **tipo de contato do Devedor** (`devedor-form.client.tsx`, `lancamento-policy.ts`) |
| Configuracao | `EVOLUTION_HOST` e `EVOLUTION_INSTANCE_TOKEN`, lidos uma vez em `worker/scheduler_worker.py:336-343` |

A conexao acontece integralmente **fora da TiaNet**: alguem com acesso ao
Evolution cria a instancia (`/instance/create`, informando um token que o
**chamador** gera), conecta o numero pelo QR (`/instance/connect` + `/instance/qr`)
e so entao o token vai para o `.env` da TiaNet. A plataforma nunca participa
desses passos.

## A decisao que isto reverte

`docs/operations/contexto-externo.md` §6.1, decidida pelo fundador em 2026-08-25:

> "Segredo do Evolution fica em variavel de ambiente, com o limite de uma
> instancia por processo declarado. [...] **No dia em que cada Tenant tiver
> instancia propria do Evolution**, isso vira tabela de segredos com
> criptografia."

E o backlog do PLAN-033, linha 68:

> "v1 opera um Tenant por processo; multi-Tenant exige desenho de segredos
> **fora deste ciclo**."

Ou seja: o dia previsto por aquele documento e hoje. A decisao de 08-25 nao
estava errada — ela declarou a condicao de saida, e a condicao chegou.

---

## Pergunta 1 — Quem conecta uma instancia, e de onde?

**Opcao A — Tela na TiaNet, por Tenant.** A plataforma vira proxy do Evolution:
cria a instancia, pede o QR, mostra na tela, faz polling do status ate conectar.
*Atende o pedido integralmente. Exige tudo da Pergunta 2, endpoints novos no
contrato publico e resolve a Pergunta 3. E o maior escopo dos tres.*

**Opcao B — Tela restrita ao Administrador da Plataforma (recomendada para o
v1).** Mesma mecanica, mas a conexao e privilegio de quem administra a
plataforma — nao de cada Tenant. *Atende o pedido real de hoje (o operador nao
precisa de conta no Evolution) sem abrir provisionamento multi-Tenant. Reduz a
superficie de autorizacao e adia a tabela de segredos por Tenant: um unico
conjunto de credenciais continua servindo enquanto ha um credor.*

**Opcao C — Manter como esta.** Quem tem acesso ao Evolution conecta, e o token
vai ao `.env`. *Custo zero de construcao. Mantem a dependencia de uma pessoa com
acesso ao servidor a cada numero novo ou a cada reconexao — que e exatamente a
dor relatada.*

> A Opcao C so e defensavel enquanto houver **um** numero e reconexao for evento
> raro. Se o WhatsApp cair e precisar reescanear num sabado, a Opcao C significa
> operacao parada ate alguem com acesso ao servidor aparecer.

## Pergunta 2 — Onde ficam os segredos do Evolution?

Se a resposta da Pergunta 1 for A ou B, a plataforma passa a **guardar
credenciais do Evolution**, e nao so a consumir uma.

**Opcao A — Tabela cifrada (obrigatoria para P1=A).** `evolution_tenant_id`,
`evolution_api_key`, `evolution_instance_id` e `evolution_instance_token` por
Tenant, com criptografia em repouso e chave fora do banco. *Migration aditiva,
dominio, repositorio e rotacao de chave. E o desenho que o §6.1 previu.*

**Opcao B — Variavel de ambiente para as credenciais de gestao, tabela so para
o token de instancia (viavel se P1=B).** A `evolution_api_key` do tenant
Evolution continua no ambiente; a plataforma so persiste o token da instancia
que ela mesma criou. *Menos superficie cifrada, menos migration. Aceita o limite
de um tenant Evolution por deploy.*

**Opcao C — Nada persistido; a tela pede a chave a cada uso.** *Evita
armazenamento, mas coloca credencial em formulario e em sessao de browser — pior
que o problema que resolve. Nao recomendada.*

## Pergunta 3 — O conflito do `webhookUrl`

O `/instance/connect` do Evolution **exige** um `webhookUrl` e uma lista de
eventos. Mas `contexto-externo.md` §2.2, decidido em 2026-08-25, diz:

> "**Sem webhook publico** na TiaNet; o agente recebe e chama endpoint
> autenticado."

Conectar instancia pela plataforma esbarra nisso. Tres saidas:

**Opcao A — Apontar o webhook para o agente (recomendada).** A TiaNet chama
`/instance/connect` informando a URL **do agente**, nao dela propria. *Preserva
§2.2 intacto: a TiaNet orquestra a conexao, o agente continua sendo quem recebe.
A plataforma precisa conhecer a URL do agente — configuracao, nao endpoint.*

**Opcao B — Expor endpoint autenticado da TiaNet como webhook.** *Reverte §2.2.
Exige validacao de assinatura do Evolution e superficie publica nova, que foi
justamente o que §2.2 evitou.*

**Opcao C — Conectar sem webhook e registra-lo em outro momento.** *Deixa uma
janela em que a instancia esta conectada e ninguem recebe mensagem. Pior dos
tres para uma operacao que depende de receber.*

## Pergunta 4 — Quando

**Opcao A — Ciclo proprio, depois do PLAN-033 (recomendada).** O PLAN-033 esta
com a Fase B fechada e o restante travado em dois insumos externos (IMP-352 e
IMP-359). Este item nao existe no plano e nao cabe nele sem reabrir desenho.
*Mantem a regra de pre-execucao e nao mistura escopo.*

**Opcao B — Emenda ao PLAN-033.** *Exige nova revisao adversarial do desenho —
a v1.0.0 ja foi refutada com 30 achados, e emendar sem revisar repete o erro que
aquela revisao pegou.*

---

## O que NAO esta bloqueado por esta DR

**O IMP-352 nao depende do QR.** Validar o formato de envio do Evolution — o
caveat 7.1, o unico capaz de fazer entrega correta virar `DESCONHECIDO`, com
prejuizo de escrituracao — se faz hoje, com variavel de ambiente e o numero do
proprio fundador. Nao ha razao para esperar tela nenhuma.

Recomendacao de sequencia: **fechar o IMP-352 primeiro**, com o que ja existe.
Ele elimina um risco real de dados; a tela elimina um atrito operacional. Risco
de dado vem antes de atrito.

---

## Resumo do custo, se P1 = B, P2 = B, P3 = A

| Entrega | Natureza |
|---|---|
| Persistencia do token de instancia | migration aditiva + ORM + repositorio |
| Cliente de gestao do Evolution | `create`, `connect`, `qr`, `status` — separado do adapter de envio |
| Endpoints da plataforma | contrato publico novo; guardrail cobra plano, contadores e snapshot OpenAPI |
| Autorizacao | permissao nova, restrita ao Administrador da Plataforma |
| Tela | QR renderizado, polling de status, estados de erro e expiracao do QR |
| Testes | unitario, contrato, BFF e uma jornada Playwright |

Nada disso e exotico; e o volume que preocupa. Por isso a Pergunta 4.

---

## Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.2.0 | 2026-08-31 | Pergunta 4 revista pelo fundador: a tela entra **antes do deploy**, nao depois do PLAN-033. A parte "ciclo proprio" permanece — materializada no PLAN-034. Mudou a ordem, nao o instrumento. |
| 1.1.0 | 2026-08-31 | **RESOLVIDA.** Tela de QR na plataforma, token cifrado em repouso, webhook para o agente e ciclo proprio. Registra o que a ADR-003 simplificou, corrige a classificacao da opcao C da Pergunta 3, e anota o dominio, o VPS em provisionamento e o item de verificacao do `webhookUrl` vazio. |
| 1.0.0 | 2026-08-31 | Abertura: pedido do fundador para conectar WhatsApp pela plataforma, evidencia do estado atual, conflito com §6.1 e §2.2, quatro perguntas com opcoes e custo. |
