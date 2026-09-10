# Plano — autenticação OpenAI/Codex antes da inferência

**Última revisão:** 2026-09-09  
**Status:** Aprovado; em execução  
**Slice atual:** Slice E — prova real assistida em verificação, sem inferência  
**Bloqueado por:** logout local real ao encerrar a avaliação do proprietário  
**Risco:** Alto  
**Impacto agentic:** PRESENT  
**Justificativa e gatilhos:** nova autenticação de provedor de IA, credencial, catálogo de modelos, limites de uso e futuro runtime agentic; parecer `ai_architect` será reconciliado antes da porta G5.  
**Autorização:** o proprietário pediu em 2026-09-09 implementar primeiro a autenticação OpenAI, testar na prática e deixar OpenRouter, NVIDIA e OmniRoute em espera; após receber arquitetura, limites, slices e checks, respondeu “ok vamos avançar com o plano!”. G5 está fechado para os Slices A–E. Não autoriza commit, push, deploy, produção, dados reais de clientes ou remoção de credenciais.  
**Plano/IMP/GATE-E do produto:** especialização preparatória do IMP-356; não renumera IMPs, não executa inferência e não fecha GATE-E1b/GATE-E3.

## Objetivo

Entregar uma tela administrativa que conecte uma conta ChatGPT ao Codex App
Server oficial por device code e mostre, sem expor tokens, o plano, os modelos
visíveis e as janelas de uso. Demonstrar o fluxo com a conta do proprietário
somente depois de toda a cadeia funcionar contra um fake local.

Ao final deste plano, nenhuma mensagem de cliente é enviada à OpenAI e nenhuma
ferramenta TiaNet é disponibilizada ao modelo.

## Contexto e achados do repositório

- O PLAN-033 prevê um processo `agent` separado, mas ele ainda não existe.
- A conexão de WhatsApp fornece o precedente de estados, portas, RBAC, BFF,
  tela, contrato OpenAPI e testes, sem justificar acoplamento ao provedor.
- A imagem Python atual não contém Codex CLI ou Node; a imagem específica do
  `agent` precisará fixar e verificar a distribuição oficial escolhida.
- O host de desenvolvimento possui `codex-cli 0.146.1` e gerou o schema estável
  com as operações necessárias.
- O App Server será filho local via `stdio`; WebSocket permanece fora.
- O desafio device code é credencial efêmera. Persisti-lo no replay genérico ou
  em auditoria viola a minimização definida na arquitetura.

## Escopo e não objetivos

Inclui adapter JSON-RPC, serviço privado mínimo, isolamento de volume/processo,
API administrativa TiaNet, duas permissões, BFF/tela, contrato e testes, prova
real assistida de login e coleta de metadados da conta.

Ficam fora: `thread/start`, `turn/start`, resposta LLM, tools, MCP,
`dynamicTools`, WhatsApp, dados de clientes, PII financeira, cálculo de
capacidade por inferência, fallback, OpenRouter, NVIDIA, OmniRoute, API key
OpenAI, deploy e produção.

## Invariantes arquiteturais

1. Tokens pertencem ao App Server e ficam apenas no volume dedicado do `agent`.
2. Frontend, API, banco, logs, auditoria e respostas nunca recebem tokens.
3. `userCode` e `loginId` são efêmeros e não são persistidos ou registrados.
4. Apenas administrador com `openai.conexao.gerir` inicia ou encerra login;
   leitura exige `openai.conexao.ler`.
5. O adapter não contém métodos de conversa, filesystem, shell ou tools.
6. Uma conta, um Tenant e um processo no v1; nenhuma sessão é compartilhada.
7. Modelo/provedor não muda automaticamente e nenhum fallback é configurado.
8. Estado desconhecido ou erro de protocolo falha fechado e não declara conta
   desconectada nem limite disponível.
9. Código e configuração do TiaNet não são montados no container do `agent`.
10. A prova real usa somente metadados da conta; inferência é uma porta futura.

## Opções e recomendação

A [arquitetura proposta](../../architecture/reviews/openai-codex-auth-pilot-2026-09-09.md)
compara API, frontend, serviço isolado e API key. O plano adota o serviço
`agent` privado como dono do App Server porque conserva a futura topologia do
IMP-356 e reduz o alcance da credencial.

## Arquitetura alvo

O navegador chama o BFF; o BFF chama a API TiaNet autenticada; a API aplica
RBAC e chama o serviço `agent` por HTTP sobre socket Unix com segredo próprio;
o serviço traduz DTOs fechados para JSON-RPC por `stdio`. O `agent` conserva
rede de egress exclusiva, sem rota TCP para API/PostgreSQL. O App Server persiste sua sessão
em volume exclusivo. O estado de conexão vem de `account/read`; catálogo e
limites são leituras separadas e podem falhar parcialmente sem transformar a
conta em desconectada.

