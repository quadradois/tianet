# Plano — IMP-370 aviso de queda do WhatsApp

**Última revisão:** 2026-09-08
**Status:** Concluído e verificado no working tree
**Slice atual:** Concluído
**Bloqueado por:** Nenhum
**Risco:** Médio
**Impacto agentic:** NONE
**Justificativa e gatilhos:** triagem STANDARD, impacto NONE; sem gatilhos para parecer especializado
**Autorização:** desenho autorizado conforme `docs/governance/agents/DESCOBERTA-IMP-370-AVISO-QUEDA.md`; plano e execução por slices aprovados explicitamente pelo proprietário nesta sessão em 2026-09-08, mantendo sem segundo canal, sem dispensa manual e limpeza automática na reconexão
**Plano/IMP/GATE-E do produto:** IMP-370; G5 fechado em 2026-09-08; GATE-E do produto permanece aberto

## Objetivo

Transformar a transição de pareada para não pareada já detectada por `SincronizarConexoesWhatsApp.executar()` em um aviso persistente e visível à operadora dentro do TiaNet, sem depender do próprio WhatsApp que caiu, sem segundo canal externo e sem dispensa manual nesta etapa.

## Contexto e achados do repositório

Fatos consolidados em `docs/governance/agents/DESCOBERTA-IMP-370-AVISO-QUEDA.md` (2026-09-08, descoberta concluída e desenho aprovado pelo proprietário):

- `SincronizarConexoesWhatsApp.executar()` devolve lista de quedas; a transição é criada somente quando `estava_pareada` passa para estado não pareado (`src/emprestimo/application/conexao_whatsapp.py`).
- `_VarreduraPeriodica.talvez_varrer()` preserva o retorno, porém `antes_do_ciclo()` o descarta (`src/emprestimo/worker/scheduler_worker.py`).
- Sincronização com intervalo padrão de 300 segundos; detecção pode atrasar até cerca de cinco minutos quando worker e provedor estão disponíveis.
- Contexto operacional lê o último estado persistido; `frontend/src/components/shell/whatsapp-badge.tsx` já exibe o selo conectado/não conectado.
- Não existe service worker, assinatura Web Push, VAPID ou uso da Notification API no frontend atual.
- Adaptador Resend existe, mas e-mail está fora do MVP e não há conta contratada (conforme `docs/operations/contexto-externo.md`).
- Enviar o aviso pelo mesmo canal WhatsApp não atende ao requisito quando a conexão está indisponível.
- Auditoria já registra pareamento/desparelhamento como histórico append-only; ela não representa estado ativo consumível pela UI.

Baseline conhecido: branch `feat/imp-370-worker-le-o-token` em `b737c20`; alterações do Harness e documentos são preexistentes.

## Escopo e não objetivos

Escopo: persistir estado de queda na conexão, consumir as quedas no worker de forma idempotente com limpeza na recuperação, expor no contexto operacional e exibir banner acessível na shell, com testes da matriz abaixo.

Não objetivos:

- Não implementar código, migration ou testes neste documento (somente planejar).
- Não editar backlog, handoff, checklist ou outros documentos.
- Não propor canal externo, push, e-mail/SMS/segundo canal, nem dispensa manual nesta etapa.
- Não prometer notificação com navegador fechado / TiaNet fechado.

## Invariantes arquiteturais

- Preservar SPEC-004, ALP-001 e PLAN-034.
- Auditoria permanece histórico append-only; estado ativo da queda vive na conexão, não em tabela histórica paralela neste slice.
- A transição observada pelo provedor registra a queda dentro da sincronização, antes do commit e ainda sob o advisory lock do tenant.
- A desconexão solicitada pela operadora não é queda e não cria alerta ativo.
- Sem segredos, sem rede externa, sem contratação de serviço.

## Opções e recomendação

| Opção | Avaliação (conforme descoberta) |
|---|---|
| Alerta persistente dentro do TiaNet | Recomendada. Reaproveita detecção, persistência e shell atuais; funciona quando a operadora voltar ou permanecer no sistema, sem contratação externa; menor solução coerente. |
| Push do navegador | Não adotada nesta etapa. Exige service worker, assinatura, chaves, permissão e operação ausentes; Notification API sem Web Push não resolve aba fechada. Evolução futura se houver necessidade comprovada. |
| E-mail, SMS ou segundo canal | Não adotado nesta etapa. Exige serviço, credencial, custódia e decisão comercial inexistentes; reavaliar apenas após contratação explícita. |

Recomendação aprovada para planejamento: estado nullable de queda na conexão + persistência idempotente no worker + contexto operacional + banner acessível, com limpeza automática na reconexão.

