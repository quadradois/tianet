# Plano de execução — Núcleo de consultas do assistente

**Identificador local:** `agentic-plano-execucao-2026-09-09`

**Versão:** 1.4.1

**Última revisão:** 2026-09-09

**Status:** Aprovado pelo proprietário em 2026-09-09; execução autorizada dentro dos slices e gates registrados.

**Slice atual:** reconciliação documental concluída; próximo slice de produto é Prontidão — IMP-359, para satisfazer GATE-E1b.

**Bloqueado por:** pré-requisitos operacionais antes do IMP-356; GATE-E1b e GATE-E3 permanecem abertos.

**Workflow / classificação / risco:** `plan` / `ARCHITECTURAL` / alto.

**Impacto agentic:** `PRESENT` — catálogo/autorização, limites/contexto e avaliação. Parecer especializado reconciliado na seção de revisão.

**Autorização:** em 2026-09-09, após revisar a versão 1.4.0 com OpenRouter, NVIDIA e OmniRoute, o proprietário respondeu “sim esta aprovado!”. Isso fecha G5 e autoriza executar os slices dentro dos parâmetros, dependências e limites deste documento. Não autoriza commit, push, PR, merge, deploy, produção, mensagens reais, uso de dados reais ou ações externas irreversíveis.

**Plano/IMP/GATE-E do produto:** [PLAN-033](../../implementation/plans/PLAN-033-copilot-tianet.md), [backlog PLAN-033](../../implementation/backlogs/PLAN-033-execution-backlog.md), IMP-355/359/361/356 A–F; GATE-E1b/E3 independentes. Este documento detalha o processo e não renumera IMPs nem substitui o backlog congelado.

## Objetivo e resultado observável

Permitir que a Operadora autorizada consulte seis capacidades da API pelo WhatsApp, com fatos financeiros apresentados por código determinístico, isolamento de contexto e recuperação que não repita envios incertos. A conclusão requer todas as entregas A–F do IMP-356 e suas dependências comprovadas; um transcript correto não basta.

A [arquitetura](../../architecture/reviews/agentic-arquitetura-capacidades-2026-09-09.md), especialmente seções 4–6, é a especificação proposta de catálogo, argumentos, campos e fronteiras. O [discovery](../../audits/discoveries/agentic-capacidade-potencial-2026-09-09.md) fundamenta o valor e as alternativas. Este plano acrescenta decomposição, parâmetros propostos e provas, sem copiar regras de domínio.

## Contexto e pré-voo

Baseline desta etapa: HEAD destacado `6ae2f685e754259e46c7489b770e2be3f0b108ea`, 1.217 arquivos versionáveis preservados antes da criação deste plano. O handoff anterior menciona uma branch; o Git observado prevalece. Alterações anteriores no conector, compose, documentação e CSV não pertencem a este plano.

O grafo foi atualizado na etapa anterior desta conversa; nesta etapa `graphify explain ConsultaSaldoService` retornou 16 conexões. Fontes atuais foram conferidas diretamente: [Motor](../../../src/emprestimo/application/motor_financeiro.py), [relatórios](../../../src/emprestimo/application/relatorios.py), [cadastro e autoria](../../../src/emprestimo/application/cadastro_devedor.py). A cobertura documental do grafo permanece parcial, conforme arquitetura; ausência no índice não demonstra ausência no produto.

| Estado observado | Consequência para execução |
|---|---|
| Saldo agregado e rotas de relatórios existem | Não reconstruir o Motor nem somar no agente; verificar contratos e permissões |
| Cadastro já contém `_autoria` e propagação de `usuario_id` | IMP-361 exige recertificação dos caminhos e reconciliação do status; não presumir retrofit inteiro ausente nem concluído por grep |
| IMP-355 publicou criação de usuário; seed mínimo ainda exige conferência | Reusar IAM administrativo e provar replay/perfil sem privilégios mutáveis |
| Proprietário confirmou OpenRouter e modelos gratuitos com tools e depois pediu análise do provedor NVIDIA direto | OpenRouter permanece a rota elegível proposta; NVIDIA direta entra na comparação sintética, sujeita aos termos de trial |
| Proprietário sugeriu conciliar o OmniRoute para acessar os modelos oferecidos | Gateway entra como opção isolada de avaliação; não altera seleção nominal, elegibilidade ou proibição de fallback |
| Serviço conversacional ainda é proposto; conexão local não prova produção | IMP-359 e prova de origem continuam pré-requisitos reais |
| Campos de posição usam estados atuais | Saldo/resumo/acertos somente hoje; registros por período não são snapshot de fechamento histórico |
| Retirar projeção do DTO não impede cálculo no backend | Qualificar custo no backend antes de habilitar relatórios |

## Escopo, invariantes e alternativas

Escopo: reconciliação formal, pré-requisitos do núcleo, ingress/inbox, limites, identidade, seis leituras, apresentação, egress, retenção e certificação. Antes do IMP-357, desconhecidos recebem apenas mensagem fixa, sem coleta cadastral ou leitura de carteira. PreCadastro segue C→D em ciclo posterior; não é eliminado do PLAN-033.

Ficam fora: cockpit e rascunhos, comandos de negócio, projeções, saldo histórico, quitação, simulação persistida, RAG, memória longa, integração produtiva com outro provedor ou reforma do frontend. A comparação sintética do endpoint NVIDIA direto e a prova do OmniRoute não autorizam integração de produção. IMP-353/354 continuam determinísticos e conservam seus gates; este recorte não os certifica nem os remove do plano maior.

Escolha aceita para detalhamento: API autenticada + catálogo fechado + apresentação determinística, conforme alternativas da arquitetura. SQL direto, prosa financeira livre e orquestrador geral continuam rejeitados neste recorte. [SPEC-004](SPEC-004-regras-normativas-do-codigo.md), [DR-005](../decision-requests/DR-005-pii-modelo-e-teto-de-custo-do-copilot.md), [ALP-001](../agent-loop/AGENT-LOOP-EXECUTION-PROTOCOL.md) e [contexto externo](../../operations/contexto-externo.md) permanecem normativos.

Controles obrigatórios: contexto/destinatário/URLs fixados pelo servidor; apenas três permissões de leitura no primeiro catálogo; extra fields recusados; referências opacas e revalidação por uso; decimal exato; nenhuma soma no agente; desconhecido sem carteira; inbox antes do ACK tratável; índice único e fencing; intenção de egress persistida; incerteza sem reenvio; logs sem conteúdo; expurgo de 90 dias separado da auditoria append-only. A API continua sem webhook público.

