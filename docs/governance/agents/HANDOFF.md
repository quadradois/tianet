# Retomada do Harness — TiaNet

**Data:** 2026-09-08
**Escopo:** Harness, conclusão verificada do IMP-370 e candidata local formada; sem push ou publicação.

## Como retomar

1. Leia [AGENTS.md](../../../AGENTS.md), [HARNESS.md](HARNESS.md) e a SPEC-004.
2. Confira branch, HEAD e working tree. Não presuma que o checkout coincide com a última entrega publicada.
3. Consulte [handoffs versionados](../handoffs) e o plano/backlog relacionado à tarefa. Se houver ponteiro pessoal `~/HANDOFF-VIGENTE.md`, ele é auxiliar: resolva-o e confira a informação no Git. Um clone não depende desse arquivo local.
4. Use os workflows em `.agents/skills`; para execução de IMPs, mantenha o ALP-001 e os gates do plano.

## Estado observado na adoção

O checkout estava em `feat/imp-370-worker-le-o-token`, HEAD `b737c20`, sem alterações versionáveis antes desta adoção. O handoff de [2026-09-04](../handoffs/2026-09-04-handoff-imp-371-e-os-testes-que-nao-provavam-nada.md) informa IMP-370 pendente, mas o HEAD já contém uma implementação desse item. Essa diferença exige conferir o [PLAN-034](../../implementation/backlogs/PLAN-034-execution-backlog.md) e suas evidências antes de retomar produto; este Harness não declara o item integrado, certificado ou publicado.

## Entrega e próxima ação

O proprietário aprovou o alerta persistente dentro do TiaNet e a execução por slices em 2026-09-08. O [plano do IMP-370](PLANO-IMP-370-AVISO-QUEDA.md) foi concluído no working tree: a queda é persistida de forma idempotente sob o lock do tenant, limpa na reconexão, exposta no contexto e exibida por banner global acessível sem dispensa manual. A [verificação](VERIFICACAO-IMP-370-AVISO-QUEDA.md) registra migration real, backend, frontend, build e Playwright verdes; G10 e G11 estão fechados e o GATE-E do produto permanece aberto.

O [PLAN-034](../../implementation/plans/PLAN-034-conexao-do-whatsapp-na-plataforma.md) e seu [backlog](../../implementation/backlogs/PLAN-034-execution-backlog.md) foram reconciliados na versão 1.2.0 com o comportamento e as evidências do IMP-370. O [checklist de entrega do TiaNet](CHECKLIST-ENTREGA-TIANET.md) acompanha a sequência restante.

A [verificação da candidata](VERIFICACAO-RELEASE-CANDIDATA-TIANET.md) concluiu os gates locais sobre `b99cb81` antes da reconciliação exclusivamente documental deste handoff. Backend, migration, build, testes frontend e a matriz principal de 156 cenários Playwright passaram; dez reexecuções focais também foram aprovadas. As 56 evidências visuais foram estabilizadas, revistas e reconciliadas por SHA-256 no [relatório aditivo](../../audits/reports/tianet-release-candidate-visual-recertification-2026-09-08.md). Docker e a stack descartável foram encerrados após os testes.

O proprietário autorizou a formação dos quatro commits locais em 2026-09-08. A série ficou organizada em `7d3a5e3` (Harness), `f1b3c8d` (backend e migration), `9473e0d` (frontend e testes) e o commit documental que contém este handoff e as evidências visuais. Nenhum push, PR, merge ou deploy foi realizado.

A próxima ação é identificar a imagem de release, preparar o procedimento de rollback e inspecionar a VPS. Nenhuma publicação foi feita; push, PR, merge e deploy continuam dependentes de autorização do proprietário.

Veja [plano de adoção](HARNESS-ADOPTION.md) e [verificação](HARNESS-VERIFICATION.md). O Harness pode orientar novas demandas a partir da raiz. A próxima tarefa de produto deve ser delimitada pelo proprietário e conciliada com o backlog atual; não há autorização de deploy ou execução automática do próximo plano nesta entrega.
