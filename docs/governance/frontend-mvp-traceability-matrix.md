# Frontend MVP - Matriz Oficial de Rastreabilidade Product, API, RBAC e E2E

**Versao:** 3.9.0

**Data:** 2026-08-22

**Status:** Frontend MVP concluido localmente; IMP-274..IMP-304 recertificados; superficie do Motor reduzida pela DR-004 (plano de parcelas removido)

---

# 1. Autoridade e finalidade

Esta matriz e o elo oficial entre jornadas do Frontend MVP, governanca Product,
contratos OpenAPI do backend certificado, permissoes RBAC e cenarios de teste
Playwright. Ela e um artefato transversal de entrega: nao e Capability, Bounded
Context, EPIC, Feature ou User Story.

A fonte contratual observada e o OpenAPI gerado por `create_app().openapi()` na
worktree derivada do commit backend `e48cb72`, congelado no snapshot governado
do PLAN-025. O contrato vigente possui 111 operacoes e 137 schemas; o SHA-256
do snapshot e
`95c45df44bf638233fe9d38d44398867d09d7f7b0a8a8fdc0e48c5c99597cb82`,
atualizado pelo IMP-368, que acrescentou as quatro operacoes de
`/platform/whatsapp/conexao`. A contagem anterior registrada aqui (105/131)
estava desatualizada desde antes do IMP-362 — o hash acompanhava o contrato, os
numeros nao. Anterior ao IMP-368 era o IMP-336, que retirou o campo obrigatorio
`parcelas_liquidadas`
de `PagamentoResponse` — **mudanca nao aditiva**, ultimo residuo do plano de
parcelas no contrato publico, amparada pela DR-004.

**Estado vigente, apos o IMP-351 (2026-08-26):** 105 operacoes e 131 schemas.
Sairam `POST /platform/tenants` e `POST /auth/ativar`, mais os schemas
`TenantCreateRequest`, `TenantProvisioningResponse` e `AtivacaoRequest` — o
provisionamento por API e o fluxo de ativacao deixaram de existir porque o
Administrador da Plataforma e o unico Tenant e nasce pela CLI. As operacoes que
publicam `Idempotency-Key` obrigatoria passaram de 63 para **62**, e as escritas
sem o header cairam de quatro para **tres**: login, refresh e logout.

Antes disso, a superficie esteve em 107 operacoes e 134 schemas: o IMP-336 nao
mexeu na contagem porque nenhum schema nasceu ou morreu, apenas um campo
obrigatorio deixou de existir; e o IMP-333 manteve a mesma superficie e elevou as
operacoes com `Idempotency-Key` de 32 para 63. A mudanca anterior, aditiva, do IMP-332 entrou
`POST /credit/pagamentos/{pagamento_id}/estornos`, com `Idempotency-Key`
obrigatoria; `PagamentoResponse` passou
a publicar `valor_devolvido`, `valor_estornado`, `valor_sobra` e `reconciliado`;
e o schema `EstornoPagamentoRequest` foi acrescentado. A mudanca anterior do
IMP-330, que tornou `NotificacaoResponse.lembrete_id` opcional para notificacoes
transacionais, permanece incorporada.
A linha de base do PLAN-025 tinha 107 operacoes e SHA-256
`8dadf18eab0dad186044d71e832f72a5850661307d196187f2d0794b9d1d9ec1`; as duas
operacoes de plano de parcelas sairam do contrato pela DR-004 e a operacao
`POST /credit/carteiras/{carteira_id}/lancamentos` entrou pelo IMP-306.
O backend de login usa `AuthLoginRequest`; o formulario publico do frontend
envia somente e-mail e senha ao BFF, que deriva `identificador_institucional`
server-only. Refresh/logout usam `AuthRefreshRequest`, as 62 operacoes
idempotentes publicam o header obrigatório e 400/422 usam `ErroResponse`
conforme a semantica runtime.

Regras de leitura:

- toda operacao protegida exige BearerAuth; a coluna RBAC acrescenta a
  Permissao efetiva exigida;
