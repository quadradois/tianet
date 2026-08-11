# ADR-015: CI/CD e Gates de Qualidade

> **Status:** Aceito
> **Data:** 2026-08-11
> **Autor(es):** Arquitetura
> **Revisor(es):** Arquitetura
> **Aprovacao:** Arquitetura / 2026-08-11
> **Substitui:** —
> **Substituido por:** —

---

## Contexto

O AMP-001 classifica CI/CD ausente como divida perigosa. A equipe ja executa
gates locais para recertificar o backend, mas ainda precisa formalizar a matriz
que deve rodar em PR e em `master`.

---

## Decisao

Decidimos que o pipeline minimo do backend deve executar:

- `uv run pytest -q`;
- `uv run ruff check .`;
- `uv run black --check .`;
- `uv run mypy src tests`;
- `npm run docs:test`;
- `npm run docs:validate`;
- validacao reproduzivel de migrations.

O CI deve ser equivalente aos comandos locais. Deploy automatico, rollback
automatizado e provisionamento cloud ficam fora do EPIC-008.

---

## Alternativas Consideradas

| Opcao | Pros | Contras | Decisao |
|---|---|---|---|
| Manter validacao manual | zero setup | regressao silenciosa e dependencia de disciplina | rejeitada |
| CI minimo sem mypy/docs | rapido | deixa divida conhecida fora do gate | rejeitada |
| CI completo com deploy | cobre mais | mistura qualidade com rollout antes da hora | rejeitada |
| CI de qualidade sem deploy | foco e baixo risco | nao entrega CD ainda | escolhida |

---

## Consequencias

- PRs passam a ter criterio objetivo de qualidade.
- Comandos locais e CI precisam permanecer alinhados.
- Migrations deixam de ser validadas apenas por revisao visual.
- Deploy continua manual ate decisao futura.

---

## Validacao

- pipeline declarado no repositorio;
- suite local equivalente documentada;
- falha intencional de teste/lint/docs/migration bloqueia o gate;
- `npm run docs:test` cobre registry e contratos documentais.

---

## Referencias

- AMP-001 - ADR-015 reservada para CI/CD / Deployment Strategy;
- EPIC-008 - Fundacao Operacional e Observabilidade;
- FEATURE-032 - Automatizar Pipeline de Qualidade;
- US-089 - Executar Gates Oficiais em PR e Master;
- US-090 - Validar Migrations de Forma Reproduzivel.

---

## Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-11 | Decisao registrada para CI de qualidade sem deploy automatico. |
