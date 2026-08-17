# DR-003 — Decision Request — Base de normalizacao dos juros por periodo no Motor

**Data:** 2026-08-17
**Solicitante:** Engenharia (verificacao manual do wizard, PLAN-027)
**Destinatario:** Arquitetura / Head de Produto
**Status:** **RESOLVIDA** — 2026-08-17
**Bloqueia:** confianca no valor de cada parcela; nao bloqueia o PLAN-027

---

> ## Resolucao
>
> Decidida a **Opcao A** (secao 7): o divisor passa a ser os dias do mes a que o
> periodo pertence, e nao os do mes de vencimento. Um periodo que cobre um mes
> calendario passa a custar exatamente a taxa contratada, e apenas periodos
> parciais permanecem proporcionais.
>
> **Autorizadas as duas correcoes independentes da secao 8:** especificacao da
> convencao em documento de dominio, com exemplo numerico, e teste de valor
> sobre um plano conhecido. Sem elas, qualquer mudanca futura da formula volta a
> passar despercebida — que e o achado mais grave desta DR.
>
> **Os 9 emprestimos do ambiente local sao dados de teste e podem ser
> descartados.** Nao ha recalculo a fazer: o sistema nao esta implantado, e o
> alcance em producao e zero.
>
> **Executada em:** PLAN-028.
>
> O conteudo abaixo e preservado como registro da analise que motivou a decisao.

---

## 1. Objeto da decisao

**Qual mes deve normalizar os juros de um periodo: o mes em que a parcela vence,
ou o mes a que o periodo pertence?**

Hoje o Motor divide pelos dias do **mes de vencimento**, enquanto o numerador
conta os dias do **periodo**, que caem quase todos no mes anterior. A decisao
define se isso e convencao deliberada ou defeito.

---

## 2. Por que a decisao e necessaria agora

O Credor percebeu a oscilacao ao conferir um lancamento real e perguntou o
motivo. A explicacao existe, mas nao havia sido registrada em lugar nenhum, e a
regra nunca foi confrontada com o que "5% ao mes" significa para quem empresta.

Nenhuma implementacao foi alterada.

---

## 3. A formula atual

`src/emprestimo/domain/credit/motor_financeiro.py:622`

```python
dias_do_calendario = Decimal(
    calendar.monthrange(periodo.data_fim.year, periodo.data_fim.month)[1]
)
return _quantizar(principal * taxa_mensal * Decimal(periodo.dias) / dias_do_calendario)
```

Regra declarada na memoria de calculo: `juros_simples_periodo_real`, versao
`1.0.0`.

---

## 4. Evidencia observada

Emprestimo real: R$ 10.000,00 em 10 parcelas, 5% ao mes, lancado em 17/08/2026,
primeiro vencimento em 01/09/2026. Base de cada parcela: R$ 1.000,00 de
principal, portanto R$ 50,00 por mes cheio.

| # | Periodo | Dias | Vence em | Dias do mes | Juros |
|---|---|---:|---|---:|---:|
| 1 | 17/08 → 01/09 | 15 | set | 30 | 25,00 |
| 2 | 01/09 → 01/10 | 30 | out | 31 | 48,39 |
| 3 | 01/10 → 01/11 | 31 | nov | 30 | 51,67 |
| 4 | 01/11 → 01/12 | 30 | dez | 31 | 48,39 |
| 5 | 01/12 → 01/01 | 31 | jan | 31 | 50,00 |
| 6 | 01/01 → 01/02 | 31 | **fev** | **28** | **55,36** |
| 7 | 01/02 → 01/03 | **28** | mar | 31 | **45,16** |
| 8 | 01/03 → 01/04 | 31 | abr | 30 | 51,67 |
| 9 | 01/04 → 01/05 | 30 | mai | 31 | 48,39 |
| 10 | 01/05 → 01/06 | 31 | jun | 30 | 51,67 |

**A aritmetica esta correta.** As dez foram recalculadas de forma independente,
com `Decimal` e o mesmo arredondamento, e todas conferem exatamente com a
formula. Nao ha erro de conta.

### 4.1 O que a formula produz

A parcela 6 cobre **01/01 a 01/02**: 31 dias, todos dentro de janeiro, que tem
31 dias. E **exatamente um mes**. Mas o divisor e fevereiro, com 28 dias:
`31/28 = 1,107`. O periodo e cobrado como **1,107 mes**.

A parcela 7 faz o inverso: fevereiro inteiro (28 dias) dividido por marco (31)
resulta em `0,903` — **0,903 mes** por um mes corrido.

Ou seja: **um mes cheio quase nunca custa um mes de juros.** Das dez parcelas,
apenas a quinta cai em 50,00, e por coincidencia de dezembro e janeiro terem 31
dias ambos.

### 4.2 Comparacao com a alternativa

Normalizando pelos dias do mes a que o periodo pertence:

