# DOMAIN-006 — Entity Pagamento

**ID:** DOMAIN-006

**Versão:** 1.2.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

O Pagamento representa o registro financeiro de um valor recebido pelo Credor para liquidação total ou parcial de uma operação de crédito.

O Pagamento nunca executa cálculos financeiros.

Ele representa o resultado do processamento realizado pelo Motor Financeiro.

---

# 2. Identidade

Um Pagamento possui identidade única dentro de um Empréstimo.

Após seu registro sua identidade permanece imutável.

---

# 3. Responsabilidades

O Pagamento é responsável por:

- registrar a data do recebimento;
- registrar o valor recebido;
- registrar a distribuição do valor entre juros, encargos e amortização;
- registrar como devolução toda sobra que exceder a dívida;
- registrar os estornos parciais confirmados pelo Credor;
- registrar o resultado do processamento financeiro;
- compor o histórico financeiro da operação.

O Pagamento não calcula juros.

O Pagamento não calcula amortizações.

O Pagamento não altera diretamente o Empréstimo.

Essas responsabilidades pertencem exclusivamente ao Motor Financeiro.

---

# 4. Ciclo de Vida

## Recebido

O valor foi recebido pelo Credor.

---

## Processado

O Motor Financeiro distribuiu o pagamento conforme as regras da operação.

Quando o valor recebido excede a dívida, a diferença é registrada como
`valor_devolvido`, fica pendente de estorno e gera aviso ao Credor.

---

## Confirmado

O estado do Empréstimo foi atualizado.

O Pagamento passa a compor definitivamente o histórico da operação.

---

## Estornado

O registro permanece preservado para auditoria.

O estorno de sobra é parcial por valor: cada lançamento aumenta
`valor_estornado` sem apagar o valor bruto recebido nem a distribuição que
liquidou a dívida. O PIX de devolução é feito pelo Credor fora do sistema.

---

# 5. Regras

## RN-001

Todo Pagamento pertence exatamente a um Empréstimo.

---

## RN-002

Todo Pagamento possui um valor recebido maior que zero.

---

## RN-003

Todo Pagamento deverá ser processado pelo Motor Financeiro.

---

## RN-004

Todo Pagamento deverá registrar quanto foi destinado aos juros.

---

## RN-005

Todo Pagamento deverá registrar quanto foi destinado à amortização.

---

## RN-006

O Pagamento não se vincula a nenhuma obrigação previamente agendada. No
empréstimo livre não existe cronograma: o que o valor recebido liquida é
determinado pelo saldo em vigor na data, na ordem juros, encargos e principal.

---

## RN-007

Todo Pagamento deverá atualizar o estado atual do Empréstimo através do Motor Financeiro.

---

## RN-008

Quando o valor recebido superar juros, encargos e principal devidos, o Motor
deve registrar a diferença em `valor_devolvido` e solicitar aviso ao Credor.

---

## RN-009

O estorno da devolução pode ser lançado em uma ou mais partes. A soma
`valor_estornado` nunca pode superar `valor_devolvido`.

---

## RN-010

O Pagamento está operacionalmente reconciliado quando todo o valor destinado
à devolução possui estorno registrado (`valor_estornado == valor_devolvido`).

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Empréstimo (1)

↓

Pagamento (0..N)

---

Pagamento

↓

Motor Financeiro

↓

Atualiza

↓

Empréstimo

---

# 7. Invariantes

## INV-001

Todo Pagamento pertence exatamente a um Empréstimo.

---

## INV-002

O valor recebido deve ser maior que zero.

---

## INV-003

A soma dos valores destinados aos juros, encargos, amortização e devolução
deverá ser exatamente igual ao valor recebido:

`valor_juros + valor_encargos + valor_amortizacao + valor_devolvido == valor_recebido`

---

## INV-004

Todo Pagamento confirmado compõe permanentemente o histórico da operação.

---

## INV-005

Nenhum Pagamento poderá alterar diretamente o Empréstimo sem processamento do Motor Financeiro.

---

## INV-006

O valor estornado deve ser não negativo e menor ou igual ao valor destinado à
devolução. Um estorno acima da sobra pendente deve ser recusado.

---

# 8. Glossário

## Pagamento

Registro financeiro de um valor recebido para liquidação total ou parcial de uma operação.

---

## Processamento Financeiro

Execução realizada pelo Motor Financeiro para distribuir corretamente o valor recebido.

---

## Sobra

Parte do valor recebido que não encontra juros, encargos ou principal a liquidar
e, por isso, é destinada à devolução.

---

## Estorno parcial

Registro, no sistema, de uma parte ou da totalidade da devolução que o Credor
executa por PIX fora da plataforma. Não apaga o Pagamento original.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.2.0 | 23/08/2026 | Residuos de Parcela removidos: responsabilidade de liquidacao, RN-006 e o vinculo do diagrama. RN-006 passa a descrever a liquidacao pelo saldo em vigor (DR-004, IMP-337). |
| 1.1.0 | 22/08/2026 | IMP-332: sobra destinada à devolução, estorno parcial e reconciliação explícita. |
| 1.0.0 | 01/08/2026 | Primeira versão oficial da Entity Pagamento. |
