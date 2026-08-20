# PLAN-028-EXEC - Backlog da Base de Normalizacao dos Juros

**ID:** PLAN-028-EXEC

**Versao:** 1.0.0

**Status:** IMP-312..314 concluidos

---

# 1. Contexto

Ordem executavel do PLAN-028. A numeracao continua apos IMP-311, ultimo item do
PLAN-027.

A ordem importa: o teste de valor (IMP-312) precede a mudanca da formula
(IMP-313) para que falhe sobre o comportamento antigo. Um teste escrito depois
apenas fixa o que ja passa e nao demonstra nada.

---

# 2. Fase A - Verificacao antes da correcao

### IMP-312 - Teste de valor da base de normalizacao

- **Objetivo:** fixar os juros de um plano conhecido, para que qualquer
  alteracao futura da formula falhe visivelmente.
- **Arquivo:** `tests/unit/domain/test_motor_juros_base.py`
- **Cobertura:** mes calendario cheio custa exatamente a taxa contratada;
  fevereiro e meses de 31 dias nao alteram esse custo; periodo parcial permanece
  proporcional aos dias reais.
- **Criterio de aceite:** o teste **falha** contra a formula antiga, com
  `Decimal('451.61') != Decimal('500.00')` para fevereiro normalizado por marco.
- **Status:** concluido — falhou como esperado antes do IMP-313.

---

# 3. Fase B - Correcao

### IMP-313 - Divisor passa a ser o mes do periodo

- **Objetivo:** `motor_financeiro.py::_calcular_juros` normaliza por
  `periodo.data_inicio`, e nao por `periodo.data_fim`.
- **Efeito:** periodo que cobre um mes calendario custa exatamente a taxa
  contratada; periodo parcial permanece proporcional.
- **Restricao:** apenas o divisor muda. Nao alterar quantizacao, periodicidade,
  geracao do plano nem a memoria de calculo.
- **Criterio de aceite:** IMP-312 verde e suite completa sem regressao.
- **Status:** concluido — 967 testes passam.

### IMP-314 - Especificacao da convencao e descarte dos dados de teste

- **Objetivo:** registrar a convencao como artefato de dominio e limpar o
  ambiente local.
- **Entregas:**
  1. `docs/domain/credit/rules/DOMAIN-030-rule-base-de-normalizacao-dos-juros.md`
     com formula, fundamento, exemplo numerico das 10 parcelas e invariantes;
  2. descarte dos 9 emprestimos e 46 parcelas do ambiente local, gerados sob a
     convencao antiga (autorizado na Resolucao da DR-003);
  3. registro do namespace `DOMAIN` avancado para 30 e `PLAN` para 28.
- **Criterio de aceite:** `npm run docs:validate` com 0 erros; contagem de
  emprestimos no ambiente local igual a zero.
- **Status:** concluido.

---

# 4. Gates de conclusao

| Gate | Resultado |
|---|---|
| `uv run pytest -q` | 967 passam |
| `ruff` / `black --check` / `mypy src tests` | limpos |
| `npm run docs:validate` | 0 erros |
| `git diff --check` | limpo |

---

# 5. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.0.0 | 2026-08-17 | Backlog do PLAN-028: teste de valor, correcao do divisor, especificacao DOMAIN-030 e descarte dos dados de teste. |