| | Formula atual | Mes do periodo |
|---|---|---|
| Parcelas 2 a 10 | oscila entre 45,16 e 55,36 | **50,00 em todas** |
| Parcela 1 (15 dias) | 25,00 | 24,19 |
| Total de juros | 475,70 | 474,19 |

Todo mes cheio passa a custar exatamente a taxa contratada, e apenas periodos
parciais sao proporcionais.

---

## 5. O achado mais grave nao e o numero

**A regra nao tem especificacao e nao tem teste.**

- Procura por convencao documentada em `docs/domain/` e `docs/product/` nao
  retornou nada: nenhuma mencao a base 30/360, actual/365, actual/actual, nem a
  qual mes normaliza.
- Nenhum teste unitario fixa o valor de juros de uma parcela. Os testes cobrem
  tipos, periodicidade e estrutura da regra — nunca o resultado.
- A linha entrou em `e582c09` (2026-08-10), no commit que implementou Contratos
  e Motor, sem justificativa registrada.

Uma regra financeira de EPIC certificado sem especificacao e sem teste de valor
significa que qualquer alteracao futura passa despercebida, e que ninguem pode
afirmar se o comportamento atual e o pretendido.

Ha ainda uma pista de que a base foi prevista e nao implementada:
`RegraCalculo` aceita `parametros={"base": "dias_reais"}`, mas a geracao do
plano nao le esse campo e a memoria de calculo nao o registra.

---

## 6. Alcance

| Item | Valor |
|---|---|
| Emprestimos no ambiente local | 9 |
| Parcelas geradas | 46 |
| Parcelas cujo valor mudaria | 44 |

Em producao o alcance e zero: o sistema ainda nao foi implantado. **Esta e a
janela barata para decidir** — depois de operar com clientes reais, mudar a
formula exige recalculo e comunicacao a devedores.

---

## 7. Opcoes

### Opcao A — Normalizar pelo mes do periodo

Divisor passa a ser os dias do mes de `data_inicio`. Mes cheio custa exatamente
a taxa contratada; periodo parcial e proporcional.

- Alinha o numero ao que "5% ao mes" significa para o Credor e para o devedor.
- Elimina a oscilacao sem eliminar a proporcionalidade real de dias.
- **Custo:** altera EPIC-005 certificado e o valor de todo emprestimo ja gerado.

### Opcao B — Base fixa de 30 dias (30/360)

`juros = principal × taxa × dias / 30`. Convencao comercial classica no Brasil.

- Simples de explicar: cada dia vale 1/30 da taxa mensal.
- Mes de 31 dias custa 1,033 mes; fevereiro custa 0,933.
- **Custo:** mesma alteracao de EPIC-005; mantem oscilacao, porem previsivel e
  explicavel.

### Opcao C — Manter e documentar

A formula atual vira convencao declarada, com especificacao em DOMAIN e testes
de valor fixando as dez parcelas do exemplo.

- Nao altera nenhum valor ja gerado.
- **Custo:** mantem o efeito de cobrar 1,107 mes por um mes corrido em janeiro,
  que e dificil de justificar a um devedor.

---

## 8. Recomendacao da Engenharia

**Opcao A**, com especificacao em DOMAIN e testes de valor obrigatorios.

Fundamento: a taxa e contratada em "por mes". Um periodo que cobre exatamente um
mes calendario deve custar exatamente essa taxa, e a formula atual so entrega
isso por coincidencia. Normalizar pelo mes do proprio periodo preserva a
proporcionalidade por dias reais — que e o proposito da regra
`juros_simples_periodo_real` — sem medir um mes com a regua de outro.

**Independente da opcao escolhida**, duas correcoes sao obrigatorias e nao
dependem desta decisao:

1. especificar a convencao em documento de dominio, com exemplo numerico;
2. criar teste de valor fixando os juros de um plano conhecido, para que
   qualquer mudanca futura falhe visivelmente.

---

## 9. Encaminhamento apos a decisao

1. Registrar a decisao, com ADR se Arquitetura entender cabivel;
2. especificar a convencao em `docs/domain/credit/`;
3. emitir teste de valor sobre um plano conhecido;
4. se A ou B, emitir IMP de alteracao do Motor e avaliar recalculo dos
   emprestimos existentes no ambiente local;
5. expor a memoria de calculo em linguagem comum na interface — o dado ja existe
   e hoje aparece como JSON colapsado.

---

## 10. Decisao pedida (sintese)

1. Adota-se A, B ou C?
2. Autoriza-se especificacao e teste de valor da regra, independente da opcao?
3. Os emprestimos ja gerados no ambiente local devem ser recalculados ou
   descartados?

---

## 11. Historico de Versoes

| Versao | Data | Descricao |
|---------|------|-----------|
| 1.0.0 | 17/08/2026 | Abertura — base de normalizacao dos juros por periodo, ausencia de especificacao e de teste de valor. |
| 1.1.0 | 17/08/2026 | Resolvida pela Opcao A, com especificacao e teste de valor autorizados e descarte dos dados de teste. Execucao em PLAN-028. |
