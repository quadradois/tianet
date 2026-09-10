# Discovery — Capacidade e potencial do Agentic TiaNet

**Identificador local:** `agentic-capacidade-potencial-2026-09-09`

**Data:** 2026-09-09

**Versão:** 1.0.0

**Workflow / classificação:** `discover` / `ARCHITECTURAL`

**Impacto agentic:** `PRESENT` — novas capacidades/tools, contexto/dados, autorização/efeitos mutáveis e avaliação.

**Status:** discovery estratégico; recomendação para Architect, sem aprovação de desenho ou fechamento de gates.

**Base observada:** HEAD destacado `6ae2f685e754259e46c7489b770e2be3f0b108ea` no worktree `d9c1`, com mudanças preexistentes preservadas. O nome de branch do handoff pertence ao checkout de origem, não a este worktree.

**Revisão especializada:** OpenCode Harness, `ai_architect`, `plan`, `READ_ONLY`; reconciliação na seção 13.

## 1. Problema, objetivo e recomendação

O PLAN-033 define um copilot por WhatsApp, mas não constitui um inventário do potencial do produto. Escolher ferramentas apenas a partir de saldo e relatórios deixaria de aproveitar cobrança, agenda, histórico, memória de cálculo, acompanhamento de falhas e preparação de trabalho. O objetivo deste discovery é tornar essas oportunidades comparáveis antes de congelar outro desenho.

**Recomendação de produto, ainda não aprovada:** preservar as fundações e os limites do PLAN-033 e evoluir para um **assistente de trabalho do Credor**: o sistema identifica pendências por regras, apresenta fatos oficiais, explica sua origem e prepara o próximo trabalho para revisão humana. WhatsApp oferece acesso rápido; a plataforma oferece contexto, conferência e decisão. A expansão deve ocorrer por jornadas, não pela exposição indiscriminada de endpoints.

O primeiro release continua proporcional: prontidão operacional, resumo e véspera determinísticos, identidade própria e consultas nominais governadas. O cockpit assistido e os rascunhos são uma expansão posterior sujeita a Architect/Plan. Comandos operacionais confirmados são outra etapa; comandos financeiros e decisões comerciais permanecem fora do v1. Não se recomenda criar agora um agente geral que percorra toda a API.

**Valor esperado é hipótese:** menos busca entre telas, menos digitação repetida, menos esquecimento e maior clareza sobre o que realmente ocorreu. Não houve entrevistas, medição de frequência, uso de dados reais nem cálculo de retorno financeiro. A prioridade abaixo é qualitativa e precisa ser testada com o Credor.

### Escopo e não objetivos

- Inventariar capacidades de domínio, API, persistência, worker e frontend; separar implementado, planejado e candidato.
- Mapear personas/jornadas, ferramentas, autoridade, valor, risco, pré-requisitos e controles; comparar quatro desenhos.
- Preparar material suficiente para Architect decidir o recorte e as mudanças formais necessárias.
- Não implementar IMPs, serviço agent, prompts, schema de ferramenta ou automação; não alterar arquitetura congelada, planos, backlog, DRs ou gates.
- Não chamar provedores, enviar mensagens, acessar credenciais/dados reais, contratar serviços, fazer commit, push, PR, merge ou deploy.

## 2. Fontes, método e limites da evidência

### Fontes governantes

| Fonte | O que determina |
|---|---|
| [Visão do produto](../../foundation/FOUNDATION-001-product-vision.md), [Product Map](../../foundation/FOUNDATION-007-product-map.md), [Capability Map](../../foundation/FOUNDATION-009-capability-map.md), [mapa de domínio](../../foundation/FOUNDATION-003-mapa-do-dominio.md) | Credor individual, agente propõe/Credor decide, capacidades e fronteiras |
| [PLAN-033](../../implementation/plans/PLAN-033-copilot-tianet.md), [backlog](../../implementation/backlogs/PLAN-033-execution-backlog.md) | Escopo vigente, dependências, v1 e exclusões |
| [DR-005](../../governance/decision-requests/DR-005-pii-modelo-e-teto-de-custo-do-copilot.md) | BYOK, PII no prompt, 90 dias, rate limit e ausência de teto monetário |
| [DR-004](../../governance/decision-requests/DR-004-base-e-acumulacao-dos-juros-e-fim-do-plano-de-parcelas.md) | Empréstimo livre, acerto e fim do plano de parcelas |
| [ADR-003](../../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md) | Um operador humano; identidade de serviço do copilot separada |
| [ADR-002](../../architecture/adrs/ADR-002-auditoria-independente-da-transacao.md), [ADR-009](../../architecture/adrs/ADR-009-notifications-channels.md), [ADR-016](../../architecture/adrs/ADR-016-observability-logging-correlation-id.md), [SPEC-004](../../governance/agents/SPEC-004-regras-normativas-do-codigo.md) | Auditoria, efeitos externos, logs, Motor e idempotência |
| [Contexto externo](../../operations/contexto-externo.md) | Evolution existente, ausência de dedupe no envio, BYOK escolhido mas identificação pendente de registro, VPS sem prontidão demonstrada, Mercado Pago futuro |
| [Discovery anterior](agentic-atendimento-relatorios-as-is-to-be-2026-09-09.md), [handoff de entrada](../../governance/handoffs/2026-09-09-handoff-agentic-capability-discovery.md) | Estado herdado e B1 do catálogo de ferramentas |
| [ALP-001](../../governance/agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md), [Harness](../../governance/agents/HARNESS.md), [triagem agentic](../../../.agents/policies/agentic-review.md) | Processo, revisão especializada e limites de autorização |

### Registro do grafo e pré-voo

Aplicada a skill Graphify para navegação e atualização local de código. O worktree não continha `graphify-out/`; a cópia existente foi localizada no checkout de origem e copiada para o diretório ignorado deste worktree, preservando a original. O detector incremental inicial apontou 235 arquivos de código, 305 documentos e 50 imagens novos/alterados, além de uma exclusão. São diferenças do detector, não uma contagem de mudanças Git desta tarefa.

| Campo da SPEC-003 | Evidência desta sessão |
|---|---|
| Gatilho | Discovery solicitado; não há alteração de rota/ORM/porta/ADR neste trabalho. O catálogo proposto exigirá novo pré-voo quando formalizado |
| Grafo fresco? | Código atualizado em 2026-09-09 com `graphify update .`: 11.575 nós, 29.068 arestas, 589 comunidades. **Documentação parcialmente defasada**: não executada extração semântica ampla; documentos governantes foram lidos diretamente |
| Consultas executadas | `graphify query 'varredura cobranca' --budget 1400`; `'saldo memoria'`; `'scheduler notification'`; `'principal permissao copilot'`; `'lancamento relatorios'`, todos com o mesmo budget |
| Truncamento | Respectivamente 40/562, 34/212, 35/394, 35/716 e 37/69 nós exibidos. Não usados para concluir ausência |
| Aprofundamento | `graphify explain 'VarreduraCobrancaService'`; `'SqlAlchemyMemoriaCalculoRepository'`; `'EntregaComprovanteService'`; `'Copilot TiaNet (segundo operador no WhatsApp)'`; `graphify explain src_emprestimo_presentation_api_dependencies_exigir_permissao`, sem corte nessas vizinhanças. O ID completo resolveu a ambiguidade de `exigir_permissao` |
| Módulos | Varredura, Motor, relatórios, Scheduler/Notification, autorização e BFF; confirmados nas fontes listadas abaixo |
| API | Rotas e schemas existentes inspecionados; nenhuma rota alterada; tool não é sinônimo de endpoint |
| Persistência | ORM, repositórios e UoW existentes inspecionados; nenhuma migration. Sessão/inbox/tool-call/PreCadastro continuam planejados |
| Segurança | Permissões de rota, Principal e campos de contexto pertencem ao backend; risco especial no GET de quitação |
| Documentação a reconciliar | PLAN-033/backlog, catálogo nominal, linguagem legada de parcelas e estados de Product; nenhuma dessas fontes foi reescrita neste discovery |
| Fora do repositório | Prontidão da VPS, origem do webhook, modelo/provedor exatos e uso real do Credor não foram testados aqui |
| Achado que mudou a recomendação | Worker já fornece automação determinística e BFF já combina jornadas; ampliar por tarefas aproveita mais que um catálogo de relatórios. GET quitação não pode entrar por método HTTP apenas |

