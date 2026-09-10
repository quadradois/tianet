# Verificação da adoção do Harness

**Data:** 2026-09-08
**Status:** VERIFICADO_COM_RESSALVAS

## Escopo

Adaptação do Harness ao TiaNet conforme [HARNESS-ADOPTION.md](HARNESS-ADOPTION.md), sem mudança de código do produto ou normas da SPEC-004.

## Evidências

| Requisito | Check | Resultado observado | Status |
|---|---|---|---|
| Entrada portátil e cinco workflows | npm run harness:check | Estrutura, links, sintaxe, envelope, namespace e comandos npm aprovados | VERIFICADO |
| Contratos OpenCode e baseline | Test-OpenCodeCoordination.ps1 | 38 checks aprovados, zero falhas; fixtures sem rede | VERIFICADO |
| Validador detecta regressão real | Test-HarnessValidation.ps1 | 3 checks aprovados: baseline válido, mutação indevida no template e link quebrado | VERIFICADO |
| Compatibilidade documental | npm run docs:validate | Zero erros; 36 avisos em documentos existentes, sem apontamento nos novos documentos do Harness | VERIFICADO_COM_RESSALVAS |
| Regressão da ferramenta documental | npm run docs:test | Nove suítes existentes concluídas com exit code zero | VERIFICADO |
| Integração real | Invoke-OpenCodeTask e Add-OpenCodeReview | TIANET_HARNESS_OK 42, exit code 0, 19.298 ms, zero changedPaths/scopeViolations; review APROVADA | VERIFICADO |
| Revisão agentic | Parecer inicial e complementar | BLOCKER técnico corrigido e reavaliado; nenhum bloqueio aberto | VERIFICADO |
| Preservação de escopo | git diff --check e inspeção de status/diff | Somente arquivos do Harness e links/comandos de entrada; nenhum arquivo de produto ou norma alterado | VERIFICADO |

O teste real usou `opencode/muse-spark-1.3-contributor-free`, envelope temporário sintético e task ID `3ae97e65-7184-4a15-a76e-78d2c2acea05`. Execução e review foram observados na telemetria local TiaNet, fora do Git. A resposta sintética valida conectividade e coordenação, não capacidade geral de implementação do modelo.

O [parecer reconciliado](HARNESS-AI-REVIEW.md) registra achados e adjudicação. A aprovação declarada é do resultado desta adoção, não dos gates do produto.

## Checks não executados e limites

Não houve recertificação backend/frontend, deploy, commit ou push. O produto não foi alterado. A descoberta automática das novas skills depende de como a sessão carrega o catálogo; a leitura direta de cada SKILL.md já permite aplicar o workflow.

READ_ONLY observa mudanças versionáveis após execução e não é sandbox. Não cobre todo estado ignorado, não impõe timeout nem deduplica tentativas. Campos livres da telemetria dependem de sanitização pelo coordenador. Essas limitações permanecem explícitas no HARNESS e não foram promovidas a garantias técnicas.
