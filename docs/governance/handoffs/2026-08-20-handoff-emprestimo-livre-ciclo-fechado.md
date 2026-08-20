# 2026-08-20 - Handoff: Ciclo do Emprestimo Livre Fechado

**Versao:** 1.2.0

**Status:** PLAN-027 (parcial), PLAN-028, PLAN-029 e PLAN-030 entregues e
recertificados localmente, com IMP-328 e IMP-311 executados apos o fechamento;
**branch nao mergeado**

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
conferido em 2026-08-20: 669593 bytes, SHA-256
`ff101380ddbc11cdcd93f019c149f9819fbd7091cb42e3feb72f7e0f67189248`
(publicado pelo IMP-328).

**Tres alteracoes deste ciclo nao sao aditivas** e isso e deliberado: o IMP-324
retirou campos exigidos do lancamento, o IMP-327 retirou operacoes e schemas, e
o IMP-328 retirou `parcela_id` de sete schemas. As tres amparadas pela
resolucao da DR-004.

---

## 3. Evidencias

Gates reexecutados em 2026-08-20, arvore limpa:

- `uv run pytest` - **985 testes verdes** em 394,48 s (983 no fechamento, mais os dois do IMP-328);
- `uv run ruff check .` - verde;
- `uv run black --check .` - verde, 260 arquivos;
- `uv run mypy src tests` - verde, 238 source files;
- `npm run docs:validate` - 351 OK, 31 avisos, **0 erros**;
- `npm run docs:test` - 173/173;
- frontend `test:unit` 70, `test:component` 65, `test:bff` 134,
  `test:contract` 40 - **309 testes**, todos verdes;
- `npm run quality:migrations` - `upgrade head -> downgrade base -> upgrade
  head` contra PostgreSQL 16 real, **verde**;
- `npm run test:jornadas` - **8/8 verdes** contra Next.js, FastAPI e
  PostgreSQL 16 reais (IMP-311), com mutacao deliberada confirmando que o
  cenario novo falha quando a cadeia quebra.

Nao reexecutadas nesta sessao: as demais suites Playwright por tela. A
evidencia delas e a do proprio ciclo, no backlog do PLAN-030.

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

### 4.4 `parcela_id` sobreviveu ao IMP-327 — resolvido no IMP-328

A remocao do IMP-327 nao alcancou o campo `parcela_id`: ele ficou em sete
schemas, nas entidades de Cobranca, Promessa e Comunicacao, na Application e no
dialogo de Cobranca, enquanto a migracao `0017` ja tinha derrubado as colunas.

**Era pior do que residuo.** `ApropriacaoPagamentoResponse` exigia o campo e o
resolvedor devolvia `None` sempre que nao havia parcela — que no emprestimo
livre e sempre. Apropriar um pagamento a uma promessa respondia **500**. Nenhum
teste cobria esse caminho pela API.

Resolvido pelo **IMP-328** (backlog do PLAN-030, §IMP-328), com prova nos dois
sentidos: com o campo exigido de volta, 500; sem ele, 200.

### 4.5 O wizard aceita `2.000` e entende dois reais

Achado do IMP-311, **nao corrigido**. O campo "Valor emprestado" aceita
`2000,00` e `2000.00`, e recusa `2.000,00` — mas aceita **`2.000`**, que o
backend le como **R$ 2,00**. Quem digitar o separador de milhar sem os centavos
lanca um emprestimo mil vezes menor, sem aviso nenhum.

Nao foi corrigido porque escolher a interpretacao e decisao de produto: `2.000`
pode ser dois mil (leitura brasileira) ou dois (leitura da maquina). As saidas
possiveis sao recusar a entrada ambigua ou formatar o campo enquanto se digita.
**Escopo proposto: IMP-329.**

### 4.6 Limitacao conhecida da fila de cobranca

Um pagamento parcial tira o emprestimo da fila. Julgar se o juro do periodo foi
quitado exige o saldo, e saldo e do Motor, que a camada de Cobranca e proibida
de importar. A fila diz **quem** procurar; o valor vem do saldo quando o
operador abre a operacao. Ha teste documentando o comportamento.

---

## 5. Pendencias herdadas

| Item | Plano | Estado |
|---|---|---|
| IMP-307 - Comprovante do lancamento | PLAN-027 | Planejado, nao iniciado |
| IMP-284 - Scaffold governado | PLAN-025 | Bloqueado ate `fable:fable-judge` |
| ~~IMP-328 - Tirar `parcela_id` do contrato e do dominio~~ | PLAN-030 | **Concluido** em 2026-08-20, ver §4.4 |
| ~~IMP-311 - Jornada real e recertificacao~~ | PLAN-027 | **Concluido** em 2026-08-20, 8/8 em stack real |
| **IMP-329 - Valor digitado ambiguo no wizard** | proposto no IMP-311 | Aberto, ver §4.5 |

**O que o IMP-311 encontrou ao rodar:** a suite nao rodava desde o IMP-327 e
devolveu 4 de 8 cenarios vermelhos na primeira execucao — seed chamando um
endpoint removido, e tres cenarios procurando textos que o PLAN-029 e o IMP-326
tinham trocado. Nenhum era defeito de codigo novo; todos eram a suite
descrevendo um produto que nao existia mais.

---

## 6. Proximo Ciclo Recomendado

Ordem sugerida:

1. push do branch e PR para `master`, com o relatorio do ciclo como corpo;
2. **IMP-329** — decidir e corrigir o valor ambiguo do wizard (§4.5). E o unico
   ponto conhecido em que o Credor pode lancar um valor errado sem perceber;
3. IMP-307, o comprovante do lancamento;
4. so entao abrir escopo novo.

A ordem tem motivo: o passo 2 e o unico achado em aberto que afeta dinheiro na
mao do Credor. A jornada real, que neste ciclo encontrou cinco defeitos que
nenhuma suite com mock encontrou, agora roda verde e passa a ser a rede de
seguranca das proximas mudancas.

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
| 1.2.0 | 2026-08-20 | IMP-311 executado: jornada real reescrita para o emprestimo livre e verde em 8/8 contra stack real. Achado novo do valor ambiguo do wizard registrado como IMP-329. |
| 1.1.0 | 2026-08-20 | IMP-328 executado: `parcela_id` sai do contrato e do dominio, fechando o 500 da apropriacao. Snapshot, matriz e gates atualizados. |
| 1.0.0 | 2026-08-20 | Fechamento do ciclo do emprestimo livre (PLAN-027 parcial, PLAN-028, PLAN-029, PLAN-030), com caveats e pendencias declaradas. |