- `proprio Principal` significa autenticacao sem Permissao administrativa
  adicional e nunca significa acesso anonimo;
- recurso fora do Tenant ou da Carteira autorizados responde `404` neutro;
- `400`, `401`, `403`, `404`, `409`, `422` e `5xx` fazem parte dos cenarios
  negativos de cada jornada aplicavel;
- o frontend apresenta respostas e envia comandos; nenhum item desta matriz
  autoriza calculo financeiro fora do Motor.

---

# 2. Decisao de reutilizacao Product

| Familia | Decisao | Justificativa |
|---|---|---|
| PRODUCT-001..PRODUCT-009 | reutilizar sem novo ID e sem criar Capability Frontend | as nove Capabilities ja expressam os resultados de negocio consumidos pela interface |
| EPIC-001..EPIC-010 | reutilizar sem novo ID e sem EPIC tecnico de telas | os EPICs existentes cobrem Plataforma, IAM e todas as jornadas de credito/operacao |
| FEATURE-001..FEATURE-045 | reutilizar; versionar somente FEATURE-011 e FEATURE-012 para 1.1.0 | apenas IAM precisava incorporar deltas funcionais comprovados |
| US-001..US-124 | reutilizar sem reescrita | as historias existentes continuam autoridade dos resultados ja certificados |
| US-125 | emitir sob FEATURE-012 | faltava consulta do contexto operacional do proprio Principal com Carteira padrao e Permissoes |
| US-126 | emitir sob FEATURE-011 | faltava consulta governada do catalogo canonico de Permissoes |
| nova Feature, novo EPIC ou nova Capability | nao emitir | auth tipado, idempotencia e matriz 400/422 sao correcao de contrato, nao valor Product novo |

Assim, a hierarquia permanece `Capability -> Bounded Context -> EPIC -> Feature
-> User Story`; "Frontend MVP" identifica o canal de entrega transversal, nao
um nivel novo dessa hierarquia.

---

# 3. Matriz de superficies

O total da coluna `Ops` das superficies certificadas e 106 — uma a menos que o
contrato, porque `POST /credit/carteiras/{carteira_id}/lancamentos` ainda nao
tem jornada frontend propria (o lancamento e composicao das operacoes ja
certificadas).

