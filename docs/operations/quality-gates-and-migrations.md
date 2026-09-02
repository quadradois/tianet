# Quality Gates e Validacao de Migrations

**Versao:** 1.0.0

**Status:** Aprovado

---

# 1. Objetivo

Este runbook define como reproduzir localmente os gates do backend e a rotina
destrutiva de validacao de migrations criada no P4/IMP-079 e IMP-080.

---

# 2. Pre-condicoes

- PostgreSQL local saudavel em `localhost:5432`, conforme `docker-compose.yml`.
- `DATABASE_URL` apontando para um Postgres **local** — o mesmo do
  `docker-compose.yml` serve. O banco descartavel e derivado dele
  (`<nome>_test`) e criado automaticamente: nao e preciso provisionar container
  nem banco separado a mao, e a stack de desenvolvimento **nao e tocada** (ver
  `ambiente-local-docker.md` §7.1). Host remoto e recusado com erro nomeado.
- `JWT_SECRET_KEY` definido para os testes de autenticacao.

Para iniciar o banco local:

```bash
docker compose up -d postgres
```

---

# 3. Gates de Qualidade

Execute os mesmos comandos usados pelo CI:

```bash
uv run pytest -q
uv run ruff check .
uv run black --check .
uv run mypy src tests
npm run docs:validate
npm run docs:test
npm run quality:migrations
```

---

# 4. Validacao de Migrations

A rotina de migrations executa:

```text
upgrade head -> downgrade base -> upgrade head
```

Ela apaga o schema durante o downgrade e deve rodar apenas em banco descartavel.
Para executar:

```bash
MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE=1 npm run quality:migrations
```

No PowerShell:

```powershell
$env:MIGRATION_VALIDATION_ALLOW_DESTRUCTIVE = "1"
npm run quality:migrations
```

---

# 5. CI

O workflow `.github/workflows/quality.yml` executa:

- suite Python completa;
- Ruff;
- Black em modo check;
- Mypy;
- ciclo destrutivo de migrations em PostgreSQL descartavel via `npm run quality:migrations`;
- validacao e testes documentais.

---

# 6. Historico de Versoes

| Versao | Data | Descricao |
|--------|------|-----------|
| 1.0.0 | 2026-08-09 | Runbook inicial dos gates de qualidade e validacao destrutiva de migrations. |
| 1.1.0 | 2026-08-11 | EPIC-008 formaliza `npm run quality:migrations` como gate oficial do CI. |
