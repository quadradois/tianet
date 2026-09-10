# Evidência sanitizada — autenticação OpenAI/Codex, Slices A e B

**Data:** 2026-09-09  
**Escopo:** adapter de conta e serviço `agent` local, ainda deslogado  
**Resultado:** aprovado para iniciar a Slice C

## Slice A

- O adapter público expõe somente conta, modelos, limites e device challenge;
  não possui operação genérica, inferência, conversa, shell ou tools.
- Framing JSONL, limite de 1 MiB, deadline único de 15 segundos, correlação,
  cancelamento, EOF, versão/identidade e notificações conhecidas foram cobertos.
- O conjunto focal `tests/unit/agent` terminou com 26 testes aprovados.
- Black, Ruff e mypy passaram no código do adapter e serviço.
- Revisão especializada `READ_ONLY`: `APPROVED`.

## Slice B

- Codex CLI `0.146.1` foi obtido da distribuição oficial e validado pelo SHA-256
  governado; a imagem-base usa digest e o schema canônico do App Server confere
  com a fixture versionada.
- O ambiente Python é instalado uma única vez por `uv` fixado por digest, a
  partir de lock completo com hashes, e validado por `pip check`. O índice
  espelho é somente transporte para contornar a falha TLS do Docker Desktop com
  o CDN do PyPI; hashes governados continuam definindo os artefatos aceitos.
- O contêiner executou como usuário `agent` (UID 10002), com raiz somente
  leitura, capabilities removidas, sem portas publicadas e apenas o volume de
  `CODEX_HOME` montado.
- A prova negativa bloqueou API TiaNet, PostgreSQL e portas equivalentes do
  host. O egress HTTPS para `auth.openai.com:443` permaneceu disponível.
- Checkout, `.git`, documentação, camadas da aplicação e volume PostgreSQL não
  estavam presentes no contêiner.
- O endpoint interno recusou segredo ausente e incorreto (`401`) e aceitou a
  fixture correta (`200`); a fixture não apareceu nos logs.
- A interrupção deliberada do processo Codex alterou `/health` para `503` e
  limpou o estado observado da conta.
- O volume de `CODEX_HOME` persistiu após recriação. Com a feature flag
  desligada e segredo vazio, o serviço iniciou saudável sem processo Codex.
- Revisão especializada `READ_ONLY`: `APPROVED`, sem pendência material.

## Limites desta evidência

Nenhuma conta foi autenticada. Não houve código de usuário, login ID, token,
e-mail, inferência, tool, mensagem de cliente, commit, deploy ou produção. O
serviço foi parado ao final e o volume não foi apagado.
