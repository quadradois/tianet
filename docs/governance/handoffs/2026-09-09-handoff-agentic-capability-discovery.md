# 2026-09-09 — Handoff: discovery de capacidade do Agentic

**Versao:** 1.0.0  
**Status:** WhatsApp local conectado; discovery documental do Agentic concluido;
proxima sessao reservada para analise de capacidade e potencial do produto.  
**Base observada:** branch `feat/imp-370-worker-le-o-token`, HEAD `6ae2f68`.  
**Escopo da retomada:** Discover e, depois, Architect. Nenhuma implementacao do
Agentic esta autorizada por este handoff.

---

## Estado atual

O conector WhatsApp esta conectado no ambiente local depois da correcao do
Evolution Go pela equipe que administra o provedor e dos ajustes locais do
adapter. O canal estar conectado nao significa que o atendimento agentic exista.

O planejamento vigente esta no
[PLAN-033](../../implementation/plans/PLAN-033-copilot-tianet.md), em seu
[backlog](../../implementation/backlogs/PLAN-033-execution-backlog.md) e na
[DR-005](../decision-requests/DR-005-pii-modelo-e-teto-de-custo-do-copilot.md).
O raio X mais recente esta em
[Discovery — Agentic de atendimento e relatorios](../../audits/discoveries/agentic-atendimento-relatorios-as-is-to-be-2026-09-09.md).

Os relatorios operacionais ja existem. O agente conversacional nao: nao ha
servico `agent` no compose, cliente LLM, inbox, sessao conversacional, tool-call
ou Aggregate `PreCadastro` no codigo de producao.

---

## Concluido

- conector WhatsApp local observado como conectado;
- documentacao do Agentic localizada e cruzada com codigo, grafo e estado Git;
- quatro endpoints de relatorios e o saldo agregado identificados;
- estado de IMP-352, IMP-353..IMP-362 reconciliado no discovery;
- revisao `ai_architect` somente leitura executada pelo OpenCode Harness na
  tarefa `8b1a8ce0-c1cf-4580-a9ef-ab24d87d4d0f`;
- `docs:validate`: 386 verificacoes OK, 36 avisos preexistentes, zero erros;
- `git diff --check`: aprovado.

---

## Em andamento

O working tree contem mudancas ainda sem commit do ciclo do WhatsApp:

- `docker-compose.yml`;
- `docs/operations/contexto-externo.md`;
- `docs/whatsapp/CRM_EVOLUTION_CONTRACT.md`;
- `src/emprestimo/infrastructure/notifications/evolution_instancia.py`;
- `src/emprestimo/presentation/api/whatsapp_routes.py`;
- `tests/unit/infrastructure/test_evolution_instancia.py`;
- discoveries de WhatsApp e Agentic ainda nao versionados.

Existe tambem
`docs/whatsapp/revisao-manual-colunas-2026-09-09.csv`, nao relacionado ao
Agentic. Preservar sem alterar, mover ou remover.

---

## Bloqueado

1. **GATE-E1b:** IMP-359 ainda exige deploy na VPS, TLS, backup/restore,
   CD/rollback, endurecimento, segredos, observabilidade e prova da origem do
   webhook ou bloqueio fail-closed da Operadora.
2. **GATE-E3 / B1:** o PLAN-033 exige allowlist nominal de GETs, mas ainda nao
   decide se os quatro relatorios operacionais entram como ferramentas, com
   quais schemas e campos.
3. O provedor BYOK foi escolhido e a chave existe segundo o contexto externo,
   mas nome, `LLM_BASE_URL` e `LLM_MODEL` ainda precisam ser registrados.

Nenhum desses bloqueios impede o discovery de capacidade. Eles impedem iniciar
ou certificar a implementacao conversacional.

---

## Decisoes vigentes

- O proximo trabalho nao parte da premissa de que o Agentic sera apenas um
  chatbot de saldo e relatorio.
- Primeiro sera avaliado todo o potencial do sistema: informacao disponivel,
  jornadas, eventos, automacoes, decisoes humanas, comandos, riscos e ganhos.
- A analise deve comparar alternativas de produto e arquitetura antes de
  escolher capacidades do v1 e evolucoes posteriores.
- O agente nunca calcula dinheiro; o Motor permanece autoridade.
- Escrita financeira, decisao comercial e aprovacao por agente continuam fora
  do v1 enquanto a governanca nao for formalmente reaberta.
- Operadora e PreCadastro permanecem isolados; o modelo nao escolhe Tenant,
  Carteira, Usuario, permissao, URL ou ferramenta.
- Nenhum segredo, conversa real, PII ou dado financeiro real pode ser enviado a
  executores auxiliares.

---

## Questoes para o discovery de capacidade

1. Quais capacidades de dominio, API, relatorios, cobranca, agenda, comunicacao,
   motor e automacao o TiaNet ja oferece?
2. Quais trabalhos a Operadora, o Credor e o Devedor tentam concluir e onde ha
   maior custo, atraso, risco ou repeticao?
3. Quais capacidades servem para consulta, explicacao, monitoramento,
   recomendacao, preparacao de trabalho ou comando com confirmacao humana?
4. Quais capacidades devem permanecer deterministicas e quais realmente se
   beneficiam de LLM?
5. Quais ferramentas podem ser expostas por persona, com quais permissoes,
   schemas, confirmacoes, idempotencia e auditoria?
6. Qual combinacao entrega maior valor com menor risco no primeiro release?
7. O PLAN-033 atual deve ser mantido, ampliado por fases ou redesenhado por uma
   nova decisao formal?

---

## Riscos

- reduzir o Agentic a interface de chat para endpoints existentes e perder
  oportunidades de monitoramento, preparacao e automacao assistida;
- ampliar autonomia antes de autenticar origem, isolar contexto e garantir
  idempotencia;
- apresentar projecao ou inferencia como fato financeiro;
- criar catalogo amplo demais e depender do prompt para autorizacao;
- misturar atendimento do Devedor com dados da Operadora;
- implementar antes de reconciliar estados e divergencias documentais.

---

## Proximo slice

**Discovery de capacidade e potencial do Agentic TiaNet**, somente leitura:

1. atualizar e consultar o grafo do repositorio;
2. inventariar capacidades por Bounded Context, API, worker e interface;
3. mapear personas, jornadas e pontos de decisao;
4. construir matriz `capacidade atual -> uso agentic -> valor -> risco ->
   pre-requisito -> controle deterministico`;
5. separar recursos deterministas, assistidos por LLM e autonomias adiadas;
6. comparar pelo menos tres desenhos de produto, incluindo o PLAN-033 atual;
7. recomendar um mapa de capacidades por fases, sem implementar;
8. submeter o resultado a `ai_architect` em modo `READ_ONLY` e reconciliar o
   parecer.

## Criterio de pronto da proxima sessao

- inventario cobre o potencial do produto, nao apenas endpoints de relatorio;
- oportunidades sao priorizadas por valor, risco, dependencia e reversibilidade;
- capacidades e ferramentas sao nominais, com persona e fronteira de autoridade;
- alternativas e trade-offs estao documentados;
- lacunas de produto, arquitetura, dados e operacao estao explicitas;
- existe recomendacao suficiente para iniciar Architect, sem codigo de producao.

## Proxima acao recomendada

Retomar pelo workflow `$discover`, ler este handoff e o discovery anterior,
consultar o grafo e construir a analise de capacidade. Nao executar IMP-356,
alterar prompts ou criar servico agent antes dessa decisao.
