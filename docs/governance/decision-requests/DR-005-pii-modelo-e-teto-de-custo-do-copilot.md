# DR-005 — Decision Request — PII, modelo e teto de custo do Copilot TiaNet

**Data:** 2026-08-27
**Solicitante:** Arquitetura (PLAN-033/IMP-358, itens 3, 4 e 10)
**Destinatario:** Fundador
**Status:** **ABERTA**
**Bloqueia:** GATE-E1 do PLAN-033; nenhum codigo das Fases A-D antes da resolucao

---

## Por que esta decisao e do fundador

O copilot conversa via API da Anthropic. Cada mensagem processada envia texto a
um fornecedor externo, e esse texto pode conter nome, CPF, telefone e valores de
Devedores reais — dados da operacao de credito. Quais campos podem sair, quanto
se paga por mes e por quanto tempo as conversas ficam guardadas sao decisoes de
negocio e de risco, nao de implementacao. A ADR-016 ja obriga mascarar documento
em **logs**; esta DR decide o que pode ir no **prompt**.

---

## Pergunta 1 — Quais dados podem ir a Anthropic?

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
*Mais simples, porem cria no fornecedor um espelho parcial do cadastro; um
incidente la vira incidente seu, e a LGPD olha para o controlador.*

**Opcao C — Nada de PII.** So valores agregados, sem nomes.
*Seguro e quase inutil: "um devedor deve 10.000" nao serve a operacao.*

## Pergunta 2 — Qual modelo, e qual teto mensal?

O uso e conversa curta com tool-use — nao exige o modelo mais capaz do
catalogo. Estimativa de ordem de grandeza para a operacao atual (uma operadora,
dezenas de conversas/dia): a dezena de reais por mes com um modelo rapido, nao a
centena.

**Opcao A — Modelo rapido da geracao atual (recomendada), teto de R$ 100/mes.**
Comeca no modelo mais barato da familia vigente (hoje, classe Haiku); se a
qualidade das respostas nao bastar, sobe um degrau (classe Sonnet) **por decisao
registrada**, nunca por fallback automatico — a regra inviolavel 10 do PLAN-033
proibe troca automatica. Teto duro: atingiu, o copilot responde mensagem fixa de
indisponibilidade ate o mes virar ou o fundador subir o teto.

**Opcao B — Modelo intermediario direto, teto de R$ 300/mes.** Menos risco de
resposta fraca, custo maior desde o primeiro dia.

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

## Resolucao

*(a preencher pelo fundador; a resolucao fecha o item 3, 4 e 10 do IMP-358)*

---

## Historico

| Data | Evento |
|---|---|
| 2026-08-27 | Aberta pela Arquitetura com opcoes e recomendacao, conforme IMP-358. |