| Jornada frontend | Product | EPIC | Feature | User Stories | Endpoint OpenAPI | Ops | Permissao RBAC | Cenario Playwright observavel |
|---|---|---|---|---|---|---:|---|---|
| ativacao, login, refresh e logout | PRODUCT-001 | EPIC-006 | FEATURE-009, FEATURE-010 | US-028..US-032 | `POST /auth/ativar`; `POST /auth/login`; `POST /auth/refresh`; `POST /auth/logout` | 4 | publico por token/credencial ou refresh token; sem RBAC | ativar administrador, autenticar, renovar, encerrar e provar que sessao encerrada nao renova; as quatro escritas sao excecoes nominais ao header de idempotencia por consumirem/rotacionarem credenciais ou sessao, sem resultado de negocio reutilizavel |
| bootstrap do shell autenticado | PRODUCT-001 | EPIC-006 | FEATURE-012 v1.1 | US-039..US-041, US-125 | `GET /iam/contexto-atual` | 1 | proprio Principal | carregar Usuario/Tenant/Carteira/Perfil/Permissoes; 401 sem sessao; 409 se provisionamento estiver incompleto |
| administracao de Tenants | PRODUCT-001 | EPIC-001 | FEATURE-001..FEATURE-004 | US-001..US-014 | `POST, GET /platform/tenants`; `GET, PATCH /platform/tenants/{tenant_id}`; `POST /platform/tenants/{tenant_id}/inativar`; `POST /platform/tenants/{tenant_id}/reativar` | 6 | `tenant.criar`, `tenant.ler`, `tenant.atualizar`, `tenant.inativar`, `tenant.reativar` | provisionar Tenant com Carteira padrao e administrador; consultar, alterar e transicionar com 403/404/409; as quatro escritas exigem `Idempotency-Key` |
| credencial propria e redefinicao administrativa | PRODUCT-001 | EPIC-006 | FEATURE-010 | US-032..US-034 | `PATCH /iam/credencial`; `POST /iam/usuarios/{usuario_id}/credencial/redefinir` | 2 | proprio Principal; `credencial.redefinir` | alterar a propria credencial e redefinir credencial conhecida com isolamento e auditoria; ambas exigem `Idempotency-Key` |
| Perfis, associacoes e Permissoes efetivas | PRODUCT-001 | EPIC-006 | FEATURE-011 | US-035..US-038 | `POST, GET /iam/perfis`; `GET, PATCH /iam/perfis/{perfil_id}`; `POST /iam/perfis/{perfil_id}/inativar`; `PUT, DELETE /iam/perfis/{perfil_id}/permissoes/{codigo}`; `PUT /iam/usuarios/{usuario_id}/perfil/{perfil_id}`; `DELETE /iam/usuarios/{usuario_id}/perfil`; `GET /iam/usuarios/{usuario_id}/permissoes` | 10 | `perfil.ler`, `perfil.gerir` | IMP-299 observado: criar Perfil, associar codigo valido, atribuir a Usuario conhecido e verificar permissoes em `/app/iam`; 404 cross-tenant neutro |
| catalogo IAM | PRODUCT-001 | EPIC-006 | FEATURE-011 v1.1 | US-126 | `GET /iam/permissoes` | 1 | `perfil.ler` | IMP-299 observado: listar catalogo versionado, impedir navegacao sem permissao e rejeitar codigo inexistente sem lista paralela |
| saude operacional | PRODUCT-001 | EPIC-008 | FEATURE-033 | US-091, US-092 | `GET /health` | 1 | publico | smoke de saude sem segredo, token, PII ou dado financeiro |
| cadastro de Devedores | PRODUCT-002 | EPIC-002 | FEATURE-005..FEATURE-008 | US-015..US-027 | `POST, GET /credit/carteiras/{carteira_id}/devedores`; `GET, PATCH /credit/carteiras/{carteira_id}/devedores/{devedor_id}`; `GET .../{devedor_id}/historico`; `POST .../{devedor_id}/inativar`; `POST .../{devedor_id}/reativar` | 7 | `devedor.criar`, `devedor.ler`, `devedor.atualizar`, `devedor.inativar`, `devedor.reativar` | listar/cadastrar/editar/inativar/reativar e consultar historico; teclado/mobile; 400/409/422; 404 cross-carteira |
| simulacao e Proposta Comercial | PRODUCT-003 | EPIC-003 | FEATURE-013..FEATURE-017 | US-043..US-052 | `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/simulacoes-comerciais`; `GET /credit/simulacoes-comerciais/{simulacao_id}`; `POST, GET .../{devedor_id}/propostas-comerciais`; `GET, PATCH /credit/propostas-comerciais/{proposta_id}`; `POST .../{proposta_id}/enviar-para-analise`; `POST .../{proposta_id}/aprovar`; `POST .../{proposta_id}/recusar`; `POST .../{proposta_id}/cancelar`; `POST .../{proposta_id}/expirar`; `GET .../{proposta_id}/contrato-logico` | 12 | `comercial.simulacao.criar`, `comercial.proposta.criar`, `comercial.proposta.ler`, `comercial.proposta.decidir`, `comercial.proposta.integrar` | IMP-292 observado: partir de Devedor ativo, simular, criar, enviar e decidir Proposta; exibir somente valores retornados; transicao invalida 409/422. IMP-333 certificou `Idempotency-Key` nas oito escritas. IMP-304 acrescentou cenario de stack real que submete o formulario com o vocabulario canonico do Motor; ate a DR-002 o cenario existia apenas contra stub e a jornada nao se completava pela interface |
| formalizacao de Contratos | PRODUCT-004 | EPIC-004 | FEATURE-018..FEATURE-022 | US-053..US-062 | `POST, GET /credit/carteiras/{carteira_id}/contratos`; `GET /credit/contratos/{contrato_id}`; `GET .../{contrato_id}/historico`; `POST .../{contrato_id}/assinar`; `POST .../{contrato_id}/liberar-para-motor`; `POST .../{contrato_id}/cancelar`; `POST .../{contrato_id}/encerrar` | 8 | `contratos.contrato.criar`, `contratos.contrato.ler`, `contratos.contrato.assinar`, `contratos.contrato.liberar`, `contratos.contrato.encerrar` | IMP-293 observado: formalizar Proposta aprovada, assinar, liberar saida logica para Motor, cancelar/encerrar e consultar historico; IMP-333 certificou `Idempotency-Key` nas cinco escritas; 403/404/409/5xx seguros e correlacionados |
| Motor Financeiro e pagamentos | PRODUCT-004 | EPIC-005 | FEATURE-023..FEATURE-027 | US-063..US-074 | `POST /credit/contratos/{contrato_id}/emprestimos`; `GET /credit/carteiras/{carteira_id}/emprestimos`; `GET /credit/emprestimos/{emprestimo_id}`; `POST .../{emprestimo_id}/pagamentos`; `POST /credit/pagamentos/{pagamento_id}/estornos`; `GET .../{emprestimo_id}/saldo`; `GET .../{emprestimo_id}/memoria-calculo`; `GET, POST .../{emprestimo_id}/quitacao`; `POST .../{emprestimo_id}/renegociacoes` | 10 | `motor.emprestimo.criar`, `motor.emprestimo.ler`, `motor.pagamento.registrar`, `motor.saldo.ler`, `motor.memoria.ler`, `motor.quitacao.executar`, `motor.renegociacao.criar` | IMP-294 observado: criar Emprestimo a partir de Contrato liberado, registrar pagamento, consultar saldo/memoria/quitacao e registrar renegociacao opaca; IMP-332 acrescentou a sobra explicita e o estorno parcial sem apagar o pagamento bruto; 5 comandos com `Idempotency-Key` certificado; nunca recalcular |
| cobranca manual | PRODUCT-005 | EPIC-007 | FEATURE-028 | US-075..US-078 | `GET /credit/cobrancas/casos`; `POST /credit/cobrancas/casos/{cobranca_caso_id}/acoes`; `POST .../{cobranca_caso_id}/promessas`; `POST /credit/cobrancas/promessas/{promessa_id}/apropriacoes` | 4 | `cobranca.caso.ler`, `cobranca.acao.registrar`, `cobranca.promessa.registrar`, `cobranca.promessa.apropriar` | IMP-295 observado: operar fila, acao, promessa e apropriacao a partir de fatos oficiais; 3 comandos com `Idempotency-Key`; empty/error/overflow, 404 neutro e sem saldo local |
| agenda e lembretes | PRODUCT-006 | EPIC-007 | FEATURE-029 | US-079..US-081 | `GET /credit/agenda`; `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/agenda/compromissos`; `POST /credit/agenda/compromissos/{agenda_item_id}/lembretes`; `POST .../compromissos/{agenda_item_id}/reagendar`; `POST .../concluir`; `POST .../cancelar`; `POST /credit/agenda/lembretes/{lembrete_id}/reagendar`; `POST .../enviar`; `POST .../concluir`; `POST .../cancelar` | 10 | `agenda.ler`, `agenda.compromisso.gerir`, `agenda.lembrete.gerir`, `notificacao.conciliar` | IMP-296 observado: consultar periodo, criar/manter compromisso e lembrete; 8 comandos idempotentes certificados, alias enviar apenas conciliacao, estados vazios, datas invalidas e 404 neutro |
| comunicacao | PRODUCT-007 | EPIC-007 | FEATURE-030 | US-082, US-083 | `POST /credit/carteiras/{carteira_id}/devedores/{devedor_id}/comunicacoes`; `GET /credit/comunicacoes` | 2 | `comunicacao.registrar`, `comunicacao.ler` | IMP-296 observado: registrar comunicacao com `Idempotency-Key` e consultar historico conforme OpenAPI atual, sem paginacao publicada e sem vazar contato cross-carteira |
| relatorios operacionais | PRODUCT-008 | EPIC-007 | FEATURE-031 | US-084..US-088 | `GET /credit/carteiras/{carteira_id}/relatorios/resumo`; `GET .../relatorios/vencimentos`; `GET .../relatorios/pagamentos`; `GET .../relatorios/fluxo` | 4 | `relatorios.operacionais.ler` | IMP-297 observado: apresentar respostas oficiais com periodo explicito, sem soma financeira local, sem `Idempotency-Key` inventada e com estados 400/401/403/404/500 correlacionados |
| Dashboard operacional composto `/app` | PRODUCT-005, PRODUCT-006, PRODUCT-008 | EPIC-007 | resultados read-only de FEATURE-028, FEATURE-029 e FEATURE-031; a composicao visual pertence ao PLAN-025, nao ao escopo Product de FEATURE-031 | previews de US-075, US-079, US-084 e US-085, sem concluir as Stories | reusa `GET /credit/cobrancas/casos`, `GET /credit/agenda`, `GET .../relatorios/resumo` e `GET .../relatorios/vencimentos` ja contabilizados | 0 | `cobranca.caso.ler`, `agenda.ler`, `relatorios.operacionais.ler` | composicao tecnica P0 de resultados existentes, sem novo agregado Product, comando, recalculo ou claim de Story concluida |
| configuracoes financeiras | PRODUCT-009 | EPIC-009 | FEATURE-037..FEATURE-041 | US-099..US-112 | `POST, GET /credit/configuracoes-financeiras`; `GET .../vigente`; `GET .../{configuracao_id}`; `POST .../{configuracao_id}/aprovar`; `POST .../{configuracao_id}/programar`; `POST .../{configuracao_id}/ativar`; `POST .../{configuracao_id}/inativar`; `POST, GET .../modalidades`; `POST, GET .../calendarios`; `POST .../snapshots` | 13 | `configuracoes_financeiras.configuracao.ler`, `configuracoes_financeiras.configuracao.gerir`, `configuracoes_financeiras.configuracao.aprovar`, `configuracoes_financeiras.configuracao.ativar`, `configuracoes_financeiras.modalidade.gerir`, `configuracoes_financeiras.calendario.gerir`, `configuracoes_financeiras.snapshot.capturar` | IMP-298 observado: `/app/configuracoes-financeiras`, criar/aprovar/programar/ativar, vigente, modalidades, calendarios e snapshot; parametros opacos, Carteira propria e correlation ID. IMP-333 certificou `Idempotency-Key` nas oito escritas |
| jobs, templates e notificacoes | PRODUCT-006, PRODUCT-007 | EPIC-010 | FEATURE-042..FEATURE-045 | US-113..US-124 | `GET /credit/automacao/jobs`; `GET /credit/automacao/jobs/{job_id}`; `POST .../{job_id}/cancelar`; `POST .../{job_id}/retry`; `GET /credit/notificacoes`; `GET /credit/notificacoes/{notification_id}`; `GET, POST /credit/notificacoes/templates`; `POST .../templates/{template_id}/aprovar`; `POST .../templates/{template_id}/ativar`; `POST .../{notification_id}/conciliar` | 11 | `automacao.job.consultar`, `automacao.job.cancelar`, `automacao.job.retry`, `notificacao.consultar`, `notificacao.template.gerir`, `notificacao.conciliar` | IMP-300 observado: consultar/retry/cancelar job, governar template e conciliar notificacao com RBAC exato; IMP-333 certificou `Idempotency-Key` nas cinco escritas antes descobertas, alem da conciliacao ja protegida; nenhum worker/provider disparado pelo frontend |