## Limites aprováveis

- frame JSON-RPC: 1 MiB;
- timeout de startup e operação de conta: 15 segundos;
- concorrência: uma mutação e um diagnóstico por Tenant;
- validade local máxima do desafio: 10 minutos, seguida de cancelamento;
- polling do snapshot local: 3 segundos por no máximo 10 minutos;
- diagnóstico: uma atualização por Tenant a cada 60 segundos, com chamadas
  concorrentes compartilhando resultado;
- reconciliação: um reinício do filho, sem retry em loop.

## Slices de implementação

### Slice A — decisão, protocolo e fake

**Propósito:** fechar G4, reconciliar o plano vigente e provar o adapter sem
conta real.

**Arquivos prováveis:** ADR e AMP-001; PLAN-033, backlog, DR-005 e HANDOFF;
novos módulos em
`src/emprestimo/agent/`; fixtures/schema em `tests/fixtures/`; testes unitários
do protocolo.

**Dependências:** aprovação deste plano; schema estável da versão fixada.

**Aceite:** ADR aceita e registrada no AMP; os documentos do PLAN-033 declaram a
preparação administrativa local anterior ao IMP-356, preservam IMP-359/GATE-E e
registram os quatro endpoints públicos; tipos próprios para conta, modelo,
limite e desafio; framing request/response/notificação; allowlist de métodos;
timeout, limite de bytes, correlação e desligamento do filho; fake não contém
método de inferência.

**Testes/verificação:** inicialização, IDs concorrentes, resposta fora de ordem,
notificação de conclusão e conclusão tardia, cancelamento, JSON inválido, frame
acima de 1 MiB, EOF, timeout de 15 segundos, versão incompatível, campo extra e
tentativa de método proibido. `docs:validate`, `docs:test`, Harness, `ruff`,
`mypy` e testes unitários focais.

**Rollback:** remover módulos e fixtures; não há dado ou credencial.

### Slice B — serviço privado e isolamento

**Propósito:** executar o adapter em processo/container separado e deslogado.

**Arquivos prováveis:** entry point do `agent`, Dockerfile dedicado,
`docker-compose.yml`, `.env.example`, composição/configuração, healthcheck e
testes de infraestrutura.

**Dependências:** Slice A verde; distribuição oficial do Codex CLI fixada por
versão e hash/origem verificável.

**Aceite:** serviço sem porta publicada no host; usuário não root; volume
exclusivo; `CODEX_HOME` explícito; sem mounts de código, banco ou credenciais da
API; segredo interno obrigatório; feature flag desligada por padrão; health
separa processo disponível de conta conectada; schema gerado no build confere
com fixture governada.

**Testes/verificação:** build da imagem, inspeção de mounts/rede/usuário,
chamada sem segredo recusada, método não permitido recusado, restart preserva
somente o volume esperado e logs não contêm fixture sensível. De dentro do
container, provas negativas tentam alcançar API TiaNet, PostgreSQL, checkout,
`.git`, volumes da aplicação e `CODEX_HOME` de engenharia; qualquer alcance
indevido bloqueia o login real.

**Rollback:** parar/remover o serviço e a referência no Compose. Volume não é
apagado automaticamente.

### Slice C — API TiaNet, RBAC e contrato

**Propósito:** expor a conexão administrativa sem revelar internals.

**Arquivos prováveis:** application port/service, cliente HTTP interno,
`openai_routes.py`, schemas, dependencies, catálogo IAM, migration de
permissões, OpenAPI gerado e testes de API/migration.

**Dependências:** Slice B verde; ADR da exceção de idempotência e emenda do
transporte por socket Unix aceitas.

**Aceite:** GET conexão, GET diagnóstico, POST login e DELETE logout conforme
arquitetura; `401/403`
corretos; escopo do Tenant; respostas com chaves fechadas; leitura parcial
preserva estado da conta; desafio só no POST; auditoria sem segredo; duas
permissões concedidas aos perfis administrativos pela migration; API alcança o
socket sem tornar API/PostgreSQL alcançáveis pelo `agent`; sem listener TCP.

**Testes/verificação:** matriz 401/403/200/502/503, Tenant divergente, login
concorrente, repetição com desafio vigente/expirado, logout durante login,
conclusão tardia, resultado incerto, restart, logout já desconectado, zero
chamadas downstream no polling de conexão, no máximo um diagnóstico por janela,
diagnóstico iniciado antes do logout impedido de publicar estado/metadados,
redação de erro, migration upgrade/downgrade/upgrade e snapshot OpenAPI.

**Rollback:** desabilitar flag/rotas; downgrade da migration somente antes de
uso externo e após verificar atribuições. O volume permanece intacto.

