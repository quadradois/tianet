# Engineering Harness — TiaNet

**Status:** Instalado; evidências em [HARNESS-VERIFICATION.md](HARNESS-VERIFICATION.md).

## Finalidade e fontes

Permitir continuidade entre sessões por **Discover → Architect → Plan → aprovação aplicável → Execute → Verify**, com slices, evidência e handoff. Origem: Harness Nox–Viagens; adaptação e autorização registradas em [HARNESS-ADOPTION.md](HARNESS-ADOPTION.md).

A [SPEC-004](SPEC-004-regras-normativas-do-codigo.md) rege o código. O [ALP-001](../agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md) rege execução do backlog. As políticas aqui não mudam a hierarquia documental nem o produto. Configurações pessoais, credenciais, sessões e caminhos de máquina continuam locais, conforme a separação da SPEC-004 §1.2. AGENTS e skills são uma distribuição portátil do processo compartilhado, referenciando as normas em vez de duplicá-las.

## Navegação e uso

| Superfície | Responsabilidade |
|---|---|
| [AGENTS.md](../../../AGENTS.md) | Mapa de entrada |
| [.agents/skills](../../../.agents/skills) | Cinco workflows, invocáveis por nome quando descobertos pela sessão |
| [.agents/policies](../../../.agents/policies) | Classificação, evidência, triagem e revisão especializada |
| [.agents/templates](../../../.agents/templates) | Formatos auxiliares e envelope OpenCode |
| [scripts/harness](../../../scripts/harness) | Verificação e coordenação efêmera |
| [HANDOFF.md](HANDOFF.md) | Retomada e fontes de estado |

Na sessão atual, leia o SKILL.md do workflow se o catálogo ainda não o exibir. Não é necessário um servidor persistente para usar os scripts. Para uma mudança pequena já autorizada, aplique o processo mínimo; para mudança material, mantenha as decisões e aprovações exigidas pelo plano. G0–G11 nunca substituem GATE-E.

## Verificações locais

```powershell
npm run harness:check
npm run harness:test
npm run docs:validate
```

`harness:check` valida estrutura, links, sintaxe PowerShell, envelope e integração documental. `harness:test` executa fixtures sem rede: valida schemas, detecta mudanças no working tree/índice/HEAD, verifica review e telemetria concorrente. Commits dos testes existem somente em repositórios temporários de fixture.

Para produto, selecione os checks materiais do plano: `uv run pytest`, Ruff/Black/Mypy no escopo aplicável, e os scripts frontend de lint, typecheck, unit, component, contract, BFF e Playwright. Leia CONTRIBUTING e o plano antes de executá-los. O comando atual `gate:full` termina com restauração de evidências via Git; não o use cegamente em árvore com trabalho alheio. Execute checks individuais preservando evidências. Instalar o Harness não recertifica o produto.

## Coordenação OpenCode

1. Copie o [envelope](../../../.agents/templates/opencode-task.json) para um diretório temporário fora do repositório. Preencha UUID, objetivo único, paths, baseline, critérios, checks, proibições e triagem.
2. Use `READ_ONLY` como padrão. `SCOPED_WRITE` é reservado ao slice de implementação autorizado. Para `ai_architect`: `PRESENT`, gatilhos, `architect`, agente `plan` e `READ_ONLY` são obrigatórios.
3. Confira o identificador com `opencode models opencode`. O Muse Spark 1.3 respondeu nesta sessão pelo ID `opencode/muse-spark-1.3-contributor-free`; disponibilidade futura não é garantida.
4. Execute uma tentativa e revise o resultado observado:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/harness/Invoke-OpenCodeTask.ps1 -EnvelopePath <temporario/envelope.json>
```

O script resolve a raiz a partir de sua própria localização. `-RepositoryRoot` permite apontar uma fixture ou checkout explícito. Registre review com `Add-OpenCodeReview.ps1`, informando TaskId, Attempt, Workflow, Classification, Model, Outcome e contagens reais de checks. `Get-OpenCodeTelemetry.ps1` apresenta o agregado.

São no máximo três tentativas por tarefa: inicial e duas correções; a primeira correção permanece no mesmo modelo, a segunda exige decisão de trocar modelo ou reduzir escopo. Não há retry automático no coordenador. O executor valida o número, mas não mantém histórico para impedir chamadas duplicadas; o CLI/provedor pode ter retries internos. Não há timeout implementado pelo wrapper: o coordenador deve acompanhar e interromper uma chamada sem progresso. Mudar budgets, roteamento ou controles exige triagem, não ajuste silencioso.

## Revisão, privacidade e limites

Triagem `PRESENT` convoca AI Architect Senior em missão somente leitura, por subagente delimitado ou OpenCode efêmero. O [template especializado](../../../.agents/templates/ai-architect-review.md) separa parecer, review do coordenador e adjudicação. `BLOCKER` aberto impede avanço; o especialista não fecha gates. O executor valida consistência do envelope, não interpreta semanticamente decisões nem autentica adjudicadores.

O resultado `EM_REVIEW` e exit code zero não provam aceite. O coordenador observa os checks e registra `APROVADA`, `CORREÇÃO` ou `BLOQUEADA`. Nenhum prompt ou texto bruto de modelo entra na documentação sem revisão e reconciliação.

Review `APROVADA` exige zero checks falhos e zero checks não executados. Checks não aplicáveis devem ser justificados no artefato e excluídos do conjunto obrigatório antes do review, nunca omitidos para esconder uma falha. Schema v1 permanece somente por compatibilidade: usa `SCOPED_WRITE` e não exige triagem v2. Novas tarefas devem usar v2; o coordenador não deve escolher v1 para contornar READ_ONLY ou revisão especializada.

Telemetria local: `%LOCALAPPDATA%\TiaNet\engineering-telemetry\opencode-events.jsonl`, separada do Nox e fora do Git. Registra metadados e contagens, nunca prompt, resposta, nomes de arquivos, código ou dados financeiros. O CLI pode manter seu próprio histórico local; a política da telemetria não configura a retenção do CLI ou do provedor.

Essa separação é garantida pelo caminho padrão, não por todos os overrides possíveis: `-TelemetryPath` é livre e deve apontar para estado local fora do Git. `Model` e `FallbackFrom` aceitam texto; o coordenador deve fornecer somente IDs sanitizados de modelos, nunca conteúdo da tarefa. A minimização desses campos é regra operacional, não filtro semântico do script.

Não enviar credenciais, dados reais de clientes, saldos, contratos ou conversas. A autorização de provedores do Nox não é uma autorização permanente para conteúdo TiaNet. Esta adoção cobre teste sintético e coordenação delimitada solicitada, sem contratação ou novos gastos.

READ_ONLY e allowedPaths detectam mudanças versionáveis após execução; não são sandbox de leitura/escrita. Arquivos ignorados, inclusive segredos locais, podem ficar fora da observação. Não delegue leitura ampla da árvore. Falhas preservam o working tree para inspeção, sem reset ou limpeza automática. O wrapper não fecha gates, não publica e não substitui revisão humana.