Limites: extração AST avisou que um arquivo SQL não contribuiu por ausência de `tree_sitter_sql`; não se infere ausência de persistência desse aviso. O HTML gerado automaticamente é agregado por comunidades, pois o grafo supera 5.000 nós; não foi usado como prova de comportamento. Atualização AST sem LLM: zero tokens de inferência para essa atualização. Consumo do OpenCode não foi medido pelo coordenador; não foi tratado como zero. Arestas `INFERRED` do grafo orientaram leitura, sem virar dependência comprovada sozinhas.

### Registro nominal de fontes de implementação

Os IDs E01–E12 são referências locais deste discovery, não novos IDs de governança. “Existe” significa observado no código; não significa certificado em produção nesta sessão.

| ID | Fontes verificadas e evidência |
|---|---|
| E01 | [Catálogo IAM](../../../src/emprestimo/application/iam_catalogo.py), [autorização](../../../src/emprestimo/application/autorizacao.py), [dependências API](../../../src/emprestimo/presentation/api/dependencies.py), [rotas IAM](../../../src/emprestimo/presentation/api/iam_routes.py): catálogo real, contexto e permissões; serviço do copilot ainda requer seed |
| E02 | [Rotas cadastrais](../../../src/emprestimo/presentation/api/devedores_routes.py), [cadastro](../../../src/emprestimo/application/cadastro_devedor.py), [Devedor](../../../src/emprestimo/domain/credit/devedor.py): criação, consulta/documento/listagem, histórico, atualização e ativação |
| E03 | [Comercial](../../../src/emprestimo/application/comercial.py), [rotas](../../../src/emprestimo/presentation/api/comercial_routes.py): simulação persistida, propostas, submissão separada de decisão |
| E04 | [Contratos](../../../src/emprestimo/application/contratos.py), [rotas](../../../src/emprestimo/presentation/api/contratos_routes.py), [lançamento](../../../src/emprestimo/application/lancamento.py): formalização e cadeia composta transacional |
| E05 | [Motor de domínio](../../../src/emprestimo/domain/credit/motor_financeiro.py), [aplicação](../../../src/emprestimo/application/motor_financeiro.py), [rotas](../../../src/emprestimo/presentation/api/motor_routes.py), [schemas](../../../src/emprestimo/presentation/api/motor_schemas.py): saldo individual/agregado, memória, pagamento, estorno, quitação e renegociação |
| E06 | [Operação diária](../../../src/emprestimo/application/operacao_diaria.py), [rotas](../../../src/emprestimo/presentation/api/operacao_diaria_routes.py), [promessa](../../../src/emprestimo/domain/credit/promessa.py): casos, ações, promessas/apropriações, agenda e comunicação |
| E07 | [Relatórios](../../../src/emprestimo/application/relatorios.py), [schemas](../../../src/emprestimo/presentation/api/operacao_diaria_schemas.py): quatro leituras oficiais e semântica dos campos |
| E08 | [Varredura](../../../src/emprestimo/application/varredura_cobranca.py), [worker](../../../src/emprestimo/worker/scheduler_worker.py), [Scheduler](../../../src/emprestimo/application/scheduler.py): snapshot por data, sincronização de casos, claim/lease e handlers |
| E09 | [Notifications](../../../src/emprestimo/application/notifications.py), [comprovante](../../../src/emprestimo/application/comprovante.py), [automação API](../../../src/emprestimo/presentation/api/automacao_routes.py), [WhatsApp adapter](../../../src/emprestimo/infrastructure/notifications/whatsapp.py): intenção, tentativa, aceite/incerteza, templates, comprovante e sobra |
| E10 | [Configurações](../../../src/emprestimo/application/configuracoes_financeiras.py), [rotas](../../../src/emprestimo/presentation/api/configuracoes_financeiras_routes.py): parâmetros/vigência/calendário e snapshots; [conexão](../../../src/emprestimo/application/conexao_whatsapp.py), [rotas WhatsApp](../../../src/emprestimo/presentation/api/whatsapp_routes.py): gestão e leitura do canal |
| E11 | [ORM](../../../src/emprestimo/infrastructure/db/orm.py), [UoW](../../../src/emprestimo/infrastructure/unit_of_work.py), [repositórios](../../../src/emprestimo/infrastructure/repositories/__init__.py), [eventos](../../../src/emprestimo/domain/credit/eventos_financeiros.py): fatos persistidos e eventos; ausência de transporte agentic não significa ausência de eventos de domínio |
| E12 | [Navegação](../../../frontend/src/lib/shell/navigation-policy.ts), [BFF início](../../../frontend/src/lib/bff/dashboard.server.ts), [BFF relatórios](../../../frontend/src/lib/bff/relatorios.server.ts), [BFF lançamento](../../../frontend/src/lib/bff/lancamento.server.ts), [instruções frontend](../../../frontend/AGENTS.md): telas e composição autenticada existentes; nenhuma inspeção visual ou teste de browser nesta sessão |

## 3. Fatos, desconhecidos e divergências

1. **Fato:** o produto tem nove documentos de Capability, PRODUCT-001..009. Motor e Contratos pertencem a Operações de Crédito; Scheduler/Notification apoiam Agenda/Comunicação. Os grupos analíticos abaixo não criam dez novas capacidades ou novos bounded contexts.
2. **Fato:** a visão atual é Credor individual com um humano. “Operadora” é contexto operacional e “Credor” é responsabilidade decisória da mesma pessoa. Separação do Principal de serviço continua necessária; não desenhar comitê, analista ou fila de aprovação entre funcionários fictícios.
3. **Fato de código:** há 111 declarações de rota encontradas por AST no pacote da API. Isso não equivale a 111 ferramentas, nem à contagem certificada do OpenAPI. Algumas leituras carregam permissões de escrita e alguns nomes não descrevem o efeito atual.
4. **Fato de código:** `docker-compose.yml` não define serviço `agent`; inspeção de produção em `src/` e ORM não encontrou cliente LLM, inbox/tool-call conversacional ou Aggregate `PreCadastro`. `Sessao` IAM não é sessão de conversa. O canal conectado foi observado na sessão anterior, não revalidado neste discovery.
5. **Fato governante:** IMP-359/GATE-E1b continua pendente; IMP-353 e IMP-354 dependem dele. B1 do catálogo nominal segue aberto. Nome/base URL/modelo BYOK precisam de registro, embora contexto externo já declare a escolha e a chave existentes. Não pedir nova escolha como se nunca tivesse ocorrido.
6. **Divergência:** Product contém estados “Proposto” e referências a parcelas apesar de APIs implementadas e DR-004 resolvida. FOUNDATION-007 não enumera Comercial explicitamente, enquanto PRODUCT-003 e FOUNDATION-009 o fazem. A descoberta registra a lacuna de alinhamento; não elimina o domínio Comercial nem aprova uma nova capacidade.
7. **Divergência:** navegação frontend ainda cita permissões `motor.parcela.*`, ausentes do catálogo IAM atual. Docstring de lançamento também cita Parcelas. Isso é evidência de texto residual, não suporte a plano de parcelas nem autorização para corrigir código neste trabalho.
8. **Fato semântico:** `principal_a_receber` não é saldo com juros; `total_realizado` não é lucro; `acertos_pendentes` não certifica toda a inadimplência. `projecao_juros` é estimativa de 12 meses via Motor sem amortizações futuras simuladas. Fluxo devolve realizado/acertos/IDs, sem valor previsto. O texto legado que afirma que relatórios não importam Motor conflita com a implementação atual de projeção, que o importa e consulta.
9. **Fato de autoridade:** GET de quitação usa `motor.quitacao.executar`; criar simulação é POST persistente com idempotência. Não conceder essas operações por serem “simulação” ou “consulta”. Alterar a permissão do GET seria mudança formal futura.
10. **Fato de efeito:** a rota de lembrete `/enviar` é alias depreciado de conciliação, com `notificacao.conciliar`; não é disparo livre. O provedor não deduplica envio por ID; ledger local ajuda, mas não resolve sozinho crash após aceite externo antes de persistência. Incerteza continua bloqueando retry.
11. **Desconhecidos:** distribuição dos trabalhos diários, maior causa de retrabalho, preferência entre WhatsApp e plataforma para conferir dados, qualidade do modelo escolhido e metas de latência/custo. Não há evidência para prometer redução de inadimplência, aumento de receita ou scoring.

