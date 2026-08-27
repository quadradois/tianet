# DR-005 — Decision Request — PII, provedor BYOK, modelo e teto de custo do Copilot TiaNet

**Data:** 2026-08-27
**Solicitante:** Arquitetura (PLAN-033/IMP-358, itens 3, 4 e 10)
**Destinatario:** Fundador
**Status:** **RESOLVIDA** — 2026-08-27
**Bloqueava:** GATE-E1 do PLAN-033; destravado por esta resolucao

---

## Decisao ja tomada pelo fundador em 2026-08-27: BYOK

**O cliente nao usa Anthropic.** O copilot opera em modelo BYOK (Bring Your Own
Key): o cliente traz a propria chave do provedor de IA que escolher — OpenRouter,
NVIDIA NIM ou similar. Tecnicamente, o agente fala a **API compativel com
OpenAI** (chat completions + function calling) contra um endpoint configuravel
(`LLM_BASE_URL`, `LLM_API_KEY`, `LLM_MODEL`): um unico cliente `httpx` cobre
todos esses provedores, e trocar de provedor e configuracao, nunca codigo. A
troca continua sendo decisao registrada, jamais fallback automatico (regra
inviolavel 10 do PLAN-033). Provedor sem function calling confiavel nao e
elegivel.

Essa decisao **agrava** a pergunta 1: com BYOK, o destino da PII varia com o
provedor escolhido pelo cliente — inclusive agregadores como o OpenRouter, onde
o prompt pode transitar por mais de uma empresa. Minimizar o que sai deixa de
ser prudencia e vira a unica postura defensavel.

## Por que o restante e do fundador

Cada mensagem processada envia texto a um fornecedor externo, e esse texto pode
conter nome, CPF, telefone e valores de Devedores reais. Quais campos podem
sair, quanto se paga por mes e por quanto tempo as conversas ficam guardadas sao
decisoes de negocio e de risco. A ADR-016 ja obriga mascarar documento em
**logs**; esta DR decide o que pode ir no **prompt**.

---

## Pergunta 1 — Quais dados podem ir ao provedor de IA?

O contexto Operadora responde perguntas como "quanto o Devedor X deve?". Para
isso o modelo precisa ver, no minimo, nome e valores. A questao e o CPF e o
telefone.

**Opcao A — Minimizacao com mascara (recomendada).** Nome e valores podem ir ao
prompt; CPF vai **mascarado** (`***.***.***-12`) e telefone **truncado**
(`...7766`) — suficientes para a Tia confirmar de quem se fala, inuteis para
reconstruir o dado. O CPF integral so existe dentro do fluxo deterministico de
pre-cadastro (validacao de digitos e unicidade acontecem no backend, que ja faz
isso hoje; o modelo nunca ve o documento completo).
*Custo: nenhum em funcionalidade v1. O unico caso que exigiria CPF no prompt —
busca por documento ditado — vira chamada deterministica sem LLM.*

**Opcao B — Tudo liberado.** Prompt carrega qualquer campo que a API devolva.
*Mais simples, porem cria no fornecedor — que em BYOK pode ser um agregador com
multiplos sub-provedores — um espelho parcial do cadastro; um incidente la vira
incidente seu, e a LGPD olha para o controlador.*

**Opcao C — Nada de PII.** So valores agregados, sem nomes.
*Seguro e quase inutil: "um devedor deve 10.000" nao serve a operacao.*

## Pergunta 2 — Qual provedor/modelo BYOK, e qual teto mensal?

O uso e conversa curta com tool-use — nao exige o modelo mais capaz de nenhum
catalogo, mas **exige function calling confiavel**, que e o criterio
eliminatorio. Estimativa de ordem de grandeza para a operacao atual (uma
operadora, dezenas de conversas/dia): a dezena de reais por mes com um modelo
rapido, nao a centena.

**Opcao A — OpenRouter com um modelo rapido (recomendada), teto de R$ 100/mes.**
O OpenRouter da acesso a dezenas de modelos com uma chave so, o que casa com
BYOK: o cliente escolhe o modelo sem trocar de integracao. Comeca num modelo
economico com bom tool-use; se a qualidade nao bastar, sobe de modelo **por
decisao registrada**, nunca por fallback automatico. Teto duro: atingiu, o
copilot responde mensagem fixa ate o mes virar ou o fundador subir o teto.

**Opcao B — NVIDIA NIM direto, teto de R$ 100/mes.** Endpoint compativel com
OpenAI, sem intermediario agregador — menos empresas vendo o prompt, catalogo
menor de modelos.

**Opcao C — Outro endpoint compativel indicado pelo cliente.** O desenho aceita
qualquer `LLM_BASE_URL` compativel; o cliente informa provedor, modelo e chave,
e a elegibilidade e conferida pelo teste de function calling da Entrega 356-D.

**Responsavel por alterar o teto:** o fundador, por atualizacao desta DR — a
alteracao e administrativa e auditada (Entrega 356-C).

## Pergunta 3 — Retencao de inbox, sessao, mensagem e tool-call

