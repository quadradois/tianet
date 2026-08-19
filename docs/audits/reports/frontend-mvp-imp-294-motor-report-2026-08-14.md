# Relatorio focal — IMP-294 Motor e pagamentos

**Plano relacionado:** PLAN-025 — Frontend MVP Transversal  
**Data:** 2026-08-14  
**Status:** IMP-294 concluido; IMP-295 nao iniciado e permanece sob novo `fable:fable-judge`.

---

## 1. Resultado

O IMP-294 materializou a jornada Motor/pagamentos em `/app/motor`, consumindo
somente as 11 operacoes oficiais do snapshot OpenAPI governado:

- criar Emprestimo a partir de Contrato liberado;
- listar e consultar Emprestimos da Carteira propria;
- gerar/consultar parcelas;
- registrar pagamento;
- consultar saldo, memoria de calculo e quitacao;
- executar quitacao;
- registrar renegociacao opaca.

O frontend apresenta valores, parametros e memoria retornados pelo backend sem
formula local, soma, arredondamento, reclassificacao ou formatacao financeira
autoritativa.

---

## 2. RED -> GREEN

- **RED inicial observado:** `node scripts/tests/test-plan-025-contracts.js` =
  136/137.
- **Falha unica esperada:** `frontend/src/lib/bff/motor.server.ts ausente`.
- **GREEN observado:** suite Motor e contrato documental passam apos a
  implementacao minima.

O RED e evidencia temporal da sessao; depois do GREEN ele nao e reproduzivel sem
reverter arquivos.

---

## 3. Contrato tecnico entregue

- RBAC por igualdade exata:
  `motor.emprestimo.criar`, `motor.emprestimo.ler`, `motor.parcela.gerar`,
  `motor.parcela.ler`, `motor.pagamento.registrar`, `motor.saldo.ler`,
  `motor.memoria.ler`, `motor.quitacao.executar` e
  `motor.renegociacao.criar`.
- Carteira vem exclusivamente do contexto operacional corrente; o browser nao
  seleciona Tenant ou Carteira.
- `Idempotency-Key` e enviada somente onde o OpenAPI exige:
  - `POST /credit/contratos/{contrato_id}/emprestimos`;
  - `POST /credit/emprestimos/{emprestimo_id}/pagamentos`;
  - `POST /credit/emprestimos/{emprestimo_id}/quitacao`;
  - `POST /credit/emprestimos/{emprestimo_id}/renegociacoes`.
- `POST /credit/emprestimos/{emprestimo_id}/parcelas` permanece sem
  `Idempotency-Key`, porque o contrato publicado nao exige esse header.
- 400/401/403/404/409/422/5xx e resposta malformada sao estados seguros e
  correlacionados; 404 permanece neutro.
- Nenhum endpoint, componente ou fluxo de Cobranca/Agenda/Relatorios/Configuracoes
  foi iniciado.

---

## 4. Evidencia visual

| Evidencia | Dimensao | SHA-256 |
|---|---:|---|
| `frontend-mvp-imp-294-motor-list-desktop.png` | 1440x900 | `be04ac5308608f63b86c21b489ad5b79bafeef6ff50f4dd81a82cbc734425bcf` |
| `frontend-mvp-imp-294-motor-list-mobile.png` | 390x844 | `2c38db4674555f765bd26d9b14bef84c1d5138e01550a716e71f1f788882a431` |
| `frontend-mvp-imp-294-emprestimo-detail-desktop.png` | 1440x900 | `95634c3f9f49f7662eab43185f37d6d91d5b71e3c876ddc17e99651fefa3203b` |
| `frontend-mvp-imp-294-pagamento-flow-mobile.png` | 390x844 | `a94449ddfd78b23cd67ebdb5986a561b24f300b81f484548e9c6e46de16bda7b` |

---

> **Pinos das duas capturas de lista avancados no IMP-309** (PLAN-027). A tela de
> lista foi reescrita em tres grupos e passou a identificar o Devedor pelo nome;
> as capturas mudaram porque a tela mudou. Verificadas estaveis em quatro
> execucoes consecutivas do `npm run test:motor`.
>
> **Atualizacao do IMP-326.** A tela de detalhe deixou de mostrar a tabela de
> parcelas e passou a mostrar o painel do emprestimo livre e o extrato do saldo
> (DR-004). Os quatro pinos foram avancados.
>
> Nova causa de instabilidade encontrada e corrigida: neste modulo o Correlation
> ID vem **concatenado na mesma string** da mensagem, e o congelador do IMP-310
> so alcancava no de texto que fosse exclusivamente o UUID. Passou a substituir
> dentro do texto. Com isso `pagamento-flow-mobile` tornou-se deterministica.
>
> `emprestimo-detail-desktop` **continua instavel** entre execucoes, agora com a
> divergencia concentrada na coluna de conteudo, com o texto pintado identico. A
> decisao mudou em relacao ao IMP-310: antes o pino ficava nos bytes versionados
> para nao registrar ruido; agora ele avanca para os bytes atuais, porque a
> alternativa passou a ser pior — a imagem versionada mostrava uma tabela de
> parcelas que o produto nao tem mais. Evidencia desatualizada engana mais do
> que evidencia que precisa ser repinada.
>
> Consequencia pratica inalterada: rodar `npm run test:motor` localmente deixa
> essa evidencia divergente do relatorio. Em CI nao ocorre, porque a
> certificacao roda antes do E2E regenerar os PNGs.

