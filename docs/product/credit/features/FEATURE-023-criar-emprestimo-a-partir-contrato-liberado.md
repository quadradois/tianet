# FEATURE-023 - Criar Emprestimo a partir de Contrato Liberado

**ID:** FEATURE-023

**Versao:** 1.0.0

**Status:** Proposta

---

# 1. Objetivo

Criar uma operacao financeira somente a partir de `ContratoLiberadoLogico`,
preservando rastreabilidade entre contrato, devedor, carteira, tenant e
parametros financeiros congelados.

---

# 2. Valor de Negócio

Garante que toda operacao financeira tenha origem formal, auditavel e
idempotente antes de qualquer processamento do Motor.

---

# 3. Escopo

- consumir contrato liberado;
- criar Emprestimo idempotente;
- impedir duplicidade por contrato;
- validar Tenant, Carteira e Devedor;
- publicar evento de Emprestimo criado;
- registrar auditoria.

---

---

# 4. Fora do Escopo

- criar contrato;
- calcular saldo, quitacao ou parcelas completas;
- registrar pagamento.

---

# 5. User Stories

- US-063 - Criar Emprestimo a partir de Contrato Liberado;
- US-064 - Impedir Emprestimo sem Contrato Liberado.

---

# 6. Dependências

- EPIC-005 - Emprestimos, Pagamentos e Motor Financeiro;
- EPIC-004 - Contratos de Credito;
- PRODUCT-004 - Administrar Operacoes de Credito.

---

# 7. Critérios de Aprovação

- contrato liberado gera um Emprestimo;
- contrato nao liberado nao gera Emprestimo;
- contrato de outro Tenant responde 404 logico;
- mesma entrada nao cria Emprestimo duplicado;
- nenhum calculo financeiro externo ao Motor e executado.

---

# 8. Histórico de Versões

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Primeira versao da Feature Criar Emprestimo a partir de Contrato Liberado. |
