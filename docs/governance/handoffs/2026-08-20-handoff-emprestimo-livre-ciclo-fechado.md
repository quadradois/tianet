# 2026-08-20 - Handoff: Ciclo do Emprestimo Livre Fechado

**Versao:** 1.0.0

**Status:** PLAN-027 (parcial), PLAN-028, PLAN-029 e PLAN-030 entregues e
recertificados localmente; **branch nao mergeado**

**Periodo coberto:** do wizard de lancamento (PLAN-027) ao fim do plano de
parcelas (PLAN-030)

**Branch:** `codex/plan-027-wizard`

**Base:** `origin/master`, 25 commits atras

**Commit de topo:** `1ea303d` - feat(relatorios): a tela de vencimentos passa a
falar de acerto (IMP-327)

**Relatorio do ciclo:**
`docs/implementation/reports/PLAN-030-emprestimo-livre-com-acerto-mensal-2026-08-20.md`

---

## 1. Estado Executivo

O produto mudou de modelo neste ciclo. O emprestimo deixou de ser um plano de
parcelas gerado no lancamento e passou a ser **livre, com acerto mensal no dia
combinado**: os juros correm sobre o saldo devedor por trecho, o devedor deve no
minimo o juro do periodo em cada acerto, e amortizar e voluntario. Atraso nao
gera multa nem encargo — sao apenas mais dias do mesmo juro.

A decisao esta na DR-004; a base de normalizacao dos juros, na DR-003. O plano
de parcelas foi removido do dominio, do banco, do contrato e das telas. A
conferencia de fechamento achou um resto que a remocao nao alcancou — o campo
`parcela_id` — e ele esta declarado no caveat 4.4, nao escondido.

**O trabalho esta apenas no branch local.** Nao ha PR aberto e o `origin/master`
segue no estado anterior ao ciclo.

---

## 2. O que foi entregue

| Plano | Estado | Conteudo |
|---|---|---|
| PLAN-027 | **Parcial** | Wizard de lancamento em tres passos, lista de emprestimos em grupos, Devedor abrindo pelos emprestimos. IMP-307 e IMP-311 seguem abertos |
| PLAN-028 | Concluido | Juros normalizados pelo mes do periodo (DR-003) |
| PLAN-029 | Concluido | Linguagem operacional da interface: painel do emprestimo, vocabulario do Credor, formatacao brasileira, menu em dois grupos, identidade TiaNet |
| PLAN-030 | Concluido | Emprestimo livre com acerto mensal e remocao do plano de parcelas (IMP-321..327) |

Efeito no contrato publico: o inventario saiu de **108 operacoes e 137 schemas**
para **106 e 133**; o catalogo de permissoes, de 55 para 53; endpoints
protegidos, de 65 para 63. A matriz de rastreabilidade esta em 3.4.0.

Snapshot vigente
(`docs/governance/contracts/openapi/frontend-mvp-backend-openapi.json`),
conferido em 2026-08-20: 671442 bytes, SHA-256
`75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34`.

**Duas alteracoes deste ciclo nao sao aditivas** e isso e deliberado: o IMP-324
retirou campos exigidos do lancamento e o IMP-327 retirou operacoes e schemas.
Ambas amparadas pela resolucao da DR-004.

---

## 3. Evidencias

Gates reexecutados em 2026-08-20, arvore limpa:

- `uv run pytest` - **983 testes verdes** em 345,60 s;
- `uv run ruff check .` - verde;
- `uv run black --check .` - verde, 260 arquivos;
- `uv run mypy src tests` - verde, 238 source files;
- `npm run docs:validate` - 351 OK, 31 avisos, **0 erros**;
- `npm run docs:test` - 173/173;
- frontend `test:unit` 70, `test:component` 65, `test:bff` 134,
  `test:contract` 40 - **309 testes**, todos verdes;
- `npm run quality:migrations` - `upgrade head -> downgrade base -> upgrade
  head` contra PostgreSQL 16 real, **verde**.

Nao reexecutadas nesta sessao: as suites Playwright, que exigem a stack real
subindo FastAPI e PostgreSQL. A evidencia delas e a do proprio ciclo, no
backlog do PLAN-030.

---

## 4. Caveats

### 4.1 Rodar os testes de integracao nesta maquina exige `DATABASE_URL`

Duas armadilhas, que juntas fazem a suite **parecer travada** em vez de falhar:

1. `DEFAULT_DATABASE_URL` aponta para `localhost`, cuja resolucao tenta `::1`
   primeiro e espera o timeout inteiro antes de cair para `127.0.0.1`. Com
   centenas de testes, isso vira meia hora de silencio;
2. a senha do padrao e `emprestimo`, mas o container sobe com a do `.env`.

Comando que funciona:

```bash
export DATABASE_URL="postgresql+psycopg://emprestimo:$(grep -m1 '^POSTGRES_PASSWORD=' .env | cut -d= -f2-)@127.0.0.1:5432/emprestimo"
uv run pytest
```

