# Bootstrap do Administrador da Plataforma

**Implementacao:** IMP-099

**Superficie:** comando operacional local; nao existe endpoint HTTP de bootstrap.

## Garantias

- cria um Tenant de controle ativo, um Usuario convidado e o Perfil
  `administrador_plataforma` em uma unica transacao;
- concede o **catalogo inteiro** de permissoes ao Usuario criado — **na primeira
  execucao**. Em banco inicializado antes do IMP-363 a garantia nao vale no
  replay: a operacao e idempotente, devolve o registro existente e nao reconcede
  nada, entao o perfil antigo continua com as cinco `tenant.*`. Para esses,
  use `scripts/seed_operador_local.py` (ver `ambiente-local-docker.md` §6).
  Coerente com a
  [ADR-003](../architecture/adrs/ADR-003-escopo-single-tenant-do-v1.md) — separar
  papel administrativo de operacional so faz sentido com mais de uma pessoa;
- define a credencial inicial por hash PBKDF2 e ativa o Usuario no mesmo commit;
- usa uma chave global fixa de idempotencia para impedir uma segunda raiz
  administrativa, inclusive em execucoes concorrentes;
- nao devolve credenciais em `stdout`;
- nao registra segredo operacional, credencial ou hash na auditoria/idempotencia.

## Pre-requisitos

1. Configure `DATABASE_URL` para o banco do ambiente correto.
2. Configure uma `JWT_SECRET_KEY` forte no processo da API.
3. Aplique as migrations antes do bootstrap:

```powershell
uv run alembic upgrade head
```

4. Gere um segredo operacional aleatorio com pelo menos 32 caracteres e calcule
   seu SHA-256 sem incluir o segredo na linha de comando:

```powershell
python -c "import getpass,hashlib; print(hashlib.sha256(getpass.getpass('Segredo: ').encode()).hexdigest())"
```

5. Exporte apenas o hash e habilite temporariamente o gate:

```powershell
$env:PLATFORM_ADMIN_BOOTSTRAP_ENABLED = "true"
$env:PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH = "<sha256>"
```

## Execucao

Execute em um terminal privado, sem redirecionar a saida para logs:

```powershell
uv run emprestimo-bootstrap-plataforma `
  --tenant-identificador "PLATAFORMA-CONTROLE" `
  --tenant-nome "Controle da Plataforma" `
  --admin-nome "Administrador da Plataforma" `
  --admin-email "admin@plataforma.local"
```

O comando solicita por `getpass` o segredo de autorizacao e, duas vezes, a
credencial inicial do administrador; nenhum deles aparece em `argv` ou na
resposta. Um replay com os mesmos dados valida o estado persistido, retorna os
mesmos IDs com `criado_agora: false` e nao altera a credencial. Dados diferentes
ou estado privilegiado inconsistente sao recusados.

Depois, autentique em `POST /auth/login` usando o identificador institucional,
o e-mail e a credencial inicial informados no comando.

## Encerramento Obrigatorio

Desabilite o gate e remova o hash assim que o login for confirmado:

```powershell
$env:PLATFORM_ADMIN_BOOTSTRAP_ENABLED = "false"
Remove-Item Env:PLATFORM_ADMIN_BOOTSTRAP_SECRET_HASH
```

Nao inative o Tenant de controle. A API bloqueia essa operacao para o proprio
Administrador da Plataforma e impede que a gestao comum de Perfis conceda
permissoes `tenant.*`.

## Falhas

- `bootstrap operacional desabilitado`: habilite o gate somente durante a janela aprovada;
- `autorizacao recusada`: confirme o segredo e o hash configurado;
- `bootstrap em andamento`: outra execucao ocupa a trava global; aguarde e consulte a auditoria;
- `Administrador da Plataforma ja inicializado`: nao tente elevar outra identidade;
- falha de resposta depois do commit: repita exatamente os mesmos argumentos;
  o replay valida a identidade persistida e a credencial informada originalmente
  continua valida.