### Slice D — BFF e tela administrativa

**Propósito:** permitir que o administrador conclua o device flow e entenda o
estado observado.

**Arquivos prováveis:** policy/BFF/actions/página/componentes OpenAI, navegação,
cliente OpenAPI gerado, testes unitários/componente/contrato/Playwright.

**Dependências:** Slice C verde.

**Aceite:** botão “Conectar conta OpenAI”; link restrito ao host oficial
permitido; código copiável e rotulado como temporário; polling limitado enquanto
aguarda e sem diagnóstico implícito; ação “Atualizar diagnóstico” respeita a
janela de 60 segundos; estados indisponível/desconectado/aguardando/conectado/
limite atingido/erro/resultado desconhecido; plano, modelos e janelas apresentados sem prometer número fixo; logout
explica que é local; teclado, leitor de tela e mobile cobertos.

**Testes/verificação:** BFF valida schema e URL, componente cobre todos os
estados, Playwright cobre login fake e logout, `api:check`, lint, typecheck e
build focais.

**Rollback:** ocultar destino e desligar flag; API permanece inacessível pela
interface e pode ser removida no rollback completo.

#### Extensão UX do Slice D — selo e painel de consumo (2026-09-10)

O proprietário aprovou mover a OpenAI de `Mais ferramentas` para um selo
operacional e, após observar a primeira versão, pediu que o selo apresentasse
limites e que `/app/openai` recebesse a hierarquia visual combinada. O contrato
de conexão passa a admitir `usageSummary`, resumo sanitizado e anulável do
último diagnóstico concluído, com horário observado e janelas de uso.

Invariantes: carregar o selo ou a página executa somente o snapshot flyweight
local; atualizar conta, modelos e limites continua dependendo da ação explícita
`Atualizar diagnóstico`; o resumo não contém credencial, e-mail, código de login
ou identificador remoto; login, logout e troca de estado de conta invalidam o
resumo; a interface apresenta percentual observado e reinício informado, sem
converter o limite em número de mensagens ou promessa de disponibilidade.

### Slice E — prova real assistida, sem inferência

**Propósito:** observar o fluxo oficial com a conta do proprietário.

**Arquivos prováveis:** evidência sanitizada em `docs/audits/evidence/`, revisão
da arquitetura/plano e runbook. Nenhum segredo ou screenshot com código entra.

**Dependências:** A–D verdes; autorização continua válida para o login
solicitado, mas a digitação da senha, MFA e confirmação ocorre somente pelo
proprietário no domínio oficial da OpenAI.

**Aceite:** estado passa a conectado; plano é observado; modelos são listados;
janelas retornam percentual/duração/reset quando disponíveis; restart recupera
a conta; logout local remove a sessão observada; busca automática confirma que
tokens, e-mail, user code e login ID não entraram nos artefatos/logs.

**Testes/verificação:** checklist manual com timestamps, versão e respostas
sanitizadas; smoke de GET/POST/DELETE; varredura de segredos; revisão
especializada e `$verify`.

**Rollback:** logout local, flag off e serviço parado. Exclusão do volume exige
ação explícita do proprietário e não integra o teste automático.

**Estado em 2026-09-10:** login, diagnóstico e recuperação após restart
aprovados; plano `prolite`, cinco modelos e janelas de uso foram observados sem
inferência. O ajuste de atualização automática da tela também foi aprovado. O
logout real e o retorno da flag para `off` ficam para o encerramento da
avaliação, conforme a [evidência sanitizada](../../audits/evidence/openai-codex-auth-slice-e-2026-09-10.md).

## Matriz de testes

| Risco | Evidência bloqueadora |
|---|---|
| Vazamento de sessão/código | testes de DTO/log/auditoria mais busca nos artefatos |
| Escape para capacidades Codex | API do adapter sem método genérico; chamadas desconhecidas recusadas |
| Confusão de estado | snapshot de conexão separado de conta, catálogo e limites; polling conta zero chamadas downstream |
| Login duplicado/tardio | lock por Tenant, geração, cancelamento, restart e resultado incerto cobertos pelo fake |
| Diagnóstico anterior ao logout | geração impede publicação do resultado e de metadados antigos |
| Processo instável | timeout, EOF, crash, restart e health degradado |
| Acesso indevido | 401, 403, segredo interno e escopo do Tenant |
| Isolamento incompleto | provas negativas de rede, mounts, checkout, banco e sessão de engenharia antes do login |
| Drift do protocolo | schema estável fixado e diff bloqueador na troca de CLI |
| UI enganosa | estados textuais, limite desconhecido explícito e logout local rotulado |
| Regressão documental | `docs:validate`, `docs:test`, Harness e `git diff --check` |

## Rollout e rollback