## Arquitetura alvo

- **Estado nullable na conexão:** adicionar `queda_detectada_em`; `None` significa que não há alerta ativo. O número anterior já existe no sinal `QuedaDeConexao` e não ganha nova persistência sem uso operacional aprovado.
- **Persistência idempotente na sincronização:** quando uma leitura do provedor observa a borda pareada → não pareada, a sincronização grava `queda_detectada_em` antes do commit e ainda sob o advisory lock. O worker dispara essa leitura periodicamente; a consulta da tela pode detectar antes. Permanência desconectada preserva o primeiro instante, falha do provedor não inventa queda e desconexão manual não cria alerta.
- **Limpeza automática na reconexão:** um novo pareamento confirmado limpa `queda_detectada_em` dentro da mesma sincronização; sem dispensa manual inicial.
- **Contexto operacional:** expõe `alerta_queda_ativa` (booleano derivado do estado nullable) e `queda_detectada_em`.
- **Banner acessível:** a shell mantém o selo existente e, enquanto a queda estiver ativa, exibe banner destacado com link para a tela de conexão; banner some automaticamente após recuperação confirmada.
- **Auditoria:** preserva o histórico; nenhuma tabela histórica paralela no primeiro slice.
- **Limite explícito:** não promete aviso com navegador fechado.

## Slices de implementação

### Slice 1 — Persistência do estado de queda

- **Propósito:** criar o estado ativo nullable da queda na conexão, base para sincronização e UI.
- **Arquivos prováveis:** nova migration em `migrations/versions/`; `src/emprestimo/domain/platform/conexao_whatsapp.py`; `src/emprestimo/infrastructure/db/orm.py`; `src/emprestimo/infrastructure/repositories/__init__.py`; testes de domínio, repositório e migration relacionados.
- **Justificativa:** sem estado ativo consumível, o contexto operacional e a UI continuam sem fonte; auditoria append-only não serve como estado.
- **Dependências:** nenhuma além da aprovação deste plano; precede Slices 2 e 3.
- **Critérios de aceite:** migration aditiva aplica e reverte em ambiente de teste; estado ausente equivale a sem alerta; `queda_detectada_em` nasce nulo e mantém timezone; mapeamento de ida e volta preserva o valor.
- **Testes:** teste de migration (aplica/rollback); teste de entidade/repositório (cria, lê, limpa estado nullable).
- **Verificação:** revisão do diff da migration e do mapeamento entidade/coluna; `diff --check`.
- **Risco de rollback:** baixo; reverter migration aditiva nullable não destrói dados existentes.

### Slice 2 — Sincronização registra a queda com idempotência e limpeza

- **Propósito:** persistir e limpar o alerta dentro da transação que observa o estado real do provedor.
- **Arquivos prováveis:** `src/emprestimo/domain/platform/conexao_whatsapp.py`; `src/emprestimo/application/conexao_whatsapp.py`; `tests/unit/application/test_varredura_conexao_whatsapp.py`; testes diretamente ligados a `ConsultarConexaoWhatsApp` e `DesconectarWhatsApp`. `src/emprestimo/worker/scheduler_worker.py` só muda se o retorno continuar necessário para observabilidade; a persistência não ocorre em `antes_do_ciclo()`.
- **Justificativa:** consumir `QuedaDeConexao` no worker depois de `executar()` abriria outra transação quando o advisory lock já foi solto. Registrar na sincronização mantém detecção e estado ativo atômicos.
- **Dependências:** Slice 1; regra de transição existente inalterada.
- **Critérios de aceite:** uma transição observada cria um alerta ainda sob lock; permanência desconectada preserva o primeiro instante; recuperação confirmada limpa; consulta da tela pode detectar a queda; desconexão manual não cria alerta; falha do provedor não inventa queda; isolamento por tenant preservado.
- **Testes:** testes de aplicação para os sete comportamentos do aceite, incluindo prova da ordem `lock → leitura → persistência → commit`.
- **Verificação:** testes da varredura e dos casos de uso de consulta/desconexão; inspeção da fronteira transacional; `diff --check`.
- **Risco de rollback:** baixo; reverter restaura o descarte atual sem perda de histórico de auditoria.

### Slice 3 — Contexto operacional e banner acessível

