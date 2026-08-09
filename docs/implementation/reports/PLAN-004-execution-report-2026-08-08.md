# PLAN-006 - Relatorio de Execucao PLAN-004 - 2026-08-08

**ID:** PLAN-006

**Versao:** 1.2.0

**Status:** Concluido

## Resultado

P0, P1 e P2 foram executados ate gate verde. P3 foi iniciado pelo plano tecnico
detalhado do EPIC-006/IAM e backlog executivo PLAN-005. Depois do fechamento do
EPIC-006/IAM, P4 foi concluido com CI e rotina reproduzivel de migrations, e P5
foi encerrado como planejamento do proximo ciclo pos-IAM/P4.

## P0 - Recuperacao tecnica

Concluido.

- Corrigido `Devedor.remover_contato`, removendo quebra de sintaxe.
- Regras de contato passaram a considerar apenas contatos ativos para unicidade
  e preferencial.
- Corrigido import de `ViolacaoInvarianteError` em `Usuario`.

## P1 - Soft-delete de Contato

Concluido.

- Criada migration `0006_contato_removido_em`.
- Repositorio e Application cobertos por testes de persistencia de `removido_em`.
- Atualizacao de contatos preserva linha antiga como removida e expõe apenas
  contato ativo na consulta publica.

## P2 - Recertificacao EPIC-002

Concluido com evidencia local.

- `uv run pytest`: 428 passed, 1 warning.
- `uv run ruff check src tests`: passou.
- `uv run black --check src tests`: passou.
- `uv run mypy src`: passou.
- `npm run docs:validate`: 138 OK, 48 avisos, 0 erros.
- `npm run docs:test`: 42/42 testes documentais passaram.

## P3 - EPIC-006/IAM

Iniciado.

- Criado `docs/implementation/plans/PLAN-005-epic-006-iam-detalhado.md`.
- Criado `docs/implementation/backlogs/PLAN-005-execution-backlog.md`.
- Proximo passo tecnico: implementar IMP-082..IMP-084 com suites de dominio IAM.

## P4 - Operacao

Concluido em 2026-08-09.

- Criado `.github/workflows/quality.yml` com Postgres service container,
  suite Python completa, Ruff, Black, Mypy, validacao de migrations,
  `docs:validate` e `docs:test`.
- Criado `scripts/validate_migrations.py` com trava
  `MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE=1` para executar
  `upgrade head -> downgrade base -> upgrade head` somente em banco descartavel.
- Criado `docs/operations/quality-gates-and-migrations.md`.

## P5 - Proximo ciclo de credito

Concluido em 2026-08-09.

- Criado `docs/implementation/plans/PLAN-008-proximo-ciclo-pos-iam-p4.md`.
- O proximo ciclo foi definido como Discovery/SDD do Epico 003 Comercial,
  preservando Epico 004 Contratos e Epico 005 Motor Financeiro como fases
  posteriores.
- O plano registra suites previstas, fronteiras de contexto e guardrails para
  impedir calculo financeiro fora do Motor Financeiro.

## Observacoes

- O validador documental segue com avisos historicos de referencias futuras e
  namespaces legados, mas sem erros.
- A suite Python segue com aviso externo de deprecacao do `fastapi.testclient`.

## Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.2.0 | 2026-08-09 | Fecha P5/IMP-081 com plano tecnico do proximo ciclo pos-IAM/P4. |
| 1.1.0 | 2026-08-09 | Fecha P4/IMP-079 e IMP-080 com CI e rotina reproduzivel de migrations. |
| 1.0.0 | 2026-08-08 | Registro da execucao P0-P3 e pendencias P4-P5 do PLAN-004. |
