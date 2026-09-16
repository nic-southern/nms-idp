#!/usr/bin/env python3
"""Validate the NMS realm template and a rendered import file."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "realm" / "nms-realm.template.json"
GENERATED = ROOT / "realm" / "generated" / "nms-realm.json"

FORBIDDEN_KEY_MARKERS = (
    "begin private key",
    "begin rsa private key",
    "begin openssh private key",
)


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def client_by_id(realm: dict, client_id: str) -> dict:
    matches = [c for c in realm.get("clients", []) if c.get("clientId") == client_id]
    if len(matches) != 1:
        raise SystemExit(f"expected exactly one client {client_id!r}, found {len(matches)}")
    return matches[0]


def assert_oidc_confidential(client: dict, client_id: str) -> dict:
    if client.get("protocol") != "openid-connect":
        raise SystemExit(f"{client_id} must be openid-connect")
    if client.get("publicClient") is not False:
        raise SystemExit(f"{client_id} must be a confidential client")
    if client.get("standardFlowEnabled") is not True:
        raise SystemExit(f"{client_id} must enable the authorization code flow")
    if client.get("implicitFlowEnabled"):
        raise SystemExit(f"{client_id} must not enable implicit flow")
    if client.get("directAccessGrantsEnabled"):
        raise SystemExit(f"{client_id} must not enable resource-owner password grants")
    if client.get("clientAuthenticatorType") != "client-secret":
        raise SystemExit(f"{client_id} must use client-secret authentication")
    mappers = {m.get("name") for m in client.get("protocolMappers", [])}
    if "groups" not in mappers:
        raise SystemExit(f"{client_id} must map group membership")
    pkce = (client.get("attributes") or {}).get("pkce.code.challenge.method")
    if pkce != "S256":
        raise SystemExit(f"{client_id} must require PKCE S256")


def assert_mfa(realm: dict) -> None:
    if realm.get("otpPolicyType") != "totp":
        raise SystemExit("realm must declare a TOTP policy")
    actions = {a.get("alias"): a for a in realm.get("requiredActions", [])}
    totp = actions.get("CONFIGURE_TOTP")
    if not totp or not totp.get("enabled"):
        raise SystemExit("CONFIGURE_TOTP must be enabled")
    if not totp.get("defaultAction"):
        raise SystemExit("CONFIGURE_TOTP should be a default action so new users enroll MFA")
    webauthn = actions.get("webauthn-register")
    if not webauthn or not webauthn.get("enabled"):
        raise SystemExit("webauthn-register must be enabled (optional, not default)")


def assert_no_users(realm: dict) -> None:
    users = realm.get("users") or []
    if users:
        raise SystemExit("do not ship users or passwords in the realm file")


def assert_no_secrets_in_template(realm: dict) -> None:
    text = json.dumps(realm).lower()
    if "scim" in text:
        raise SystemExit("SCIM is deferred; do not include it in this realm")
    for marker in FORBIDDEN_KEY_MARKERS:
        if marker in text:
            raise SystemExit("realm file must not contain private keys")
    for client in realm.get("clients", []):
        secret = client.get("secret")
        if secret not in (None, "", "__INJECTED__"):
            raise SystemExit(
                f"template client {client.get('clientId')} must not contain a real secret"
            )


def assert_generated_secrets(realm: dict) -> None:
    for client_id in ("lockhaven", "tickets"):
        client = client_by_id(realm, client_id)
        secret = client.get("secret") or ""
        if secret in ("", "__INJECTED__", "replace_me"):
            raise SystemExit(f"generated {client_id} secret was not injected")
        if not client.get("redirectUris"):
            raise SystemExit(f"{client_id} redirect URIs missing after render")


def main() -> None:
    template = load(TEMPLATE)
    if template.get("realm") != "nms":
        raise SystemExit("realm name must be nms")
    if template.get("displayName") != "New Market Security":
        raise SystemExit("displayName must be New Market Security")
    assert_no_users(template)
    assert_no_secrets_in_template(template)
    assert_oidc_confidential(client_by_id(template, "lockhaven"), "lockhaven")
    assert_oidc_confidential(client_by_id(template, "tickets"), "tickets")
    assert_mfa(template)

    if not GENERATED.is_file():
        print("template ok; generated realm not present (run scripts/render-realm.py)")
        return

    generated = load(GENERATED)
    assert_no_users(generated)
    assert_oidc_confidential(client_by_id(generated, os.environ.get("LOCKHAVEN_CLIENT_ID", "lockhaven")), "lockhaven")
    assert_oidc_confidential(client_by_id(generated, os.environ.get("TICKETS_CLIENT_ID", "tickets")), "tickets")
    assert_generated_secrets(generated)
    assert_mfa(generated)
    print("realm template and generated import look valid")


if __name__ == "__main__":
    main()
