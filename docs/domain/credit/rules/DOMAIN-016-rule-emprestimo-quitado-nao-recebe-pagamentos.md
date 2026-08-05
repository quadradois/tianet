# DOMAIN-016 — Business Rule Empréstimo Quitado não Recebe Pagamentos

**ID:** DOMAIN-016

**Versão:** 1.0.0

**Status:** Aprovado

---

# 1. Identificador

BR-003

---

# 2. Descrição

Uma operação de crédito que esteja no estado **Quitado** não poderá receber novos pagamentos.

Qualquer tentativa de registrar um novo Pagamento deverá ser rejeitada pelo domínio.

---

# 3. Motivação

Um Empréstimo Quitado representa uma operação cuja obrigação financeira foi integralmente cumprida.

Permitir novos pagamentos comprometeria a consistência financeira da operação e poderia gerar saldos negativos ou registros incorretos.

Caso seja necessário corrigir uma operação quitada, deverá ser utilizado um processo específico de estorno ou ajuste operacional.

---

# 4. Regra

Sempre que um novo Pagamento for solicitado, o domínio deverá verificar o estado atual do Empréstimo.

Se o estado for **Quitado**, o registro do Pagamento deverá ser recusado.

---

# 5. Exceções

Não existem exceções na versão 1 da plataforma.

Processos de estorno, correção ou reabertura de operações serão tratados por funcionalidades específicas em versões futuras.

---

# 6. Exemplos

## Válido

Empréstimo Ativo recebe um novo Pagamento.

---

## Inválido

Empréstimo Quitado recebe um novo Pagamento.

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 01/08/2026 | Primeira versão oficial da regra que impede pagamentos em operações quitadas. |