As divergências materiais ficam para Architect antes de transformar candidatos em contrato; não se escolheu silenciosamente qual documento congelado reescrever. A autorização desta sessão cobre descoberta e artefato documental, não implementação.

## 4. Inventário de capacidade por domínio e superfície

Legenda: **E** observado em código; **P** planejado pendente; **C** candidato deste discovery. As fontes PRODUCT de cada grupo delimitam o negócio; E01–E12 comprovam a superfície atual.

| Grupo / Capability | Estado e trabalho disponível | API, worker e interface | Potencial agentic |
|---|---|---|---|
| Plataforma/IAM — [PRODUCT-001](../../product/platform/capabilities/PRODUCT-001-administrar-plataforma.md) | E: Tenant, autenticação, contexto, usuários, perfis/permissões; P: seed mínimo copilot | E01/E11/E12; login, IAM, bootstrap e health | Resolver contexto em código; explicar acesso negado sem elevar privilégio. IAM é infraestrutura do assistente, não catálogo administrativo do LLM |
| Cadastro — [PRODUCT-002](../../product/credit/capabilities/PRODUCT-002-administrar-cadastro.md) | E: Devedor/contatos/documento/histórico/estados; P: PreCadastro | E02; listagem/detalhe/edição frontend | Localizar sem ambiguidade, sintetizar alterações, preparar correções e coletar pré-cadastro isolado |
| Comercial — [PRODUCT-003](../../product/credit/capabilities/PRODUCT-003-administrar-comercial.md) | E: simulação de parâmetros persistida, proposta e decisões | E03; Comercial por Devedor | Explicar proposta existente; apontar dados faltantes; preparar trabalho futuro sem escolher taxa, aprovar ou prometer viabilidade |
| Contratos e lançamento — [PRODUCT-004](../../product/credit/capabilities/PRODUCT-004-administrar-operacoes-de-credito.md) | E: estados contratuais, histórico e lançamento composto numa UoW | E04/E12; Contratos e Novo empréstimo | Explicar etapa/pendência; preparar formulário para decisão humana. “Liberar para Motor” não é transferência bancária |
| Motor — PRODUCT-004 | E: empréstimo livre, saldo, memória, pagamentos/estornos, quitação/renegociação | E05/E11/E12; Empréstimos e jornadas de recebimento | Consulta/explicação rastreável; roteiro de conferência. Decidir condições e executar efeitos financeiros ficam com humano |
| Cobrança — [PRODUCT-005](../../product/credit/capabilities/PRODUCT-005-administrar-cobrancas.md) | E: varredura, casos, ações, promessas e apropriações | E06/E08; fila Cobrança | Explicar por que caso aparece, ordenar por critério aprovado, preparar contato/retorno; promessa não equivale a pagamento |
| Agenda — [PRODUCT-006](../../product/credit/capabilities/PRODUCT-006-administrar-agenda.md) | E: compromissos, reagendamento/conclusão/cancelamento, lembretes | E06/E08; Agenda e cartões Início | Consultar dia, identificar conflito temporal por regra, preparar compromisso ou reagendamento |
| Comunicação — [PRODUCT-007](../../product/credit/capabilities/PRODUCT-007-administrar-comunicacao.md) | E: histórico manual, templates/preferências, solicitações, comprovante e aviso de sobra; P: diálogo | E06/E09/E10; Agenda, Automação e WhatsApp | Resumo contextual, acompanhamento de aceite/incerteza, rascunho para humano e conversa limitada; sem tratar registro manual como prova de envio |
| Relatórios — [PRODUCT-008](../../product/credit/capabilities/PRODUCT-008-administrar-relatorios.md) | E: resumo, vencimentos/acertos, pagamentos/encerramentos e fluxo realizado | E07/E12; Início e Relatórios | Perguntas por período, explicação de indicadores e síntese de pendências; comparações monetárias exigem campos agregados oficiais novos se não existirem |
| Configurações — [PRODUCT-009](../../product/credit/capabilities/PRODUCT-009-administrar-configuracoes-financeiras.md) | E: modalidade/calendário/vigência/snapshots e estados | E10/E11; Configurações | Explicar qual configuração rege um fato; conferir snapshot histórico versus vigente. Alterar taxas/vigências é decisão humana |
| Suporte transversal Scheduler/Notification/Observability | E: jobs, tentativas, lease/fencing, cancel/retry, heartbeat, logs e sincronização de conexão; P: métricas/inbox agentic | E08/E09/E10/E11; Automação, health e estado do canal | Resumir incidentes sem segredo, preparar conciliação, sinalizar falha persistente por regra. Sem infraestrutura adicional presumida |

### Workers, eventos e limites de reutilização

O `SchedulerWorker.main()` registra quatro handlers: `enviar_lembrete`, comprovante de lançamento, aviso de sobra e `varrer_cobranca_diaria` (E08/E09). Antes do ciclo há semeadura diária de cobrança e, quando configurada, sincronização de conexão WhatsApp. O lembrete existente usa o canal de e-mail, fora do MVP operacional; sua presença não comprova véspera via WhatsApp. IMP-353/354 ainda são entregas novas.

Eventos como `PagamentoRegistrado`, `EmprestimoQuitado`, `EmprestimoRenegociado` e eventos de proposta/cadastro existem no domínio/persistência. Isso permite investigar monitores de mudança, mas não prova um Event Bus ou dispatcher durável ativo. IMP-348 está fora do PLAN-033. Um monitor inicial pode ser determinístico sobre consultas/snapshots; um consumidor novo precisa definir fonte, checkpoint, replay e dono antes de implementação.

O snapshot retornado pela varredura inclui todos os empréstimos ativos examinados e recortes de hoje/amanhã; a fila persistida contém casos de cobrança. Não substituir um pelo outro. Retorno em memória não é automaticamente histórico durável, API consultável ou série temporal. IDs/versionamento de snapshot para o agente são requisitos candidatos, não campos afirmados como existentes.

## 5. Personas e jornadas com pontos de decisão

| Persona/contexto | Jornada a concluir | Assistência útil | Decisão/autoridade que permanece humana |
|---|---|---|---|
| Credor como Operadora autenticada | Abrir o dia → ver acertos/cobrança/agenda → escolher próximos trabalhos | Resumo determinístico; perguntas em linguagem natural; explicar critérios e abrir contexto do item | Escolher quem contatar e como proceder; não aceitar ranking como decisão automática de crédito |
| Credor como decisor, mesma pessoa | Novo pedido → conferir cadastro/condições → lançar empréstimo → conferir comprovante | Coletar lacunas e preparar conferência; leitura do estado e explicação do comprovante | Valor, taxa, dia de acerto, aprovação e lançamento |
| Credor no recebimento | Consultar posição → registrar recebimento → conferir distribuição → lidar com sobra/erro | Explicar memória e estados oficiais; preparar lista de conferência e encaminhar para tela existente | Confirmar pagamento, estorno, quitação ou renegociação; conversa do Devedor não comprova recebimento |
| Credor no acompanhamento | Rever promessa → associar pagamento real → reagendar retorno | Localizar vínculos, explicar divergência de estado, preparar compromisso | Afirmar compromisso e apropriar pagamento; não baixar dívida pela palavra “paguei” |
| Credor na recuperação operacional | Ver falha → distinguir não envio/aceite/incerteza → conciliar | Explicar status e evidência disponível; agrupar falhas por código, sem logs brutos | Atos administrativos e conciliação conforme prova exigida; confirmar não substitui prova externa |
| Devedor cadastrado | Pedir posição/comprovante ou informar intenção de pagamento | Horizonte: autosserviço do próprio vínculo após desenho de identidade; hoje encaminhamento limitado | Nenhuma leitura de carteira só porque telefone consta do cadastro; não existe terceira classe autenticada no PLAN-033 |
| Remetente desconhecido | Informar dados → revisar dados mascarados → confirmar → aguardar Credor | P: PreCadastro isolado, validado e idempotente | Remetente confirma seus dados; Credor aprova/rejeita criação do Devedor; zero proposta/contrato decorrente automaticamente |

