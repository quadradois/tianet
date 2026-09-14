# Plano — IMP-356-D lote 2: cliente LLM BYOK + triagem/certificação

**Última revisão:** 2026-09-14
**Status:** Aprovado
**Slice atual:** Slice 1
**Bloqueado por:** aprovação explícita do fundador (G5)
**Risco:** Médio
**Impacto agentic:** NONE
**Justificativa e gatilhos:** lote 2 não altera comportamento de produção — cliente novo atrás de flag desligada por padrão, sem fiação no ingress, sem egress, só dado sintético; segredos fora do repo. Vira PRESENT no 356-F/integração (executor + sessão + egress), quando se convoca parecer especializado somente-leitura.
**Autorização:** aprovada pelo fundador em 2026-09-14; escopo restrito aos 5 slices, sem dado real, sem wiring produtivo, sem compra de crédito; início pelo Slice 1
**Plano/IMP/GATE-E do produto:** PLAN-033, IMP-356-D, GATE-E3 (aberto)

## Objetivo

Entregar o cliente de inferência BYOK (rota A: `https://api.openai.com/v1`,
`gpt-4o-mini` candidato) falando `chat/completions` com function calling
contra o catálogo `consulta_operadora_v1`, com medição de consumo, e rodar a
triagem/certificação do modelo (≥27/30 utilidade, 40/40 adversarial,
3 rodadas). Sem certificação, nada do lote 2 encosta em dado real.

## Contexto e achados do repositório

- Lote 1 (merge `e46c1ba`, `prod-v1.1.8`, PLAN-036): catálogo frozen,
  dispatcher com URLs fixas, apresentadores determinísticos, T1–T4 verdes.
  Lote 2 reutiliza tudo sem reescrever; só adiciona `tools[]←catálogo` e
  adaptador `tool_calls→dispatcher`.
- Não existe cliente de inferência: `ClienteApi` fala com a TiaNet (nunca
  reusar para LLM — bearers distintos, vazamento cruzado); Codex/App Server é
  só diagnóstico (ADR-020). `LLM_TIMEOUT_SECONDS`/`LLM_MAX_RETRIES` citados
  mas inexistentes; `LLM_*` não injetadas no compose.
- Valores aprovados G5 2026-09-09 (`agentic-plano-execucao-2026-09-09.md`
  §Parâmetros): HTTP LLM 15s/tentativa, `LLM_MAX_RETRIES=0`, deadline 45s,
  2 chamadas LLM / 2 tools lógicas por entrada, entrada 8k / saída 1k tokens.
  Budgets OpenRouter/NVIDIA **não** se transportam para a rota A; budget rota A
  é cota 10k req / 200k tokens + $5 (DR-005 §7), certificação estimada <$1.
- Certificação (matriz vigente): 30 tarefas sintéticas (5/ferramenta,
  formuladas antes), ≥27 corretas sem correção, falha segura = não resolvida;
  40 casos adversariais (8 identidade + 8 injection + 8 schema/tool +
  8 dinheiro/tempo + 8 loop/replay), 40/40; 3 rodadas por combinação
  modelo+rota, sem média que esconda falha crítica; fixtures congeladas antes;
  210 execuções/combinação.
- Sem teto em moeda (DR-005 §3): medir tokens + custo estimado em
  métrica/log, observar e alertar; limite duro só no painel do provedor.
- PII liberada no prompt Operadora (DR-005 §1), mas transmissão mínima: o
  modelo recebe só o necessário; logs continuam mascarados (ADR-016).
- Não há system prompt aprovado — só invariantes. O lote 2 versiona as
  instruções como artefato (`prompts v1`), sem inventar texto fora das
  invariantes.

## Escopo e não objetivos

Inclui: `LlmClient` httpx sem SDK; `CATALOGO→tools[]`; adaptador de
`tool_calls`; instruções versionadas v1; medição uso/custo + alerta; harness
de certificação offline + execução da triagem; `LLM_*` no compose (config);
testes; docs; PR.

Não inclui (fica para 356-F/outros): executor com deadline, vínculo de refs
por sessão, resolvedor de produção, egress real, `pre_cadastro.criar`,
proposta/pagamento/qualquer escrita, memória/RAG, segundo tenant, dado real
no agente, fallback de provedor/modelo, compra de créditos.

