# PLAN-031 - Relatorio do Ciclo do Emprestimo Livre (PLAN-027..PLAN-030)

**ID:** PLAN-031

**Versao:** 1.1.0

**Data:** 2026-08-20

**Escopo:** IMP-321..IMP-327 do PLAN-030, com o contexto do branch que os carrega

**Planos relatados:** PLAN-027, PLAN-028, PLAN-029, PLAN-030

**Decisao de origem:** DR-003 e DR-004

**Status:** Ciclo concluido, recertificado localmente e depois incorporado ao
`master`; pendencias IMP-307/IMP-329 resolvidas em PRs posteriores

---

# 1. Resultado

O produto trocou de modelo. O emprestimo deixou de ser um plano de parcelas
gerado no lancamento e passou a ser livre, com acerto mensal no dia combinado:
os juros correm sobre o saldo devedor por trecho, o devedor paga no minimo o
juro do periodo, e amortizar e voluntario.

O plano de parcelas saiu inteiro — agregado, ORM, repositorio, porto, duas
operacoes HTTP, quatro schemas, tabela e permissoes —, sem deixar arquivo
legado, conforme a decisao 5 do PLAN-030.

Este relatorio cobre o PLAN-030 e situa os tres planos que o antecedem no mesmo
branch, porque nenhum deles tinha relatorio proprio: PLAN-027 (wizard de
lancamento, depois concluido pelo PR #14), PLAN-028 (base de normalizacao dos
juros) e PLAN-029 (linguagem operacional da interface).

---

# 2. Escopo entregue no branch

**Branch:** `codex/plan-027-wizard`

**Base:** `origin/master`

**Diferenca:** 25 commits, 172 arquivos, +6779 / -2756

| Plano | Estado | IMPs |
|---|---|---|
| PLAN-027 - Wizard de lancamento | Concluido apos PR #14 | IMP-305..311 concluidos; IMP-307 entrou no PR #14 e IMP-311 ja estava recertificado |
| PLAN-028 - Base de normalizacao dos juros | Concluido | IMP-312..314 |
| PLAN-029 - Linguagem operacional da interface | Concluido | IMP-315..320 |
| PLAN-030 - Emprestimo livre com acerto mensal | Concluido | IMP-321..327 |

---

# 3. Resultado por IMP do PLAN-030

| IMP | Resultado observado |
|---|---|
| IMP-321 | Juros acumulam por trecho sobre o saldo em vigor; marcos em cada pagamento e em cada virada de mes |
| IMP-322 | `domain/credit/dia_de_acerto.py` responde quando cai o proximo acerto, fora do Motor porque e calendario, nao dinheiro |
| IMP-323 | O `Emprestimo` conhece `dia_de_acerto`, `proximo_acerto_em` e `acerto_vigente_em`, sem migracao |
| IMP-324 | O lancamento cria emprestimo sem plano; o wizard pergunta o dia do acerto |
| IMP-325 | Resumo da Carteira troca a ancora: `acertos_pendentes` e `principal_a_receber` |
| IMP-326 | A tela do emprestimo mostra extrato do saldo no lugar da tabela de parcelas |
| IMP-327 | O plano de parcelas sai do dominio, do banco, do contrato e dos relatorios |

O detalhe de execucao de cada item, incluindo os defeitos encontrados e as
decisoes de nomenclatura, esta em
`docs/implementation/backlogs/PLAN-030-execution-backlog.md`. Este relatorio nao
o duplica.

## 3.1 Defeitos que so a jornada real encontrou

Tres vezes neste ciclo a stack real encontrou o que o mock nao encontrou, e
vale registrar porque o padrao se repete:

1. **IMP-325** — os validadores de forma dos BFFs de Inicio e Relatorios ainda
   exigiam os campos antigos e rejeitavam o payload inteiro. Unidade,
   componente e BFF passaram verdes porque seus fixtures foram atualizados
   junto; quem pegou foi o Playwright contra a stack.
2. **IMP-327** — o Motor recusava pagamento e quitacao com "plano de parcelas
   deve ser gerado antes do pagamento". No emprestimo livre nao ha plano, e o
   pagamento e o evento que move a divida: a regra bloqueava o fluxo central do
   produto. **Nenhum teste cobria essa regra** — a suite seguiu verde com a
   remocao, o que confirma que ela nunca foi verificada.
3. **IMP-327** — o campo de valor recusava "500,00", que e como se escreve
   dinheiro em portugues; e `Recebido em` era texto livre com um instante fixo
   no codigo, cinco dias no passado.

---

# 4. Contrato: inventario e cadeia de snapshots

O snapshot governado
(`docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json`) deve
bater byte a byte com `create_app().openapi()`. Cada alteracao de contrato deste
ciclo o regerou:

