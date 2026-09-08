# TiaNet — mapa operacional para agentes

## Comece aqui

1. Leia [docs/README.md](docs/README.md) e o [mapa de retomada](docs/governance/agents/HANDOFF.md).
2. Leia a [SPEC-004](docs/governance/agents/SPEC-004-regras-normativas-do-codigo.md): ela é a fonte das regras do código. Configurações pessoais de executor não substituem normas versionadas.
3. Confira o plano/backlog da tarefa, os ADRs aplicáveis e o [ALP-001](docs/governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md) antes de executar IMPs. Não confunda um handoff histórico com o estado atual do Git.
4. Inspecione `git status --short`; preserve alterações preexistentes. Consulte o grafo quando disponível e confirme as conclusões nas fontes atuais.
5. Antes de propor integração ou infraestrutura, leia [contexto externo](docs/operations/contexto-externo.md). Para frontend, leia também [frontend/AGENTS.md](frontend/AGENTS.md).

## Workflows

O fluxo é **Discover → Architect → Plan → aprovação aplicável → Execute → Verify**.

As skills em [.agents/skills](.agents/skills) oferecem `$discover`, `$architect`, `$plan`, `$execute` e `$verify`. Se a sessão não as listar, leia o respectivo SKILL.md diretamente; a instalação no repositório não garante recarga do catálogo em uma sessão já aberta.

Use a [classificação e gates](.agents/policies/classification-and-gates.md) proporcionalmente ao risco. G0–G11 não substituem GATE-E do ALP-001 nem liberam planos bloqueados. Autorizações já dadas continuam válidas dentro de seu escopo.

Toda demanda recebe triagem pela [política agentic](.agents/policies/agentic-review.md). Com impacto `PRESENT`, convoque o AI Architect Senior em missão delimitada e somente leitura; seu parecer não aprova gates.

## Regras essenciais

- Responda e documente em português brasileiro.
- `docs/` permanece a raiz documental oficial. Não copie regras do produto para criar fontes concorrentes.
- Não redesenhe silenciosamente nem altere arquitetura congelada sem reabertura pela governança vigente.
- Não declare sucesso sem observação; diferencie fato, hipótese, desconhecido, risco e decisão.
- Não envie dados reais de clientes, informações financeiras, segredos ou conversas a executores auxiliares.
- Commit, push, publicação, produção e ações externas exigem autorização do proprietário. Não faça limpeza automática do working tree.

## Verificação

Leia [HARNESS.md](docs/governance/agents/HARNESS.md) para comandos e limites. Validação local do Harness: `npm run harness:check` e `npm run harness:test`. Os gates do produto continuam definidos em seus planos e em [CONTRIBUTING.md](CONTRIBUTING.md).
