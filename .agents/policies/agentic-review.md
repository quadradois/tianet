# Política de triagem e revisão agentic

## Finalidade

Identificar demandas com impacto de IA ou agente e convocar revisão especializada somente quando o risco justificar. Esta política integra o Harness conforme HARNESS-ADOPTION.md sem transferir autoridade do coordenador ou do proprietário.

## Triagem obrigatória

O coordenador classifica toda demanda como:

- `NONE`: nenhum impacto agentic material foi encontrado;
- `PRESENT`: existe ao menos um gatilho material e o AI Architect Senior deve participar.

Demandas `STANDARD`, `SUBSTANTIAL` ou `ARCHITECTURAL` e qualquer demanda `PRESENT` registram a triagem em artefato durável. Demandas `TRIVIAL` ou `SMALL` classificadas `NONE` exigem somente justificativa breve no contexto de trabalho.

## Gatilhos para `PRESENT`

- nova capacidade de IA, agente, skill, plugin, ferramenta MCP ou worker inteligente;
- mudança de prompt de sistema, catálogo ou schema de ferramenta;
- mudança de modelo, endpoint, provedor, quantização, fallback ou roteamento;
- memória, RAG, contexto, mídia, retenção ou dado enviado à inferência;
- autorização, Confirmação ou efeito mutável alcançável pelo agente;
- budget de tokens, chamadas, etapas, tempo, retries ou custo;
- avaliação, métrica ou critério bloqueador de comportamento inteligente;
- incidente de falso sucesso, ação não autorizada, vazamento, prompt injection ou loop;
- decisão agentic em G3/G5 ou entrega mutável aplicável em G9/G10.

## Casos normalmente classificados `NONE`

- ajuste visual ou textual sem alterar instrução ou significado para agente;
- CRUD e regra determinística sem IA;
- infraestrutura sem mudança de runtime, dados, rede ou política inteligente;
- correção mecânica coberta por arquitetura e avaliações vigentes;
- indisponibilidade isolada de fornecedor sem lacuna arquitetural.

Uma dispensa deixa de ser válida quando a demanda contém qualquer gatilho obrigatório.

## Convocação

Com `PRESENT`, o coordenador cria missão delimitada, sanitizada e `READ_ONLY` para o papel `ai_architect`. A missão pode usar subagente ou executor efêmero; o papel não fica preso a modelo ou plataforma.

O especialista recebe somente fontes necessárias, critérios, decisões abertas e formato de retorno. Segredo, credencial, dado pessoal, conversa, mídia ou conteúdo real do produto não são enviados.

## Três contratos separados

### Parecer do especialista

Deve conter:

1. AI Impact Brief;
2. alternativas e recomendação;
3. invariantes e controles determinísticos;
4. contrato de avaliação;
5. achados `BLOCKER`, `CONCERN`, `SUGGESTION` ou parecer `APPROVED`;
6. itens adiados.

### Review do coordenador

O coordenador verifica completude, fontes, coerência, fronteiras, autoridade e evidência. Saída bruta do especialista é transitória; somente versão reconciliada pode entrar em `docs/`.

### Adjudicação

Cada `BLOCKER` recebe estado `OPEN`, `RESOLVED`, `ACCEPTED_RISK` ou `REJECTED_WITH_RATIONALE`, ator e evidência. O especialista não preenche a adjudicação. Codex pode registrar resolução técnica comprovada; risco, escopo ou arquitetura material exigem decisão do proprietário.

## Efeito sobre gates

- `PRESENT` sem parecer aplicável mantém a porta aberta;
- parecer incompleto vai para correção;
- `BLOCKER` em estado `OPEN` impede avançar;
- indisponibilidade do especialista não fabrica aprovação;
- parecer do especialista nunca fecha gate;
- executor não interpreta semanticamente texto livre nem adjudica achado.

## Alcance do enforcement

O Harness valida consistência somente quando a triagem aparece em envelope, plano ou parecer persistido. Ele não intercepta toda interação do coordenador. Fluxos fora dessas superfícies dependem de review e disciplina operacional, e não podem ser descritos como enforcement automático.

Detecção de mudança após execução não é sandbox e pode não observar arquivos ignorados. Tarefas read-only continuam sujeitas a minimização, inspeção do baseline e review.

## Evidência e telemetria

Cada conclusão relevante liga `requisito → evidência esperada → check → resultado → status`. Telemetria pode registrar impacto, papel, quantidade de gatilhos, parecer e contagem de achados, mas nunca prompt, resposta, achado textual, segredo, dado pessoal ou conteúdo do produto.
