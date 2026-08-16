# DR-002 — Decision Request — Guard de chaves financeiras do frontend versus parametros opacos do Comercial

**Data:** 2026-08-16
**Solicitante:** Engenharia (sessao de validacao local em Docker do Frontend MVP)
**Destinatario:** Arquitetura / Head de Produto
**Status:** **RESOLVIDA** — 2026-08-16
**Bloqueia:** conclusao da jornada P0 `Contrato ate pagamento` pela interface

---

> ## Resolucao
>
> Decidida a **Opcao B** (secao 7): `parseOpaqueParameters` deixa de inspecionar
> nomes de chave e passa a validar apenas que o payload e objeto JSON nao vazio
> dentro do limite de tamanho. Parametro comercial declarado opaco volta a ser
> opaco de fato.
>
> A garantia contra motor financeiro paralelo permanece integral e continua
> verificada por gate proprio: o scanner estatico
> `certifyNoFinancialEngineParallel`, que veta `.reduce(`, `parseFloat(`,
> `parseInt(`, `toFixed(` e soma sobre identificadores financeiros no frontend.
>
> **Autorizada** a correcao do defeito acessorio da secao 6 no mesmo pacote.
>
> **Postura de merge:** o PR #10 so entra com a jornada fechando pela interface,
> incluindo o cenario de jornada real ausente. Nao se mergeia matriz que declara
> observada uma jornada que nao se completa.
>
> **Sem ADR.** A numeracao ADR e governada pela tabela do AMP-001 §354, que nao
> preve este tema; emitir um identificador novo exigiria emenda previa ao AMP-001.
> A decisao fica registrada nesta DR e no backlog do PLAN-025. Caso Arquitetura
> entenda que a remocao de um controle declarado merece ADR proprio, o caminho e
> emendar o AMP-001 primeiro.
>
> **Executada em:** IMP-304 (PLAN-025).
>
> O conteudo abaixo e preservado como registro da analise que motivou a decisao.

---

## 1. Objeto da decisao

**O frontend deve inspecionar os nomes das chaves de `parametros` comerciais,
sendo que a governanca declara esses parametros opacos e o Motor Financeiro
exige um vocabulario que o guard atual bloqueia?**

Esta e uma decisao sobre a fronteira entre "o frontend nao calcula regra
financeira" e "parametros comerciais sao retorno oficial e opaco do backend".
Hoje as duas regras coexistem e se contradizem na pratica.

---

## 2. Por que a decisao e necessaria agora

O Frontend MVP esta concluido, certificado localmente e com PR aberto. Durante
a validacao manual da stack em Docker constatou-se que **nenhum operador
consegue lancar um Emprestimo ate o plano de parcelas usando apenas a
interface**. A cadeia trava na etapa Comercial.

A implementacao **nao foi alterada**. O defeito esta descrito na secao 3 e
permanece como esta, aguardando esta decisao.

---

## 3. Evidencia observada

Ambiente: stack completa em Docker (Next.js + FastAPI + PostgreSQL), conforme
`docs/operations/ambiente-local-docker.md`.

### 3.1 O guard

`frontend/src/lib/comercial/comercial-policy.ts:57`

```text
FORBIDDEN_FINANCIAL_KEYS =
  /(?:juros|mora|multa|amortiza|saldo|quitacao|renegocia|parcela|pagamento|emprestimo|memoria)/i
```

`parseOpaqueParameters` (mesmo arquivo, linha 100) descarta o objeto inteiro
quando **qualquer** chave casa com o padrao.

### 3.2 O vocabulario exigido pelo Motor

| Chave exigida | Origem | Guard do frontend |
|---|---|---|
| `valor_contratado` | `domain/credit/emprestimo.py:123` | passa |
| `principal_original` | `domain/credit/emprestimo.py:124` | passa |
| `primeiro_vencimento` | `domain/credit/motor_financeiro.py:140` | passa |
| `moeda` | `domain/credit/emprestimo.py:126` | passa |
| `quantidade_parcelas` | `domain/credit/motor_financeiro.py:131` | **bloqueada** (`parcela`) |
| `taxa_juros_mensal` | `domain/credit/motor_financeiro.py:660` | **bloqueada** (`juros`) |

