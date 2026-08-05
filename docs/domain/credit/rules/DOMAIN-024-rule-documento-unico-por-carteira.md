# DOMAIN-024 — Business Rule Documento Único por Carteira

**ID:** DOMAIN-024

**Versão:** 1.0.0

**Status:** Proposto

---

# 1. Identificador

BR-005

---

# 2. Descrição

O documento (CPF) do Devedor é único dentro da Carteira.

Não é permitida a existência de dois Devedores — ativos ou inativos — com o mesmo documento na mesma Carteira.

---

# 3. Motivação

A unicidade do documento é o critério objetivo de identificação civil do Devedor.

Ela impede cadastros duplicados, operações sobrepostas e inconsistências na rastreabilidade de crédito dentro da Carteira.

O documento é invariável (DOMAIN-020 INV-003) e, portanto, o critério mais estável de unicidade.

---

# 4. Regra

Antes de criar um Devedor, deve-se verificar a ausência de cadastro com o mesmo documento na mesma Carteira.

A regra aplica-se também à reativação: a reativação revalida a unicidade do documento —
não pode existir outro cadastro com o mesmo documento na mesma Carteira, em qualquer
estado (Ativo ou Inativo). Como o §2 já veda dois Devedores com o mesmo documento, esta
verificação é uma guarda defensiva contra inconsistências de dados (DOMAIN-023).

A unicidade é assegurada em duas camadas:

1. Domain (UnicidadeDevedorService — DOMAIN-023);
2. constraint UNIQUE no repositório (proteção contra corrida).

---

# 5. Exceções

| Exceção | Condição | Comportamento Diferente |
|---------|----------|-------------------------|
| Documento de outra Carteira | O documento pertence a outro Tenant/Carteira | Sem conflito — a unicidade é por Carteira |

---

# 6. Exemplos

| Situação | Aplicação da Regra | Resultado |
|----------|--------------------|-----------|
| Criar Devedor com documento inexistente na Carteira | Verificação de ausência | Válido — Devedor criado |
| Criar Devedor com documento já cadastrado (Ativo) | Verificação de presença | Inválido — 409 documento_ja_cadastrado |
| Criar Devedor com documento já cadastrado (Inativo) | Verificação de presença | Inválido — 409 documento_ja_cadastrado |
| Reativar Devedor cujo documento já existe em outro cadastro da Carteira (guarda defensiva) | Verificação de presença | Inválido — 409 documento_ja_cadastrado |

---

# 7. Histórico de Versões

| Versão | Data | Descrição |
|---------|------|-----------|
| 1.0.0 | 05/08/2026 | Primeira versão oficial da regra Documento Único por Carteira, criada no ciclo SDD do EPIC-002 (contexto Cadastro). |