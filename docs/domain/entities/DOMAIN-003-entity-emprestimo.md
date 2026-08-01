# DOMAIN-003 — Entity Empréstimo

**ID:** DOMAIN-003

**Versão:** 1.0.0

**Status:** Aprovado

**Aggregate Pai:** DOMAIN-001 — Aggregate Carteira

---

# 1. Definição

O Empréstimo representa um acordo financeiro entre o proprietário da Carteira e uma Pessoa.

Seu objetivo é registrar a entrega de um valor financeiro, as condições de devolução e acompanhar toda a sua evolução até a quitação ou encerramento.

O Empréstimo é a principal entidade operacional do domínio.

---

# 2. Identidade

Um Empréstimo possui identidade única dentro de uma Carteira.

Após sua criação, sua identidade nunca poderá ser alterada.

Todo Empréstimo pertence obrigatoriamente a uma Pessoa.

---

# 3. Responsabilidades

O Empréstimo é responsável por:

- registrar o valor emprestado;
- registrar as condições do empréstimo;
- controlar sua situação;
- possuir Parcelas;
- receber Pagamentos;
- calcular o saldo devedor;
- determinar quando está quitado;
- emitir eventos do domínio.

O Empréstimo não envia mensagens.

O Empréstimo não realiza cobranças.

Essas responsabilidades pertencem aos serviços do domínio.

---

# 4. Ciclo de Vida

## Criado

O empréstimo foi registrado.

---

## Ativo

Possui saldo devedor.

Pode receber pagamentos.

Pode possuir parcelas pendentes.

---

## Quitado

Não possui saldo devedor.

Não poderá receber novos pagamentos.

Seu histórico permanece disponível.

---

## Cancelado

Representa um empréstimo invalidado antes de produzir efeitos financeiros.

Permanece registrado para fins históricos.

---

# 5. Regras

## RN-001

Todo Empréstimo pertence exatamente a uma Pessoa.

---

## RN-002

Todo Empréstimo pertence exatamente a uma Carteira.

---

## RN-003

Todo Empréstimo deve possuir um valor inicial maior que zero.

---

## RN-004

Todo Empréstimo deve possuir pelo menos uma Parcela.

---

## RN-005

Um Empréstimo pode receber vários Pagamentos.

---

## RN-006

Um Empréstimo Quitado não poderá receber novos Pagamentos.

---

## RN-007

Todo Pagamento recebido reduz o saldo devedor.

---

## RN-008

Quando o saldo devedor atingir zero, o Empréstimo deverá assumir automaticamente o status Quitado.

---

# 6. Relacionamentos

## Aggregate

Pertence ao Aggregate:

DOMAIN-001 — Aggregate Carteira

---

## Relacionamentos

Pessoa (1)

↓

Empréstimo (0..N)

---

Empréstimo (1)

↓

Parcela (1..N)

---

Empréstimo (1)

↓

Pagamento (0..N)

---

# 7. Invariantes

## INV-001

Todo Empréstimo pertence exatamente a uma Pessoa.

---

## INV-002

Todo Empréstimo pertence exatamente a uma Carteira.

---

## INV-003

Todo Empréstimo possui pelo menos uma Parcela.

---

## INV-004

O saldo devedor nunca poderá ser negativo.

---

## INV-005

Empréstimos Quitados não recebem novos Pagamentos.

---

# 8. Glossário

## Empréstimo

Acordo financeiro registrado na Carteira.

---

## Saldo Devedor

Valor ainda pendente de pagamento.

---

## Quitação

Estado em que o saldo devedor é igual a zero.

---

# 9. Histórico de Versões

| Versão | Data | Descrição |
|---------|------------|------------------------------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial. |