| Data | Origem | Operacoes / Schemas | SHA-256 (prefixo) |
|---|---|---:|---|
| 2026-08-16 | IMP-306 publica o lancamento | 108 / 137 | `5ebbe33b73ffa20d` |
| 2026-08-17 | IMP-324, o emprestimo nasce livre (nao aditivo) | 108 / 137 | `ba4342af3a977fe6` |
| 2026-08-17 | IMP-325, ancora do Resumo da Carteira | 108 / 137 | `367381a54d6f4d24` |
| 2026-08-19 | IMP-326, campos de acerto em `EmprestimoResponse` (aditivo) | 108 / 137 | `6b24001ab24f9e4c` |
| 2026-08-19 | IMP-327, o plano de parcelas sai (nao aditivo) | **106 / 133** | `75a15e1f119a0fe0` |

Inventario vigente, conferido em 2026-08-20 sobre o arquivo em disco:
**106 operacoes, 133 schemas, 671442 bytes**, SHA-256
`75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34`.

Catalogo de permissoes: 53 (era 55; sairam `motor.parcela.gerar` e
`motor.parcela.ler`). Endpoints protegidos: 63 (era 65). Matriz de
rastreabilidade em 3.4.0: Motor de 11 para 9 operacoes, total certificado de
107 para 105.

---

# 5. Gates observados em 2026-08-20

Executados nesta sessao de fechamento, sobre a arvore limpa do branch:

| Gate | Resultado observado | Estado |
|---|---|---|
| `uv run pytest` | **983 testes** em 345,60 s | Verde |
| `uv run ruff check .` | `All checks passed!` | Verde |
| `uv run black --check .` | 260 arquivos sem mudanca | Verde |
| `uv run mypy src tests` | sem issue em 238 source files | Verde |
| `npm run docs:validate` | 351 OK, 31 avisos, **0 erros** | Verde |
| `npm run docs:test` | 173/173 | Verde |
| `frontend: test:unit` | 70 testes, 15 arquivos | Verde |
| `frontend: test:component` | 65 testes, 15 arquivos | Verde |
| `frontend: test:bff` | 134 testes, 15 arquivos | Verde |
| `frontend: test:contract` | 40 testes, 14 arquivos (inclui `api:check` e `typecheck`) | Verde |
| `npm run quality:migrations` | `upgrade head -> downgrade base -> upgrade head` contra PostgreSQL 16 real | Verde |

Total frontend nas quatro suites sem navegador: **309 testes**.

As suites Playwright (`test:e2e`, `test:jornadas` e as por tela) exigem a stack
real subindo FastAPI e PostgreSQL e nao foram reexecutadas nesta sessao de
fechamento; a evidencia delas e a do proprio ciclo, registrada no backlog.

## 5.1 A migracao `0017` passou pelo gate de reversibilidade

`0017_remove_plano_de_parcelas` e a unica migracao do repositorio que faz
`DROP` — da tabela `parcela`, de quatro FKs, das quatro colunas `parcela_id`
das tabelas referentes e de duas permissoes. A excecao a regra "aditivas
apenas" esta autorizada pela DR-004 e fundamentada no PLAN-030 §5.1.

O ciclo completo `upgrade head -> downgrade base -> upgrade head` foi executado
contra PostgreSQL 16 real e fechou nas 17 migracoes, com `0017` na cabeca nas
duas subidas. O `downgrade` recria a estrutura; o que ele nao devolve e dado, e
nao ha dado a devolver.

## 5.2 Como rodar os testes de integracao nesta maquina

Duas armadilhas custaram meia hora e ficam registradas:

1. `DEFAULT_DATABASE_URL` aponta para `localhost`. A resolucao tenta `::1`
   primeiro e **espera o timeout inteiro** antes de cair para `127.0.0.1` — com
   centenas de testes, a suite parece travada em vez de falhar. Trocar o host
   por `127.0.0.1` no `DATABASE_URL` resolve.
2. A senha do `DEFAULT_DATABASE_URL` e `emprestimo`, mas o container sobe com a
   do `.env` local. Sem `DATABASE_URL` explicita, a autenticacao falha.

Comando que funciona, sem expor a senha:

```bash
export DATABASE_URL="postgresql+psycopg://emprestimo:$(grep -m1 '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)@127.0.0.1:5432/emprestimo"
uv run pytest
```

Correcao sugerida, de uma palavra: trocar `localhost` por `127.0.0.1` em
`DEFAULT_DATABASE_URL` (`infrastructure/db/session.py`). O Compose define
`DATABASE_URL` explicitamente para os containers, entao o padrao so afeta
execucao local. Nao foi aplicada aqui para nao alterar `src/` num commit de
fechamento.

---

# 6. Defeitos encontrados no fechamento

## 6.1 Registro de snapshot inconsistente

