# Retomada do Harness — TiaNet

**Data:** 2026-09-09
**Escopo:** WhatsApp local conectado e discovery do Agentic concluido; proxima
sessao dedicada a analise de capacidade e potencial, sem implementacao.

## Como retomar

1. Leia [AGENTS.md](../../../AGENTS.md), [HARNESS.md](HARNESS.md) e a SPEC-004.
2. Confira branch, HEAD e working tree. Não presuma que o checkout coincide com a última entrega publicada.
3. Consulte [handoffs versionados](../handoffs) e o plano/backlog relacionado à tarefa. Se houver ponteiro pessoal `~/HANDOFF-VIGENTE.md`, ele é auxiliar: resolva-o e confira a informação no Git. Um clone não depende desse arquivo local.
4. Use os workflows em `.agents/skills`; para execução de IMPs, mantenha o ALP-001 e os gates do plano.

## Estado observado

O checkout esta em `feat/imp-370-worker-le-o-token`, HEAD `6ae2f68`, com
alteracoes versionaveis e discoveries ainda sem commit. O conector WhatsApp foi
observado conectado localmente. Preserve o working tree e, em especial, o CSV
nao relacionado listado no handoff vigente.

## Handoff vigente e proxima acao

Leia o
[handoff de capacidade do Agentic](../handoffs/2026-09-09-handoff-agentic-capability-discovery.md)
e o
[raio X do Agentic](../../audits/discoveries/agentic-atendimento-relatorios-as-is-to-be-2026-09-09.md).

A proxima sessao deve executar um discovery estrategico do potencial do TiaNet:
inventariar capacidades, personas, jornadas, ferramentas possiveis, valor,
riscos e controles antes de aceitar o desenho atual como limite. Use o grafo e
as fontes atuais. Como o impacto e `PRESENT`, convoque `ai_architect` em missao
delimitada e `READ_ONLY`.

Nao implemente o IMP-356, nao altere prompts e nao feche gates nesse discovery.
Commit, push, PR, merge e deploy continuam dependentes de autorizacao do
proprietario.

## Decisao vigente 2026-09-10 (rota A)

Trilha auth do `d9c1` portada e verificada (ADR-020, piloto auth, `agent`
isolado, API/RBAC, tela). Inferência pela **API OpenAI, chave de projeto,
`gpt-4o-mini` candidato** (chave validada; $5 de credito). OAuth fica só
diagnóstico; demais provedores em espera. Proximo slice de produto: prontidão
IMP-359 (GATE-E1b), com Operadora em fail-closed ate prova de origem.