Duas das chaves canonicas do proprio backend sao rejeitadas pelo frontend por
coincidencia de substring no nome.

### 3.3 Os dois caminhos, ambos sem saida

**Caminho 1 — com o vocabulario correto.** O guard rejeita; a Proposta e
enviada com `parametros: {}` e o backend responde `422`. Payload identico
enviado diretamente a API responde `201`.

**Caminho 2 — apenas com as chaves que passam no guard.** Proposta, decisao,
Contrato, assinatura, liberacao e Emprestimo respondem `201`/`200`. A geracao
do plano de parcelas falha:

```text
409 conflito_estado
Invariante EPIC-005 violada: quantidade_parcelas deve ser inteiro
```

O Emprestimo nasce sem poder virar plano de parcelas.

---

## 4. Por que os gates nao detectaram

Nao houve falha de execucao dos gates; houve ausencia de cenario na costura
entre eles.

| Suite | Submete o formulario Comercial | Backend |
|---|---|---|
| `comercial-e2e` | sim | `backend-fixture.mjs` (stub, aceita qualquer payload) |
| `jornadas-e2e` (IMP-301) | **nao** | FastAPI + PostgreSQL reais |

A unica suite contra backend real semeia os dados por
`tests/jornadas-e2e/seed_integrated.py`, no nivel Python, e usa a interface
apenas para leitura e navegacao. Nenhum cenario envia o vocabulario real do
Motor pelo formulario real ao backend real.

As duas suites passam. A composicao delas e que nao existe.

---

## 5. A tensao documental

| Fonte | Regra |
|---|---|
| Matriz de rastreabilidade, superficie Comercial | parametros sao "opacos" e o frontend "exibe somente valores retornados" |
| PLAN-025 e handoff do Backend MVP | o frontend "nao calcula juros, mora, multa, saldo, quitacao, amortizacao, renegociacao ou memoria de calculo" |
| Matriz, secao 6 (gate) | "nenhum cenario esperar calculo financeiro no frontend ou no BFF" |

O guard tenta implementar a segunda regra e, ao faze-lo por nome de chave,
viola a primeira: um parametro so e opaco se o frontend nao inspecionar seu
conteudo.

Cabe registrar a distincao que a implementacao atual nao faz: **transportar um
valor digitado pelo operador nao e calcular**. Enviar `quantidade_parcelas: 3`
nao constitui motor financeiro paralelo; nenhuma aritmetica ocorre no
frontend.

Cabe registrar tambem que o guard, como esta, **nao protege contra o risco que
nomeia**: calculo pode ser escrito com qualquer nome de variavel. A protecao
efetiva contra motor paralelo e o scanner estatico
`certifyNoFinancialEngineParallel` (`frontend/tests/certification/ui-security-boundaries.mjs:127`),
que bloqueia `.reduce(`, `parseFloat(`, `parseInt(`, `toFixed(` e soma sobre
identificadores financeiros. Esse scanner e independente do guard de chaves e
permanece integro em qualquer das opcoes abaixo.

---

## 6. Defeito acessorio, independente desta decisao

`frontend/src/lib/bff/comercial.server.ts:351` faz:

```text
const parametros = parseOpaqueParameters(...) ?? {};
```

A falha de validacao e silenciosamente convertida em objeto vazio e enviada ao
backend, que responde `422` generico. As funcoes irmas tratam o mesmo caso
corretamente, devolvendo `400` com mensagem acionavel:

- `createCommercialSimulation` — linha 335;
- `updateCommercialProposal` — linha 370.

Por ALP-001 secao 5.1 isto e bug de implementacao local, de resolucao autonoma
pelo Execution Gate. Esta registrado aqui apenas para que a correcao nao se
perca, e deve ser corrigido independentemente da opcao escolhida.

---

## 7. Opcoes

