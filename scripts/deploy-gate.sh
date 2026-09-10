#!/bin/bash
# Gate de deploy da VPS — ÚNICO comando que a chave de deploy pode executar
# (authorized_keys com command=, sem agent/port-forward/X11).
# Uso: /opt/tianet/bin/deploy prod-vX.Y.Z
# Lê segredos SOMENTE de /root/tianet/.env.prod (600). Nunca exibe valores:
# este script imprime nomes, contagens e status — jamais conteúdo de segredo.
set -euo pipefail

TAG="${1:?uso: deploy prod-vX.Y.Z}"
case "$TAG" in
  prod-v[0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "TAG fora do padrão prod-vX.Y.Z: recuso" >&2; exit 2 ;;
esac

COMPOSE="docker compose -f /opt/tianet/docker-compose.prod.yml"
ENV_FILE=/root/tianet/.env.prod
LAST_GOOD=/opt/tianet/.last-good-tag
REGISTRY=ghcr.io/quadradois/tianet

[ -f "$ENV_FILE" ] || { echo "falta $ENV_FILE" >&2; exit 2; }
[ -s "$ENV_FILE" ] || { echo "$ENV_FILE vazio" >&2; exit 2; }

falha() { echo "DEPLOY-FALHA: $1" >&2; exit 1; }

rollback() {
  if [ -f "$LAST_GOOD" ]; then
    PREV="$(cat "$LAST_GOOD")"
    echo "rollback para $PREV"
    TAG="$PREV" $COMPOSE --env-file "$ENV_FILE" pull -q api worker frontend agent agent-egress-proxy || true
    TAG="$PREV" $COMPOSE --env-file "$ENV_FILE" up -d api worker frontend agent agent-egress-proxy || true
  fi
}

trap 'falha "erro na etapa (rollback tentado)"; rollback' ERR

export TAG
export REGISTRY

echo "== pull $TAG =="
$COMPOSE --env-file "$ENV_FILE" pull -q api worker migrate frontend agent agent-egress-proxy

echo "== migrate =="
$COMPOSE --env-file "$ENV_FILE" run --rm migrate

echo "== up =="
$COMPOSE --env-file "$ENV_FILE" up -d api worker frontend agent agent-egress-proxy

echo "== health =="
for i in $(seq 1 24); do
  if curl -fsS -m 5 http://127.0.0.1:8000/health >/dev/null 2>&1; then
    echo "api ok após ${i}x5s"
    break
  fi
  [ "$i" = "24" ] && falha "api sem health em 120s"
  sleep 5
done

trap - ERR
echo "$TAG" > "$LAST_GOOD"
chmod 600 "$LAST_GOOD"
echo "DEPLOY-OK $TAG"