Suporte técnico é uma responsabilidade de operação, não nova persona de negócio nem funcionário presumido. O assistente de engenharia/OpenCode não é o agente de aplicação: seus dados e permissões não se confundem.

## 6. Modelo de domínio necessário para orientar Architect

| Conceitos e ownership | Estados/eventos relevantes | Invariante e entrada/saída |
|---|---|---|
| Tenant → Carteira → Devedor/Contato; Platform/Cadastro | Devedor ativo/inativo; eventos de cadastro/alteração | Escopo e unicidade validados no backend. Entrada identificada; saída DTO, não Aggregate |
| Simulação → Proposta → Contrato → Empréstimo; Comercial/Contratos/Motor | Proposta em rascunho/análise/decisão; contrato formalizado/assinado/liberado/cancelado/encerrado; empréstimo ativo/quitado/cancelado | Snapshot e autoria preservados. Lançamento composto não permite saltar invariantes |
| Pagamento → memória/evento → saldo; Motor | Recebido/processado/confirmado/estornado; quitação/renegociação | Motor calcula distribuição e saldo; estorno não apaga fato; texto livre não cria recebimento |
| Caso → Ação → Promessa → Apropriação; Cobrança | Caso pendente/em andamento/encerrado; promessa pendente/pagamento informado/cumprida/descumprida | Pagamento informado não é cumprida; apropriação referencia pagamento existente, estorno pode invalidar cumprimento |
| AgendaItem → Lembrete → Job/Tentativa → Solicitação → Comunicação | Compromisso aberto/reagendado/concluído/cancelado; solicitação preparada/aceita/falha/resultado desconhecido/conciliada | Horário, consentimento, template e destinatário validados. Aceite não é entrega; job concluído não prova pagamento |
| Configuração e snapshot; Configurações Financeiras | Rascunho/aprovada/programada/ativa/substituída/inativa | Configuração vigente não reescreve condições contratadas; agente não escolhe defaults financeiros |
| P: PreCadastro; fluxo PLAN-033 D | Pendente/aprovado/rejeitado; Devedor nasce após decisão | Aggregate próprio; confirmar dados não aprova crédito; `pre_cadastro.criar` é diferente de `pre_cadastro.decidir` |
| P: Inbox/Sessão/Mensagem/ToolCall/Egress; serviço agent | Recepção durável, dedupe, processamento e resultado | Não reutilizar Sessao IAM nem RegistroComunicacao obrigatório por Devedor; separar Operadora/PreCadastro em todo o ciclo |

**Quatro modelos separados:** domínio define verdade e invariantes; ORM armazena fatos/índices/jobs; API publica DTOs e permissões; interface combina leituras e oferece ações ao humano. Ferramentas do agente seriam adaptadores menores sobre casos de uso/DTOs, nunca espelho do ORM, SQL livre, navegação arbitrária ou substituto de autorização. Rascunho conversacional não é automaticamente entidade persistida; seu armazenamento, prazo e autoria ainda precisam de desenho.

## 7. Matriz capacidade atual → uso agentic → valor → risco → pré-requisito → controle determinístico

Tipos: **Q** consulta, **E** explicação, **M** monitoramento, **R** recomendação, **P** preparação, **A** automação determinística, **C** comando confirmado futuro. Prioridade P1/P2/P3 é proposta relativa; risco inclui confidencialidade, efeito e possibilidade de erro. Toda funcionalidade agentic da matriz é P ou C, nunca declarada implementada.

| ID / capacidade atual | Uso agentic e valor esperado | Risco | Pré-requisito | Controle determinístico | Prioridade/fase proposta |
|---|---|---|---|---|---|
| K01 — snapshot varredura E08 | A: resumo do dia/amanhã ao Credor; reduzir esquecimento | Médio: destinatário ou universo errado | IMP-359, 353; ponto de consumo do snapshot | Data/carteira fixadas, seleção em código, texto fixo, dedupe/egress | P1 / F1 |
| K02 — contatos/Notification E09 | A: véspera ao Devedor; aviso oportuno | Alto: comunicação indevida/duplicada | IMP-359, 354; consentimento e template específico | Validar vínculo/opt-out a cada envio; incerteza bloqueia retry | P1 / F1 |
| K03 — saldo agregado E05 | Q/E: posição do Devedor com componentes oficiais | Alto: exposição ou número inventado | B1/356; resolução inequívoca de vínculo | Backend injeta escopo/data; renderização de campos sem soma; 404 não vira zero | P1 / F2 |
| K04 — relatórios E07 | Q/E: resumo, pagamentos e fluxo de um período | Alto: projeção vendida como fato | B1 decide quatro tools e filtros | Allowlist de campos; preservar data/semântica; nenhum total calculado pelo LLM | P1 / F2 |
| K05 — fila/agenda E06 | Q/E: “o que precisa de atenção?” com links | Médio/alto: omitir ou misturar itens | Catálogo ampliado e limites por coleção | Filtros de contexto, paginação completa ou parcialidade explícita; regra de ordenação auditável | P1 / F3 |
| K06 — memória E05 | E: explicar juros/amortização já calculados | Alto: regra inventada ou números alterados | Schema de passos filtrado e contrato de explicação | Valores/etapas ancorados; falha em vínculo implica recusa; não refazer cálculo | P1 / F3 |
| K07 — Devedor/histórico E02 | Q/P: localizar pessoa e preparar correção | Alto: homônimo/PII/dado errado | Desambiguação e conjunto mínimo de campos | Escolha por identificador opaco vinculado ao contexto; nada de autoatualizar | P2 / F3 |
| K08 — ação/promessa E06 | R/P: preparar próximo contato e compromisso | Alto: promessa inventada ou pressão inadequada | Critério do Credor e formulário de revisão | Só sugerir dados explícitos; lacunas visíveis; nenhuma apropriação/pagamento | P1 / F3 |
| K09 — agenda E06 | P/C: preparar e depois criar/reagendar compromisso | Médio: duplicidade/horário errado | F3 rascunho; F5 comando após governança | Preview canônico, fuso, versão, permissão, confirmação vinculada e idempotência | P2 / F3→F5 |
| K10 — histórico comunicação E06 | Q/E/P: recuperar contexto e preparar resposta | Alto: injection em texto histórico | Proveniência e filtro de conteúdo | Histórico tratado como dado; destinatário e efeito separados; sem enviar rascunho automaticamente | P1 / F3 |
| K11 — jobs/notificações/conexão E08–E10 | M/E: apontar falha persistente e explicar próximo passo | Médio/alto: expor segredo ou falso sucesso | Projeção mínima e limiar de alerta | Monitor determinístico com dedupe; sem token/QR/corpo bruto; aceite ≠ entrega | P1 / F3 |
| K12 — eventos/pagamentos E05/E11 | M: avisar mudança relevante e atualizar visão de trabalho | Alto: dado velho ou alerta repetido | Fonte de evento/checkpoint ou polling governado; snapshot não existe como série por suposição | Reconsulta do fato oficial, watermark, supressão de duplicados e janela | P2 / F3+ |
| K13 — simulação/proposta E03 | Q/E/P: conferir parâmetros e pendências de proposta existente | Alto: confundir simulação com recomendação de crédito | Reabertura de escopo comercial; sem tool de criação v1 | Diferenciar GET existente de POST persistente; decisão e taxa humanas | P3 / Horizonte |
| K14 — contrato/lançamento E04 | E/P: explicar estado e preparar entrada para tela | Alto: lançar dívida por engano | Reabertura para preparação financeira | Formulário não executa; referência atual e lista de campos faltantes; nenhuma decisão padrão | P3 / Horizonte |
| K15 — configuração E10 | Q/E: explicar versão/snapshot que originou condição | Médio/alto: aplicar taxa vigente retroativamente | Escopo de leitura escolhido nominalmente | Buscar snapshot vinculado; vedar gerir/aprovar/ativar ao copilot | P2 / F3+ |
| K16 — PreCadastro P | P: coletar dados e submeter pendência | Alto: cadastro indevido e vazamento | IMP-356/357 e fila humana | Confirmação de dados pelo remetente, validação, pendência distinta de Devedor, decisão exclusiva do Credor | P1 / F4 |
| K17 — comandos operacionais E06/E09 | C: registrar ação/comunicação ou compromisso após conferência | Alto: fato operacional falso | Governança e contrato de confirmação F5 | Revalidar estado, autoria proponente/decisor, hash/expiração, idempotência e resultado observado | P2 / F5 |
| K18 — pagamento/estorno/quitação/renegociação E05 | P/C: conferir e eventualmente comandar efeito financeiro | Muito alto | Fora v1; decisão formal específica; autorização forte e validação transacional | Motor exclusivo, decisão humana, nenhuma escrita no catálogo v1; confirmação não elimina risco | P3 / Horizonte |
| K19 — próprio saldo do Devedor | Q/E: autosserviço restrito ao titular | Alto: vincular identidade errada | Novo desenho de identidade/recuperação/vínculo e revisão de canais | Identidade comprovada e ferramentas próprias; nenhum acesso via classe desconhecida atual | P3 / Horizonte |
| K20 — integração Mercado Pago futura | A/M: conciliar recebimento externo com fato do Motor | Muito alto: cobrança ou baixa duplicada | Integração própria, evento autenticado, decisão sobre pagamento divergente | Adapter/validação/idempotência determinísticos; LLM não interpreta webhook como ordem de baixa | P3 / Horizonte |