## Provedores e modelos — confirmações do proprietário

**OpenRouter permanece o provedor de acesso proposto para o piloto**, com `LLM_BASE_URL=https://openrouter.ai/api/v1`, chave do cliente e integração `httpx` já prevista. Em 2026-09-09 o proprietário esclareceu que já houve análise de modelos e que a intenção é usar **LLMs gratuitos com suporte nativo a tools/function calling**. Depois solicitou analisar também os modelos gratuitos no provedor NVIDIA direto, em especial Nemotron. Essa solicitação reabre a comparação técnica, sem declarar a rota NVIDIA apta à produção.

A lista nominal e os resultados dessa análise não foram localizados na busca textual dos documentos deste checkout, histórico Git, handoffs, tarefas acessíveis e sessões locais. As referências encontradas no PLAN-033/DR-005 mencionam OpenRouter, mas não identificam a lista gratuita analisada. A busca foi então reconstruída no discovery atual do OpenRouter (`openrouter-modelos-gratuitos-tools-2026-09-09.md`, artefato em espera fora deste checkout por decisão da rota A em DR-005 §7), sem apresentar a nova lista como se fosse o artefato antigo. Os modelos `opencode/...` registrados na revisão de engenharia não são a seleção de LLM da aplicação TiaNet.

O catálogo público OpenRouter retornou 17 variantes `:free` com preço zero e `tools`. Somente `inclusionai/ling-3.0-flash-fin:free` e `inclusionai/ling-3.0-flash-sante:free` também apareceram, pelo `model_id` gratuito exato, na lista oficial de endpoints ZDR. **`inclusionai/ling-3.0-flash-fin:free` permanece o candidato elegível primário para o piloto**, ainda sujeito às três rodadas e à reconfirmação de privacidade.

A análise do provedor NVIDIA direto (`nvidia-nemotron-provedor-direto-2026-09-09.md`, artefato em espera fora deste checkout por decisão da rota A em DR-005 §7) confirmou endpoint gratuito OpenAI-compatible para `nvidia/nemotron-3-super-120b-a12b`, com foco declarado em agentes, raciocínio e tool calling. Ele entra como **principal comparador técnico sintético**. Os termos do NVIDIA API Catalog limitam a rota gratuita a trial e proíbem produção; também não foi demonstrado controle ZDR equivalente. Nemotron direto ou via OpenRouter fica, portanto, fora do piloto real enquanto essas restrições persistirem.

O discovery do OmniRoute (`omniroute-gateway-llm-2026-09-09.md`, artefato em espera fora deste checkout por decisão da rota A em DR-005 §7) confirmou compatibilidade de transporte: o projeto oferece gateway local OpenAI-compatible, rotas específicas por provedor e registros para OpenRouter, NVIDIA e Nemotron. Ele entra como **opção de infraestrutura em avaliação**, executada como sidecar privado; não será incorporado ao backend Python nem se tornará fonte de verdade do catálogo TiaNet.

A versão inspecionada do OmniRoute pode converter uma chamada de ferramenta escrita como texto em `tool_calls` estruturado. Esse comportamento impede certificação porque oculta a ausência de function calling nativo. O gateway só pode avançar ao piloto se a conversão for desativada ou removida de forma sustentável e se uma prova direta versus gateway demonstrar transparência. A configuração TiaNet também precisa fixar provedor e modelo, exigir autenticação e criptografia, omitir corpos de logs e desativar `auto`, combos, fallback, compressão, memória, caches, sync e extensões.

Critérios para o slice BYOK, preservando os controles da arquitetura:

