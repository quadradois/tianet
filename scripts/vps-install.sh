#!/bin/bash
# Instala/atualiza os artefatos de deploy da VPS a partir de uma tag publicada.
#
# Uso, na VPS, como root:   ./vps-install.sh prod-vX.Y.Z
#
# Existe porque `docker-compose.prod.yml` e o gate `/opt/tianet/bin/deploy`
# vivem no servidor como cópias, fora da imagem. Antes disso serem conferidos,
# um deploy publicava imagens novas contra uma topologia antiga e nada acusava:
# serviço, volume ou variável acrescentada no repositório simplesmente não
# chegava à VPS. O gate agora recusa (exit 3) quando os digests divergem, e
# este script é o jeito de fazê-los convergir.
#
# A fonte é a PRÓPRIA IMAGEM da tag, não o git: a imagem carrega /app/deploy
# (ver Dockerfile), então o que se instala aqui é exatamente o que o gate vai
# conferir. Puxar do git abriria a fresta de instalar um arquivo de um commit
# diferente do que gerou a imagem.
#
# Primeira instalação (o script ainda não está na VPS; repositório é público):
#   curl -fsSLO https://raw.githubusercontent.com/quadradois/tianet/master/scripts/vps-install.sh
#   chmod +x vps-install.sh && ./vps-install.sh prod-vX.Y.Z
set -euo pipefail

TAG="${1:?uso: vps-install.sh prod-vX.Y.Z}"
case "$TAG" in
  prod-v[0-9]*.[0-9]*.[0-9]*) ;;
  *) echo "TAG fora do padrão prod-vX.Y.Z: recuso" >&2; exit 2 ;;
esac
case "$TAG" in
  *[!A-Za-z0-9.-]*) echo "TAG com caractere fora de [A-Za-z0-9.-]: recuso" >&2; exit 2 ;;
esac

REGISTRY=ghcr.io/quadradois/tianet
IMAGEM="${REGISTRY}-tianet-api:${TAG}"
DESTINO=/opt/tianet

[ "$(id -u)" = "0" ] || { echo "rode como root: escreve em $DESTINO" >&2; exit 2; }

echo "== puxando $IMAGEM =="
docker pull -q "$IMAGEM"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

# Extrai para temporário e só promove depois de conferir: um download truncado
# não pode substituir um gate que hoje funciona.
extrair() {  # <arquivo na imagem> <destino final> <permissão>
  local origem="$1" final="$2" modo="$3" tmp="$TMP/$(basename "$2")"
  docker run --rm --entrypoint cat "$IMAGEM" "$origem" > "$tmp"
  [ -s "$tmp" ] || { echo "FALHA: $origem veio vazio da imagem" >&2; exit 1; }

  if [ -f "$final" ] && [ "$(sha256sum < "$final" | cut -d' ' -f1)" = "$(sha256sum < "$tmp" | cut -d' ' -f1)" ]; then
    echo "$(basename "$final"): já estava na versão de $TAG"
    return 0
  fi

  mkdir -p "$(dirname "$final")"
  [ -f "$final" ] && cp -p "$final" "${final}.anterior"
  install -m "$modo" "$tmp" "$final"
  echo "$(basename "$final"): atualizado para $TAG (cópia anterior em ${final}.anterior)"
}

echo "== instalando artefatos =="
extrair /app/deploy/docker-compose.prod.yml "$DESTINO/docker-compose.prod.yml" 644
extrair /app/deploy/deploy-gate.sh          "$DESTINO/bin/deploy"              755

# Conferência final pela MESMA regra do gate: se isto passar, o próximo deploy
# não recusa por divergência de artefato.
echo "== conferência =="
for par in "docker-compose.prod.yml:$DESTINO/docker-compose.prod.yml" \
           "deploy-gate.sh:$DESTINO/bin/deploy"; do
  nome="${par%%:*}"; caminho="${par#*:}"
  na_imagem="$(docker run --rm --entrypoint sha256sum "$IMAGEM" "/app/deploy/$nome" | cut -d' ' -f1)"
  na_vps="$(sha256sum "$caminho" | cut -d' ' -f1)"
  [ "$na_imagem" = "$na_vps" ] || { echo "DIVERGE ainda: $caminho" >&2; exit 1; }
  echo "$nome: confere"
done

echo
echo "INSTALL-OK $TAG"
echo "Falta a linha da chave restrita em ~/.ssh/authorized_keys (ver cabeçalho de $DESTINO/bin/deploy)."