**O que realmente pede LLM:** compreender intenção variada, pedir esclarecimento, condensar histórico e explicar fatos em linguagem adequada. **O que não pede:** relógio, cálculo, filtros, totais, ordenação por regra, elegibilidade, envio programado, dedupe, estados, autorização e alertas por limiar. “Recomendar” aqui é propor próximo trabalho com razão explícita; não avaliar solvência, escolher taxa ou conceder crédito.

## 8. Catálogo candidato: persona, permissões e contratos mínimos

Os nomes seguintes são candidatos para discussão de B1 e da expansão. **Não constituem allowlist aprovada nem schema pronto para implementação.** E01 contém as permissões reais. `Operadora` significa somente o contexto autenticado previsto no plano, jamais qualquer remetente cadastrado.

### Leituras candidatas

Prefixo `/credit` nas rotas abaixo, exceto conexão. Identificadores de Tenant/Carteira/Usuário, permissões, URL e dispatch não são argumentos livres do modelo. A aplicação resolve identificadores de negócio a partir de seleção autorizada; data/período continuam parâmetros validados e apresentados ao humano.

| Tool candidata / fase | Endpoint existente | Persona / permissão | Entrada de negócio e saída mínima sugerida |
|---|---|---|---|
| `consultar_saldo_devedor` / F2 | `GET /credit/devedores/{devedor_id}/saldo` | Operadora; `motor.saldo.ler` | Seleção de Devedor e data; principal/juros/encargos/total, quantidade considerada, referências de empréstimo; sem recomputar |
| `consultar_resumo_carteira` / F2 | `GET /credit/carteiras/{carteira_id}/relatorios/resumo` | Operadora; `relatorios.operacionais.ler` | Data; contagens, principal_a_receber e total_realizado. **Proposta:** excluir projecao_juros da primeira tool; decisão ainda aberta |
| `consultar_acertos` / F2 | `GET /credit/carteiras/{carteira_id}/relatorios/vencimentos` | Operadora; `relatorios.operacionais.ler` | Data; referência de operação, dia/acerto, dias_sem_pagamento, situacao; não renomear para inadimplência certificada |
| `consultar_pagamentos_periodo` / F2 | `GET /credit/carteiras/{carteira_id}/relatorios/pagamentos` | Operadora; `relatorios.operacionais.ler` | Início/fim; valor/estado/data/IDs de pagamentos, operações quitadas e total oficial |
| `consultar_fluxo_realizado` / F2 | `GET /credit/carteiras/{carteira_id}/relatorios/fluxo` | Operadora; `relatorios.operacionais.ler` | Início/fim; data/realizado/acertos/IDs; não possui total geral nem previsão para o LLM inventar |
| `localizar_devedor` / dependência de F2 | `GET /credit/carteiras/{carteira_id}/devedores` | Operadora; `devedor.ler` | Busca validada, paginação; nome/estado e identificador opaco, máscara apenas quando necessária. Sem unicidade da seleção, pedir esclarecimento |
| `consultar_memoria_emprestimo` / F3 | `GET /credit/emprestimos/{emprestimo_id}/memoria-calculo` | Operadora; `motor.memoria.ler` | Referência vinculada; memórias e passos permitidos, datas e valores oficiais; limites explícitos de quantidade |
| `consultar_fila_cobranca` / F3 | `GET /credit/cobrancas/casos` | Operadora; `cobranca.caso.ler` | Estado/Devedor; apenas itens da carteira fixada, situação e referências; critério de prioridade vem de regra, não score do modelo |
| `consultar_agenda` / F3 | `GET /credit/agenda` | Operadora; `agenda.ler` | Janela/estado válidos; compromissos/lembretes e horários; horário ausente não pode ser completado silenciosamente |
| `consultar_historico_comunicacao` / F3 | `GET /credit/comunicacoes` | Operadora; `comunicacao.ler` | Devedor/janela; autoria, data, canal e conteúdo mínimo. Texto livre é entrada não confiável |
| `consultar_jobs` / F3 | `GET /credit/automacao/jobs` | Operadora em escopo autorizado; `automacao.job.consultar` | Filtros limitados; estado/tipo/tentativas/códigos seguros. Remover payload bruto e detalhes desnecessários |
| `consultar_notificacoes` / F3 | `GET /credit/notificacoes` | Operadora; `notificacao.consultar` | Janela/estado; referências e aceite/falha/incerteza; não afirmar leitura ou entrega |
| `consultar_estado_whatsapp` / F3 | `GET /platform/whatsapp/conexao` | Operadora; `whatsapp.conexao.ler` | Sem argumento de instância/URL livre; estado mínimo, sem token/QR/telefone integral |
| `consultar_configuracao_vinculada` / F3+ | Leituras de configuração/snapshot em E10; composição ainda a definir | Operadora; `configuracoes_financeiras.configuracao.ler` e escopo de origem | Referência contratual, versão e parâmetros permitidos; não substituir snapshot por `/vigente` |

`consultar_quitacao` **não entra no catálogo inicial**: o GET atual exige `motor.quitacao.executar`. `criar_simulacao` também não entra: persiste por POST. Consulta de contrato/proposta existente pode ser avaliada no horizonte, com `contratos.contrato.ler`/`comercial.proposta.ler`, sem incluir gerar contrato lógico por semelhança de nome. A cobertura completa de domínio é maior que o catálogo recomendado.

### Rascunhos e comandos possíveis, com autoridade explícita