- **Propósito:** expor `alerta_queda_ativa` e `queda_detectada_em` e exibir/remover o banner conforme o estado.
- **Arquivos prováveis:** `src/emprestimo/application/autorizacao.py`; `src/emprestimo/presentation/api/schemas.py`; `src/emprestimo/presentation/api/iam_routes.py`; contrato OpenAPI e cliente gerado; `frontend/src/lib/bff/context.server.ts`; `frontend/src/components/shell/app-shell.tsx`; novo componente de alerta na shell; testes de contexto, contrato, componente e jornada da shell. O selo existente só muda se necessário para evitar mensagem conflitante.
- **Justificativa:** torna a queda visível à operadora que voltar ou permanecer no sistema, sem canal externo.
- **Dependências:** Slices 1 e 2; não inicia sem estado ativo e worker definidos.
- **Critérios de aceite:** com queda ativa, banner destacado visível com link para conexão; sem queda, apenas selo normal; recuperação remove o banner automaticamente; sem dispensa manual; banner acessível (papel de alerta, contraste, navegação por teclado).
- **Testes:** testes de contexto operacional (deriva `alerta_queda_ativa` do estado nullable); testes de UI (exibe com queda, remove após limpeza).
- **Verificação:** inspeção visual/teclado do banner; conferência de `alerta_queda_ativa` contra o estado persistido; `diff --check`.
- **Risco de rollback:** baixo; reverter remove o banner e mantém o selo pré-existente.

### Slice 4 — Endurecimento e matriz de aceitação

- **Propósito:** demonstrar de ponta a ponta os comportamentos contratados antes de pedir GATE-E.
- **Arquivos prováveis:** nenhum arquivo de produção novo; apenas testes e evidências.
- **Justificativa:** consolida a garantia sem ampliar escopo.
- **Dependências:** Slices 1–3.
- **Critérios de aceite:** todos os casos da matriz abaixo verdes.
- **Testes:** execução da matriz completa (inclui migration e UI).
- **Verificação:** relatório de testes; `docs:validate`; `diff --check`; conferência de referências e escopo dos slices.
- **Risco de rollback:** nenhum (sem mudança de produção).

## Matriz de testes

| Caso | O que demonstra | Tipo |
|---|---|---|
| Queda única | transição pareada → não pareada cria exatamente um alerta | aplicação/worker |
| Permanência desconectada | ciclos subsequentes desconectados preservam o primeiro instante e não duplicam o alerta | aplicação/worker |
| Recuperação | novo pareamento confirmado limpa o alerta automaticamente | aplicação/worker |
| Consulta detecta primeiro | leitura real feita pela tela registra a transição antes do próximo ciclo do worker | aplicação |
| Desconexão manual | ação explícita da operadora não cria falso alerta de queda | aplicação |
| Falha do provedor | erro/indisponibilidade do provedor não inventa queda | aplicação/worker |
| Isolamento de tenant | queda de um tenant não afeta o estado de outro | aplicação/worker |
| Migration | migration aditiva aplica e reverte; nulos por padrão | migration |
| UI exibe | com `alerta_queda_ativa`, banner com link aparece além do selo | frontend |
| UI remove | após limpeza, banner some e selo volta ao normal | frontend |

## Rollout e rollback

- Rollout por slices 1 → 2 → 3 → 4, sem flag externa; cada slice só avança com aceite verificado.
- Rollback por slice (migrations aditivas nullable, reversão do consumo no worker, remoção do banner); auditoria append-only preservada em qualquer rollback.

## Riscos

- Detecção atrasar até ~5 minutos pelo intervalo de 300 s — aceito no MVP; reduzir intervalo é decisão posterior.
- Sem aviso com navegador/TiaNet fechado — limite declarado; Web Push ou canal externo exigem plano próprio.
- Tentação de dispensa manual ou tabela histórica paralela — fora deste plano; forçam redesign (ver abaixo).

## Registro de decisões

- Alerta persistente dentro do TiaNet como menor solução coerente (descoberta 2026-09-08).
- Sem segundo canal, sem push, sem dispensa manual nesta etapa.
- Limpeza automática na reconexão confirmada.

## Registro de revisão

- Descoberta reconciliada pelo coordenador; entrega bruta da descoberta recebeu `CORREÇÃO / SCOPE_VIOLATION` por leitura fora de `allowedPaths` e comando não autorizado (sem segredos lidos); duas tentativas anteriores foram interrompidas por sobrecarga 502.
- O OpenCode materializou a primeira versão deste plano a partir da descoberta e do template. A revisão do coordenador corrigiu a fronteira transacional: o alerta passa a ser gravado pela sincronização antes do commit, porque consumir a lista no worker ocorreria depois da liberação do advisory lock.

## Progresso