### Opcao A — Allowlist do vocabulario canonico do Motor

Manter o guard e excetuar as chaves oficiais
(`valor_contratado`, `principal_original`, `quantidade_parcelas`,
`primeiro_vencimento`, `taxa_juros_mensal`, `moeda`).

- Desbloqueia a jornada com a menor alteracao.
- Mantem um gate visivel no BFF.
- **Custo:** acopla o frontend ao vocabulario do backend. Cada novo parametro
  do Motor passa a exigir alteracao no frontend, e a allowlist institucionaliza
  a contradicao com a opacidade declarada.

### Opcao B — Remover a inspecao de chaves

`parseOpaqueParameters` passa a validar apenas que o payload e objeto JSON nao
vazio dentro do limite de tamanho, sem olhar nomes de chave.

- Elimina a contradicao: parametro opaco volta a ser opaco.
- Desacopla frontend e vocabulario do Motor.
- Garantia anti-calculo preservada pelo scanner estatico da secao 5.
- **Custo:** remove um gate declarado, o que exige registro explicito na matriz
  e no relatorio de certificacao.

### Opcao C — Renomear o vocabulario do backend

Ajustar o Motor para nomes que nao casem com o padrao.

- **Custo:** altera contrato publico ja certificado, OpenAPI, snapshot,
  migrations de dados e EPIC-005. Desproporcional ao problema.

### Opcao D — Substituir a textarea JSON por formulario tipado

Derivar campos do contrato em vez de pedir JSON cru ao operador.

- Resolve tambem a ergonomia: hoje o operador precisa conhecer o vocabulario
  interno do Motor para lancar um emprestimo.
- **Custo:** exige Discovery e provavelmente nova User Story; nao e correcao de
  defeito. Nao desbloqueia o MVP no prazo atual.

---

## 8. Recomendacao da Engenharia

**Opcao B**, acompanhada da correcao da secao 6, e com a **Opcao D registrada
como trabalho de produto subsequente**.

Fundamento: o guard de chaves nao entrega a protecao que seu nome promete
(secao 5), e a Opcao A preserva o gate apenas na aparencia, ao custo de
formalizar o acoplamento que a governanca declarou nao existir. A protecao real
contra motor paralelo ja existe e e verificada por gate proprio.

Qualquer opcao escolhida deve vir acompanhada de **um cenario de jornada real
que submeta o formulario Comercial contra o backend real** — a ausencia desse
cenario e a causa de o defeito ter atravessado a certificacao.

---

## 9. Encaminhamento apos a decisao

1. Registrar a decisao (ADR, se Arquitetura entender cabivel, dado que altera
   uma fronteira declarada do Frontend MVP);
2. Emitir os IMPs de correcao sob PLAN-025, conforme ALP-001;
3. Corrigir o defeito acessorio da secao 6 no mesmo pacote;
4. Acrescentar cenario de jornada real cobrindo a submissao do formulario
   Comercial com o vocabulario do Motor;
5. Atualizar a matriz de rastreabilidade: a superficie Comercial declara hoje
   jornada observada que, contra backend real, nao se completa;
6. Reexecutar os gates e o veredito adversarial antes de reafirmar a
   certificacao do Frontend MVP.

---

## 10. Decisao pedida (sintese)

1. Adota-se A, B, C ou D como tratamento do guard de chaves?
2. Autoriza-se a correcao do defeito acessorio da secao 6 no mesmo pacote?
3. A matriz de rastreabilidade deve receber caveat sobre a superficie Comercial
   antes do merge, ou o merge aguarda a correcao completa?

---

## 11. Historico de Versoes

| Versao | Data | Descricao |
|---------|------|-----------|
| 1.0.0 | 16/08/2026 | Abertura da Decision Request — guard de chaves financeiras versus parametros opacos do Comercial. |
| 1.1.0 | 16/08/2026 | Resolvida pela Opcao B, com correcao do defeito acessorio autorizada e merge condicionado ao fechamento da jornada. Execucao em IMP-304. |
