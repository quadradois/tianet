# Adoção do Engineering Harness — TiaNet

**Data:** 2026-09-08
**Status:** Concluído localmente
**Classificação:** STANDARD
**Impacto agentic:** PRESENT
**Gatilhos:** workflows e instruções de agentes; executor auxiliar e contexto de inferência.

## Autorização e limites

O proprietário solicitou nesta sessão identificar o Harness do Nox–Viagens e aplicá-lo ao repositório de empréstimos. Essa autorização cobre a adaptação local do processo existente e sua verificação. Não aprova funcionalidades, gates de produto, commit, push, deploy, contratação ou mudanças nas regras da SPEC-004.

## Descoberta e decisão de adaptação

A origem possui cinco workflows, políticas de evidência, classificação G0–G11, revisão AI Architect Senior, templates e coordenação efêmera OpenCode. O TiaNet já possui SPEC-004, ALP-001, ADRs, planos e backlogs. A alternativa de copiar a governança do Nox integralmente criaria fontes concorrentes e importaria congelamentos e permissões de outro produto. A adaptação escolhida mantém essas fontes do TiaNet e instala somente o mecanismo reutilizável de engenharia.

O AGENTS.md será mapa portátil de navegação; configuração pessoal continua fora do versionamento conforme a SPEC-004. Os workflows referenciam a governança existente. G0–G11 organizam o trabalho do executor e não substituem GATE-E nem aprovam o backlog. A telemetria usa o namespace local TiaNet. O modelo inicial mantém Muse Spark 1.3 com o identificador que respondeu ao teste desta sessão: `opencode/muse-spark-1.3-contributor-free`.

## Slices e aceite

| Slice | Entrega | Aceite / verificação |
|---|---|---|
| S1 | AGENTS, workflows, políticas e templates adaptados | Links resolvem; fontes do TiaNet preservadas; nenhuma dependência de C:/Viagens |
| S2 | Executor, review, telemetria e fixtures | Schema v1/v2, falhas, isolamento, preservação de baseline e review verificados sem rede |
| S3 | Validador estrutural, comandos, documentação e handoff | Validação documental e testes existentes passam; teste negativo detecta quebra; revisão especializada reconciliada |

## Invariantes e avaliação

- Nenhum arquivo de produto, migração, credencial ou configuração pessoal precisa mudar.
- OpenCode recebe contexto mínimo e sanitizado. Dados financeiros reais, pessoas, segredos e conversas não entram em testes.
- READ_ONLY compara estado Git após execução; não é sandbox, não observa todo arquivo ignorado e não impede acesso de leitura.
- Aprovação depende de revisão do coordenador, nunca somente de exit code ou texto do modelo.
- Telemetria não guarda prompt, resposta, nomes de arquivos ou conteúdo de negócio.
- Aprovação e termos de provedores do Nox não são importados como autorização permanente para dados do TiaNet.

## Rollback

Reverter somente os arquivos desta adoção após revisar o diff. Não usar reset, limpeza ampla, nem apagar alterações de outras tarefas. A telemetria fica fora do Git e não afeta o produto. Não alterar os backlogs para acomodar o Harness.

## Revisão e evidências

O AI Architect Senior revisou a adaptação em missão somente leitura; o [parecer reconciliado](HARNESS-AI-REVIEW.md) registra o bloqueio inicial, correções, aprovação complementar e adjudicação técnica. Evidências em [HARNESS-VERIFICATION.md](HARNESS-VERIFICATION.md).

## Progresso

- Descoberta concluída; adaptação local autorizada pelo pedido do proprietário.
- S1–S3 concluídos e verificados localmente; nenhuma porta do produto fechada por esta adoção.
- Ajustes técnicos identificados na verificação: SHA256 .NET para funcionar no PowerShell filho do npm; review recusa checks falhos/pendentes; limpeza das fixtures valida o destino temporário antes de remover.
