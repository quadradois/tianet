# PLAN-030-EXEC - Backlog do Emprestimo Livre

**ID:** PLAN-030-EXEC

**Versao:** 1.4.0

**Status:** IMP-321..327 concluidos; PLAN-030 encerrado

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
- **Status:** Concluido no Resumo da Carteira, que alimenta o Inicio e os
  Relatorios. Fila de Cobranca e Agenda seguem no IMP-326.
- **Nota de execucao:** `parcelas_previstas` e `parcelas_vencidas` deram lugar a
  `acertos_pendentes`, e `total_previsto` — que vinha do plano e viraria zero —
  deu lugar a `principal_a_receber`: o que saiu menos o que ja voltou como
  amortizacao. Na tela, "Acertos pendentes" e "Ainda na rua".
- **Nomenclatura deliberada:** o metodo do agregado chama-se
  `acerto_sem_pagamento_em`, e nao "inadimplente". Julgar se os juros do periodo
  foram quitados exige o saldo, e saldo e do Motor, que esta camada e proibida
  de importar. Um pagamento parcial tira o emprestimo da fila — limitacao
  conhecida, com teste proprio que a documenta. A fila diz **quem** procurar; o
  valor exato vem do saldo quando o operador abre a operacao.
- **Defeito encontrado pela jornada real:** o validador de forma dos BFFs de
  Inicio e Relatorios ainda exigia os campos antigos, e rejeitava o payload
  inteiro. Unidade, componente e BFF passaram verdes porque seus fixtures foram
  atualizados junto; quem pegou foi o Playwright contra a stack. Terceira vez
  neste ciclo que a jornada real encontra o que o mock nao encontra.

---

# 5. Fase D - Telas do emprestimo

### IMP-326 - Extrato no lugar da tabela de parcelas

- **Objetivo:** a tela do emprestimo mostra saldo de hoje, juros do periodo, o
  que ja foi pago e quanto falta.
- **Dependencias:** IMP-325.
- **Status:** Concluido na tela do emprestimo. A apropriacao de promessa segue
  no IMP-327, junto com a remocao.
- **Nota de execucao:** o painel deixou de falar em parcela. Mostra Emprestado,
  **Deve hoje**, **Juros do periodo** — o minimo do acerto — e **Proximo
  acerto**, com o dia combinado. Atraso aparece no lugar da situacao, em
  destaque, e nao escondido numa coluna. A tabela de parcelas deu lugar ao
  extrato: quanto ainda esta emprestado, quanto de juros correu e o total.
- **Contrato:** `EmprestimoResponse` ganhou `dia_de_acerto`,
  `proximo_acerto_em` e `acerto_pendente_desde`. Aditivo; 108 operacoes e 137
  schemas inalterados. Os tres sao **derivados na leitura**, nao colunas: o
  proximo acerto anda com o calendario, e uma coluna gravada envelheceria em
  silencio a cada mes. No replay de idempotencia sao recalculados pelo mesmo
  motivo — gravar congelaria a data no dia em que a chave foi usada.
- **Decisao de projeto:** a data do acerto vem do backend em vez de ser
  calculada no navegador. Calcular calendario no frontend duplicaria uma regra
  de dominio, com dois lugares para divergir.

---

# 6. Fase E - Remocao

### IMP-327 - O plano de parcelas sai

- **Objetivo:** remover agregado, tabela, operacao do contrato e testes.
- **Dependencias:** IMP-326.
- **Criterios de conclusao:** nenhum arquivo legado; o inventario deixa de ser
  108/137 e o novo valor e registrado; `test_motor_juros_base.py` sai junto,
  porque descreve um calculo que deixa de existir.
- **Status:** Concluido.
- **Feito nas telas:** saiu o cartao "Quanto ainda falta", que repetia o
  extrato; "Como a conta foi feita" deixou de renderizar vazio; e o comando
  "Gerar parcelas" saiu das operacoes.
- **Defeito que bloqueava o produto, encontrado ao exercitar a tela:** o Motor
  recusava pagamento e quitacao com `plano de parcelas deve ser gerado antes do
  pagamento`. No emprestimo livre nao ha plano, e o pagamento e justamente o
  evento que move a divida — a regra impedia o fluxo central. Removida das duas
  operacoes. **Nenhum teste cobria essa regra**: a suite de 999 seguiu verde
  com a remocao, o que confirma que ela nunca foi verificada.
