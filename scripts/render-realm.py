#!/usr/bin/env python3
"""Render the NMS realm JSON by injecting client secrets and redirect URIs from env."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path


def csv_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def require_env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise SystemExit(f"missing required environment variable: {name}")
    return value


def find_client(realm: dict, client_id: str) -> dict:
    for client in realm.get("clients", []):
        if client.get("clientId") == client_id:
            return client
    raise SystemExit(f"realm template is missing OIDC client {client_id!r}")


def apply_client(
    client: dict,
    *,
    client_id: str,
    secret: str,
    root_url: str,
    redirect_uris: list[str],
    web_origins: list[str],
    post_logout: str,
) -> None:
    if not redirect_uris:
        raise SystemExit(f"{client_id} has no redirect URIs")
    if not web_origins:
        raise SystemExit(f"{client_id} has no web origins")
    client["clientId"] = client_id
    client["secret"] = secret
    client["rootUrl"] = root_url
    client["baseUrl"] = root_url
    client["redirectUris"] = redirect_uris
    client["webOrigins"] = web_origins
    attributes = client.setdefault("attributes", {})
    attributes["post.logout.redirect.uris"] = post_logout
    attributes["pkce.code.challenge.method"] = "S256"


def paths() -> tuple[Path, Path]:
    container_template = Path("/realm/nms-realm.template.json")
    if container_template.is_file():
        return container_template, Path("/realm/generated/nms-realm.json")
    root = Path(__file__).resolve().parent.parent
    return root / "realm" / "nms-realm.template.json", root / "realm" / "generated" / "nms-realm.json"


def main() -> None:
    template_path, out_path = paths()
    realm = json.loads(template_path.read_text(encoding="utf-8"))

    lockhaven = find_client(realm, "lockhaven")
    apply_client(
        lockhaven,
        client_id=os.environ.get("LOCKHAVEN_CLIENT_ID", "lockhaven").strip() or "lockhaven",
        secret=require_env("LOCKHAVEN_CLIENT_SECRET"),
        root_url=os.environ.get("LOCKHAVEN_ROOT_URL", "http://localhost:3000").strip(),
        redirect_uris=csv_list(os.environ.get("LOCKHAVEN_REDIRECT_URIS")),
        web_origins=csv_list(os.environ.get("LOCKHAVEN_WEB_ORIGINS")),
        post_logout=os.environ.get("LOCKHAVEN_POST_LOGOUT_REDIRECT_URIS", "http://localhost:3000/*").strip(),
    )

    tickets = find_client(realm, "tickets")
    apply_client(
        tickets,
        client_id=os.environ.get("TICKETS_CLIENT_ID", "tickets").strip() or "tickets",
        secret=require_env("TICKETS_CLIENT_SECRET"),
        root_url=os.environ.get("TICKETS_ROOT_URL", "http://localhost:4000").strip(),
        redirect_uris=csv_list(os.environ.get("TICKETS_REDIRECT_URIS")),
        web_origins=csv_list(os.environ.get("TICKETS_WEB_ORIGINS")),
        post_logout=os.environ.get("TICKETS_POST_LOGOUT_REDIRECT_URIS", "http://localhost:4000/*").strip(),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(realm, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {out_path}")


if __name__ == "__main__":
    main()
