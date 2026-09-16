#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"

if [ ! -f .env ]; then
  echo "copy .env.example to .env and set replace_me secrets first" >&2
  exit 1
fi

# shellcheck disable=SC1091
set -a
. ./.env
set +a

EDGE_NETWORK=${EDGE_NETWORK:-proxy}
if ! docker network inspect "$EDGE_NETWORK" >/dev/null 2>&1; then
  echo "creating edge network $EDGE_NETWORK (exists on the Console host as proxy)"
  docker network create "$EDGE_NETWORK" >/dev/null
fi

python3 scripts/render-realm.py
python3 scripts/validate-realm.py
exec docker compose up -d "$@"