**Registro de snapshot inconsistente no PLAN-026 §7.1.** O hash
`75a15e1f...` estava lancado na entrada de 2026-08-17 ao lado de "108
operacoes, 137 schemas". Impossivel: esse hash pertence ao snapshot de 106/133
produzido pelo IMP-327, dois dias depois. Um mesmo SHA-256 aparecia descrevendo
dois inventarios diferentes.

A entrada foi reconstruida a partir do historico do proprio arquivo em `git`,
com cada hash conferido contra a contagem de operacoes e schemas do commit
correspondente. Duas regeracoes que nao estavam registradas (IMP-325 e IMP-326)
foram acrescentadas. O PLAN-026 foi para a versao 1.3.0.

## 6.2 Restos de `parcela` que o IMP-327 nao alcancou

O criterio de conclusao do IMP-327 era "nenhum arquivo legado". A conferencia
de fechamento encontrou tres restos. Um foi corrigido aqui; os outros dois
mudam contrato ou codigo de dominio e por isso viram escopo declarado, nao
correcao silenciosa.

**Corrigido nesta sessao.** `tests/conftest.py` listava `parcela` em
`TABELAS_TRUNCATE` e `TABELAS_DROP`. Ambas as listas sao filtradas contra as
tabelas existentes, entao a entrada nunca quebrou nada — era residuo morto.
Duas linhas removidas.

**Nao corrigido, e o mais serio: `parcela_id` continua no contrato publico.**
Sete schemas ainda o carregam — `AcaoCobrancaCreateRequest`,
`ApropriacaoPagamentoCreateRequest`, `ApropriacaoPagamentoResponse`,
`ComunicacaoManualCreateRequest`, `PromessaPagamentoCreateRequest`,
`PromessaPagamentoResponse` e `RegistroComunicacaoResponse` — e o dialogo de
Cobranca no frontend ainda envia o campo. A migracao `0017` **derrubou as
colunas `parcela_id`** das quatro tabelas referentes, junto com as FKs. O
resultado e um campo que a API aceita, o dominio valida e o repositorio nao
tem onde gravar: some na releitura, sem erro. Perda silenciosa num caminho de
Cobranca.

**Nao corrigido: read model morto.** `domain/credit/operacao_diaria.py` ainda
declara `VencimentoOperacional`, com `parcela_id: uuid.UUID` **obrigatorio**, e
o exporta em `__all__`. Nada o constroi — os relatorios usam
`VencimentoOperacionalResultado`, da camada Application. E codigo morto que
ainda exige um identificador de um agregado que nao existe.

**Deliberado, nao e resto.** A coluna JSON `pagamento.parcelas_liquidadas`
permanece e fica sempre vazia; o proprio codigo registra que o nome e historico.

Nenhum outro defeito surgiu no fechamento.

---

# 7. Pendencias e caveats

Pendencias de escopo declaradas no fechamento original, reconciliadas apos os
PRs posteriores:

- **IMP-307 - Comprovante do lancamento** (PLAN-027): concluido no PR #14,
  mergeado em 2026-08-20.
- **IMP-311 - Jornada real e recertificacao** (PLAN-027): concluido em
  2026-08-20, com 8/8 jornadas verdes contra stack real.
- **IMP-284** (PLAN-025): o backlog vigente do PLAN-025 marca o scaffold como
  concluido; a referencia antiga a bloqueio por `fable:fable-judge` era
  historica.

Escopo novo aberto por este fechamento e ja encerrado:

- **IMP-328 - Tirar `parcela_id` do contrato e do dominio.** Concluido em
  2026-08-20, com snapshot, inventario e matriz atualizados. Ver §6.2 e o
  backlog vigente do PLAN-030.
- **IMP-329 - Valor digitado ambiguo no wizard.** Concluido no PR #16,
  mergeado e deployado em 2026-08-20.

Caveats operacionais:

- **A baseline documental subiu de 29 para 31 avisos.** Os dois novos sao o
  mesmo aviso em dois documentos: `PLAN-013` e `PLAN-030` citam
  `GET/POST /credit/emprestimos/{}/parcelas`, que deixou de existir. O aviso e
  verdadeiro e a decisao de mante-lo esta no PLAN-030 §4: suprimi-lo exigiria
  reescrever a historia do EPIC-005. Zero erros.
- **Limitacao conhecida da fila de cobranca**: um pagamento parcial tira o
  emprestimo da fila. Julgar se o juro do periodo foi quitado exige o saldo, e
  saldo e do Motor, que a camada de Cobranca e proibida de importar. Ha teste
  proprio documentando o comportamento.

---

# 8. Historico de versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-08-20 | Atualizacao pos-merge/deploy: PR #14 encerrou IMP-307, PR #16 encerrou IMP-329, e pendencias historicas foram reconciliadas com os backlogs vigentes. |
| 1.0.0 | 2026-08-20 | Fechamento do ciclo do emprestimo livre: IMP-321..327, cadeia de snapshots reconstruida, gates reexecutados e pendencias declaradas. |
