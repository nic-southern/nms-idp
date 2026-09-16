#!/bin/sh
set -eu
ROOT=$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)
cd "$ROOT"
mkdir -p realm/exported
docker compose exec keycloak /opt/keycloak/bin/kc.sh export --realm nms --file /tmp/nms-realm.json
docker compose cp keycloak:/tmp/nms-realm.json "$ROOT/realm/exported/nms-realm.json"
echo "wrote realm/exported/nms-realm.json (gitignored; may contain users — do not commit)"
