# PLAN-030-EXEC - Backlog do Emprestimo Livre

**ID:** PLAN-030-EXEC

**Versao:** 1.0.0

**Status:** IMP-321..324 concluidos; IMP-325..327 planejados

---

# 1. Contexto

Ordem executavel do PLAN-030. A numeracao continua apos IMP-320, ultimo item do
PLAN-029.

---

# 2. Fase A - Motor e dominio

### IMP-321 - Acumulacao de juros por trecho

- **Objetivo:** os juros acumulam sobre o saldo em vigor em cada trecho, e nao
  sobre o saldo de hoje aplicado a toda a historia.
- **Marcos:** cada pagamento (muda o saldo) e cada virada de mes (muda a base de
  normalizacao, `DOMAIN-030`).
- **Status:** Concluido.
- **Nota de execucao:** um mes depois de amortizar 4.500 de 10.000, o sistema
  pedia 41,13 onde devia pedir 275,00. O marco de virada de mes nao estava
  previsto e apareceu porque o teste cobriu o caso sem pagamento nenhum: dois
  meses cheios custavam 983,87 em vez de 1.000,00.
- **Regra de atraso:** verificada sem codigo adicional. A acumulacao vale ate
  qualquer data, entao atraso e apenas mais dias do mesmo juro. Nove dias apos
  o acerto de 500,00, o devido e 650,00, com encargos em zero.

### IMP-322 - Regra de calendario do acerto

- **Objetivo:** dado um dia do mes, saber quando cai o proximo acerto.
- **Componentes:** `domain/credit/dia_de_acerto.py`.
- **Status:** Concluido.
- **Nota de execucao:** vive fora do Motor de proposito — quem pergunta e
  Cobranca, Agenda e Operacao Diaria, e o guardrail proibe esses contextos de
  importarem `motor_financeiro`. Como e calendario e nao dinheiro, nao foi
  preciso abrir excecao.
- **Casos fixados:** emprestimo antes do dia acerta no mesmo mes; depois, no
  seguinte; no proprio dia, no seguinte, porque periodo de zero dia nao tem
  juros; dia 31 cai em 28/02 e em 29/02 no ano bissexto, sem escorregar para
  marco — se escorregasse, fevereiro ficaria sem acerto.

### IMP-323 - O Emprestimo conhece o proprio dia

- **Objetivo:** `dia_de_acerto`, `proximo_acerto_em` e `acerto_vigente_em`.
- **Status:** Concluido.
- **Nota de execucao:** `acerto_vigente_em` e a base do atraso da fase C.
  Ausencia de dia e estado **legitimo** ate a remocao do plano: tratar como
  violacao quebraria todo emprestimo ja existente. Sem migracao —
  `parametros_financeiros` ja e JSON.

---

# 3. Fase B - Lancamento e wizard

### IMP-324 - O emprestimo nasce livre

- **Objetivo:** o lancamento cria o Emprestimo sem plano de parcelas e o wizard
  pergunta o dia do acerto.
- **Componentes:** `application/lancamento.py`,
  `application/motor_financeiro.py`, schemas e rota do lancamento, snapshot
  OpenAPI, cliente tipado, wizard e camada BFF.
- **Status:** Concluido.
- **Nota de execucao:** nao ha plano a gerar. O que o devedor deve em cada
  acerto e calculado na consulta, sobre o saldo daquele dia — fixar isso num
  plano seria congelar um valor que muda a cada amortizacao. O
  `proximo_vencimento_em` do emprestimo passa a guardar o primeiro acerto, o que
  da a fase C uma ancora consultavel sem mudanca de schema.
- **Contrato:** primeira alteracao **nao aditiva** do repositorio. Campos
  exigidos sairam. O hash do snapshot foi avancado deliberadamente em 14
  arquivos e publicado no relatorio do PLAN-026, ao lado dos dois hashes
  anteriores. Contagem inalterada: 108 operacoes, 137 schemas.
- **Wizard:** "Quantidade de parcelas" e "Primeiro vencimento" deram lugar a
  "Dia do acerto", com a explicacao de que a cada acerto o devedor deve, no
  minimo, os juros do periodo.

---

# 4. Fase C - Operacao diaria

### IMP-325 - Cobranca, Agenda, Inicio e Relatorios trocam a ancora

- **Objetivo:** "acerto vencido" no lugar de "parcela vencida".
- **Dependencias:** IMP-323, IMP-324.
- **Risco:** o maior do plano — tres epicos certificados.
- **Status:** Planejado.

---

# 5. Fase D - Telas do emprestimo

### IMP-326 - Extrato no lugar da tabela de parcelas

- **Objetivo:** a tela do emprestimo mostra saldo de hoje, juros do periodo, o
  que ja foi pago e quanto falta.
- **Dependencias:** IMP-325.
- **Status:** Planejado.

---

# 6. Fase E - Remocao

### IMP-327 - O plano de parcelas sai

- **Objetivo:** remover agregado, tabela, operacao do contrato e testes.
- **Dependencias:** IMP-326.
- **Criterios de conclusao:** nenhum arquivo legado; o inventario deixa de ser
  108/137 e o novo valor e registrado; `test_motor_juros_base.py` sai junto,
  porque descreve um calculo que deixa de existir.
- **Status:** Planejado.

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-17 | Backlog inicial IMP-321..327; fases A e B concluidas. |
