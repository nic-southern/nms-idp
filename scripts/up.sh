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

python3 scripts/render-realm.py
python3 scripts/validate-realm.py
exec docker compose up -d "$@"
