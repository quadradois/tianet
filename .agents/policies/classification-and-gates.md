# Classificação de trabalho e gates

## Classificação

| Classe | Característica | Processo mínimo |
|---|---|---|
| `TRIVIAL` | Local, reversível, sem mudança de comportamento relevante | inspecionar, alterar, checar |
| `SMALL` | Poucos arquivos e risco baixo | descobrir, plano em conversa, executar, verificar |
| `STANDARD` | Comportamento novo ou mudança multifile | descobrir, planejar, aprovar, executar por slices, verificar |
| `SUBSTANTIAL` | Cruzamento de módulos, dados, integração ou operação | modelar, arquitetar, decidir quando necessário, plano durável e revisão |
| `ARCHITECTURAL` | Altera fronteiras, invariantes, tecnologia, segurança ou implantação | fluxo completo e decisão formal antes de implementar |

Em dúvida entre duas classes, escolha a de maior risco apenas quando houver consequência concreta. Tarefa pequena não ganha ADR, revisão multiagente ou plano durável sem necessidade.

## Gates

| Gate | Evidência de saída |
|---|---|
| G0 — Repositório pronto | instruções, fontes e estado localizados |
| G1 — Problema entendido | objetivo, escopo, fatos, desconhecidos e riscos |
| G2 — Domínio entendido | conceitos, estados, eventos, fronteiras e invariantes |
| G3 — Arquitetura definida | alternativas, recomendação, impactos e estratégia de teste |
| G4 — Decisão registrada | ADR ou decisão de governança aprovada |
| G5 — Plano aprovado | slices, critérios, testes, rollback e aprovação explícita |
| G6 — Slice pronto | limites, orçamento de mudança e checks definidos |
| G7 — Implementação concluída | diff focal e documentação coerente |
| G8 — Testes aprovados | checks executados e resultados registrados |
| G9 — Revisão concluída | objeções classificadas e resolvidas ou aceitas |
| G10 — Verificação concluída | requisitos ligados a evidências reais |
| G11 — Handoff concluído | estado e próximo passo recuperáveis por nova sessão |

Nem todo trabalho atravessa todos os gates. `ARCHITECTURAL` usa G0–G11; `TRIVIAL` normalmente usa apenas G0, G6, G7, G8 e G10.

## Integração com o TiaNet

G0–G11 descrevem o ciclo do executor. Os GATE-E do ALP-001 e as portas específicas do plano/backlog continuam independentes e obrigatórios para execução de produto. Um slice corresponde à IMP ou ao conjunto autorizado pelo plano; não renumere IMPs nem crie aprovação paralela.

As fontes normativas são SPEC-004, arquitetura/ADRs e planos vigentes em `docs/`. Use os templates documentais existentes do TiaNet para artefatos de produto. Templates de `.agents/templates` são auxiliares do processo, não substituem campos obrigatórios daqueles documentos.

Uma autorização explícita já recebida vale dentro de seu escopo. Não peça novamente a mesma aprovação; registre sua origem. Uma demanda para aplicar o Harness não autoriza executar o backlog do produto.
