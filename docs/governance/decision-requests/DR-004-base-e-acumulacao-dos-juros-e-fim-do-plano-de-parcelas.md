# DR-004 — Decision Request — Base e acumulacao dos juros, e fim do plano de parcelas

**Data:** 2026-08-17
**Solicitante:** Credor (conferencia do plano gerado na stack local)
**Destinatario:** Arquitetura / Head de Produto
**Status:** **RESOLVIDA** — 2026-08-17
**Bloqueia:** o valor de todo emprestimo; o modelo operacional do produto

---

> ## Resolucao
>
> **O modelo passa a ser o emprestimo livre.** O devedor toma o valor, e na data
> de pagamento combinada pede a atualizacao; o sistema calcula os juros do
> periodo sobre o saldo devedor, o devedor paga o quanto puder, e o sistema
> separa juros de amortizacao. Repete ate quitar.
>
> **Todo emprestimo tem data de pagamento.** Decisao do Credor, e ela preserva a
> ancora de que Cobranca, Agenda e Inicio dependem (secao 6).
>
> **O plano de parcelas sai de cena, sem deixar arquivo legado.**
>
> **Ordem de execucao decidida: o operacional primeiro.** A correcao da
> acumulacao (secao 5) antecede a remocao do plano, porque e ela que torna o
> modelo livre correto e nao depende de remover nada.
>
> **Executada em:** PLAN-030.

---

## 1. Objeto da decisao

Duas perguntas, encontradas na mesma conferencia:

1. **Sobre qual base incidem os juros?**
2. **O produto e um plano de parcelas ou um emprestimo livre?**

---

## 2. Como apareceu

O Credor conferiu o plano de um emprestimo de R$ 10.000,00 a 5% ao mes em 10
parcelas e observou que o total de juros era de R$ 474,19 — cerca de 5% do
principal em dez meses, e nao 5% ao mes.

---

## 3. Defeito 1 — juros sobre a fatia de amortizacao

`src/emprestimo/domain/credit/motor_financeiro.py:157`

```python
juros = _calcular_juros(
    principal=principal,      # <- fatia de amortizacao (1.000), nao o saldo
    taxa_mensal=taxa,
    periodo=periodo,
)
```

`principal` e `principal_original / quantidade_parcelas`. A taxa incide sobre a
parcela de amortizacao, nao sobre o que o devedor ainda deve.

| | Hoje | Sobre saldo devedor |
|---|---:|---:|
| Parcela 1 (15 dias) | 24,19 | 241,94 |
| Parcelas 2 a 9 | 50,00 | 450,00 → 100,00 |
| **Total de juros** | **474,19** | **2.491,94** |

O Credor recebe **R$ 2.017,75 a menos** por operacao de R$ 10.000,00, e a
distorcao cresce com o numero de parcelas.

---

## 4. Falha de verificacao admitida

A DR-003 concluiu que "a aritmetica esta correta — as dez foram recalculadas de
forma independente e todas conferem". A afirmacao era verdadeira **para a
formula como escrita**: aquela DR perguntou *qual mes normaliza* e nunca
perguntou *sobre qual base incide*.

Pior: o teste de valor criado no PLAN-028
(`tests/unit/domain/test_motor_juros_base.py`) fixa `50,00` nas nove parcelas
cheias. Ele **congelou o defeito** e foi apresentado como protecao.

Como o plano de parcelas sai de cena, esse teste sera **removido junto**, e nao
corrigido: ele descreve um calculo que deixa de existir. Ele permanece verde ate
la porque a correcao da acumulacao (secao 5) atua no caminho do saldo, e a base
errada da secao 3 vive no caminho do plano.

Licao registrada: um teste de valor prova que o numero nao muda sem aviso; nao
prova que o numero esta certo. Fixar resultado sem confrontar a regra com o que
o negocio espera apenas torna o erro estavel.

---

## 5. Defeito 2 — acumulacao recalcula a historia sobre o saldo atual

`src/emprestimo/domain/credit/motor_financeiro.py:503`

```python
data_inicio = emprestimo.criado_em.date()
periodo = PeriodoFinanceiro(data_inicio=data_inicio, data_fim=data_referencia)
return _calcular_juros(principal=principal, ...)   # principal = saldo de HOJE
```

A acumulacao mede sempre da criacao ate a data de referencia, aplicando o saldo
**atual** sobre **todo** o periodo decorrido. Cada amortizacao devolve
retroativamente juros ja corretamente cobrados.

Simulacao contra o Motor real — R$ 10.000,00 em 01/08, 5% ao mes:

| Momento | principal | juros | veredito |
|---|---:|---:|---|
| 01/09, antes de pagar | 10.000,00 | 500,00 | correto |
| pagamento de 5.000,00 | — | 500,00 juros + 4.500,00 amortizacao | correto |
| 01/09, apos o pagamento | 5.500,00 | 0,00 | correto |
| **01/10, um mes depois** | 5.500,00 | **41,13** | **deveria ser 275,00** |

`41,13 = 5.500 × 5% × 61/31 − 500`. O primeiro mes e recobrado sobre 5.500 em
vez de 10.000.

**A base do caminho de saldo ja esta certa** — usa o saldo devedor. O que esta
errado e o intervalo: falta acumular **por trecho entre eventos que mudam o
saldo**.

---

## 6. Alcance de remover o plano de parcelas

| Camada | Alcance |
|---|---|
| Backend | 24 arquivos, 528 ocorrencias |
| Testes backend | 95 arquivos |
| Frontend | 25 arquivos |
| Contrato | 1 operacao e 4 schemas saem; o inventario deixa de ser 108/137 |
| Banco | 4 tabelas com FK para `parcela`: `cobranca_acao`, `comunicacao_registro`, `promessa_pagamento`, `promessa_apropriacao` |

**Sem parcela nao existe "vencimento", e vencimento e o gatilho da operacao
diaria.** A fila de Cobranca se forma de parcela vencida; Agenda e lembretes
disparam por data de vencimento; os Relatorios contam `parcelas_previstas` e
`parcelas_vencidas`; o Inicio lista as parcelas do dia; a Promessa de pagamento
aponta para a parcela que cobre.

Remover o plano sem substituto deixaria EPIC-008, 009 e 010 sem funcao: o
sistema continuaria calculando certo e ficaria mudo — incapaz de dizer quem
esta atrasado.

**A data de pagamento resolve isso.** Uma data por emprestimo, no lugar de dez
parcelas fixas, mantem a ancora de que os tres epicos dependem.

---

## 7. Divida encontrada e resolvida no caminho

**Resolvida durante a execucao.** A acumulacao passou a quebrar tambem em cada
virada de mes, e nao apenas em cada pagamento. Sem isso, dois meses cheios de um
emprestimo sem pagamento nenhum custavam 983,87 em vez de 1.000,00, por
normalizar setembro pela regua de agosto — defeito que so apareceu porque o
teste de valor cobriu o caso sem pagamento.

---

## 8. Historico de Versoes

| Versao | Data | Descricao |
|---------|------|-----------|
| 1.0.0 | 2026-08-17 | Abertura e resolucao: dois defeitos de juros, adocao do emprestimo livre com data de pagamento e fim do plano de parcelas. |