---

# 4. Jornadas compostas e prioridade

| Prioridade | Jornada composta | Superficies da matriz | Resultado observavel |
|---|---|---|---|
| P0 | sessao e shell autenticado | auth + contexto certificado + health | sessao server-only, navegacao por Permissoes e Carteira padrao resolvida |
| P0 | dashboard operacional | relatorios + agenda + cobranca | primeira tela operacional com loading/empty/error/overflow e links autorizados |
| P0 | Devedor ate Proposta | Devedores + Comercial | Devedor ativo chega a Proposta aprovada sem calculo financeiro definitivo no frontend |
| P0 | Proposta ate Contrato | Comercial + Contratos | contrato formalizado, assinado e liberado conforme estado backend |
| P0 | Contrato ate pagamento | Contratos + Motor | Emprestimo, parcelas e pagamento idempotente; valores apenas apresentados |
| P1 | cobranca ate comunicacao | cobranca + agenda + comunicacao | operador acompanha caso, promessa, retorno e historico no mesmo escopo |
| P1 | relatorios e configuracoes | relatorios + configuracoes | leitura operacional e administracao autorizada sem motor paralelo |
| P1 | IAM contratualmente permitido | credenciais + Perfis + catalogo certificado | administra Perfis e Usuarios conhecidos; nao promete listagem/ciclo de vida integral |
| P1 | automacao operacional | agenda + jobs/templates/notificacoes | observa e reconcilia automacao com Permissoes e correlation ID |
| P1 | jornadas compostas certificadas | P0/P1 transversal | IMP-301 observou login, RBAC, 404 neutro, Devedor-Proposta-Contrato-Emprestimo, pagamento idempotente, Motor, operacao diaria, Relatorios, Configuracoes, IAM, Automacao e 5xx correlacionado em stack real Next.js/FastAPI/PostgreSQL. **IMP-311 (2026-08-20) reexecutou a suite no modelo do emprestimo livre**: acrescentou o cenario wizard -> painel -> extrato -> pagamento e reparou tres cenarios que o PLAN-029 e o IMP-326/327 tinham deixado apontando para telas que nao existiam mais. 8/8 verdes, com mutacao deliberada verificando que o cenario novo falha quando a cadeia quebra |
| P1 | UI, seguranca e fronteiras certificadas | superficie frontend transversal | IMP-302 observou 50 PNGs vigentes, bundle publico sem tokens, Client Components sem backend direto, Web Interface Guidelines e scanner anti-calculo financeiro |