Correcao sugerida, de uma palavra: `localhost` -> `127.0.0.1` em
`DEFAULT_DATABASE_URL` (`infrastructure/db/session.py`). O Compose define
`DATABASE_URL` para os containers, entao o padrao so afeta execucao local. Nao
foi aplicada para nao alterar `src/` num commit de fechamento.

### 4.2 Baseline documental de 29 para 31 avisos

Os dois avisos novos sao o mesmo caso em dois documentos: `PLAN-013` e
`PLAN-030` citam `GET/POST /credit/emprestimos/{}/parcelas`, que deixou de
existir. O aviso e verdadeiro e mante-lo e decisao registrada no PLAN-030 §4 —
suprimi-lo exigiria reescrever a historia do EPIC-005. Zero erros.

### 4.3 Registro de snapshot corrigido no fechamento

O PLAN-026 §7.1 atribuia o hash vigente a um inventario que nao era o dele. A
cadeia foi reconstruida a partir do historico do arquivo em `git` e o PLAN-026
foi para 1.3.0. Detalhe no §6 do relatorio do ciclo.

### 4.4 `parcela_id` sobreviveu no contrato publico

A remocao do IMP-327 nao alcancou o campo `parcela_id`. Ele continua em **sete
schemas** do OpenAPI vigente, nas entidades de Operacao Diaria e Promessa, na
camada Application e no dialogo de Cobranca do frontend — mas a migracao `0017`
derrubou as colunas correspondentes.

Efeito pratico: a API aceita o campo, o dominio o valida, e o repositorio nao
tem onde grava-lo. O valor some na releitura, **sem erro**. E o unico ponto
deste ciclo em que o produto perde dado em silencio.

Junto com ele sobrou codigo morto: o read model `VencimentoOperacional`, no
dominio, com `parcela_id` obrigatorio e nenhum construtor.

Escopo proposto: **IMP-328** (ver §5). Nao foi corrigido aqui porque muda
contrato — exige regeracao de snapshot, novo inventario e matriz atualizada, o
que e trabalho de ciclo, nao de fechamento.

### 4.5 Limitacao conhecida da fila de cobranca

Um pagamento parcial tira o emprestimo da fila. Julgar se o juro do periodo foi
quitado exige o saldo, e saldo e do Motor, que a camada de Cobranca e proibida
de importar. A fila diz **quem** procurar; o valor vem do saldo quando o
operador abre a operacao. Ha teste documentando o comportamento.

---

## 5. Pendencias herdadas

| Item | Plano | Estado |
|---|---|---|
| IMP-307 - Comprovante do lancamento | PLAN-027 | Planejado, nao iniciado |
| IMP-311 - Jornada real e recertificacao | PLAN-027 | Planejado, **enunciado obsoleto** |
| IMP-284 - Scaffold governado | PLAN-025 | Bloqueado ate `fable:fable-judge` |
| **IMP-328 - Tirar `parcela_id` do contrato e do dominio** | proposto neste fechamento | Aberto, ver §4.4 |

**Sobre o IMP-311:** o enunciado manda cobrir a jornada do wizard "ate o plano
de parcelas". Esse objeto nao existe mais. Reescrever contra o extrato do saldo
e o acerto mensal **antes** de executar — caso contrario o cenario certifica uma
tela que nao existe.

---

## 6. Proximo Ciclo Recomendado

Ordem sugerida:

1. push do branch e PR para `master`, com o relatorio do ciclo como corpo;
2. **IMP-328** — tirar `parcela_id` do contrato e do dominio (caveat 4.4). E o
   unico item que ainda perde dado em silencio;
3. reescrita do IMP-311 contra o modelo novo, e execucao da jornada real;
4. IMP-307, o comprovante do lancamento;
5. so entao abrir escopo novo.

A ordem tem motivo: o passo 2 e o unico defeito de comportamento ainda em
aberto, e o passo 3 e o unico que exercita o produto inteiro contra a stack
real — que neste ciclo encontrou tres defeitos que nenhuma suite com mock
encontrou.

---

## 7. Regras que o ciclo confirmou

- **O Motor e a autoridade sobre dinheiro.** Frontend formata e envia texto; o
  valor e do Motor. A troca de virgula por ponto no campo de valor e pontuacao,
  nao calculo.
- **Calendario nao se calcula no navegador.** `proximo_acerto_em` vem do
  backend; duplicar a regra daria dois lugares para divergir.
- **Campos derivados na leitura, nao colunas.** O proximo acerto anda com o
  calendario; uma coluna gravada envelheceria em silencio a cada mes — inclusive
  no replay de idempotencia.
- **Mock verde nao e produto verde.** Fixtures atualizados junto com o codigo
  escondem quebra de contrato entre camadas.

---

## 8. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-20 | Fechamento do ciclo do emprestimo livre (PLAN-027 parcial, PLAN-028, PLAN-029, PLAN-030), com caveats e pendencias declaradas. |
