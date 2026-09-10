#!/bin/bash
# Gate de deploy da VPS — ÚNICO comando que a chave de deploy pode executar.
# Uso: /opt/tianet/bin/deploy prod-vX.Y.Z
# Lê segredos SOMENTE de /root/tianet/.env.prod (600). Nunca exibe valores:
# este script imprime nomes, contagens e status — jamais conteúdo de segredo.
#
# Linha correspondente em ~/.ssh/authorized_keys da VPS (uma linha só):
#
#   command="/opt/tianet/bin/deploy",no-agent-forwarding,no-port-forwarding,\
#   no-pty,no-user-rc,no-X11-forwarding ssh-ed25519 AAAA... deploy@github
#
set -euo pipefail

# Com `command=` no authorized_keys o sshd IGNORA o comando enviado pelo
# cliente e executa o fixo, entregando o original em $SSH_ORIGINAL_COMMAND —
# a tag NÃO chega em "$1". Ler só "$1" fazia todo deploy pela chave restrita
# morrer em "uso: deploy prod-vX.Y.Z". Aceitamos as duas formas: pela chave e
# invocado à mão no servidor.
TAG="${1:-}"
if [ -z "$TAG" ] && [ -n "${SSH_ORIGINAL_COMMAND:-}" ]; then
  # Última palavra do comando original. Nada aqui é avaliado como shell: o
  # valor é só um texto que ainda precisa passar pelas validações abaixo.
  TAG="${SSH_ORIGINAL_COMMAND##* }"
fi
[ -n "$TAG" ] || { echo "uso: deploy prod-vX.Y.Z" >&2; exit 2; }

# Fronteira de confiança: entrada vinda da rede. Duas validações, porque o
# glob do `case` termina em `*` e sozinho aceitaria `prod-v1.0.0; rm -rf /`.
case "$TAG" in
  prod-v[0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "TAG fora do padrão prod-vX.Y.Z: recuso" >&2; exit 2 ;;
esac
case "$TAG" in
  *[!A-Za-z0-9.-]*) echo "TAG com caractere fora de [A-Za-z0-9.-]: recuso" >&2; exit 2 ;;
esac

COMPOSE_FILE=/opt/tianet/docker-compose.prod.yml
COMPOSE="docker compose -f $COMPOSE_FILE"
ENV_FILE=/root/tianet/.env.prod
LAST_GOOD=/opt/tianet/.last-good-tag
REGISTRY=ghcr.io/quadradois/tianet

[ -f "$ENV_FILE" ] || { echo "falta $ENV_FILE" >&2; exit 2; }
[ -s "$ENV_FILE" ] || { echo "$ENV_FILE vazio" >&2; exit 2; }

# Serviços de longa duração. `migrate` fica de fora de propósito: é one-shot.
SERVICOS="api worker frontend agent agent-egress-proxy"

ETAPA="inicialização"

falha() { echo "DEPLOY-FALHA: $1" >&2; exit 1; }

# Retorna 0 só quando a stack anterior voltou a subir. Os `|| true` da versão
# anterior engoliam a falha do próprio rollback e faziam o log afirmar que
# tinha voltado quando não tinha.
rollback() {
  if [ ! -f "$LAST_GOOD" ]; then
    echo "ROLLBACK-IMPOSSIVEL: $LAST_GOOD não existe (primeiro deploy)" >&2
    return 1
  fi
  PREV="$(cat "$LAST_GOOD")"
  [ -n "$PREV" ] || { echo "ROLLBACK-IMPOSSIVEL: $LAST_GOOD vazio" >&2; return 1; }

  echo "ROLLBACK-INICIO: voltando para $PREV" >&2
  if TAG="$PREV" $COMPOSE --env-file "$ENV_FILE" pull -q $SERVICOS \
    && TAG="$PREV" $COMPOSE --env-file "$ENV_FILE" up -d $SERVICOS; then
    echo "ROLLBACK-OK: $PREV" >&2
    return 0
  fi
  echo "ROLLBACK-FALHOU: $PREV" >&2
  return 1
}

# O handler afirma estado, não intenção: falha-com-rollback e falha-sem-rollback
# são resultados diferentes e param em linhas diferentes do log. A versão
# anterior era `falha "..."; rollback` — `falha` termina em `exit`, então o
# rollback era código morto e todo deploy quebrado ficava de pé na imagem nova
# enquanto o log dizia "rollback tentado".
ao_falhar() {
  trap - ERR   # sem reentrância: uma falha dentro do handler não redispara
  if rollback; then
    falha "$ETAPA — revertido para a tag anterior"
  fi
  falha "$ETAPA — SEM ROLLBACK, produção em estado indefinido, intervenção manual necessária"
}