---

# 5. Contrato comum de erro e seguranca

| HTTP | Significado governado | Obrigacao da interface e do E2E |
|---:|---|---|
| 400 | sintaxe, query, header ou shape invalido | preservar entrada segura, apontar campos quando houver detalhe e nao converter em 422 localmente |
| 401 | sessao ausente, invalida, expirada ou Usuario inativo | tentar refresh somente quando aplicavel; limpar sessao server-only; voltar ao login sem loop |
| 403 | Principal valido sem Permissao | esconder/desabilitar antecipadamente por ergonomia, mas manter tratamento autoritativo do backend |
| 404 | inexistente ou fora do Tenant/Carteira | mensagem neutra; nunca sugerir que o recurso existe em outro escopo |
| 409 | conflito de estado, unicidade, idempotencia divergente ou contexto incompleto | manter intencao visivel, impedir replay cego e oferecer recuperacao segura |
| 422 | invariante/regra de dominio rejeitada pelo backend | exibir mensagem segura; nunca corrigir por regra ou calculo local |
| 5xx | falha inesperada/indisponibilidade | estado recuperavel, retry consciente e `X-Correlation-ID` visivel ao operador |

Toda mutacao declarada idempotente reutiliza a mesma `Idempotency-Key` para a
mesma intencao e gera nova chave para uma nova intencao. A chave, o Bearer token
e o refresh token ficam em codigo server-only.