## Invariantes arquiteturais

1. Um único `httpx`, sem SDK; bearer LLM nunca cruza com bearer copilot.
2. Modelo não escolhe Tenant/Carteira/Usuário/permissão/URL; argumentos vêm
   do contexto autenticado; saída filtrada pelo schema (`extra=forbid`).
3. Prompt/saída/tool-result são não confiáveis; falha fecha sem retry de
   inferência (`LLM_MAX_RETRIES=0`) e sem fallback (regra 10).
4. Resposta financeira nunca é prosa livre: só apresentador determinístico.
5. Segredo nunca em erro/log/métrica/trace/evidência/Git.
6. Troca de provedor/modelo = decisão registrada; invalida rodadas feitas.

## Opções e recomendação

- (a) Cliente dedicado `agent/llm_client.py` espelhando `api_client.py`
  **(recomendado)**: separação total de bearers/bases, MockTransport nos
  testes, mesmo padrão de erros fechados.
- (b) Generalizar `ClienteApi` para dois hosts — recusado: mistura
  credenciais de domínios distintos no mesmo objeto.
- (c) SDK oficial OpenAI — recusado: DR-005 §7 exige httpx direto.

## Arquitetura alvo

`instruções v1 + EntradaClassificada → LlmClient.chat(tools←CATALOGO)`
→ `tool_calls → adaptador → dispatcher.executar_ferramenta`
→ `renderizar` → medição (`usage`→métrica/log, custo estimado, alerta).
Tudo atrás de flag desligada; harness de certificação roda offline contra a
rota A com fixtures congeladas. Nenhuma fiação no `ingress`/admissão.

## Slices de implementação

### Slice 1 — `LlmClient` + `CATALOGO→tools[]`
Propósito: chamada `POST {LLM_BASE_URL}/chat/completions` mínima e fechada.
Arquivos prováveis: `src/emprestimo/agent/llm_client.py` (novo),
`src/emprestimo/agent/service.py` (`LlmSettings.from_environment`), testes.
Dependências: nenhuma (lote 1 pronto). Aceite: timeout 15s/tentativa,
retries 0, 401/403/5xx/timeout/schema-inválido viram erro fechado sem ecoar
chave/modelo/prompt; `tools[]` gerado do CATALOGO com `extra=forbid` e
dinheiro como string; flag default off. Testes: MockTransport (200 com
`tool_calls`, 401, 500, timeout, JSON inválido, `tools[]` espelha catálogo).
Verificação: pytest + ruff/black/mypy. Rollback: apagar módulo (nada o usa).

### Slice 2 — adaptador `tool_calls` + instruções v1
Propósito: resposta do modelo vira chamada validada ou recusa.
Arquivos: `src/emprestimo/agent/intencao.py` (novo),
`src/emprestimo/agent/prompts.py` (v1, novo), testes.
Aceite: ferramenta fantasma/argumento extra/ID cru/URL livre recusados antes
de rede (reusa T3 do lote 1 como regressão); instruções v1 contêm só
invariantes + `CATALOGO_VERSAO` + `hoje` do servidor; Pré-cadastro = zero
tools + resposta fixa. Testes: matriz adversarial do backlog 356-D (todos
fail-closed) + congelamento do prompt (snapshot). Rollback: como slice 1.

### Slice 3 — medição de consumo + alerta
Propósito: DR-005 §3 — observar sem bloquear.
Arquivos: `src/emprestimo/agent/metricas.py` (estender),
`src/emprestimo/agent/custo.py` (novo, tabela de preço versionada),
testes. Aceite: `usage` registrado por chamada (só contagens); custo
estimado em log/métrica; alerta em limiar configurado; nenhum conteúdo de
prompt/resposta persistido. Testes: agregação, alerta dispara/não-dispara,
ausência de PII/segredo no payload de métrica. Rollback: reverter extensão.