export TAG
export REGISTRY

IMAGEM_API="${REGISTRY}-tianet-api:${TAG}"

# ATENÇÃO: até a etapa `up` nada de produção foi tocado, então o trap ERR de
# rollback ainda NÃO está instalado. Falhar aqui tem que sair limpo — mandar a
# stack para a tag anterior por causa de um pull ou de um hash divergente
# mexeria em produção sem necessidade.

ETAPA="pull $TAG"
echo "== pull $TAG =="
$COMPOSE --env-file "$ENV_FILE" pull -q migrate $SERVICOS

# A topologia e este próprio script vivem na VPS como cópias manuais, fora da
# tag. Sem esta conferência, um deploy publicava imagens novas contra um
# compose antigo — serviço, volume ou env acrescentado no repo simplesmente não
# chegava ao servidor, e nada acusava. A imagem da tag carrega os dois arquivos
# em /app/deploy (ver Dockerfile); aqui só comparamos os digests.
echo "== artefatos de deploy correspondem à tag =="
conferir_artefato() {  # <arquivo na VPS> <arquivo dentro da imagem>
  local local_sha imagem_sha
  local_sha="$(sha256sum "$1" | cut -d' ' -f1)"
  # Imagem anterior à introdução de /app/deploy não tem o arquivo: falha aqui é
  # tag velha, não divergência de conteúdo — e as duas pedem ações diferentes.
  imagem_sha="$(docker run --rm --entrypoint sha256sum "$IMAGEM_API" "$2" | cut -d' ' -f1)" || {
    echo "DEPLOY-FALHA: $IMAGEM_API não carrega $2" >&2
    echo "  imagem anterior aos artefatos de deploy: publique uma tag nova" >&2
    exit 3
  }
  if [ "$local_sha" != "$imagem_sha" ]; then
    echo "DEPLOY-FALHA: $1 diverge da versão publicada em $TAG" >&2
    echo "  VPS:    $local_sha" >&2
    echo "  $TAG: $imagem_sha" >&2
    echo "  copie o arquivo da tag para a VPS antes de repetir o deploy" >&2
    exit 3
  fi
  echo "$(basename "$1"): confere"
}
conferir_artefato "$COMPOSE_FILE" /app/deploy/docker-compose.prod.yml
conferir_artefato "$0" /app/deploy/deploy-gate.sh

# Daqui para a frente produção é tocada: o rollback passa a valer.
trap 'ao_falhar' ERR

# `up -d` também satisfaz a dependência `service_completed_successfully` do
# migrate, então não há `run --rm` separado: rodá-lo aqui só faria o alembic
# subir duas vezes por deploy.
ETAPA="subida da stack $TAG (inclui migrate)"
echo "== up (migrate + serviços) =="
$COMPOSE --env-file "$ENV_FILE" up -d $SERVICOS

# Espera um HTTP responder. Uso: esperar_http <url> <rótulo>
esperar_http() {
  for i in $(seq 1 24); do
    if curl -fsS -m 5 "$1" >/dev/null 2>&1; then
      echo "$2 ok após ${i}x5s"
      return 0
    fi
    sleep 5
  done
  return 1
}

ETAPA="health da api"
echo "== health =="
esperar_http http://127.0.0.1:8000/health api || ao_falhar

ETAPA="health do frontend"
esperar_http http://127.0.0.1:3000/ frontend || ao_falhar

# worker, agent e proxy não expõem porta, e `up -d` devolve 0 mesmo para um
# container que subiu e morreu em seguida. O que dá para afirmar sem inventar
# healthcheck é que cada um está de pé — antes, um worker em crash-loop saía
# daqui como DEPLOY-OK.
ETAPA="estado dos serviços"
for s in $SERVICOS; do
  CID="$($COMPOSE --env-file "$ENV_FILE" ps -q "$s" || true)"
  if [ -z "$CID" ]; then
    ETAPA="serviço $s não tem container"
    ao_falhar
  fi
  ESTADO="$(docker inspect -f '{{.State.Status}}' "$CID" || echo desconhecido)"
  if [ "$ESTADO" != "running" ]; then
    ETAPA="serviço $s em estado '$ESTADO' (esperado running)"
    ao_falhar
  fi
  echo "$s: running"
done

trap - ERR
echo "$TAG" > "$LAST_GOOD"
chmod 600 "$LAST_GOOD"
echo "DEPLOY-OK $TAG"