| Candidato | Efeito atual disponível / condição | Autoridade proposta |
|---|---|---|
| `preparar_acao_cobranca`, `preparar_compromisso`, `preparar_comunicacao` | F3: rascunho não executável exibido ao humano; contrato/armazenamento novos | LLM propõe campos, humano corrige; nenhuma gravação operacional automática |
| `criar_pre_cadastro` | P: novo recurso IMP-357; `pre_cadastro.criar` ainda não é permissão disponível no catálogo real | Remetente confirma dados; serviço cria pendente. Só Credor com `pre_cadastro.decidir` aprova/rejeita |
| `registrar_acao_confirmada` | F5: POST `/credit/cobrancas/casos/{id}/acoes`; `cobranca.acao.registrar` | Humano confirma o fato ocorrido; backend valida caso, ator, hash e replay |
| `criar_compromisso_confirmado`, `reagendar_compromisso_confirmado` | F5: POST de compromisso/reagendamento de E06; `agenda.compromisso.gerir` | Humano confirma data/fuso/vínculo; backend revalida estado e evita duplicidade |
| `registrar_comunicacao_confirmada` | F5: POST de comunicação em E06; `comunicacao.registrar` | Humano atesta comunicação manual ocorrida; não equivale a envio nem Receipt |
| `registrar_promessa_confirmada` | Horizonte/F5 a decidir: POST de promessa; `cobranca.promessa.registrar` | Valor/data vêm de declaração humana explícita, sem inferência. Não apropria pagamento; recomenda-se adiar além dos primeiros comandos operacionais |
| `retry_job`, `conciliar_notificacao`, `enviar_mensagem` | Administração/egress sensíveis; nenhuma tool inicial | Confirmação humana não prova não aceite. Requer evidência e contrato próprio; não usar `/enviar` legado como disparo |
| `lancar_emprestimo`, `registrar_pagamento`, `estornar`, `quitar`, `renegociar`, `decidir_proposta` | Efeitos de crédito existentes, fora v1 agentic | Permanecem em UI humana; horizonte requer reabertura formal. Nunca conceder `decidir` ao modelo |

### Contrato comum a decidir em Architect

1. **Identidade e escopo:** origem verificada, Principal revogável, conjunto mínimo de permissões e vínculo de entidade revalidado em cada chamada. Modelo só sugere chamada dentre candidatas; código valida nome, argumentos e dispatch. Pré-cadastro tem zero leitura de carteira.
2. **Dados:** schema fechado por tool, campos extras recusados, decimais como valores tipados, período/data explícitos, limites de resultados e paginação. DR-005 permite PII no prompt Operadora, mas não obriga enviar tudo; filtros mínimos são recomendação, não revogação daquela decisão.
3. **Explicação:** cada número monetário apresentado é ligado a campo oficial e chamada concreta; números podem ser renderizados por template determinístico ao lado da explicação. Não confiar só em “não calcular” no prompt. Campo ausente/inválido/resultado parcial não vira zero ou total inferido.
4. **Confirmação futura:** intenção canônica com alvo, ação, campos, estado/versão observados, proponente, decisor, prazo e hash. Aprovação explícita ligada a essa intenção; mudar qualquer campo ou estado relevante exige nova confirmação. Silêncio, texto de histórico e “sim” sem vínculo não autorizam.
5. **Execução futura:** permissão e estado conferidos novamente no commit; idempotência na mesma transação; autoria distingue agente proponente e humano decisor; replay recupera resultado. Não reutilizar credencial humana no agente.
6. **Efeitos externos:** gravar intenção antes do envio; distinguir aceito, falhou e desconhecido. Nova confirmação não autoriza duplicar efeito incerto; conciliar só com evidência exigida. A mensagem “feito” exige observação do resultado persistido, não sucesso do LLM.
7. **Operação:** limites explícitos de chamadas/etapas/tempo/concorrência e medição de tokens/custo, sem inventar teto em moeda. Valores operacionais ainda devem ser decididos no plano. Timeout/401/revogação/erro têm saída fixa e encerram sem loop ou fallback de provedor.
8. **Memória/auditoria:** separar contexto, cache e histórico por identidade/classe/instância/escopo; 90 dias para artefatos conversacionais do plano, expurgo testável; auditoria financeira permanece append-only. Nenhum SQL, URL, segredo ou ferramenta genérica de administração para o modelo.

## 9. Quatro desenhos de produto comparados

| Critério | A — PLAN-033 vigente | B — Assistente de trabalho em cockpit + WhatsApp | C — Orquestrador de comandos confirmados | D — Automação e UI sem LLM |
|---|---|---|---|---|
| Promessa | Falar com a operação por WhatsApp; resumo/véspera e pré-cadastro | Entender o dia, explicar fatos e preparar próximos trabalhos | Converter pedido em plano/preview e executar comandos limitados após confirmação | Entregar alertas, consultas e formulários determinísticos |
| Capacidade | A/B/C/D do plano, leitura nominal e PreCadastro | Base A + visão de cobrança/agenda/histórico/memória, links e rascunhos | B + protocolo de intenção/confirmar/revalidar/executar | Resumo/véspera e operação manual atual aperfeiçoados |
| Benefício esperado | Conveniência no canal já usado | Redução de troca de telas e retrabalho em jornadas completas | Menos transcrição final e mais continuidade entre etapas | Previsibilidade e baixo custo de inferência |
| Risco principal | Webhook/PII, semântica incorreta e falsa confiança no chat | Mesmos riscos de IA mais rascunhos incorretos e atenção dispersa | Efeito errado/duplicado, confirmação obsoleta, encadeamento de permissões | Menor flexibilidade; usuário continua procurando/interpretando |
| Complexidade/custo relativo | Médio: serviço novo e operação de IA, mesmo sendo leitura | Médio/alto: camada de preparação/UI, catálogo e avaliações por jornada | Alto: protocolo transacional, auditoria de decisão, recuperação e gates por comando | Menor custo de IA; ainda exige prontidão operacional e manutenção |
| Reversibilidade | Desligar conversa; dados enviados ao provedor não são recuperados; PreCadastro aprovado persiste | Retirar assistência mantém UI; rascunhos têm ciclo de descarte a definir | Desabilitar tools impede novos efeitos, mas não desfaz dívida/comunicação já emitida | Alta para regras/avisos; mensagens já enviadas permanecem |
| Relação com governança | É o plano vigente, ainda bloqueado; não é só relatório | Expansão proposta, precisa revisão formal de escopo/catálogo; não entra silenciosamente no v1 | Novo desenho e gates próprios; finanças/decisão continuam fora v1 | Alternativa de piloto/baseline; não cancela PLAN-033 por decisão deste discovery |
| Quando preferir | Uso real confirma que perguntas curtas no WhatsApp resolvem maior parte do trabalho | Gargalo é reunir contexto e preparar acompanhamento; hipótese principal | Rascunhos têm bom aproveitamento e transcrição humana é o gargalo medido | Benefício incremental da linguagem natural não compensa erros/custo |

**Escolha recomendada:** B como direção por fases, A como base vigente e D como baseline de medição/degradação. C fica condicionado a benefício comprovado e controle por comando. RAG, memória longa e Mercado Pago não são pré-requisitos técnicos universais de C; têm problemas e decisões próprios. Mesmo C não implica autonomia geral ou aprovação de crédito pelo agente.

Exemplo de jornada candidata: “O que preciso resolver hoje?” → consulta escopada de agenda/cobrança e fatos oficiais → cartões com data, fonte e razão determinística → “prepare um retorno para este caso” → rascunho editável → humano registra na tela. A fase posterior pode trocar a última digitação por comando confirmado, mantendo a mesma autoridade.

## 10. Mapa por fases e critérios de progressão

F0–F5 são rótulos analíticos deste discovery, **não novos gates nem substitutos das fases A–D/IMPs**. Não criam prazo, orçamento ou autorização. Dependências do backlog continuam prevalecendo.