> **Causa da irreprodutibilidade isolada e corrigida no IMP-310.** As capturas de
> detalhe variavam entre execucoes identicas: 34% dos pixels diferiam, em toda a
> area da imagem. A causa e o Correlation ID — um UUID novo a cada requisicao.
> Mesmo dentro da regiao escondida por `visibility: hidden`, ele desestabiliza a
> captura, porque a regiao continua ocupando layout e glifos diferentes quebram
> a linha em pontos diferentes, deslocando todo o conteudo abaixo. A jornada
> agora o congela antes da captura, preservando os 36 caracteres.
>
> Resultado medido: `pagamento-flow-mobile` passou a ser deterministico e teve o
> pino avancado. Em `emprestimo-detail-desktop` a instabilidade caiu de 441.801
> para 9.616 pixels, confinados a uma faixa de 8 pixels na borda inferior da
> viewport — residuo nao isolado. Por isso o pino dessa unica evidencia
> permanece nos bytes ja versionados: a tela de detalhe nao mudou no IMP-310, e
> pinar bytes instaveis registraria ruido em vez de prova. Consequencia pratica:
> quem rodar o Playwright do Motor localmente vera o gate
> `test-plan-025-contracts` acusar divergencia apenas nessa evidencia. Em CI nao
> ocorre, porque a certificacao roda antes do E2E regenerar os PNGs.

---

## 5. Gates observados

- `npm --prefix frontend run lint` — verde.
- `npm --prefix frontend run typecheck` — verde.
- `npm --prefix frontend run build` — verde.
- `npm --prefix frontend run test:unit -- --run tests/unit/motor-policy.test.ts`
  — 5/5.
- `npm --prefix frontend run test:component -- --run tests/component/motor.test.tsx`
  — 4/4.
- `npm --prefix frontend run test:bff -- --run tests/bff/motor.test.ts` — 6/6.
- `npm --prefix frontend run test:contract -- --run tests/contract/motor.test.ts`
  — 3/3, incluindo `api:check` e `typecheck`.
- `npm --prefix frontend run test:motor` — 8/8.

Gates documentais finais (`test-plan`, scope, docs validate/test e diff-check)
devem ser reobservados no judge focal.

---

## 6. Inventario e escopo

Baseline IMP-294: 237 caminhos.  
Mutaveis declarados: 11.  
Protegidos: 226.  
Novos declarados: 22.  
Inventario final esperado: 259 caminhos.

O predecessor encadeado e
`docs/audits/evidence/frontend-mvp-imp-293-protected-baseline.json` com SHA-256
`702c0decb21c8339216b053da9588a701e375fd766ec73428e8ef37044634202`.

Arquivos criados principais:

- `frontend/src/lib/bff/motor.server.ts`;
- `frontend/src/lib/motor/motor-policy.ts`;
- `frontend/src/components/motor/motor.tsx`;
- `frontend/src/components/motor/motor-command-dialog.client.tsx`;
- `frontend/src/app/app/motor/page.tsx`;
- `frontend/src/app/app/motor/[emprestimoId]/page.tsx`;
- `frontend/src/app/app/motor/actions.ts`;
- testes unit/component/BFF/contract/Playwright Motor;
- `scripts/tests/test-imp-294-scope.js`;
- este relatorio e as 4 evidencias visuais.

Arquivos protegidos nao alterados pelo IMP-294: backend Python, migrations,
testes Python, Product, Registry, snapshot OpenAPI, cliente OpenAPI gerado,
lockfiles e BFF de sessao.

---

## 7. Caveats nao bloqueantes

- CI remota Linux/Windows ainda nao foi observada sem commit/push.
- O RED inicial e temporal.
- Avisos EOL do Windows podem aparecer no `git diff --check`; nao sao alteracao
  de contrato.
- A toolchain exata permanece governada por `frontend/tests/toolchain-check.mjs`
  e CI, embora o shell local possa divergir.

---

## 8. Decisao

O IMP-294 esta tecnicamente concluido no estado local observado. O IMP-295
continua bloqueado ate novo `$fable:fable-judge` focal.
