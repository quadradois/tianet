# DOMAIN-025 — Business Rule Exclusão Física Proibida do Devedor

**ID:** DOMAIN-025

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Identificador

BR-006

---

# 2. Descrição

Um Devedor nunca é excluído fisicamente da base.

Quando não deve mais originar operações, o Devedor é inativado; seu histórico cadastral e financeiro permanece integralmente preservado.

---

# 3. Motivação

O Devedor é origem de operações de crédito (DOMAIN-003 RN-002) e centro de rastreabilidade.

A exclusão física quebraria a cadeia histórica de Contratos, Empréstimos e Pagamentos, violando a auditoria append-only (ADR-002) e o princípio de preservação do histórico (DOMAIN-002 RN-005/RN-006).

---

# 4. Regra

Nenhuma operação de remoção física de Devedor é permitida.

O ciclo de vida do cadastro encerra em estado Inativo, nunca em ausência do registro.

A inativação não altera o histórico cadastral nem financeiro.

---

# 5. Exceções

| Exceção | Condição | Comportamento Diferente |
|---------|----------|-------------------------|
| Correção de cadastro indevido | Erro administrativo comprovado | Tratamento administrativo auditado; nunca exclusão física |
| Reativação | Devedor Inativo volta a operar | Transição Inativo → Ativo (DOMAIN-020 INV-005) |

---

# 6. Exemplos

| Situação | Aplicação da Regra | Resultado |
|----------|--------------------|-----------|
| Devedor encerra relacionamento | Inativação | Estado Inativo; histórico preservado |
| Tentativa de DELETE de Devedor | Verificação da regra | Bloqueado — exclusão física não existe |
| Devedor inativo volta a operar | Reativação | Estado Ativo; mesmo documento e histórico |

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da regra Exclusão Física Proibida do Devedor, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |