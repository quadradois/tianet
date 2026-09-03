# Ambiente Local em Docker

**Versao:** 1.1.0

**Status:** Aprovado

---

# 1. Objetivo

Subir a stack completa do TiaNet em containers para teste local ponta a ponta:
PostgreSQL, migrations, API FastAPI, worker do Scheduler e frontend Next.js.

Este runbook e o passo anterior ao deploy em servidor. O que roda aqui e a
mesma imagem que deve rodar la; o que muda esta na secao 8.

---

# 2. Topologia

| Servico | Papel | Porta publicada |
|---|---|---|
| `postgres` | PostgreSQL 16 com volume duravel | `127.0.0.1:5432` |
| `migrate` | One-shot `alembic upgrade head`; api e worker esperam ele concluir | nenhuma |
| `api` | Uvicorn com a aplicacao FastAPI | `127.0.0.1:8000` |
| `worker` | `emprestimo-scheduler-worker`, processa lembretes | nenhuma |
| `frontend` | Next.js em modo producao | `127.0.0.1:3000` via netns da `api` |

Todas as portas publicam apenas em loopback. Nenhum servico escuta na interface
publica da maquina.

## 2.1 Por que o frontend compartilha a netns da api

`frontend/src/lib/bff/session.server.ts` recusa `FRONTEND_BACKEND_URL` sem HTTPS
quando `NODE_ENV=production`, exceto para host loopback. Um endereco de rede
Docker comum (`http://api:8000`) seria recusado, e `next start` sempre roda em
producao.

A solucao e `network_mode: "service:api"`: o frontend entra na mesma network
namespace da API, entao `http://127.0.0.1:8000` e loopback de verdade — o
trafego com token nunca atravessa a rede. A checagem de seguranca continua
valendo integralmente; nada foi afrouxado.

Consequencia: a porta `3000` e declarada no servico `api`, nao no `frontend`.

---

# 3. Pre-requisitos

1. Docker com Compose v2 ou superior.
2. Arquivo `.env` na raiz com os segredos do ambiente local.

O `.env` e ignorado pelo git (`.gitignore` cobre `.env`, `*.env` e
`.secrets.local/`). Gere os valores em vez de digitar segredos previsiveis:

```bash
node -e '
const c=require("crypto"),fs=require("fs");
const b=(n)=>c.randomBytes(n).toString("base64url");
const boot=b(36);
fs.writeFileSync(".env",`APP_ENV=development
POSTGRES_PASSWORD=${b(24)}
JWT_SECRET_KEY=${b(48)}
FRONTEND_ORIGIN=http://localhost:3000
FRONTEND_SESSION_KEY_ID=local-v1
FRONTEND_SESSION_KEY=${b(32)}
PLATFORM_ADMIN_BOOTSTRAP_ENABLED=true
PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH=${c.createHash("sha256").update(boot).digest("hex")}
`);
fs.mkdirSync(".secrets.local",{recursive:true,mode:0o700});
fs.writeFileSync(".secrets.local/bootstrap-secret",boot,{mode:0o600});
'
```

`FRONTEND_SESSION_KEY` precisa ter exatamente 43 caracteres base64url (32 bytes).
Valor fora desse formato faz o BFF recusar a configuracao.

O compose usa `${VAR:?}` nas variaveis obrigatorias: se faltar segredo, ele
falha na hora com o nome da variavel, em vez de subir um servico quebrado.

---

# 4. Subir a stack

```bash
docker compose build
docker compose up -d
docker compose ps
```

A ordem e garantida por healthcheck e por
`depends_on: migrate: condition: service_completed_successfully`. A API so sobe
com o schema em `head`; o frontend so sobe com a API `healthy`.

---

# 5. Bootstrap do primeiro Administrador

O gate de bootstrap e o descrito em
`docs/operations/bootstrap-administrador-plataforma.md`. Dentro do compose, o
comando roda na imagem da API:

```bash
docker compose run --rm api emprestimo-bootstrap-plataforma \
  --tenant-identificador tianet-local \
  --tenant-nome "TiaNet Local" \
  --admin-nome "Administrador Local" \
  --admin-email admin@local.test
```

O comando pede o segredo de autorizacao e a credencial inicial por prompt, sem
eco. Nao passe segredo por linha de comando nem por variavel exportada no shell.

O Administrador criado recebe o **catalogo inteiro** de permissoes desde o
IMP-363, entao o Dashboard abre operacional — nao ha passo de seed nem criacao
de perfil para fazer depois. Ate aquele item eram apenas as cinco `tenant.*`, e
o unico usuario ficava sem conseguir operar nem se autoconceder permissao.

**Se o seu banco foi criado ANTES do IMP-363**, o perfil existente continua com
as cinco `tenant.*`, e rodar o bootstrap de novo **nao corrige**: ele e
idempotente e devolve o registro guardado sem reconceder nada. O Dashboard vai
mostrar "Sem permissao" nas secoes operacionais.

A saida e o `scripts/seed_operador_local.py` da secao seguinte, que concede o
catalogo ao usuario existente **sem apagar nada**. Nao use `docker compose down
-v` para isso: ele destroi todo o dado local acumulado para resolver um problema
de permissao que o seed resolve no lugar.

Apos criar o administrador, volte `PLATFORM_ADMIN_BOOTSTRAP_ENABLED=false` e
recrie a API.

---

# 6. Liberar as jornadas para teste manual — **apenas em banco anterior ao IMP-363**

> **Banco criado depois do IMP-363 nao precisa desta secao.** O bootstrap ja
> concede o catalogo inteiro, e o Dashboard abre operacional. Pule para a §7.

Em banco antigo, o perfil tem apenas `tenant.*`, e o unico caminho navegavel e a
administracao de Tenants — nao da para percorrer Devedores, Comercial,
Contratos, Motor ou Operacao Diaria. Nesse caso, `scripts/seed_operador_local.py`
cria um Perfil com o catalogo completo e o atribui ao usuario, **sem apagar
nada**:

```bash
docker compose run --rm -T -v "C:\emprestimo\scripts:/app/scripts:ro" api \
  python scripts/seed_operador_local.py \
    --institution tianet-local --email admin@local.test
```

No Git Bash do Windows, prefixe com `MSYS_NO_PATHCONV=1` e use caminho absoluto
no estilo Windows; caminho relativo (`./scripts`) monta um diretorio vazio.

O script recusa executar com `APP_ENV=production`. Ele existe para teste local:
em producao, Perfis sao criados pela tela de IAM com permissao minima por funcao.

Faca logout e login de novo para a sessao recarregar as Permissoes.

---

# 7. Verificacao

Checklist minima de que o ambiente esta realmente de pe:

```bash
# schema na versao head
docker compose exec -T postgres psql -U emprestimo -d emprestimo \
  -c 'select version_num from alembic_version;'

# API viva e enxergando o banco
curl -s http://127.0.0.1:8000/health

# frontend servindo
curl -s -o /dev/null -w '%{http_code}\n' http://localhost:3000/login

# worker com heartbeat recente
docker compose exec -T postgres psql -U emprestimo -d emprestimo \
  -c 'select worker_id, ultimo_heartbeat_em, lag_segundos from scheduler_worker_heartbeat;'
```

Esperado: `/health` responde `{"status":"healthy",...,"database":"healthy"}`,
`/login` responde `200`, e o heartbeat do worker tem `lag_segundos` proximo de
zero.

Verificacao de fronteira de sessao, no console do navegador ja autenticado:

```js
({ cookie: document.cookie, ls: Object.keys(localStorage) })
```

Esperado: ambos vazios. O cookie de sessao e `httpOnly` e nenhum token pode
estar acessivel ao JavaScript.

## 7.1 A suite usa banco proprio, e nao apaga mais esta stack

`tests/conftest.py` recria o schema e trunca as tabelas a cada sessao — mas
desde 2026-09-01 ele faz isso em **`emprestimo_test`**, derivado do
`DATABASE_URL` e criado sozinho. O banco `emprestimo` desta stack **nao e mais
tocado**, nem pela suite nem pelo ciclo de validacao de migrations.

Ate essa data os dois compartilhavam o mesmo banco, e rodar `pytest` apagava o
Tenant e o administrador — a API respondia 503 e o worker morria com
`relation "audit_log" does not exist`.

Se voce encontrar essa cena num banco antigo, `docker compose run --rm migrate`
**nao basta**: o schema apagado levou junto o Tenant e o administrador, e a
migration so recria tabelas vazias. A API volta a responder, mas nao ha com quem
autenticar. Rode o bootstrap depois da migration — ou recrie do zero com
`docker compose down -v`, que e mais rapido quando nao ha dado a preservar.

A `POSTGRES_PASSWORD` gerada protege contra isso por acidente: a suite usa a
credencial padrao (`emprestimo:emprestimo`) e falha a conexao em vez de
destruir dados. A falha esperada e:

```text
FATAL:  password authentication failed for user "emprestimo"
```

Para rodar a suite de integracao, suba um PostgreSQL descartavel proprio:

```bash
docker run -d --name tianet-pytest \
  -e POSTGRES_USER=emprestimo -e POSTGRES_PASSWORD=emprestimo \
  -e POSTGRES_DB=emprestimo -p 127.0.0.1:55433:5432 postgres:16

DATABASE_URL='postgresql+psycopg://emprestimo:emprestimo@127.0.0.1:55433/emprestimo' \
  uv run pytest -q

docker rm --force tianet-pytest
```

---

## 7.2 `password authentication failed` — leia isto antes de procurar a senha

**Corrigido em 2026-09-03. Esta secao fica como registro do sintoma, porque ele
enganou duas sessoes e uma rodada de review inteira.**

O erro era este, ao rodar `pytest` na maquina:

```
FATAL:  password authentication failed for user "emprestimo"
```

**A senha nunca esteve errada.** O Compose carrega o `.env` sozinho, entao a API
e o worker subiam normalmente; `pytest` na maquina **nao lia esse arquivo em
lugar nenhum** e caia na URL de convencao embutida em `session.py`, cuja senha
nao tem por que bater com a `POSTGRES_PASSWORD` que criou o container. O sintoma
apontava para credencial; o defeito era arquivo nao lido.

Custo real: o Codex nao conseguiu rodar a suite integrada ao revisar o IMP-368 e
entregou o parecer com essa lacuna declarada.

**O que mudou.** `database_url()` passou a resolver nesta ordem:

| # | Fonte | Quem usa |
|---|---|---|
| 1 | `DATABASE_URL` no ambiente | CI (workflow) e containers (Compose injeta) |
| 2 | `DATABASE_URL` no `.env` | banco fora do Compose — outro host, porta ou usuario |
| 3 | **`POSTGRES_PASSWORD` no `.env`, derivando a URL** | maquina do desenvolvedor, e o caso normal |
| 4 | `DEFAULT_DATABASE_URL` | clone limpo, sem `.env` |

O passo 3 e o conserto: **nao ha nada a configurar**. Quem tem a stack do Compose
de pe roda `uv run pytest` e funciona.

**E por que derivar em vez de pedir a URL inteira:** o `.env.example` mandava
escrever a senha **duas vezes**. Duas copias divergem — troca-se uma, esquece-se
a outra, e o mesmo erro volta com outra cara. A linha `DATABASE_URL` continua
existindo e vencendo a derivacao, mas agora e **opcional e comentada**.

A precedencia esta fixada por teste em
`tests/unit/infrastructure/test_database_url.py`, inclusive o escape de senha com
`/`, `+`, `=` e `@` — sem ele o `@` da senha corta o host ao meio e o erro passa
a falar de host inexistente, mandando quem investiga para o lado errado de novo.

**Se o erro voltar mesmo assim**, a stack e que esta divergente: o Postgres so
aplica `POSTGRES_PASSWORD` na PRIMEIRA subida, entao trocar a senha no `.env`
depois nao alcanca um container ja criado. Realinhe sem destruir dado:

```bash
docker exec -it tianet-postgres-1 psql -U emprestimo -d emprestimo   -c "ALTER USER emprestimo WITH PASSWORD 'a-senha-do-seu-env';"
```

---

# 8. O que muda no servidor

Este runbook cobre apenas o ambiente local. Antes de subir para um servidor:

- **Segredos:** gere novos. Nada de `.env` local reaproveitado. `JWT_SECRET_KEY`
  e `FRONTEND_SESSION_KEY` diferentes por ambiente.
- **`APP_ENV=production`:** com isso o worker passa a **exigir** `RESEND_API_KEY`
  e `RESEND_FROM`; sem eles ele recusa iniciar em vez de silenciosamente usar o
  canal falso.
- **HTTPS:** com dominio real, `FRONTEND_BACKEND_URL` passa a ser a URL HTTPS
  publica da API e o truque de netns da secao 2.1 deixa de ser necessario.
- **`FRONTEND_ORIGIN`:** precisa ser a origem publica real; o cookie
  `__Host-emprestimo-session` exige `Secure`, o que so funciona em HTTPS (ou
  loopback).
- **Postgres:** manter em loopback ou rede interna, nunca publicado; definir
  politica de backup antes do primeiro dado real.
- **Bootstrap:** manter `PLATFORM_ADMIN_BOOTSTRAP_ENABLED=false` como padrao,
  ligando apenas durante a criacao do primeiro administrador.

---

# 9. Encerrar

```bash
docker compose down            # para tudo, mantem o volume
docker compose down -v         # DESTROI o banco local tambem
```

---

# 10. Historico de Versoes

| Versao | Data | Descricao |
|---|---|---|
| 1.1.0 | 2026-09-03 | Secao 7.2: `password authentication failed` do `pytest` na maquina nunca foi senha errada — era o `.env` que nada lia fora do Compose. `database_url()` passou a resolver por ambiente, arquivo e **derivacao da POSTGRES_PASSWORD**, nesta ordem, de modo que nao ha mais nada a configurar. A linha `DATABASE_URL` do `.env.example` virou opcional porque pedia a senha duas vezes, e duas copias divergem. |
| 1.0.0 | 2026-08-15 | Stack local completa em Docker: postgres, migrations, api, worker e frontend, com bootstrap e verificacao ponta a ponta. |
