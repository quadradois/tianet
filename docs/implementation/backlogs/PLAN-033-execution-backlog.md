# PLAN-033-EXEC - Copilot TiaNet

**ID:** PLAN-033-EXEC

**Versao:** 1.0.0

**Status:** Desenhado - aguardando abertura de execucao

**Origem:** decisao do fundador em 2026-08-26 de dar forma ao segundo operador
previsto no `FOUNDATION-001 §3.1`, sobre a base recertificada do PLAN-032

**Base:** `origin/master` em `6fe7861` (merge do PR #27)

---

# 1. Contexto

A Tia opera uma carteira de credito pelo WhatsApp e pela memoria. O sistema tem
105 operacoes de API, fila de cobranca, agenda e relatorios — tudo atras de uma
interface web. O Copilot e a ponte: **deixa a operadora conversar com o sistema
no canal onde ela ja vive**, e faz o sistema falar primeiro quando ha algo a
dizer.

Este plano **nao comeca do zero**, e reconhecer isso e metade do desenho:

| Ativo existente | Onde | O que destrava |
|---|---|---|
| Agente como segundo operador | `FOUNDATION-001 §3.1` | a visao ja e oficial |
| Topologia sem webhook publico | `contexto-externo.md` §2.2 (decisao de 2026-08-25) | Evolution -> agente -> endpoint autenticado |
| Transporte WhatsApp | `EvolutionWhatsAppNotificationChannel` (IMP-346) | envio pronto, com o caveat de formato |
| Fila de cobranca por estado | IMP-331, `ConsultarFilaCobranca` | fonte do resumo diario sem recalculo |
| Calendario no backend | `proximo_acerto_em` (IMP-326) | vespera sem calcular data no copilot |
| Scheduler duravel com retry | `TIPO_JOB_*` + worker | notificacao agendada e o mesmo padrao do comprovante |
| Preferencia de notificacao | `PreferenciaNotificacaoORM` | opt-in do devedor ja tem entidade |
| `credor_whatsapp` | `Configuracao` (IMP-332) | destino do resumo ja tem chave |
| Idempotencia + auditoria em toda escrita | IMP-333/334 | acoes do copilot ficam na trilha como as de qualquer operador |

**A visao do IMP-347 e absorvida por este plano** (Fase A). O IMP-347 deixa de
existir como item avulso.

---

# 2. Regras inviolaveis

Estas nao sao preferencias — sao as regras que o PLAN-032 confirmou, aplicadas
ao copilot:

1. **O copilot nunca calcula dinheiro.** Saldo, juro e distribuicao vem do
   Motor, e o copilot **repete** a resposta da API. Duplicar regra no agente
   daria dois lugares para divergir — a mesma razao pela qual o frontend nao
   calcula calendario.
2. **O copilot nunca aprova o que ele mesmo propos.** Pre-cadastro e proposta
   nascem pendentes; a decisao e do Credor, sempre.
3. **O copilot e um Usuario, com perfil proprio e permissoes minimas.** Cada
   acao dele entra na trilha de auditoria com identidade propria — nunca com a
   identidade da Tia, nunca como superusuario.
4. **Escrita financeira por chat nao entra no v1.** Registrar pagamento,
   estornar, renegociar: fora. Estorno e renegociacao, fora de qualquer versao
   sem confirmacao humana explicita.

---

# 3. Fase 0 - Fundacao (bloqueia tudo)

### IMP-352 - Validar o formato de envio do Evolution

- **Objetivo:** fechar o caveat 4.1 do handoff vigente. O payload
  `{number, text, id}` e o criterio de aceite `data.Info.ID` vieram de
  documentacao externa, nao do contrato auditado. Se divergirem, todo envio
  bem-sucedido e classificado como `DESCONHECIDO` — o canal do copilot inteiro
  nasce com escrituracao cega.
- **Execucao:** um envio real contra a instancia de producao, para o numero do
  proprio fundador (decisao de 2026-08-25: nao ha ambiente de teste). Ler a
  resposta crua, conferir `data.Info.ID`, ajustar `_classificar_resposta` se
  divergir.
- **Depende de:** numero do fundador e `EVOLUTION_INSTANCE_TOKEN` no ambiente.
  **Ja solicitados; e o unico item que espera insumo externo.**
- **Criterio de pronto:** resposta real documentada no
  `CRM_EVOLUTION_CONTRACT.md` ou em adendo; classificador conferido contra ela;
  caveat 4.1 fechado no handoff.

---

# 4. Fase A - O sistema fala primeiro (sem IA)

Nenhum item desta fase usa LLM. Sao textos de template sobre dados que a API ja
serve — o que os torna baratos, deterministas e testaveis como qualquer job.

### IMP-353 - Resumo diario ao Credor

- **Objetivo:** a visao registrada do fundador: "hoje vence o Devedor 01, saldo
  10.000, juros 5%, 500 a receber; Devedor 02, saldo 11.000, 5%, 550".
- **Desenho:** job diario novo (`TIPO_JOB_RESUMO_DIARIO`), semeado pelo mesmo
  padrao do `SemeadorDiarioCobranca`. Le a fila de cobranca (IMP-331) e os
  saldos do Motor, monta o texto por template e envia ao `credor_whatsapp` pelo
  canal existente. **Nada e calculado no job** — os valores vem prontos.
- **Idempotencia:** um job por data, `origem_tipo` proprio — replay do seed nao
  duplica o resumo, como a varredura de cobranca ja garante para si.
- **Criterio de pronto:** teste de integracao no molde do
  `test_entrega_comprovante.py` — semeia, roda o worker, observa o envio e o
  `RegistroComunicacao`; dia sem vencimento nao envia nada.

### IMP-354 - Aviso de vespera ao devedor

- **Objetivo:** "amanha e o dia do pagamento, saldo 10.000, juros 5%, 500".
- **Desenho:** o mesmo seed diario enfileira um job por emprestimo cujo
  `proximo_acerto_em` seja amanha. Destinatario e o contato WhatsApp
  preferencial do Devedor; **respeita `PreferenciaNotificacao`** — devedor que
  nao consentiu nao recebe, e a ausencia de consentimento e auditada como o
  `enfileirar.ignorado` do aviso de sobra ja faz.
- **Criterio de pronto:** teste cobrindo os tres caminhos — envia na vespera,
  nao envia fora dela, nao envia sem preferencia — e retry reusando a mesma
  chave idempotente.
- **Nota de operacao:** esta fase pressupoe a stack no ar todos os dias. Roda
  em qualquer lugar onde o compose rode; o servidor em contratacao e o
  pre-requisito de operacao continua, nao de implementacao.

---

# 5. Fase B - Identidade do copilot

### IMP-355 - Rota de criacao de usuario e perfil do copilot

- **Objetivo:** fechar a lacuna achada em 2026-08-26: **nao existe rota para
  criar usuario**. Sem ela, o copilot agiria com a identidade de outrem — e a
  trilha de auditoria mentiria sobre quem fez o que.
- **Escopo:** `POST /iam/usuarios` (protegido, `Idempotency-Key`, permissao
  nova de gestao de usuarios), criando usuario com credencial definida pelo
  administrador — **sem ressuscitar o fluxo de token de ativacao** que o
  IMP-351 removeu; o caminho e o `definir credencial na criacao`, como a CLI de
  bootstrap ja faz. Perfil `copilot` no catalogo com o minimo: leituras das
  telas operacionais + criacao de devedor e proposta. Nada de Motor-escrita,
  estorno, IAM ou configuracao.
- **Efeito no contrato publico:** aditivo (uma operacao, schemas novos).
  Snapshot, matriz e contadores seguem o rito da §9.10 do PLAN-032 — categoria
  por categoria, sem reescrever historico.
- **Criterio de pronto:** teste de que o perfil `copilot` **nao** alcanca as
  operacoes proibidas; auditoria registrando o ator correto.

---

# 6. Fase C - Copilot conversacional (leitura)

### IMP-356 - Servico de conversa com resposta ancorada na API

- **Objetivo:** "quanto o Devedor X deve?", "quem vence hoje?", "como foi o
  mes?" — respondidos no WhatsApp, com dados que vem dos GETs.
- **Desenho:** processo novo no **mesmo repositorio e mesmo compose** (como o
  worker), nao um repositorio novo — um fundador, um CI, um deploy. Recebe as
  mensagens do Evolution, conversa via API da Anthropic com **tool-use restrito
  aos endpoints GET** autenticado como o usuario `copilot`, e responde pelo
  canal de envio existente.
- **Guardrail central:** as ferramentas do agente sao a unica fonte de numeros.
  Resposta monetaria sem tool-call correspondente e defeito, e o teste do
  servico deve provar isso com transcript gravado.
- **Decisoes de implementacao (nao de desenho):** modelo (custo x qualidade),
  janela de contexto por conversa, e o mecanismo de recepcao junto ao Evolution
  — o contrato preve webhook de mensagem recebida; o agente e quem o expoe,
  nunca a TiaNet (topologia decidida).
- **Depende de:** IMP-352 (canal validado), IMP-355 (identidade), e **servidor
  provisionado** — o agente precisa ser alcancavel pelo Evolution.

---

# 7. Fase D - Pre-cadastro conversacional

### IMP-357 - Devedor novo entra pelo WhatsApp, Credor aprova

- **Objetivo:** o papel original do agente no `FOUNDATION-001`: colher nome,
  documento e contato na conversa, criar o pre-cadastro e submeter ao Credor.
- **Desenho:** reusa `DevedorCadastroService` e `PropostaComercialService` — o
  copilot cria com o proprio usuario, em estado pendente, e o Credor decide na
  interface (ou, mais tarde, respondendo ao proprio copilot). Validacao de CPF
  e unicidade ja sao do dominio; o agente nao as reimplementa.
- **Criterio de pronto:** jornada completa em teste — conversa simulada,
  pre-cadastro criado, aprovacao pelo Credor, e a trilha mostrando os dois
  atores distintos.

---

# 8. Fora do escopo, declarado

- **Escrita financeira por chat** (registrar pagamento por conversa): candidata
  a v2, somente com confirmacao humana explicita por operacao. Nao entra aqui.
- **Estorno e renegociacao pelo copilot:** nunca, em nenhuma versao, sem humano.
- **IMP-348** (dispatcher de `EventPublisher`): continua fora, sem consumidor.

---

# 9. Ordem de execucao e dependencias

| Ordem | Item | Depende de |
|---|---|---|
| 1 | IMP-352 | numero + token do fundador (ja solicitados) |
| 2 | IMP-353, IMP-354 | IMP-352; implementaveis ja, operam quando houver servidor |
| 3 | IMP-355 | nada — pode andar em paralelo com a Fase A |
| 4 | IMP-356 | IMP-352, IMP-355, servidor provisionado |
| 5 | IMP-357 | IMP-356 |

O servidor em contratacao e pre-requisito de **operacao** das Fases A-D e de
**implementacao** apenas da C em diante. As Fases 0, A e B podem ser
codificadas e certificadas antes dele existir.

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-26 | Desenho inicial: quatro fases sobre os ativos do PLAN-032, IMP-347 absorvido pela Fase A, regras inviolaveis herdadas do ciclo, escopo negativo declarado. |
