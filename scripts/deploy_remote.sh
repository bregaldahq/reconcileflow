#!/usr/bin/env bash
set -Eeuo pipefail

deploy_path="${1:?Informe o diretório de implantação}"
backend_image="${2:?Informe a imagem imutável do backend}"
frontend_image="${3:?Informe a imagem imutável do frontend}"

[[ "$backend_image" == *@sha256:* ]] || {
  echo "BACKEND_IMAGE deve usar digest sha256." >&2
  exit 1
}
[[ "$frontend_image" == *@sha256:* ]] || {
  echo "FRONTEND_IMAGE deve usar digest sha256." >&2
  exit 1
}

cd "$deploy_path"
[[ -f compose.production.yaml ]] || {
  echo "compose.production.yaml não encontrado em $deploy_path." >&2
  exit 1
}
[[ -f .env.production ]] || {
  echo ".env.production não encontrado em $deploy_path." >&2
  exit 1
}

umask 077
release_file=".env.release"
previous_file=".env.release.previous"
next_file=".env.release.next"

printf 'BACKEND_IMAGE=%s\nFRONTEND_IMAGE=%s\n' \
  "$backend_image" "$frontend_image" > "$next_file"

had_previous=false
if [[ -f "$release_file" ]]; then
  cp -p "$release_file" "$previous_file"
  had_previous=true
fi
mv "$next_file" "$release_file"

compose=(
  docker compose
  --env-file .env.production
  --env-file "$release_file"
  --file compose.production.yaml
)

rollback() {
  local exit_code=$?
  trap - ERR
  echo "A implantação falhou; iniciando rollback." >&2
  if [[ "$had_previous" == true && -f "$previous_file" ]]; then
    cp -p "$previous_file" "$release_file"
    "${compose[@]}" pull
    "${compose[@]}" up --detach --remove-orphans --wait --wait-timeout 180
    echo "Rollback concluído com a versão anterior." >&2
  else
    echo "Não existe uma versão anterior para rollback automático." >&2
  fi
  exit "$exit_code"
}
trap rollback ERR

"${compose[@]}" config --quiet
"${compose[@]}" pull
"${compose[@]}" up --detach --remove-orphans --wait --wait-timeout 180
bash scripts/smoke_test.sh "http://127.0.0.1:${WEB_PORT:-8080}"

trap - ERR
echo "Implantação concluída com imagens imutáveis."
