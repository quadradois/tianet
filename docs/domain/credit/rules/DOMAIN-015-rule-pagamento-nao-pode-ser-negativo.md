# DOMAIN-015 — Business Rule Pagamento não pode ser negativo

**ID:** DOMAIN-015

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Identificador

BR-002

---

# 2. Descrição

Todo Pagamento registrado na plataforma deverá possuir valor maior que zero.

A plataforma não permite registros de pagamentos negativos ou iguais a zero.

---

# 3. Motivação

Um Pagamento representa o recebimento de um valor pelo Credor.

Valores negativos ou nulos não representam um recebimento válido e podem comprometer a integridade financeira da operação.

Estornos deverão ser tratados por regras próprias, nunca através de pagamentos com valor negativo.

---

# 4. Regra

Todo Pagamento deverá possuir valor monetário maior que zero.

Caso contrário, o registro deverá ser rejeitado pelo domínio.

---

# 5. Exceções

Não existem exceções na versão 1 da plataforma.

Estornos serão tratados por processo específico.

---

# 6. Exemplos

## Válido

Pagamento de R$ 350,00.

Pagamento de R$ 0,01.

---

## Inválido

Pagamento de R$ 0,00.

Pagamento de R$ -100,00.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da regra de validação de valores de Pagamento. |
