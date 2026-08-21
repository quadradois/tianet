# Contribuindo

## Gates de qualidade locais (antes de abrir o PR)

O CI valida tudo, mas é melhor pegar erros antes de subir. Há dois gates
locais que rodam automaticamente após um comando one-time:

- **pre-commit** (rápido): `docs:validate` + frontend `lint` + `typecheck`
- **pre-push** (pesado): frontend `build` + `test:unit` + `test:component`

Ative com:

```bash
npm run docs:hooks
```

Isso roda `git config core.hooksPath hooks` — os scripts ficam em `hooks/`
(`pre-commit` e `pre-push`). Depois disso, todo commit e todo push passam
pelas checagens acima antes de qualquer coisa chegar ao GitHub.

Alternativamente, quem já usa o pre-commit framework cobre Python + frontend
lint/typecheck com:

```bash
uv run pre-commit run --all-files
```

(as suítes Playwright/e2e ficam no CI de propósito — precisam de browser)

O CI continua sendo a confirmação final; o gate local apenas evita o
round-trip de um run quebrado por erro de lint/typecheck/build.