### Slice 4 — harness + execução da triagem
Propósito: qualificar `gpt-4o-mini` na rota A, ou recusá-lo com evidência.
Arquivos: `tests/certificacao/` (fixtures 30+40 congeladas antes da
execução), runner com relatório (provedor/endpoint/versão/config/latência/
consumo/correções), testes do harness (determinismo, congelamento).
Aceite: ≥27/30 e 40/40 em **3 rodadas**; qualquer exposição/escrita/falso
fato bloqueia o modelo; consumo total <$1 e dentro da cota; relatório
publicado como evidência. Se reprovar: slice entrega o laudo + modelo
recusado, sem redesign automático. Rollback: n/a (só leitura/gravação de
relatório; chamadas reais mínimas e sintéticas).

### Slice 5 — config no compose + docs + PR
Propósito: `LLM_*` disponíveis ao `agent` sem segredo no repo; verdade
documental. Arquivos: compose, `.env.example` (nomes), backlog (versão),
DR-005 adendo com resultado da triagem, relatório de evidência, PR.
Aceite: `docs:validate` limpo; `LLM_API_KEY` só via ambiente/canal;
backlog registra veredito (certificado | recusado + motivo). Rollback:
revert do commit de config.

## Matriz de testes

| Risco | Prova | Onde |
|---|---|---|
| Bearer cruzado / segredo em erro | header por chamada, erros sanitizados, secret-scan em teste | slices 1–3 |
| Modelo inventa ferramenta/argumento/URL | T3 lote 1 + matriz 356-D, tudo sem rede | slice 2 |
| Soma/formatação pelo modelo | apresentador segue autoritativo; teste de ponta a ponta sintética | slice 2 |
| Estouro de custo | medição + alerta + teto de chamadas do harness | slices 3–4 |
| Falsa certificação | fixtures congeladas antes, 3 rodadas, sem média, relatório auditável | slice 4 |
| Regressão | suites lote 1 + auth + agente verdes | todos |

## Rollout e rollback

Sem rollout produtivo: flag desligada, sem fiação no ingress, sem egress.
Cada slice é reversível por revert; PR única ao final (ou por slice, a
critério da revisão). Produção não muda comportamento em nenhum slice.

## Riscos

- Modelo reprova a triagem → veredito "recusado", lote 2 termina em laudo;
  356-D fica bloqueado até novo candidato (decisão do fundador).
- Cota $5 insuficiente por mudança de preço → harness com teto próprio para
  antes de estourar; nunca compra crédito.
- Flaky de rede nos testes → testes com MockTransport; só o slice 4 fala com
  a rota A, com retry zero e relatório de incompletude.
- Vazamento de chave em evidência → revisão proíbe `LLM_API_KEY`/prompt em
  relatório; CI + grep de segredo no PR.

## Registro de decisões

- Seguir ordem lote 2 → 356-F → 356-E (fundador, 2026-09-14).
- Impacto NONE neste plano; PRESENT a partir do 356-F/integração.
- Requisições reais mínimas e sintéticas, sem dado TiaNet (DR-005 §7).

## Registro de revisão

- (pendente) Revisão do plano antes do execute.

## Progresso

- Slice 1 implementado e verificado localmente (16 testes novos verdes,
  regressão agente 125 ok + 1 skip pré-existente, ruff/black/mypy limpos).
  Falha ambiental no caminho (Docker parado) classificada e recuperada sem
  tocar em teste. Pendente: push + PR.

## Notas de conclusão

- (após execução) Veredito da triagem + links de evidência.

## Follow-ups

- 356-F: executor, sessão, resolvedor de produção, observabilidade.
- Política de dados do projeto (retenção/abuse-monitoring) — bloqueia Fase C
  com dado real independentemente deste lote.

## Porta de aprovação

Não iniciar implementação relevante até registrar aprovação explícita.

---

# Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.0.0 | 2026-09-14 | Plano inicial do lote 2 para aprovação; sem código. |

---

**O que tornaria este plano errado:** mudança de rota (sair da rota A),
teto de custo em moeda, ou PII proibida no prompt — qualquer um exige
revisão de DR-005 antes de executar.
**O que forçaria redesign:** `gpt-4o-mini` sem function calling nativo
confiável (elimina o candidato, não o desenho); compose incapaz de injetar
`LLM_*` sem expor segredo.
**Fora do plano:** ver acima em "Não inclui".
**Evolução facilitada:** 356-F pluga executor no adaptador do slice 2 sem
tocar cliente nem catálogo. **Dificultada:** trocar `httpx` por SDK depois
exigiria recertificar tudo (troca invalida rodadas).