| Fase proposta | Entrega de valor / capacidades | Dependência e critério para discutir avanço | Reversibilidade / responsável |
|---|---|---|---|
| F0 — decisão e prontidão | Reconciliar linguagem, B1 e contrato de tools; comprovar IMP-359 | Architect/Plan e decisões aplicáveis; origem webhook provada ou Operadora desabilitada; produção/restauração/segredos observáveis | Sem mudança de produto aqui; proprietário decide escopo, engenharia produz evidência |
| F1 — base determinística | K01/K02; resumo e véspera, completar identidade/autoria da Fase B | IMP-353/354 **após GATE-E1b**; texto/consentimento/dedupe/egress testados; seed copilot no momento previsto do plano | Desabilitar jobs governados; mensagens enviadas não se desfazem |
| F2 — conversa mínima de leitura | K03/K04 e resolução necessária de Devedor; catálogo fechado para Operadora | IMP-356 A–F, dependências já listadas no backlog, B1 decidido; testes de isolamento/dinheiro/erro, métrica contra D | Desabilitar contexto/credencial; operar pela UI |
| F3 — cockpit e preparação | K05–K11; ampliar leitura por jornadas; rascunhos de ação/agenda/comunicação; monitor por regra | Reabertura de escopo para B, schema e UX de conferência; piloto mostra aproveitamento sem carga maior de revisão. K12/K15 opcionais, após resolver fonte/vínculo | Desabilitar recurso e descartar rascunhos conforme contrato; operação manual continua |
| F4 — captação isolada | K16; PreCadastro da Fase D, fila de revisão humana | IMP-357 depende do IMP-356; validação/confirmar/criar pendente/aprovar/rejeitar/replay com dois atores | Suspender entrada; preservar decisões e Devedores já criados |
| F5 — comandos operacionais limitados | K09/K17; começar por compromisso e registro de ação já revisados | Decisão formal, intenção canônica + confirmação vinculada + revalidação + idempotência/auditoria; nenhum comando financeiro herdado | Revogar tool; efeitos persistidos obedecem transição de domínio, não apagamento |
| Horizonte fora v1 | K13/K14/K18/K19/K20; comercial, preparação financeira, autosserviço e integrações | Discovery/DR/ADR próprios conforme risco. Scoring, RAG, mídia/OCR, memória longa e autonomia ampla apenas com problema/dados/controle demonstrados | Decisão por capacidade; não um pacote obrigatório de “agente completo” |

F4 pode seguir F2 sem aguardar F3: é dependência existente do PLAN-033. F3/F4 competem por prioridade de produto: se captação for o gargalo confirmado, priorizar F4. A ordem acima recomenda valor operacional primeiro, sem alterar a cadeia formal. F5 depende da preparação avaliada e de decisão nova, não exige que toda hipótese de horizonte exista.

### Métricas para validar a hipótese de valor

- **Tempo até entender o dia:** medir início da consulta até localizar pendências relevantes; comparar UI/baseline determinístico e assistência nas mesmas tarefas sintéticas, depois piloto autorizado.
- **Trabalho útil:** proporção de consultas resolvidas com fonte correta; proporção de rascunhos aproveitados, corrigidos e descartados; esforço de conferir comparado ao de digitar.
- **Qualidade:** taxa de explicações com todos os números rastreáveis; desambiguação correta; nenhum sucesso alegado sem efeito observado; recusas corretas sem bloquear tarefas legítimas em excesso.
- **Operação:** latência por jornada, backlog/idade de inbox, mensagens incertas/duplicadas, falhas de autenticação, expurgo e consumo por tarefa útil. Sem meta monetária inventada.
- **Monitoramento:** alertas úteis versus ignorados e duplicados; limiar/supressão definidos pelo produto. Não prometer recuperação de crédito como efeito causal do LLM.

Não há baseline medido nem metas numéricas de benefício aprovadas. Architect/Plan deve fixar amostra, metas e condições de parada antes do piloto. Violações de autorização, exposição entre contextos, duplicação indevida e número financeiro fabricado são falhas bloqueadoras, independentemente de ganho de tempo.

## 11. Contrato de avaliação futuro

Esta tabela define evidência a produzir na implementação; **nenhum destes testes de produto foi executado neste discovery**. Fixtures somente sintéticas; incluir mais de um vínculo mesmo no produto single-tenant para provar recusa, sem transformar multi-tenancy em roadmap.

| Requisito/cenário | Evidência esperada | Check futuro | Bloqueador |
|---|---|---|---|
| Identidade/origem e dois contextos | Spoof, LID/desconhecido e principal revogado não alcançam tools de carteira | Contar chamadas reais ao backend; nenhuma chamada proibida | Sim |
| Autorização por tool | Permissão nominal mínima; GET quitação negado ao perfil de leitura | Matriz positiva/negativa de rotas e campo extra/URL/tool inválida | Sim |
| Dinheiro e semântica | Todo valor monetário emitido corresponde ao campo tipado da tool; fluxo não ganha previsto | Fixtures multiempréstimo, estorno, data, vazio/404, projeção e total parcial | Sim |
| Prompt injection | Mensagem/histórico/tool result malicioso não troca papel, tool ou destinatário | Instruções adversariais em todas as entradas; medir efeito, não só resposta verbal | Sim |
| Paginação/atualidade | Nenhuma primeira página chamada de total; período e fonte visíveis | Mais itens que o limite; mudança de estado entre consulta e apresentação | Sim para afirmação financeira incorreta |
| Durabilidade | Replay/crash antes e após inbox/tool/egress não duplicam processamento ou efeito | Falhas injetadas com observação persistida e contagem de envio | Sim |
| Egress incerto | Timeout/5xx após possível aceite não é reenviado; aceito não vira entregue | Canal sintético sem dedupe; conciliação sem evidência recusada | Sim |
| Confirmação futura | Intenção modificada/expirada ou estado alterado não executa; replay converge | Duas confirmações concorrentes, alteração de payload, permissão revogada e nova conferência | Sim para F5 |
| PreCadastro | Confirmar dados cria só pendente; só Credor decide; aprovar converge a um Devedor | Correção de dados, CPF inválido, duplicidade, rejeição, concorrência, crash e dois atores | Sim para F4 |
| Degradação/budgets | 401/revogação/timeout/provedor indisponível encerram com resposta fixa; sem loop/fallback | Limites configurados de etapa/chamada/tempo/concorrência e medição | Sim |
| Privacidade/retenção | Prompt autorizado não vaza para logs/traces; expurgo em 90 dias não apaga auditoria financeira | Inspeção de persistência/logs sintéticos, expurgo temporal e restauração | Sim |
| Valor de jornada | Assistência reduz trabalho ou aumenta clareza sem piorar precisão | Comparação assistida versus determinística, revisão pelo Credor e metas previamente escolhidas | Condição de produto antes de expandir |

## 12. Questões e decisões que Architect deve encaminhar

| Questão | Evidência disponível / falta | Owner e encaminhamento |
|---|---|---|
| Qual trabalho merece ser o centro: dia/cobrança, perguntas pontuais ou captação? | Fontes de produto e UI favorecem rotina; frequência real desconhecida | Credor/produto: ordenar jornadas com exemplos sintéticos; pode inverter F3/F4 |
| B1: quais leituras exatas e quais campos? | Tabela da seção 8; saldo já previsto, quatro relatórios ainda não governados | Architect/Plan: decidir catálogo, schema, filtro, paginação, datas e proibições; não fechar B1 por este inventário |
| Quitação e simulação devem existir no assistente? | Permissão compartilhada no GET e POST persistente | Arquitetura: excluir inicialmente; eventual separação de leitura exige contrato/RBAC e rito próprio |
| Como identificar Devedor cadastrado fora da Operadora? | Número conhecido não autentica sujeito; PLAN-033 só tem duas classes | Proprietário/arquitetura: desenho específico antes de qualquer saldo ao titular |
| Onde ficam rascunhos, sua validade e prova da confirmação? | Nenhum protocolo agentic implementado | Architect: separar memória de conversa, rascunho e intenção executável; decidir retenção aplicável sem herdar prazo por suposição |
| Quais monitores e com qual fonte de mudança? | Jobs e snapshots existem; dispatcher do IMP-348 fora do plano | Arquitetura/produto: escolher polling/snapshot ou consumidor governado por necessidade; evitar alerta em todo ciclo |
| Provedor/modelo e operação | Escolha declarada, identificação e prova operacional não registradas | Proprietário/engenharia: registrar insumos não secretos e completar IMP-359, sem reabrir BYOK |
| Divergências Product/DR-004/PLAN-033 | Seção 3 e discovery anterior | Governança: erratas/revisão formal no ciclo apropriado; não aceitar rótulo legado como regra atual |

## 13. Parecer especializado, review e adjudicação

### Materialização e privacidade

