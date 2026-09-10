# Parecer reconciliado — AI Architect Senior / Harness TiaNet

**Data:** 2026-09-08
**Classificação:** STANDARD
**Impacto agentic:** PRESENT
**Materialização:** subagente delimitado, somente leitura, sem rede ou dados reais.
**Escopo:** adaptação local do Harness; não inclui certificação de produto.

## 1. AI Impact Brief

A adoção distribui workflows, instruções e coordenação efêmera para engenharia. SPEC-004, ALP-001 e portas de produto permanecem fontes superiores. A autorização do proprietário abrange aplicação local e testes do fluxo, sem publicação ou liberação de IMPs.

## 2. Alternativas e recomendação

O especialista recomenda adaptar o mecanismo portátil à governança TiaNet. Copiar o Nox integralmente importaria regras e permissões alheias. Sandbox ou controlador persistente ampliariam operação sem necessidade demonstrada nesta adoção. A recomendação deve ser reavaliada para execução autônoma ou contexto sensível.

## 3. Invariantes e controles determinísticos

Exit code zero significa EM_REVIEW; o coordenador verifica aceite. Contrato especializado exige schema v2, PRESENT, architect/plan e READ_ONLY. Baseline observa conteúdo versionável, índice e HEAD. Review não aprova checks falhos, pendentes ou BLOCKER aberto. Telemetria padrão é separada em TiaNet. Limites de leitura, arquivos ignorados, timeout, retries internos e campos livres não são descritos como garantias de sandbox.

## 4. Contrato de avaliação

| Cenário | Evidência exigida |
|---|---|
| Envelope inválido / especialista incompatível | Recusa nas fixtures antes da execução |
| Falso sucesso | EM_REVIEW na execução; aprovação contraditória recusada sem novo evento |
| Mutação fora do contrato | Detecção de arquivo, índice e HEAD; preservação da alteração para review |
| Telemetria | Ausência de sentinelas de prompt/resposta; JSONL concorrente íntegro |
| Portabilidade | Namespace TiaNet e referências locais; validador aceita fixture válida e rejeita regressões |
| Disponibilidade | Resposta sintética real, supervisionada; sem inferir disponibilidade futura |

## 5. Parecer e achados

A primeira revisão apontou BLOCKER. Após correções, o parecer complementar foi APPROVED para a adaptação local, sem fechar gates.

| ID | Classe inicial | Achado | Correção examinada |
|---|---|---|---|
| R1 | BLOCKER | Review aceitava APROVADA com checks falhos ou pendentes | Add-OpenCodeReview recusa ambas as contradições antes de persistir; duas fixtures verificam recusa e ausência de evento |
| R2 | CONCERN | Compatibilidade v1 podia ser confundida com READ_ONLY | HARNESS explica fallback SCOPED_WRITE de v1 e exige v2 para novas tarefas |
| R3 | CONCERN | TelemetryPath e IDs livres podiam parecer tecnicamente sanitizados | HARNESS distingue caminho padrão de override e sanitização operacional de filtragem semântica |

## 6. Itens adiados

Sandbox, timeout automático, deduplicação persistente e autenticação de adjudicadores dependem de demanda de autonomia e decisão específica. Certificação do produto permanece nos seus planos. O parecer não autoriza acesso a informações reais ou contratação de serviços.

## Review do coordenador

Parecer reconciliado a partir da revisão estática e da revisão complementar. O coordenador reexecutou os testes: 38 verificações da coordenação, incluindo as duas recusas de falso sucesso, passaram. O teste real retornou a sentinela prevista, sem mudança no baseline. A troca de Get-FileHash por SHA256 .NET corrigiu a indisponibilidade do cmdlet no PowerShell filho iniciado pelo npm e preserva cálculo sobre os bytes do arquivo.

## Adjudicação pelo coordenador

| Achado | Estado | Ator | Evidência |
|---|---|---|---|
| R1 | RESOLVED | CODEX | Duas fixtures negativas passaram; nenhuma aprovação falsa persistida |
| R2 | RESOLVED | CODEX | Comportamento v1/v2 explícito no HARNESS |
| R3 | RESOLVED | CODEX | Limites de namespace e sanitização explícitos no HARNESS |

Nenhum BLOCKER permanece aberto nesta adoção. Não houve aceitação de risco material pelo coordenador nem fechamento de GATE-E do produto.