Cada slice termina em revisão antes do próximo. A flag fica desligada até a
prova real e volta a desligada ao final. Não há deploy neste plano sem
autorização separada. A rota OpenAI não recebe tráfego de cliente.

O rollback operacional preserva o volume para permitir logout ou investigação.
Excluir credenciais locais ou tentar revogação remota são ações separadas. Os
demais provedores continuam em espera e não são acionados como contingência.

## Riscos

| Risco | Tratamento |
|---|---|
| App Server ainda é marcado experimental | versão fixada, schema sem experimental, prova antes de qualquer inferência |
| Conta pessoal não satisfaz política de PII | prova sem dados TiaNet; dados reais bloqueados pela DR-005 |
| Limite Free não tem número público fixo | mostrar leitura real, sem converter ausência em zero |
| CLI amplia superfície no futuro | adapter fechado e diff de schema a cada atualização |
| Distribuição oficial não encaixa na imagem atual | imagem `agent` separada; falha no Slice B reabre empacotamento |
| Logout não revoga remotamente | texto e evidência distinguem logout local de revogação |
| Serviço privado vira API pública por configuração | teste de Compose e ausência de `ports` publicados |

## Registro de decisões

- 2026-09-09: proprietário priorizou OpenAI auth e colocou OpenRouter, NVIDIA e
  OmniRoute em espera.
- App Server oficial substitui o proxy comunitário apenas neste experimento.
- Serviço isolado foi escolhido sobre execução dentro da API/frontend.
- Device code foi escolhido para a topologia VPS/navegador remoto.
- Inferência foi separada da autenticação; a prova deste plano não consome um
  turno deliberado de modelo.

## Registro de revisão

Triagem `PRESENT`. O `ai_architect` revisou arquitetura e plano em missão
`READ_ONLY`, sem dados ou segredos, e retornou `CHANGES_REQUESTED` com três
blockers: polling acionava diagnóstico externo, o recorte antecipava IMP-356 sem
reconciliar dependências e o ciclo não fechava logout concorrente com login.

Todos foram incorporados: GET de conexão passou a snapshot sem downstream e o
diagnóstico ganhou rota/limite próprios; Slice A agora reconcilia PLAN-033,
backlog, DR-005 e HANDOFF sem fechar IMP/gates; `account/login/cancel`, lock por
Tenant, geração, restart do filho e reconciliação impedem conclusão tardia
silenciosa. O concern sobre números foi resolvido na seção de limites. A segunda
leitura retornou `APPROVED` para prontidão documental, com dois concerns de
implementação agora convertidos em aceite: geração também protege diagnóstico
concorrente com logout e isolamento negativo é demonstrado antes do login real.
Parecer não fecha gate nem autoriza implementação.

## Progresso

| Slice | Estado | Evidência |
|---|---|---|
| A | concluído | adapter fechado, protocolo tipado, 26 testes focais no conjunto `tests/unit/agent` e revisão `READ_ONLY` aprovada |
| B | concluído | imagem fixada, schema canônico, isolamento e degradação por morte do filho comprovados; [evidência sanitizada](../../audits/evidence/openai-codex-auth-slices-a-b-2026-09-09.md); revisão `READ_ONLY` aprovada |
| C | concluído | API/RBAC, migration, socket Unix e egress fechado comprovados; [evidência sanitizada](../../audits/evidence/openai-codex-auth-slice-c-2026-09-09.md); revisão READ_ONLY aprovada |
| D | concluído | BFF/tela, contrato 115/145, polling sem diagnóstico, fake desktop/mobile e a11y comprovados; [evidência sanitizada](../../audits/evidence/openai-codex-auth-slice-d-2026-09-09.md); revisão READ_ONLY aprovada |
| E | pronto para prova assistida | depende da ação do proprietário no login oficial; sem inferência |

## Notas de execução

- As Slices A e B terminaram sem login real, inferência, tools ou dados de
  clientes.
- A flag do serviço permaneceu desligada ao fim da prova e o volume dedicado
  não foi removido.
- O desenho da Slice C usará um canal local dedicado para que a API alcance o
  serviço sem colocar o `agent` na rede da API ou do PostgreSQL.

## Follow-ups

Depois da prova de autenticação, o proprietário decide entre: encerrar o
experimento; executar uma prova sintética de uma inferência OpenAI; ou retomar a
comparação OpenRouter/NVIDIA/OmniRoute. Nenhuma opção é automática.

## Porta de aprovação

G5 foi fechado pelo proprietário em 2026-09-09. A aprovação autoriza os Slices A–E neste checkout, com
fake e login real assistido limitado aos metadados da própria conta. Não
autoriza commit, push, PR, deploy, produção, inferência, tools, dados reais de
clientes, remoção do volume ou retomada dos demais provedores.
