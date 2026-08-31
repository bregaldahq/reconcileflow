#!/usr/bin/env bash
set -Eeuo pipefail

base_url="${1:-http://127.0.0.1:8080}"
base_url="${base_url%/}"
max_attempts="${SMOKE_MAX_ATTEMPTS:-30}"
retry_seconds="${SMOKE_RETRY_SECONDS:-2}"

request_until_ready() {
  local path="$1"
  local expected="$2"
  local description="$3"
  local attempt response

  for ((attempt = 1; attempt <= max_attempts; attempt += 1)); do
    if response="$(curl --fail --silent --show-error --location \
      --connect-timeout 3 --max-time 10 "${base_url}${path}" 2>/dev/null)" \
      && grep -Fq "$expected" <<< "$response"; then
      printf 'OK: %s\n' "$description"
      return 0
    fi
    if ((attempt < max_attempts)); then
      sleep "$retry_seconds"
    fi
  done

  printf 'Falha: %s não respondeu como esperado após %s tentativas.\n' \
    "$description" "$max_attempts" >&2
  return 1
}

request_until_ready "/" "ReconcileFlow" "interface web"
request_until_ready "/health/ready" '"status":"ready"' "saúde da API"
request_until_ready "/api/v1/profiles" '"label"' "catálogo de perfis"

printf 'Smoke test concluído em %s.\n' "$base_url"