- Descoberta e plano aprovados em 2026-09-08.
- Slice 1 concluído e aprovado em 2026-09-08: `queda_detectada_em` persistido por migration aditiva, entidade, ORM e repositório; head Alembic `c1d2e3f4a5b6`.
- Evidências do Slice 1: ciclo real `upgrade head → downgrade base → upgrade head` em Postgres descartável; 29 testes focais; suíte unitária completa; Ruff, Black, mypy, `docs:validate` e `git diff --check` aprovados.
- Delegação do Slice 1: tarefa OpenCode `e9792162-ccae-4584-b201-7c31b65f08a7`. A tentativa 1 recebeu correção por comandos Docker fora do envelope e por um teste que congelava comportamento contrário ao Slice 2; a tentativa 2 corrigiu o escopo e foi aprovada pelo coordenador.
- Slice 2 iniciado após G7–G9 do Slice 1, sem redesign ou ampliação material.
- Slice 2 concluído e aprovado em 2026-09-08: a sincronização persiste a borda pareada → não pareada antes do commit e sob o lock; permanência não duplica, reconexão limpa e desconexão manual não cria alerta.
- Evidências do Slice 2: 83 testes focais; suíte unitária completa; 34 integrações de conexão/API/repositório; Ruff, Black, mypy, `docs:validate` e `git diff --check` aprovados.
- Delegação do Slice 2: tarefa OpenCode `de7d3827-1d0e-44cf-a149-20eeac0c07f1`, tentativa 1 aprovada após o coordenador executar os testes que o agente deixou bloqueados por ausência de Postgres.
- Slice 3 iniciado após G7–G9 do Slice 2, sem redesign ou ampliação material.
- Slice 3 concluído e aprovado em 2026-09-08: o contexto operacional expõe `alerta_queda_ativa` e `queda_detectada_em`; o BFF valida consistência e RFC 3339; a shell autenticada exibe banner global persistente, sem dispensa, com link para reconexão e horário em `America/Sao_Paulo`.
- Evidências do Slice 3: 61 testes backend focais; OpenAPI regenerado de forma determinística; `api:check`, typecheck e lint; 137 testes BFF, 82 de componentes e 42 de contrato; 22 testes Playwright de sessão e 4 de acessibilidade em desktop e mobile; Ruff, Black, mypy e `git diff --check` aprovados nos escopos aplicáveis.
- Delegação do Slice 3: backend/contrato na tarefa OpenCode `036e55ef-eceb-4c35-9d8f-bcac92052349`; sincronização do hash e cliente na tarefa `282c1e34-ddd0-4985-b16f-293a4b01a7ae`; BFF/UI/testes na tarefa `adae055a-dcad-4471-858f-b4c7dbf5a178`. A tarefa intermediária `281c6393-0d94-4092-85cd-a0973964efac` não alterou arquivos: a primeira tentativa sofreu limite do provedor e a segunda revelou que o gerador estava fora do escopo; o trabalho foi reduzido em subtarefas auditáveis. A primeira revisão da UI recebeu correção porque `Date.parse` aceitava datas calendariamente impossíveis e o fuso dependia da VPS; a tentativa 2 corrigiu ambos e foi aprovada.
- Slice 4 iniciado após G7–G9 do Slice 3, sem novo escopo de produção.
- Slice 4 concluído em 2026-09-08: a matriz completa foi reconciliada e está em [VERIFICACAO-IMP-370-AVISO-QUEDA.md](VERIFICACAO-IMP-370-AVISO-QUEDA.md). Backend, migration real, frontend, build, navegador, acessibilidade, documentação e Harness passaram; a auditoria OpenCode `df28a52f-b84e-4aa8-bcf4-012c3fb9fd19` permaneceu somente leitura e não encontrou blocker.

## Notas de conclusão

- Os quatro slices foram implementados, revisados e verificados no working tree em 2026-09-08.
- G10 está fechado pela matriz de evidências; G11 está fechado pelo plano, verificação e handoff reconciliados.
- A entrega está pronta para revisão humana e preparação de commit/release. Não houve commit, push, merge ou deploy; o GATE-E do produto permanece aberto.

## Follow-ups

- Eventual Web Push ou canal externo independente, somente como decisão e plano próprios após contratação/necessidade comprovada.
- Eventual ciência manual com responsável ou retenção operacional independente da auditoria, somente via redesign.

## O que força redesign

Forçam redesign (não inferir neste plano): exigir aviso com o TiaNet fechado / navegador fechado; exigir retenção operacional independente da auditoria; exigir ciência/dispensa manual com responsável; exigir canal externo (e-mail, SMS, push, segundo WhatsApp). Essas escolhas criam novas responsabilidades e viram decisão e plano próprios.

## Porta de aprovação

- Status atual: **execução e verificação concluídas no working tree**. G5, G10 e G11 fechados; GATE-E do produto permanece aberto.
- Próxima porta: revisão humana e autorização específica para commit/PR/release antes de qualquer publicação.
