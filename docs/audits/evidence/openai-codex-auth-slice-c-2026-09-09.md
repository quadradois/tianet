# Evidência sanitizada — autenticação OpenAI/Codex, Slice C

**Data:** 2026-09-09  
**Escopo:** API TiaNet, RBAC, transporte privado e migration.  
**Resultado:** verde; revisão READ_ONLY aprovada após três ciclos corretivos.

## Contrato entregue

- GET /platform/openai/conexao retorna somente o snapshot local.
- GET /platform/openai/diagnostico consulta conta, modelos visíveis e limites.
- POST /platform/openai/conexao/login devolve somente URL oficial, código
  temporário e expiração.
- DELETE /platform/openai/conexao exige Idempotency-Key e confirma logout local.
- As permissões openai.conexao.ler e openai.conexao.gerir são concedidas apenas
  aos perfis administrativos previstos.

## Provas observadas

- Testes focais do agent, aplicação, infraestrutura, API e inventários: verdes.
- Ruff, Black e mypy focais: verdes.
- Migration d2e4f6a8b0c1: upgrade, downgrade até base e novo upgrade: verde em
  emprestimo_test descartável.
- API sem bearer: 401; matriz automatizada cobre 401, 403, 200, 502 e 503.
- API alcançou o agent pelo socket e observou DESCONECTADO, sem token.
- Diretório do socket: 0750, UID 10002, GID 10003; socket: 0660.
- API: UID 10001, membro suplementar do GID 10003 e mount runtime somente leitura;
  tentativa de criar arquivo no volume falhou.
- Agent: UID 10002, sem porta publicada e somente na rede interna agent-egress.
- Egress direto do agent para api, postgres, host.docker.internal e
  auth.openai.com falhou. O proxy permitiu CONNECT para auth.openai.com:443 e
  recusou host.docker.internal:8000 com 403.
- Proxy: UID 10004, filesystem somente leitura, sem volumes, credenciais ou
  portas publicadas.
- O filho Codex recebeu somente o proxy e variáveis ambientais allowlisted; o
  segredo interno não foi propagado.
- Nenhum login real, inferência, tool ou dado de cliente foi usado.
- Cancelamento externo e timeout de mutações mantêm a exclusão até a
  reconciliação; diagnóstico possui deadline individual sem cancelar a coleta
  compartilhada.
- Prova POSIX matou e recolheu com SIGKILL um filho sintético que ignorou
  SIGTERM enquanto a chamada de fechamento era cancelada.

## Correção produzida pela prova

A primeira composição isolava nomes de serviço, mas ainda permitia alcançar a
porta publicada da API por host.docker.internal. A rede do agent passou a ser
interna e o único egress agora atravessa proxy CONNECT com allowlist de hosts
OpenAI, porta 443, rejeição de IP privado, limites de cabeçalho, tempo e bytes.
ADR-020 e arquitetura foram atualizadas antes do fechamento do slice.