**Opcao A — 90 dias, expurgo automatico (recomendada).** Conversa e material de
operacao, nao registro contabil: a trilha de auditoria (ADR-002) e quem guarda
as escritas para sempre. 90 dias cobrem disputa operacional ("o que eu pedi
semana passada?") sem acumular PII indefinidamente.

**Opcao B — 30 dias.** Menor exposicao, menor memoria de disputa.

**Opcao C — Sem expurgo.** Nao recomendada: PII conversacional crescendo sem
limite e passivo, nao ativo.

---

## Resolucao — 2026-08-27

Decidida pelo fundador. Fecha os itens 3, 4 e 10 do IMP-358 e destrava o
GATE-E1 no que dependia desta DR.

### 1. PII no prompt: **tudo liberado**

O prompt pode carregar qualquer campo que a API devolva, **inclusive CPF
integral e telefone completo de Devedores**.

**Decisao consciente, tomada com o risco na mesa.** A Arquitetura recomendou
minimizacao com mascara e apresentou, antes da decisao, que (a) nenhuma
funcionalidade do v1 perderia nada com a mascara, (b) em BYOK o prompt pode
transitar por agregador com multiplos sub-provedores, e (c) os CPFs sao de
**terceiros** — Devedores que entregaram o documento a operacao de credito, nao
a um provedor de IA, com o fundador como controlador sob LGPD. O fundador
manteve a decisao ciente disso.

**O que esta decisao NAO altera, e continua obrigatorio:**

- **ADR-016 continua valendo para logs.** Esta DR decide o que vai no *prompt*;
  documento pessoal, telefone, token e segredo continuam mascarados ou omitidos
  em log, metrica e trace. Prompt liberado nao e log liberado.
- **Isolamento entre contextos permanece absoluto** (regra inviolavel 5 do
  PLAN-033): o contexto Pre-cadastro segue com zero ferramentas de leitura de
  carteira, e nenhuma resposta a remetente desconhecido contem dado de terceiro.
  A PII liberada circula **somente** no contexto Operadora.
- **A suite adversarial da Entrega 356-D nao afrouxa.** Prompt injection e
  exfiltracao continuam falhando fechados; o que muda e o conteudo permitido no
  prompt legitimo, nao o que um atacante pode extrair.

**Consequencias que passam a existir:**

- a escolha do provedor no item 2 deixa de ser so tecnica e vira **decisao de
  tratamento de dado pessoal**: politica de retencao do provedor, uso para
  treino, regiao de processamento e sub-processadores entram no criterio;
- um incidente no provedor passa a ser incidente de dados do controlador;
- se um Devedor exercer direito de exclusao, o dado ja enviado ao provedor esta
  fora do alcance do sistema.

### 2. Provedor e modelo: **decisao adiada, com criterio fixado**

O provedor sera escolhido junto com o cliente. O desenho aceita qualquer
`LLM_BASE_URL` compativel com a API OpenAI.

**Criterios de elegibilidade, ja fixados:**

- **function calling confiavel** — eliminatorio, conferido pelo teste da
  Entrega 356-D antes de qualquer uso real;
- por causa da decisao 1, o provedor precisa ter **politica de dados aceitavel**
  para PII de terceiros: retencao declarada, sem uso para treino, e
  sub-processadores conhecidos.

Enquanto nao houver escolha, `LLM_BASE_URL`, `LLM_API_KEY` e `LLM_MODEL` ficam
sem valor e o contexto conversacional (Fase C) nao sobe. As Fases A e B nao
dependem de LLM e seguem normalmente.

### 3. Teto mensal de custo: **nao estipulado**

Nao ha teto em moeda. A Entrega 356-C **muda de forma, mas nao desaparece**:

- **sai** o bloqueio por teto mensal — nao ha valor a comparar;
- **fica** o rate limiting por instancia, remetente e contexto, com teto de
  concorrencia. Ele nunca foi sobre dinheiro: protege contra abuso, rajada e
  loop, e continua obrigatorio;
- **fica** a medicao de consumo — tokens e custo estimado seguem em metrica e
  log. Sem teto o sistema **observa e alerta**, em vez de bloquear;
- o gasto passa a ser limitado pelo que o proprio provedor permitir na chave do
  cliente. Se o cliente quiser limite duro, o caminho e o painel do provedor,
  nao o codigo.

Retirar o teto **sem retirar o rate limit** e deliberado: sem rate limit, um
unico remetente em loop consumiria a chave do cliente ate o provedor cortar.

### 4. Retencao de inbox, sessao, mensagem e tool-call: **90 dias**

Expurgo automatico aos 90 dias, conforme recomendado. A trilha de auditoria da
ADR-002 nao e afetada: escritas continuam append-only e permanentes.

Com a decisao 1, esta retencao passa a valer sobre **conversas com PII
integral** — o que torna o expurgo automatico um controle de risco, nao apenas
higiene de armazenamento. Ele nao pode ser silenciosamente desligado.

---

## Historico

| Data | Evento |
|---|---|
| 2026-08-27 | Aberta pela Arquitetura com opcoes e recomendacao, conforme IMP-358. |
| 2026-08-27 | **RESOLVIDA** pelo fundador: PII liberada no prompt (ciente do risco, com ADR-016 e isolamento de contexto intactos), provedor adiado com criterios fixados, sem teto de custo (rate limit e medicao permanecem), retencao de 90 dias. |
| 2026-08-27 | Reescrita para BYOK apos decisao do fundador: o cliente nao usa Anthropic; provedor via endpoint compativel com OpenAI (OpenRouter, NVIDIA NIM ou similar), chave do cliente. Perguntas 1 e 3 inalteradas; pergunta 2 passa a escolher provedor+modelo. |