---

# 6. Gate de rastreabilidade

A matriz so pode ser declarada sem lacunas quando:

- as 106 operacoes certificadas continuarem representadas exatamente uma vez
  na contagem de superficies;
- os endpoints de contexto e catalogo permanecerem presentes no OpenAPI e no
  snapshot deterministico;
- cada superficie protegida possuir Product, EPIC, Feature, User Story,
  Permissao e cenario Playwright;
- os cenarios negativos cobrirem 401/403/404 e, quando aplicavel,
  400/409/422/5xx;
- o snapshot OpenAPI e o cliente gerado falharem por drift nao aprovado;
- nenhum cenario esperar calculo financeiro no frontend ou no BFF.

---

# 7. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 3.9.0 | 2026-08-26 | IMP-351: provisionamento de Tenant por API e fluxo de ativacao removidos. Superficie de 107/134 para **105/131**; operacoes idempotentes de 63 para 62; excecoes auth de quatro para tres. O cabecalho ja marcava 3.9.0 antes desta entrada, sem linha correspondente aqui — lacuna herdada, fechada agora em vez de saltar para 3.10.0 e deixar o buraco. |
| 3.8.0 | 2026-08-22 | IMP-333: guardrail estrutural para toda escrita; 31 operacoes passaram a exigir `Idempotency-Key`, elevando o inventario de 32 para 63, com quatro excecoes auth nominais; superficie preservada em 107/134. |
| 3.7.0 | 2026-08-22 | IMP-332: novo estorno parcial idempotente; `PagamentoResponse` explicita devolucao, estorno, sobra e reconciliacao; contrato passa de 106/133 para 107/134. |
| 3.6.0 | 2026-08-20 | IMP-311: jornada real recertificada em 8/8 contra stack real, com o cenario do emprestimo livre (wizard, extrato e pagamento). A suite estava quebrada desde o IMP-327 e desatualizada pelo PLAN-029; nenhuma operacao, permissao ou contagem mudou. |
| 3.5.0 | 2026-08-20 | IMP-328 retirou `parcela_id` de sete schemas (`AcaoCobrancaCreateRequest`, `ApropriacaoPagamentoCreateRequest`, `ApropriacaoPagamentoResponse`, `ComunicacaoManualCreateRequest`, `PromessaPagamentoCreateRequest`, `PromessaPagamentoResponse`, `RegistroComunicacaoResponse`): a migracao 0017 ja havia derrubado as colunas. Contagem inalterada em 106 operacoes e 133 schemas; snapshot novo `ff101380ddbc11cdcd93f019c149f9819fbd7091cb42e3feb72f7e0f67189248`. |
| 3.4.0 | 2026-08-19 | IMP-327 aplicou a DR-004: `POST, GET /credit/emprestimos/{emprestimo_id}/parcelas` e as permissoes `motor.parcela.gerar`/`motor.parcela.ler` sairam do contrato e da matriz. Motor caiu de 11 para 9 operacoes, o total certificado de 107 para 105 e o contrato de 107 para 106 operacoes, com 133 schemas preservados. |
| 3.3.0 | 2026-08-16 | IMP-304 executou a DR-002: parametros comerciais voltaram a ser opacos, falha silenciosa de parametro invalido corrigida para `400` acionavel e cenario de stack real acrescentado submetendo o formulario Comercial. API/RBAC 107/133 preservados. |
| 3.2.0 | 2026-08-14 | IMP-303 recertificou localmente a matriz final do Frontend MVP, preservou API/RBAC 107/133 e publicou relatorio final; CI remota nao observada. |
| 3.1.0 | 2026-08-14 | IMP-302 certificou UI, seguranca e fronteiras com 50 PNGs vigentes, bundle publico sem tokens, Client Components sem backend direto, Web Interface Guidelines e anti-calculo; IMP-303 sob judge. |
| 3.0.0 | 2026-08-14 | IMP-301 observou jornadas compostas P0/P1 em stack real Next.js/FastAPI/PostgreSQL, sem mocks Playwright, preservando OpenAPI 107/133 e bloqueando IMP-302 ate novo judge. |
| 2.9.0 | 2026-08-14 | Automacao IMP-300 observada em `/app/automacao` com 11 operacoes oficiais, jobs/templates/notificacoes, RBAC exato, conciliacao com `Idempotency-Key`, evidencias desktop/mobile e IMP-301 sob judge. |
| 2.8.0 | 2026-08-14 | IAM permitido IMP-299 observado em `/app/iam` com Perfis, catalogo canonico, permissoes efetivas de Usuario conhecido, 11 operacoes oficiais, RBAC exato, sete comandos com `Idempotency-Key` e evidencias desktop/mobile; IMP-300 sob judge. |
| 2.7.0 | 2026-08-14 | Configuracoes Financeiras IMP-298 observado com 13 operacoes oficiais, RBAC exato, parametros opacos, Carteira propria, correlation ID, ausencia de `Idempotency-Key` inventada e evidencias desktop/mobile; IMP-299 sob judge. |
| 2.6.0 | 2026-08-14 | Relatorios IMP-297 observado com 4 GETs oficiais, periodo explicito, RBAC exato, ausencia de `Idempotency-Key` inventada e evidencias desktop/mobile; IMP-298 sob judge. |
| 2.5.0 | 2026-08-14 | Agenda/Comunicacao IMP-296 observado com 12 operacoes oficiais, 10 comandos idempotentes certificados, 2 consultas sem `Idempotency-Key`, RBAC exato, historico conforme OpenAPI atual e evidencia desktop/mobile; IMP-297 sob judge. |
| 2.4.0 | 2026-08-14 | Cobranca IMP-295 observado com 4 operacoes oficiais, 3 comandos idempotentes certificados, fila/acao/promessa/apropriacao e exibicao sem saldo local; IMP-296 sob judge. |
| 2.3.0 | 2026-08-14 | Motor/pagamentos IMP-294 observado com 11 operacoes oficiais, 4 comandos idempotentes certificados e exibicao sem calculo financeiro local; IMP-295 sob judge. |
| 2.2.0 | 2026-08-14 | Contratos IMP-293 observado com 8 operacoes oficiais, historico, liberacao logica sem Motor/pagamentos e OpenAPI preservado em 107/133. |
| 2.1.0 | 2026-08-14 | Comercial IMP-292 observado com jornada Devedor ativo -> Simulacao -> Proposta -> decisao, preservando OpenAPI 107/133 e sem criar Contratos/Motor. |
| 2.0.0 | 2026-08-14 | Devedores `/app/devedores` observado com listagem, consulta por documento, detalhe, historico e comandos idempotentes, preservando inventario OpenAPI 107/133; IMP-292 nao iniciado. |
| 1.9.0 | 2026-08-14 | Dashboard `/app` observado com resumo, vencimentos, agenda e cobranca read-only, RBAC exato e Carteira propria; inventario OpenAPI 107/133 preservado e IMP-291 nao iniciado. |
| 1.7.0 | 2026-08-13 | Login, shell e bootstrap do contexto proprio US-125 observados; API/RBAC 107/133 preservados e destinos de negocio continuam nos IMP-290+. |
| 1.6.0 | 2026-08-13 | Sessao JWE e BFF auth minimo do IMP-288 concluidos; API/RBAC 107/133 preservados e jornadas nao iniciadas. |
| 1.5.0 | 2026-08-13 | Cliente tipado IMP-287 concluido a partir do snapshot 107/133; nenhuma jornada, API, RBAC ou contagem foi alterada. |
| 1.4.0 | 2026-08-13 | Foundation IMP-286 concluida; nenhuma jornada, API, RBAC ou contagem 107/133 foi alterada. |
| 1.3.0 | 2026-08-13 | Harness IMP-285 concluido; nenhuma jornada, API, RBAC ou contagem 107/133 foi alterada. |
| 1.2.0 | 2026-08-12 | Gate adversarial satisfeito e scaffold IMP-284 concluido; cobertura Product/API/RBAC permanece 107/133. |
| 1.1.0 | 2026-08-12 | Matriz recertificada com 107 operacoes, contratos IAM efetivos e snapshot governado. |
| 1.0.0 | 2026-08-12 | Matriz oficial do Frontend MVP materializada a partir do backend certificado e dos deltas US-125/US-126. |