OpenCode foi acionado pelo Harness com modelo disponível `opencode/muse-spark-1.3-contributor-free`, agente `plan`, papel `ai_architect`, `READ_ONLY`, tarefa `e572015e-ecea-4346-8e68-67c1e434ac9d`. Recebeu um repositório temporário sem commit com dois arquivos: fatos sanitizados pelo coordenador e nomes/linhas/rotas extraídos por AST de 110 arquivos. Não recebeu dados de clientes, valores financeiros reais, credenciais, conversas, CSV, checkout completo ou contexto externo bruto. `allowedPaths` delimita instrução e detecção, não sandbox; o isolamento do pacote reduz exposição, sem alegar confinamento de segurança do processo.

Uma validação inicial de envelope foi recusada antes da inferência (`INVALID_AGENTIC_CONTRACT`): PRESENT exige papel `ai_architect`. O envelope foi corrigido para `architect`/`ai_architect`/`plan`/`READ_ONLY`; a execução válida da tentativa 1 retornou em 137.504 ms, exit 0, sem mudança de arquivos, índice ou HEAD do pacote. Isso comprova preservação observada, não aceite semântico.

### AI Impact Brief e parecer reconciliado da primeira análise

O especialista cobriu dez grupos analíticos, personas, matriz, alternativas, fases e avaliação. Favoreceu cockpit assistido com leitura e rascunhos, identificando riscos de origem do webhook, identidade do Devedor, efeitos incertos e confusão snapshot/fila. O coordenador confirmou o benefício como hipótese e manteve os bloqueios do plano.

**Review do coordenador da tentativa 1: CORREÇÃO.** A saída bruta não foi incorporada como verdade. Reconciliações materiais:

- Zero classes/funções no AST de `iam_catalogo.py` não significa arquivo vazio: o catálogo é uma constante real (E01). Descartado esse achado.
- Quantidade de símbolos em `financial_guardrails.py` não mede robustez ou custo agentic. Descartada a inferência.
- Simulação criada por POST persiste; GET de quitação exige permissão de execução (E03/E05). Excluídos da primeira seleção de tools.
- `PreCadastro` é persistido como pendente após confirmação do remetente; aprovação humana cria Devedor. Não é apenas rascunho efêmero e não exige aprovação do Credor para criar a pendência.
- RAG, memória longa, Mercado Pago, teto monetário e nova fila de resumo não são pré-requisitos universais para comandos confirmados. As exclusões do v1 não são uma lista de coisas obrigatórias no futuro.
- Reversibilidade não apaga PII enviada ao provedor, PreCadastro aprovado ou mensagens já enviadas; “risco baixo porque GET” foi rejeitado.
- Origem verificada e política de incerteza continuam pré-requisitos do plano; resumo/vespera permanecem possíveis sem LLM. Não se introduz confirmação por mensagem determinística já autorizada pela finalidade/consentimento.

### Adjudicação do coordenador — sem aceite de risco material

| Achado | Classificação/estado | Ator / evidência | Porta afetada |
|---|---|---|---|
| B1 herdado: catálogo nominal não decidido | BLOCKER / OPEN | Coordenador; PLAN-033/backlog e seção 8 são candidatos, não decisão | GATE-E3 / 356-D |
| B-1 especialista: origem e prontidão operacional | BLOCKER / OPEN | Coordenador; IMP-359 não executado | GATE-E1b e habilitação Operadora |
| B-2 especialista: egress sem dedupe | CONCERN para discovery; BLOCKER / OPEN para retry/envio mutável futuro sem contrato | Coordenador; ADR-009/E09. Restrição não impede projetar leitura nem substitui o controle de incerteza vigente | 356-E e futura expansão de egress |
| B-3 especialista: identidade do Devedor | BLOCKER / OPEN apenas para autosserviço autenticado | Coordenador; nenhuma leitura ao Devedor habilitada no recorte proposto | Horizonte K19 |
| C-1/C-2: universos e semântica financeira | CONCERN / RESOLVED no texto de discovery; avaliação de produto pendente | Coordenador; seções 3, 7, 8 e 11 distinguem snapshot/fila/realizado/projeção | Catálogo/avaliação futuros |
| C-3/C-4: catálogo vazio e cobertura inferida por símbolos | REJECTED_WITH_RATIONALE | Coordenador; constantes de E01 e inadequação do método de contagem | Nenhuma liberação de gate |

### Parecer final sobre o documento

A tentativa 2, no mesmo modelo e tarefa, recebeu somente `discovery.md` e esclarecimentos sanitizados em outro pacote temporário. Não seguiu links para o checkout original. Retornou em 50.499 ms, exit 0, `EM_REVIEW`, sem alterações observadas. O especialista apresentou AI Impact Brief, comparação das quatro alternativas, invariantes, avaliação e itens adiados; seu parecer foi **APPROVED PARA O DISCOVERY**, sem erro material remanescente. Manteve como preocupações de implementação a prontidão para resumo/véspera e a decisão de excluir ou expor projeção em B1.

**Review final do coordenador: APROVADA para o artefato de discovery.** Os três checks do envelope foram observados: completude do parecer, revalidação das alegações contra fontes e preservação READ_ONLY do pacote sanitizado. Registrados 3 aprovados, 0 falhos e 0 não executados na telemetria local do Harness. As correções inválidas da primeira análise não foram repetidas. Depois da revisão semântica, apenas o identificador local foi ajustado ao validador documental e esta seção de evidências foi completada.

Os zero bloqueadores dessa revisão referem-se **ao discovery**, não ao produto. B1, IMP-359 e os bloqueios condicionais da tabela anterior permanecem abertos nos escopos indicados. Não houve aceite de risco material, adjudicação pelo especialista, fechamento de gate ou aprovação de arquitetura.

## 14. Handoff e evidências de encerramento

**Próximo workflow recomendado:** Architect, tomando este inventário como contexto e mantendo PLAN-033/DR-005/DR-004 como fontes governantes. Decidir A versus expansão B, recorte de F2, fronteira de rascunho e sequência F3/F4; registrar alterações formais necessárias antes de Plan/Execute. Nenhuma IMP foi executada e nenhum gate G0–G11/GATE-E foi fechado por esta sessão.

O CSV não relacionado `docs/whatsapp/revisao-manual-colunas-2026-09-09.csv` e todas as mudanças preexistentes devem permanecer intactos. Baseline de hashes foi capturado antes das escritas documentais; a verificação final compara esses arquivos, índice e HEAD. O grafo atualizado é derivado local ignorado pelo Git, não nova fonte normativa.

| Verificação executada | Resultado observado | Limite |
|---|---|---|
| `npm run docs:validate` | 388 verificações OK, 36 avisos preexistentes, zero erros | Primeira chamada falhou por dependência `ajv/dist/2020` ausente no worktree. Reexecução usou `NODE_PATH=C:/emprestimo/node_modules`, só no processo, aproveitando dependências existentes. Identificador novo inicialmente interpretado como namespace não registrado foi corrigido; nenhuma regra/Registry foi alterada |
| `npm run harness:check` | 135 checks aprovados, zero falhas | Estrutura/processo, não certificação do Agentic |
| `npm run harness:test` | 40 checks de coordenação e 3 do validador aprovados, zero falhas | Fixtures do Harness, sem rede e sem commits no checkout do produto |
| Links locais deste discovery | 69 destinos existentes, nenhum quebrado | Confere existência; revisão semântica é separada |
| `git diff --check` e inspeção do novo arquivo | Sem erro de whitespace | Não representa teste de produto |
| Hashes SHA-256 do baseline | 1.215 arquivos anteriores idênticos; zero alterado/removido pelo discovery | Inclui mudanças preexistentes e CSV não relacionado; arquivos ignorados não fazem parte desse baseline |
| Índice e HEAD | Índice sem alterações; HEAD permanece `6ae2f685e754259e46c7489b770e2be3f0b108ea` | Nenhum commit, push, PR, merge ou deploy |

O único novo arquivo versionável desta sessão é este discovery; não foi feito commit. O mapa de retomada e o handoff de entrada foram preservados: ao retomar, este artefato complementa seu estado histórico. Não foi executado `gate:full`, que restaura evidências via Git. Testes de produto, chamadas à VPS/provedores e validação visual não foram executados nem são alegados como feitos.