- Recapturar os candidatos do discovery com ID exato e variante gratuita realmente disponível no catálogo; não presumir que acrescentar `:free` cria uma variante existente. Entrada, saída e demais componentes da requisição precisam manter gratuidade, sem recursos pagos adicionais.
- Fixar um modelo nominal certificado por configuração no primeiro recorte. Outros modelos gratuitos podem ser candidatos à mesma avaliação; alternância dinâmica ou fallback não estão autorizados pelo simples uso do plural “modelos”.
- Conferir suporte a `tools` e aos parâmetros utilizados no endpoint efetivo, além de executar a avaliação sintética prevista. A declaração de suporte no catálogo não substitui prova de seleção correta da ferramenta e validade dos argumentos. A documentação oficial explica o [contrato de tool calling](https://openrouter.ai/docs/guides/features/tool-calling).
- Dividir a seleção em comparação técnica e filtro de elegibilidade. A comparação usa fixtures sintéticas idênticas entre Ling Fin via OpenRouter e Nemotron 3 Super via NVIDIA direta; somente uma rota que também passe privacidade, licença/termos, gratuidade vigente e capacidade mínima pode chegar ao piloto.
- Tratar créditos e limites por chave/provedor. A cota NVIDIA é desconhecida até inspeção da conta e não amplia o orçamento do OpenRouter nem sustenta promessa de disponibilidade.
- Tratar o catálogo gratuito do OmniRoute apenas como fonte de descoberta. Cada entrada continua sujeita aos termos, cota, privacidade e suporte nativo a tools do provedor efetivo; endpoints públicos anônimos ou não oficiais são inelegíveis.
- Se o OmniRoute for avaliado, usar rota vinculada ao provedor e allowlist de um único modelo. Modelo `auto`, aliases mutáveis, combos e qualquer fallback permanecem proibidos.
- Não usar `openrouter/free` neste desenho de modelo fixo: esse [roteador seleciona modelos gratuitos automaticamente](https://openrouter.ai/docs/guides/routing/routers/free-router). A restrição é à troca automática já excluída pela arquitetura, não ao acesso gratuito.
- Falta de capacidade, quota esgotada, remoção do modelo ou perda de gratuidade gera indisponibilidade controlada; não migra para modelo pago, não compra créditos e não altera provedor/modelo automaticamente. Gratuidade é critério de elegibilidade da rota, não novo teto mensal em moeda, cuja ausência continua regida pela DR-005.
- Requisições do piloto com dados autorizados exigem `provider.data_collection=deny` e `provider.zdr=true`, além de política equivalente na conta. Nenhum endpoint elegível produz falha fechada; não relaxar a privacidade nem selecionar rota paga.
- Antes de habilitar, registrar limites atuais da conta/rota e endpoint de execução, além dos critérios de dados já vigentes. Verificar também o roteamento interno do OpenRouter: modelo fixo não garante executor upstream fixo. Não declarar esses pontos medidos nesta correção documental.

Consulta à documentação/API pública em 2026-09-09, sem chave nem chamada de inferência. Os discoveries do OpenRouter, da NVIDIA direta e do OmniRoute passam a ser as referências correntes; localizar o artefato antigo deixa de bloquear o planejamento, mas qualquer divergência futura deve ser reconciliada, não mesclada silenciosamente.

## Parâmetros propostos para aprovação

Os valores abaixo são uma configuração inicial conservadora para testes sintéticos, não limites medidos do produto nem SLA. Aprovar este plano aceita ensaiá-los; habilitação exige o resultado dos ensaios e os gates operacionais. Configuração obrigatória ausente ou incoerente impede iniciar a capacidade. Não há limite financeiro mensal.

| Parâmetro | Proposta inicial | Prova e comportamento no limite |
|---|---|---|
| Texto da mensagem | 2.000 caracteres Unicode | Acima: descarte/recusa fixa sem LLM; mídia descartada antes de persistir |
| Entrada de inferência | 8.000 tokens por chamada, incluindo instruções, schemas, histórico, referências, resultados filtrados e metadados de tools | Tokenizador compatível ou limite superior demonstrável para o modelo escolhido; sem medidor confiável, inferência desabilitada |
| Saída de inferência | 1.000 tokens por chamada | Provider cap + validação; truncamento não executa ferramenta |
| Chamadas LLM / tools por entrada | 2 / 2 tools lógicas sequenciais; até 6 requisições HTTP de consulta no total, incluindo páginas e reconsulta | Localizar é 1 tool lógica com até 5 páginas HTTP; saldo pode consumir a sexta. Cada HTTP consome reserva durável; esgotamento recusa resultado incompleto, sem reinício de orçamento |
| Tempo total de processamento | 45 segundos desde o primeiro claim persistido, incluindo chamadas | Deadline imutável `primeiro_claim_em + 45 s`; reclaim só usa o restante. Contadores reservados por entrada/índice antes de cada tentativa; expiração não inicia novo efeito |
| HTTP LLM / API | 15 / 5 segundos por tentativa, limitados pelo deadline restante | Timeout não implica cancelamento no servidor; budget backend verificado separadamente |
| Retries de inferência | 0 automáticos (`LLM_MAX_RETRIES=0`) | Erro/incerteza degrada sem nova cobrança; nova mensagem recebe novo orçamento |
| Reconsulta GET após falha | No máximo 1 tentativa adicional de HTTP na entrada, dentro do teto de 6 HTTP e do deadline | Reautoriza; registra novo instante; sem reserva restante, não repete. Reclaim não zera contador nem transforma tentativa incerta em gratuita |
| Concorrência / sessão | 2 trabalhos globais, 1 por sessão | Reserva atômica em PostgreSQL; 1 vaga reservada à Operadora, desconhecido não a ocupa |
| Admissão por janela móvel de 60 s | Instância: 30; Operadora por remetente: 6; desconhecido por remetente: 2 e classe: 6 | Relógio servidor e decisão atômica, replay não consome nova quota; recusa não gera tempestade de respostas |
| Admissão diária no nível gratuito | 20 novas entradas com LLM por chave/dia, reservando 2 chamadas por entrada | Teto local de 40 chamadas deixa 10 das 50 documentadas como margem. Header externo só pode reduzir disponibilidade; nunca aumenta o teto automaticamente |
| Resposta a quota excedida | No máximo 1 aviso por remetente por 60 s | Aviso percorre egress e orçamento de envio; demais entradas descartadas com métrica |
| Backlog pendente | 100 entradas por instância, 10 por sessão | Admissão antes de aceite; saturação retorna indisponibilidade de transporte sem guardar corpo e pode provocar retries limitados do provedor |
| Idade máxima antes do claim | 120 segundos | Entrada vencida não consulta; estado terminal e métrica |
| Referência opaca | 5 minutos; apenas seleção pendente na sessão | Expira por relógio e invalidação; não herda retenção de 90 dias |
| Contexto conversacional ativo | 10 mensagens, até 30 minutos; subordinado ao teto de tokens | Seleção determinística; persistência continua sob retenção de 90 dias |
| Busca e exibição | Página de 20; máximo 5 páginas consultadas; até 5 candidatos exibidos | Resultado incompleto pede refinamento; nunca escolhe primeiro homônimo |
| Intervalo de relatório | Até 31 dias inclusivos, `fim <= hoje` | Período maior exige refinamento; calendário válido, fuso operacional explícito |
| Resposta API consumida | 256 KiB e até 100 itens processados | Leitura em streaming limitada; exceder recusa relatório completo, sem truncamento enganoso |
| Resposta ao canal | Uma mensagem de até 3.000 caracteres | Exceder encaminha para rota fixa da plataforma, sem dividir resposta financeira parcial |
| Claim / heartbeat | Lease 60 s, renovação a cada 10 s com fencing | Executor vencido não finaliza nem inicia envio; tentativa externa iniciada que perde dono torna-se incerta |
| Retenção / expurgo | 90 dias; execução diária em lotes de 1.000 linhas | Cascatas/referências e restore ensaiados; nunca apagar auditoria financeira |

**Envelope bruto:** não fixar `AGENT_WEBHOOK_MAX_BYTES` em 64 KiB por conveniência. O backlog exige valor acima do maior HistorySync observado. O primeiro slice registra somente o tamanho e a forma sanitizada, sem copiar mídia/conversa; propõe o próximo múltiplo de 64 KiB estritamente acima da amostra máxima, com teto de engenharia de 8 MiB. Esse teto é proposta a validar: se a amostra exigir mais, parar para revisar consumo/streaming antes de aprovar o valor. Proxy e aplicação devem limitar leitura incremental; eventos HistorySync dentro do limite recebem 2xx de descarte, sem inbox. Corpo realmente acima do limite pode receber 413 e retries do provedor: medir e registrar esse comportamento, não prometer zero retry para rejeição de transporte.

**Custo efetivo das APIs:** antes da certificação, executar 100 consultas sintéticas por ferramenta em carteira com 1.000 operações e 10.000 pagamentos, com dois clientes concorrentes. Meta inicial: p95 <= 2 s, nenhuma consulta > 5 s, teto de execução de statement de 3 s no acesso do serviço. Cada ferramenta exige mecanismo efetivo no backend para limitar também volume e cálculo em aplicação; statement timeout isolado não limita CPU do Motor. Registrar máquina, dataset, plano da consulta e cancelamento/limitação efetivos; timeout HTTP sozinho reprova o requisito. Limite de volume suportado precisa ser verificável no backend antes de cálculo custoso, sem resposta financeira parcial. Sem mecanismo efetivo, ferramenta desabilitada obrigatoriamente, mesmo se a amostra tiver boa latência. Se isso exigir API/arquitetura adicional, não ampliar o slice: desabilitar a ferramenta e reabrir desenho/plano. Desabilitar protege operação, mas não certifica o catálogo de seis ferramentas.

## Slices e orçamento de mudança

Os nomes abaixo são rótulos locais subordinados às IMPs existentes. Cada slice inclui apenas código do seu comportamento, testes materiais e documentação associada. Estimativa de arquivos é teto inicial de revisão, não justificativa para omitir teste; se extrapolado, dividir antes de continuar. Caminhos novos são propostas e serão confirmados no pré-voo, sem criar arquivos nesta sessão.

### Reconciliação — primeiro slice documental

- **Propósito / dependência:** registrar formalmente a direção aceita e integrar esta decomposição à governança existente, após aprovação deste plano. Não é nova IMP nem altera a conclusão histórica do IMP-358.
- **Arquivos / orçamento:** até 6 documentos: PLAN-033, seu backlog, arquitetura proposta, este plano, decisão formal aplicável e ponteiro de handoff. Sem `src`, migration, prompt, compose ou CSV.
- **Aceite:** identificar rito e eventual ADR pela governança vigente sem inventar número; registrar aprovação de catálogo/apresentadores; reconciliar status de provedor sem ler chave, ausência de teto monetário, estado da autoria, B1 e desconhecido antes do IMP-357. Preservar E1b, E2/E3/E4 e dependências. Registrar quais decisões são aceitas e quais dependem de evidência.
- **Checks:** `npm run docs:validate`, links e diff focal; inspeção dos 6 nomes, 3 permissões e referências ao ALP-001. Nenhum gate de produto fecha por edição de status.
- **Rollback:** reverter somente o diff documental desta entrega mediante necessidade; não apagar histórico de aprovação nem arquivos anteriores. **G6:** limites definidos e G5 recebido; este slice documental foi concluído.

### Prontidão — IMP-359 e GATE-E1b

- **Propósito:** satisfazer checklist operacional já existente antes do IMP-356. Planejar ensaios localmente e preparar diff/configuração revisável; produção, envios reais e exclusão de instância exigem autorização específica.
- **Arquivos / orçamento:** até 8 por subentrega operacional; compose, configuração de proxy/deploy e runbooks em `docs/operations`. Dividir backup/restore, ingress e implantação em subentregas do mesmo IMP se necessário; não tratar IMP-359 inteiro como patch único.
- **Aceite:** checklist original completo, prova de origem ou Operadora bloqueada, API/DB privados, segredos fora de Git/logs, restore e rollback demonstrados. Medição do envelope e configuração dos limites; registrar modelo/base URL previamente escolhidos e política de dados sem trocar fornecedor. Preservar ordem de medir logout antes da remoção prevista no backlog, conferindo antes o estado real da instância.
- **Testes / verificação:** ensaio de restore sintético, spoof de origem, healthcheck/restart e rollback; evidência externa sanitizada quando autorizada. **Rollback:** desabilitar ingress/agente e restaurar release, preservando banco/intenção; exclusão externa não é reversível.

### Identidade mínima — pendência IMP-355 e evidência IMP-361

- **Propósito / dependências:** após reconciliação, concluir seed restrito e recertificar autoria existente. Não depende de canal para teste local; não adianta o IMP-356 antes do IMP-359.
- **Arquivos / orçamento:** até 8; caso de uso administrativo/seed no módulo IAM existente, testes IAM/API e cadastro, contrato/documentação se alterados. Não conceder `pre_cadastro.criar` antes da capacidade correspondente existir e ser planejada.
- **Aceite:** usuário/perfil/atribuição convergem em replay; três permissões de leitura exatas; usuário desativado/perfil revogado recusados; escrita e administração recebem 403, cross-tenant recebe resposta neutra. IMP-361 só ganha conclusão se sucesso/falha/rollback/replay propagarem autoria pelos caminhos atuais; corrigir lacuna concreta, não reescrever o serviço.
- **Testes / verificação:** integrações IAM em PostgreSQL, matriz positiva/negativa, testes atuais de cadastro; observar número de efeitos/auditorias. **Rollback:** desabilitar usuário de serviço; reverter somente concessões feitas por este seed, sem apagar perfil humano.

### Entrada durável — 356-A/B e base de 356-F

- **Propósito / dependências:** após IMP-352/355/359/361/362 comprovados, criar ingresso limitado e persistência própria sem inferência/envio habilitado.
- **Arquivos / orçamento:** até 12; pacote proposto `src/emprestimo/agent/` para contratos/configuração/ingress/store, migration manual em `migrations/versions`, wiring e testes `tests/unit/agent` e `tests/integration/agent`. Tabelas conversacionais não pertencem a `RegistroComunicacao`; usuário DB sem acesso às tabelas de crédito.
- **Aceite:** unicidade `(instance_id, provider_input_id)`, ACK tratável após commit; descarte suportado com 2xx; sem ID/grupo/própria/mídia não gera tool/LLM. Verificar dedupe antes de consumir quota; inserção de inbox e reserva de admissão compõem decisão transacional, com conflito de unicidade desfazendo a reserva concorrente. Duplicata já aceita recebe ACK e métrica sem consumir quota nem gerar aviso. Dois IDs iguais em instâncias distintas não colidem. Sessão vincula contexto; origem não comprovada nunca abre Operadora. Crash após commit recupera a mesma entrada; migração aditiva com downgrade estrutural testado.
- **Testes / verificação:** PostgreSQL real para corrida/uniqueness, falha no commit, payload em fronteira, descarte HistorySync, contagem zero de chamadas externas. **Rollback:** parar claims/ingress; preservar inbox. Não executar downgrade destrutivo em banco com mensagens por rotina.

### Execução limitada e sessão — 356-C/F

- **Propósito:** admission control, reserva durável, contexto, login/refresh e recuperação antes de liberar LLM. Depende da entrada durável.
- **Arquivos / orçamento:** até 10; configuração/runner/auth/session do pacote agent, store e testes de concorrência/tempo.
- **Aceite:** limites da tabela aplicados atomicamente também em restart; uma execução por sessão; desconhecido não ocupa reserva Operadora; fencing rejeita executor antigo. Refresh respeita contrato real de 15 minutos/7 dias, no máximo uma tentativa de renovação por falha, sem loop de 401; tokens em mecanismo de segredo definido na prontidão, nunca nas tabelas conversacionais. Referências expiram e contexto não atravessa classe.
- **Testes / verificação:** relógio controlado, rajadas distribuídas, virada da janela, dois workers, lease vencido, revogação antes de tool e antes de egress. **Rollback:** bloquear novos claims, encerrar com deadline, revogar credencial se necessário; recuperar somente ações não iniciadas.

### Catálogo e apresentadores — parte determinística de 356-D

- **Propósito:** implementar as seis ferramentas e apresentadores, testáveis sem LLM. Depende de identidade e sessão; todas as ferramentas permanecem desabilitadas no canal.
- **Arquivos / orçamento:** até 12 por lote; catálogo/DTO/dispatcher/presenters/referências e testes agent. Dividir em lote localizar+saldo e lote quatro relatórios sob a mesma 356-D; APIs existentes não mudam sem necessidade comprovada e revisão do escopo.
- **Aceite:** nomes/argumentos/campos iguais à arquitetura; URLs fixas; schema `extra=forbid`; autorização por chamada. Homônimo exige seleção; consulta histórica não vira hoje; períodos inclusivos e fuso explícito. Decimal/string e rótulos oficiais preservados; 404 não vira zero; projeção e acertos de fluxo não vazam. Resultado parcial/excessivo recusa apresentação completa. Limite de busca não autoriza omitir candidato.
- **Testes / verificação:** fixtures sintéticas + integração nas rotas reais; duas operações por Devedor, estorno e operação encerrada, mais de uma página, mudança de data, grandes decimais, campos extra, outro contexto/tenant. Executar qualificação de custo backend da tabela; registrar resultado por ferramenta. **Rollback:** desabilitar ferramenta/versão, sem fallback para GET mais amplo.

### Interpretação OpenRouter BYOK — conclusão de 356-D

- **Propósito:** ligar interpretação ao dispatcher certificado via OpenRouter, avaliando primeiro `inclusionai/ling-3.0-flash-fin:free` e os controles elegíveis definidos no discovery atual. Depende dos apresentadores e não pré-certifica o candidato.
- **Arquivos / orçamento:** até 8; cliente `httpx`, protocolo de intenção, instruções versionadas, runner e testes. Não acrescentar SDK ou fornecedor.
- **Aceite:** máximo duas inferências/duas tools e deadline; financeiro não é prosa livre. Modelo/variante fixos e gratuitos, `data_collection=deny` e `zdr=true`; ausência de endpoint elegível, 429 ou perda da variante degradam sem fallback. LLM recebe somente metadados/referências necessários; argumentos, resposta e tool-result são dados não confiáveis. Erro de schema, timeout, excesso, ferramenta arbitrária, autoridade simulada ou tentativa de escrita falham fechados. Após crash com inferência iniciada sem resultado, registrar consumo desconhecido e não reiniciar automaticamente.
- **Testes / verificação:** servidor falso determinístico para matriz adversarial; avaliação sintética no modelo escolhido somente em ambiente autorizado, com tokens/latência medidos e sem dados reais. **Rollback:** desabilitar cliente, respostas fixas via egress; nunca trocar modelo automaticamente.

### Comparação sintética NVIDIA — apoio a 356-D/F

- **Propósito:** medir `nvidia/nemotron-3-super-120b-a12b` diretamente em `https://integrate.api.nvidia.com/v1`, sem conectar essa rota ao canal, ao dispatcher produtivo ou a APIs de negócio. Depende das fixtures e schemas congelados do catálogo; não altera o aceite OpenRouter para o piloto.
- **Arquivos / orçamento:** até 5; adapter de avaliação isolado, configuração local do runner, fixtures/resultados sanitizados e testes. A credencial NVIDIA fica fora do Git. Não registrar o provedor no runtime do canal nem acrescentar fallback.
- **Aceite:** somente fixtures sintéticas e ferramentas simuladas; `enable_thinking=false` congelado para as 210 execuções; `tool_calls` nativo e schema fechado. Uma prova curta, não pontuada, pode observar reasoning ligado apenas para compatibilidade de resposta. Budget fixado abaixo do saldo/limites vistos na conta; nenhum dado real, egress, operação financeira ou promessa de disponibilidade. Resultado técnico não supera o filtro de termos, privacidade e produção.
- **Testes / verificação:** servidor falso para contrato do adapter e, em ambiente autorizado, prova curta seguida das três rodadas completas na combinação fixa. Registrar 401/402/429, créditos, tokens e latência sem conteúdo sensível. **Rollback:** desabilitar/remover a configuração do runner e revogar a chave se necessário; nenhum efeito de produto existe para reverter.

### Prova de transparência OmniRoute — opção de infraestrutura para 356-D/F

- **Propósito:** verificar se uma release fixa do OmniRoute pode intermediar a mesma combinação provedor/modelo sem mudar request, response, tool calling, roteamento ou retenção. É um experimento isolado posterior às fixtures congeladas; não conecta canal, dispatcher produtivo ou APIs reais.
- **Arquivos / orçamento:** até 7; compose/perfil experimental separado, configuração sanitizada, patch mínimo somente se não houver opção upstream para desligar tool calls textuais, testes de contrato e relatório. Nenhum código OmniRoute é copiado para o backend; credenciais e volumes ficam fora do Git.
- **Aceite:** tag formal e imagem fixadas por digest; rede privada; autenticação e criptografia obrigatórias; uma chave e um modelo permitidos; rota específica do provedor. `auto`, combo, fallback, retry interno de inferência, compressão, memória, caches, sync, exportação, MCP/A2A e proxy MITM desligados. Resposta textual permanece textual, `tool_calls` nativo conserva nome/argumentos/IDs e erros 401/429/timeout/modelo removido falham fechados. Cada tentativa admitida produz no máximo uma tentativa upstream. SQLite e logs não guardam corpos nem segredos em claro; credenciais necessárias ficam cifradas, com chave de criptografia fora do volume e do Git. Restart não reativa recursos. Qualquer divergência eliminatória encerra a opção.
- **Testes / verificação:** servidor upstream falso compara request/response direto e via gateway, incluindo `provider.data_collection=deny`, `provider.zdr=true`, tool nativa, envelope textual, streaming, erro, timeout e indisponibilidade. Contar tentativas upstream também em 429, desconexão e reinício. Depois, se o contrato passar, repetir amostra sintética no provedor/modelo exato e medir latência adicional. Inspecionar banco/logs/configuração após reinício. **Rollback:** suspender novas chamadas, remover o sidecar e restaurar conjuntamente `LLM_BASE_URL`, referência segura à credencial direta, `LLM_MODEL` e parâmetros de privacidade para a mesma rota nominal; chamada iniciada ou incerta não é repetida e nenhuma troca automática ocorre.

### Saída durável — 356-E

- **Propósito:** enviar uma resposta renderizada pelo adapter existente após revalidação; depende de catálogo, sessão e budgets certificados.
- **Arquivos / orçamento:** até 8; egress/store/runner do agent e testes com `EvolutionWhatsAppNotificationChannel` existente. Não criar segundo adapter nem substituir aquisição de token atual por variável antiga.
- **Aceite:** intenção/payload canônico contextual persistidos antes do envio; chave entrada/índice estável, divergência terminal. Sucesso persiste como aceito, sem alegar entrega. Timeout/5xx/2xx inválido/crash após chamada resultam em desconhecido sem retry. Somente falha com prova de não aceitação admite até uma nova tentativa dentro do deadline e quota; lease não reautoriza envio incerto. Links limitados às três rotas da arquitetura.
- **Testes / verificação:** crash em cada fronteira, dois workers, replay, mudança de contexto/destinatário, adapter falso que conta envios e não deduplica. Para aceite/incerteza anterior, replay deve adicionar zero chamadas de envio. **Rollback:** interromper novos envios e conciliar incertos; mensagem já enviada não pode ser recolhida por rollback.

### Certificação — conclusão de 356-F e GATE-E3

- **Propósito:** expurgo, observabilidade, recuperação integrada e avaliação A–F, sem novo escopo.
- **Arquivos / orçamento:** até 10; rotina de retenção/health/metrics, testes de integração/eval e relatório de gate/runbook. Separar eventual correção por slice responsável.
- **Aceite:** expurgo 90 dias alcança inbox/sessão/mensagem/tool-call/egress e referências; trilha financeira intacta. Restore bloqueia egress que pode ter sido enviado depois do backup até conciliação; nunca retoma toda a fila automaticamente. Logs sem PII/segredo/corpo; consumo desconhecido distinguido de zero. Seis entregas verdes e dependências com evidência atual, sem subset silencioso.
- **Testes / verificação:** matriz abaixo, restore e crash end-to-end sintéticos, qualidade no escopo e relatório ALP-001 com IMPs, testes, cobertura, qualidade, pendências, riscos, validade e autorização de seguir. **Rollback:** desabilitar capacidade inteira, preservar intenções e UI humana. Produção e envio real continuam sujeitos a autorização específica.

## Matriz de testes e critérios de avaliação

| Risco / requisito | Evidência esperada | Check e critério bloqueador | Slice |
|---|---|---|---|
| Exfiltração / identidade | Dois tenants, dois devedores, desconhecido, LID, spoof e revogação | Zero tool de carteira/egress financeiro em contexto indevido; contar chamadas reais do teste | Entrada/sessão/catálogo |
| Dinheiro e tempo | Resultado oficial comparado ao texto renderizado | Zero valor/semântica inventados; 404 distinto de zero, histórico recusado, sem float/soma | Catálogo |
| Completude / performance | Mais páginas/itens que limite e carteira de volume | Não publicar truncado como total; metas de custo backend satisfeitas ou tool bloqueada | Catálogo |
| Loop / abuso | Workers simultâneos e relógio controlado | Nunca exceder reserva/budget em race/restart; quota não multiplica avisos | Limites |
| Falso sucesso / repetição | Fault injection antes/depois de inferência, persistência e envio | Zero reenvio automático após aceite/incerteza; resultado aceito não diz entregue | BYOK/egress |
| Privacidade / restauração | Canários sintéticos em conteúdo e backups | Nenhum canário sensível em logs; expurgo observado e restore não reenvia | Certificação |
| Utilidade | 30 tarefas sintéticas, 5 por ferramenta, formuladas antes da execução | >= 27 resolvidas corretamente sem correção; falha segura conta como não resolvida | Certificação |
| Resistência adversarial | 40 casos: 8 identidade, 8 injection, 8 schema/tool, 8 dinheiro/tempo, 8 loop/replay | 40/40 respeitam controles; qualquer exposição/escrita/falso fato bloqueia | Certificação |

Rodar utilidade e adversarial três vezes por combinação fixa de modelo e rota: cada rodada cumpre o critério, sem média que esconda falha crítica. Congelar fixture/esperado antes de avaliar; registrar provedor, endpoint, versão, configuração, quantidade, latência, consumo e correções. No OpenRouter, o runner terá orçamento local próprio de 40 chamadas por dia, compartilhará a mesma cota externa da chave e só poderá rodar com a admissão conversacional desabilitada. As 210 execuções por combinação exigem no mínimo seis janelas diárias com uma chamada por caso, ou até onze se todos os casos consumirem duas chamadas; as 10 chamadas restantes da cota externa são margem operacional, não outro orçamento. Na NVIDIA direta, o budget será fixado abaixo do saldo e dos limites observados na conta antes da primeira rodada, sem transferir ou somar capacidade entre provedores. O OmniRoute somente entra depois de passar sua prova de transparência e usa budget da rota upstream, nunca uma cota presumida do gateway; seus resultados ficam em combinação separada. Troca/remoção do modelo ou da rota invalida a rodada. Isso qualifica comportamento sob amostra, não prova ausência universal de falha. Comparação de tempo/esforço com UI humana fica no piloto autorizado e somente em rota elegível: tarefas pareadas e meta de redução de pelo menos 20% no tempo mediano, com zero aumento de erros financeiros, antes de justificar expansão cockpit.

Comandos futuros no escopo Python: `uv run pytest <arquivos-do-slice>`, `uv run ruff check <escopo>`, `uv run black --check <escopo>`, `uv run mypy <escopo>` conforme configuração vigente; integrações exigem PostgreSQL de teste. Para migrations, upgrade/downgrade somente em banco descartável. Atualizar OpenAPI/snapshot/matriz apenas se contrato público realmente mudar. Validação documental: `npm run docs:validate`. Consultar [CONTRIBUTING](../../../CONTRIBUTING.md) e [HARNESS](HARNESS.md); não executar `gate:full` que restaura evidências alheias, nem instalar hooks por inferência de autorização. Nenhum teste de produto foi executado nesta sessão de Plan.

## Rollout, riscos e condições de redesign

Sequência: aprovação/reconciliação → prontidão e dependências → slices A–F desabilitados → comparações diretas → prova opcional do OmniRoute → certificação sintética → autorização específica de piloto/produção. Entregas IAM independentes podem ser verificadas antes da operação, como admite E1a; IMP-356 não atravessa E1b por essa exceção. Certificação do núcleo não conclui automaticamente o PLAN-033, as Fases A/D ou seus gates.

Este plano fica errado se a API não puder garantir escopo/semântica, se o provedor não sustentar function calling elegível, se controle de origem não for demonstrável ou se custo do backend não for limitável. Nesses casos desabilitar capacidade e retornar a Architect, sem contornar por prompt, aceitar URL secreta como autenticação ou somar dinheiro fora do Motor.

Também exigem redesign: múltiplos tenants por processo, escrita de negócio pelo chat, resposta financeira livre, replay externo exatamente uma vez, saldo histórico real ou consulta maior que o orçamento suportado. Catálogo versionado facilita novas leituras e apresentadores; a escolha por resposta determinística dificulta prosa genérica deliberadamente. Rascunhos e comandos precisam de novo ciclo de decisão, sem herdar G5 deste plano.

## Decisões, revisão e progresso

| Item | Estado / autoridade |
|---|---|
| Direção/catálogo/apresentação determinística | Aceitos para detalhar pelo proprietário em 2026-09-09; arquitetura anterior preservada como registro histórico da proposta |
| OpenRouter + modelos gratuitos com tools | Confirmados pelo proprietário; discovery atual reconstruiu 17 candidatos e indica Ling 3.0 Flash Fin gratuito como primeiro candidato, ainda sujeito à avaliação |
| OmniRoute | Compatível como gateway opcional isolado; bloqueado para piloto até eliminar síntese textual de tools e passar prova de transparência/segurança |
| Parâmetros numéricos e slices deste documento | Aprovados em G5 pelo proprietário em 2026-09-09; execução permanece sequencial e condicionada |
| Formalização G4 e reconciliação B1 | Aprovadas e registradas no primeiro slice documental; não fecham GATE-E1b/GATE-E3 |
| GATE-E1b e E3 | Permanecem pendentes; só evidência de produto e operação resolve |
| Revisão especializada do Plan | `APPROVED` para prontidão documental; preocupações reconciliadas abaixo, sem autorização de execução |
| Implementação / testes de produto / publicação | Código e testes de produto ainda não executados; publicação continua dependente de autorização específica |

### Revisão especializada reconciliada

OpenCode Harness, task `340b2ddb-27f3-4796-a779-ce8b14952125`, tentativa 1, modelo `opencode/muse-spark-1.3-contributor-free`, agente `plan`, `READ_ONLY`. O workflow do coordenador é Plan; o envelope especializado usa `architect` conforme HARNESS. Pacote externo limitado a duas cópias documentais sanitizadas, sem dados reais, segredos ou conversa; não seguir links para o checkout. Execução em 121.431 ms, exit 0, zero arquivos alterados e zero violações de escopo observadas.

O parecer incluiu brief, alternativas, invariantes, avaliação e itens adiados e concluiu `APPROVED` para o plano proposto, com quatro concerns, três sugestões e nenhum blocker. Recomendou manter API/catálogo/apresentadores e a avaliação sintética em três rodadas; não aprovou gates. A coordenação verificou completude, reconciliou fontes e preservação das fronteiras antes de aceitar o parecer:

| Achado | Resolução da coordenação / evidência |
|---|---|
| C1 — tool lógica versus páginas HTTP | Resolvido na tabela: duas tools lógicas e seis HTTP totais, incluindo páginas/reconsulta; reservas duráveis e deadline comum |
| C2 — reclaim poderia reiniciar tempo | Resolvido: primeiro claim persistido fixa deadline imutável; contadores por entrada/índice reservados antes de chamar |
| C3 — dedupe poderia consumir quota | Resolvido no aceite 356-A/B: dedupe antes da quota, reserva/inserção transacionais e rollback da reserva em conflito |
| C4 — limite backend condicional | Resolvido: mecanismo efetivo por ferramenta obrigatório; statement timeout não basta para CPU; ausência desabilita e impede certificação |
| S1 — G6 supostamente indefinido | Sugestão de remover rejeitada com fundamento: G6 está definido na política de classificação e gates do Harness; esta é a porta do executor, distinta de GATE-E |
| S2 — tokens de resultado/metadados | Incorporado explicitamente ao teto de entrada, incluindo histórico/referências |
| S3 — duplicar nomes e rotas no slice | Mantida referência precisa à arquitetura §4/§7 como fonte única; aceite exige igualdade literal dos seis nomes, três permissões e três rotas, sem catálogo concorrente |

As correções são precisões documentais conferidas pela coordenação após o parecer, não alegação de implementação ou de nova revisão do especialista. Nenhum risco material foi aceito silenciosamente. O proprietário fechou G5 em 2026-09-09; G4/B1 foram formalizados no primeiro slice documental.

### Revisão da correção de provedor — versão 1.1.0

O `ai_architect` participou por subagente delimitado `revisar_openrouter`, `READ_ONLY`, recebendo somente a descrição sanitizada da correção, sem arquivos, dados reais ou segredos. Parecer `APPROVED` para coerência documental; não verificou fontes externas nem execução. A coordenação conferiu a base pública no exemplo oficial de chat completions do OpenRouter e o comportamento do roteador gratuito. Os concerns sobre disponibilidade e compatibilidade estão cobertos pelos critérios desta emenda.

O especialista apontou um `BLOCKER` restrito à execução BYOK com modelo indefinido. Adjudicação da coordenação: **OPEN para habilitação BYOK**, resolúvel pela recuperação do ID da análise anterior e qualificação atual; **não bloqueia esta correção documental**. Isso não reabre a escolha de OpenRouter e não equivale a rejeição automática de aprovação. Não houve inferência, contratação, configuração de credencial ou mudança de código.

### Revisão da análise reconstruída — versão 1.2.0

O mesmo `ai_architect`, ainda em missão `READ_ONLY`, revisou o discovery reconstruído e a integração ao plano. Confirmou a interseção observada de 17 modelos gratuitos com tools e somente dois IDs exatos gratuitos presentes na lista ZDR, além da escolha do Ling Fin como candidato ainda sujeito à certificação. Apontou duas inconsistências, ambas corrigidas: o Nemotron sem ZDR foi retirado da certificação e do piloto; o runner de avaliação recebeu orçamento próprio de 40 chamadas/dia, com admissão conversacional desabilitada, exigindo de seis a onze janelas diárias para as 210 execuções. O parecer não aprova gates e não substitui a decisão do proprietário.

### Revisão da inclusão NVIDIA — versão 1.3.0

O `ai_architect` revisou em modo `READ_ONLY` os dois discoveries e o plano ampliado. Retornou `CHANGES_REQUESTED` por ausência de slice executável que isolasse a comparação NVIDIA e registrou concerns sobre configurações de reasoning, referência residual a Gemma e histórico da versão. A coordenação incorporou todos: criou o slice sintético NVIDIA sem acesso ao canal/APIs reais, congelou `enable_thinking=false` para a matriz completa, classificou Gemma como referência exploratória inelegível e acrescentou esta versão ao histórico. Na segunda leitura, o especialista retornou `APPROVED` para prontidão documental, sem blocker ou concern material remanescente nesse escopo. O aceite ZDR do OpenRouter continua incondicional para o piloto; resultado técnico NVIDIA não contorna termos ou privacidade. O parecer não aprova gates nem autoriza execução.

### Revisão da opção OmniRoute — versão 1.4.0

O `ai_architect` revisou em modo `READ_ONLY` o discovery e a emenda ao plano. Na primeira leitura retornou `CHANGES_REQUESTED`: proibir fallback não limitava retries ao mesmo upstream, o rollback restaurava apenas a URL e o texto precisava distinguir segredos cifrados de segredos em claro. A coordenação incorporou uma tentativa upstream por tentativa admitida, contador em falhas/reinício, rollback conjunto de URL/referência à credencial/modelo/privacidade, suspensão durante a troca e armazenamento somente cifrado das credenciais necessárias. Também tornou explícita a preservação de `provider.data_collection=deny` e `provider.zdr=true` na rota OpenRouter.

Na segunda leitura, o especialista retornou `APPROVED` para prontidão documental, sem pendência material nesse escopo. A síntese textual de tools continua bloqueador operacional: aprovação do plano autoriza somente a prova isolada, e o OmniRoute não entra no piloto até remover esse comportamento e passar todos os critérios eliminatórios. O parecer não aprova gates nem certifica o runtime.

### Validação desta entrega

`npm run docs:validate`: 394 verificações OK, 36 avisos preexistentes, zero erros. A consulta atual aos endpoints públicos confirmou 17 IDs gratuitos OpenRouter com `tools`, a interseção ZDR exata de dois IDs Ling e os endpoints gratuitos NVIDIA descritos no discovery. A inspeção somente leitura da release/branch do OmniRoute confirmou o gateway OpenAI-compatible, o registro NVIDIA/Nemotron e a síntese textual de tool calls que condiciona a avaliação. Os links locais do plano resolvem e `git diff --check` não apontou problema. As alterações preexistentes do working tree foram preservadas; nesta etapa foram acrescentados o plano e os discoveries dos provedores/gateway. Dependências documentais existentes foram usadas via `NODE_PATH=C:/emprestimo/node_modules`, sem instalação. Testes de produto não se aplicam à entrega documental e não foram executados.

### Execução da reconciliação documental — versão 1.4.1

Após a aprovação explícita “sim esta aprovado!”, o primeiro slice atualizou somente os seis documentos autorizados: arquitetura, este plano, PLAN-033, backlog do PLAN-033, DR-005 e HANDOFF. A reconciliação registra o catálogo B1 de seis ferramentas, três permissões, apresentação determinística, OpenRouter como rota proposta e as condições de NVIDIA/OmniRoute. GATE-E1b e GATE-E3 permanecem abertos; nenhum código, credencial, inferência, envio ou produção foi acionado.

A análise separada do `openai-oauth` concluiu que o projeto agrega valor como referência, mas é inelegível ao runtime nas condições observadas. Ela não altera a direção aprovada nem autoriza laboratório. A validação documental terminou com 394 verificações OK, 36 avisos preexistentes e zero erros; `git diff --check` passou. A revisão final `READ_ONLY` retornou `APPROVED` após corrigir o estado de G5, a relação entre IMP-359 e GATE-E1b e a delimitação de PreCadastro para o IMP-357. O parecer não certifica implementação nem produção.

## Porta de aprovação e handoff

O resultado entregue é um plano revisável, com primeiro slice documental delimitado. Aprovação G5 autoriza a execução dos slices dentro das dependências, parâmetros e limites aceitos; não autoriza commit, push, PR, merge, deploy, mensagens reais, exclusões externas ou acesso a segredos por auxiliares. Autorizações específicas anteriores só valem se reconstituídas no contexto aplicável, não por menção histórica no backlog.

Próxima retomada: usar `$execute` no slice de prontidão do IMP-359 e avançar somente onde os pré-requisitos estiverem demonstrados. Preservar os 1.217 arquivos da baseline exceto mudanças concretas do slice autorizado, especialmente trabalho anterior ainda sem commit. Se dado operacional obrigatório faltar, continuar preparação independente e solicitar apenas o dado necessário, sem reabrir aprovação de direção já recebida.

## Histórico de Versões

| Versão | Data | Descrição |
|---|---|---|
| 1.4.1 | 2026-09-09 | Registra G5 e a execução do primeiro slice documental, formaliza B1/G4 e mantém GATE-E1b/GATE-E3 abertos; incorpora como referência separada a análise negativa do openai-oauth para runtime. |
| 1.4.0 | 2026-09-09 | Inclui OmniRoute como gateway opcional isolado, condicionado à remoção da síntese textual de tools, perfil restrito e prova direta de transparência e segurança. |
| 1.3.0 | 2026-09-09 | Inclui NVIDIA direta e Nemotron 3 Super na comparação sintética isolada, preservando OpenRouter/ZDR como rota elegível proposta e separando budgets e termos por provedor. |
| 1.2.0 | 2026-09-09 | Incorpora discovery reconstruído: 17 modelos gratuitos com tools, shortlist com Ling 3.0 Flash Fin, requisito ZDR/data_collection, teto local de 20 entradas/dia e avaliação distribuída. |
| 1.1.0 | 2026-09-09 | Correção do proprietário: OpenRouter definido e uso de modelos gratuitos com tools. Distingue recuperação da análise nominal, elegibilidade atual e modelos de engenharia; mantém modelo fixo e ausência de fallback pago. |
| 1.0.0 | 2026-09-09 | Plano proposto do núcleo, com autorização de detalhamento, slices subordinados ao PLAN-033, parâmetros sintéticos, testes, riscos e aprovação de execução pendente. |