- **Segundo defeito, mesmo caminho:** o campo de valor recusava "500,00". O
  Credor digita virgula, que e como se escreve dinheiro em portugues. A troca e
  de pontuacao, feita por texto, e o Motor continua sendo a autoridade sobre o
  valor.
- **Formulario de pagamento:** `Recebido em` era texto livre com
  `2026-08-14T12:00:00Z` fixo no codigo — data de cinco dias antes. Virou campo
  de data com hoje preenchido, resolvido no servidor. A conversao usa meio-dia
  UTC, e nao meia-noite: em America/Sao_Paulo `00:00Z` e 21h do dia anterior, e
  o pagamento mudaria de dia sozinho. `Idempotency-Key` saiu da vista — e
  protocolo, nao decisao do Credor, e o BFF ja a gera.
- **Um teste que escrevi pegou defeito meu:** a primeira versao aceitava
  `2026-13-01` porque validava so o formato. Passou a usar `isDate`, que
  verifica o calendario.
- **Verificado contra a stack real:** pagamento de R$ 500,00 digitado com
  virgula gravou `500.00` recebido, `0.00` de juros e `500.00` de amortizacao. O
  painel passou a mostrar "Deve hoje R$ 9.500,00". Juros zero esta certo — o
  emprestimo foi lancado no mesmo dia.
- **Remocao no backend:** sairam o agregado `Parcela`, o ORM, o repositorio, o
  porto, `gerar_plano_parcelas`, `_liquidar_parcelas`, `_memoria_plano` e as
  duas operacoes `POST, GET /credit/emprestimos/{emprestimo_id}/parcelas`. A
  migracao `0017_remove_plano_de_parcelas` derruba a tabela `parcela`, as quatro
  FKs que apontavam para ela e as permissoes `motor.parcela.gerar` e
  `motor.parcela.ler`, com downgrade reversivel.
- **Inventario novo, registrado:** 106 operacoes e 133 schemas (era 108/137),
  SHA-256 do snapshot
  `75a15e1f119a0fe01cbf3401a202680b0bb812f191fd1c00e5d3c9fcef123d34`; catalogo
  de permissoes 53 (era 55) e endpoints protegidos 63 (era 65). A matriz de
  rastreabilidade foi para 3.4.0: Motor de 11 para 9 operacoes, total
  certificado de 107 para 105.
- **Ultimo resto encontrado no fim:** os relatorios de vencimento do Inicio e de
  Relatorios ainda liam `parcela_id`, `numero`, `valor_previsto` e
  `valor_liquidado` — colunas de um objeto que nao existe mais. Passaram a
  mostrar acerto, situacao, dia combinado, dias sem pagamento e o emprestado. No
  fluxo diario, `previsto` — que so podia vir do plano — deu lugar a contagem de
  acertos do dia: um `previsto` alimentado por nada devolveria 0,00 em silencio,
  que num relatorio financeiro e mentira, nao lacuna.
- **Gates:** 983 testes Python, 309 testes frontend (unit/component/bff/contract),
  `ruff`/`black`/`mypy` limpos, `docs:validate` com 0 erros e o gate governado em
  173/173.

---

# 7. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.4.0 | 2026-08-19 | IMP-327 concluido: plano de parcelas removido do dominio, do banco, do contrato e dos relatorios; inventario novo 106/133 registrado e matriz em 3.4.0. PLAN-030 encerrado. |
| 1.3.0 | 2026-08-19 | IMP-327 nas telas: restos do plano removidos, formulario de pagamento operavel e duas regras que bloqueavam o fluxo central corrigidas. |
| 1.2.0 | 2026-08-19 | IMP-326 concluido na tela: painel do emprestimo livre e extrato no lugar da tabela de parcelas. |
| 1.1.0 | 2026-08-17 | IMP-325 concluido no Resumo da Carteira: acertos pendentes e principal a receber no lugar dos contadores de parcela. |
| 1.0.0 | 2026-08-17 | Backlog inicial IMP-321..327; fases A e B concluidas. |
