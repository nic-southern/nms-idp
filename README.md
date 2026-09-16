# nms-idp

Company identity for **New Market Security**. This repository runs Keycloak
with Postgres so Console, tickets, and later tools share one login.

Public hostname: `auth.newmarketsecurity.com`

This is infrastructure only. It is not part of the Lockhaven application repo
and does not share a database with Lockhaven.

## What ships

- Official images: `quay.io/keycloak/keycloak:26.7.3` and `postgres:16-alpine`
- Docker Compose project name `nms-idp` (isolated from any Lockhaven stack)
- Realm `nms` imported on first start
- Confidential OIDC clients: `lockhaven` (Console) and `tickets` (placeholder)
- TOTP enrollment on first login; WebAuthn available; no SCIM

Secrets stay in `.env`. Client secrets are injected into a gitignored realm file
at start. Do not commit `.env`, generated realm JSON, or realm exports.

## Boot locally

Requires Docker Compose and a `.env` with real random values (not `replace_me`).

```sh
cp .env.example .env
# set POSTGRES_PASSWORD, KC_BOOTSTRAP_ADMIN_PASSWORD,
# LOCKHAVEN_CLIENT_SECRET, and TICKETS_CLIENT_SECRET
# openssl rand -hex 24

./scripts/up.sh
```

Compose publishes Keycloak only on loopback:

- Sign-in and admin: http://localhost:8080
- Realm: `nms`
- Issuer: http://localhost:8080/realms/nms
- Discovery: http://localhost:8080/realms/nms/.well-known/openid-configuration
- Health: http://localhost:9000/health/ready

Master-realm admin is `KC_BOOTSTRAP_ADMIN_USERNAME` /
`KC_BOOTSTRAP_ADMIN_PASSWORD` (first start only). Create users in the `nms`
realm. Do not use the master admin as a daily operator account.

First import wins. Later `compose up` will not overwrite an existing `nms`
realm. To re-import, remove the Postgres volume (this wipes identity data):

```sh
docker compose down -v
```

Export a running realm (gitignored; may include users — never commit it):

```sh
./scripts/export-realm.sh
```

## Point Lockhaven PR F at this IdP

Lockhaven SSO consumption (PR F) should treat this Keycloak as a generic OIDC
provider. Set these on the Lockhaven side (env only):

```sh
SSO_OIDC_ISSUER=https://auth.newmarketsecurity.com/realms/nms
SSO_OIDC_CLIENT_ID=lockhaven
SSO_OIDC_CLIENT_SECRET=<same value as LOCKHAVEN_CLIENT_SECRET>
SSO_OIDC_DISCOVERY_URL=https://auth.newmarketsecurity.com/realms/nms/.well-known/openid-configuration
SSO_OIDC_SCOPES=openid,profile,email
```

Local Lockhaven against this Compose stack:

```sh
SSO_OIDC_ISSUER=http://localhost:8080/realms/nms
SSO_OIDC_CLIENT_ID=lockhaven
SSO_OIDC_CLIENT_SECRET=<same value as LOCKHAVEN_CLIENT_SECRET>
SSO_OIDC_DISCOVERY_URL=http://localhost:8080/realms/nms/.well-known/openid-configuration
```

Redirect URIs must match the callback PR F actually registers. The realm
defaults assume better-auth `genericOAuth`:

`{console origin}/api/auth/oauth2/callback/lockhaven`

Also allow `{console origin}/api/auth/callback/lockhaven`. Put every Console
origin in `LOCKHAVEN_ROOT_URL`, `LOCKHAVEN_REDIRECT_URIS`, and
`LOCKHAVEN_WEB_ORIGINS` before the first import (or update the client in the
admin console after).

Suggested allowlist: company email domain `newmarketsecurity.com`. Tokens
include `email`, `email_verified`, `preferred_username`, `groups`, and `roles`
for JIT mapping. IdP MFA is TOTP (required at first login); PR F can trust
that signal and skip a second Console OTP if you choose.

SAML can be added later on the same realm. SCIM is out of scope.

## DNS and TLS for auth.newmarketsecurity.com

1. Create an A/AAAA record for `auth.newmarketsecurity.com` to the VPS that
   will run **this** compose project.
2. Copy `.env.example` to `.env` on the host. Set:
   - `KC_HOSTNAME=https://auth.newmarketsecurity.com`
   - `KC_HOSTNAME_STRICT=true`
   - `KC_HTTP_ENABLED=true`
   - `KC_PROXY_HEADERS=xforwarded`
   - `LOCKHAVEN_ROOT_URL` and redirect/origin lists to the real Console origin
   - `ACME_EMAIL` to an operator address you control
3. Suggested host layout (not `/opt/lockhaven`):

   ```text
   /opt/nms-idp/
     .env
     compose.yaml
     compose.proxy.yaml
     Caddyfile
     realm/
     scripts/
   ```

4. Start with TLS:

   ```sh
   docker compose -f compose.yaml -f compose.proxy.yaml up -d
   ```

Caddy terminates HTTPS and proxies to Keycloak on the internal `nms-idp`
network. Keycloak HTTP stays bound to `127.0.0.1` on the host.

Do not attach this file to the Lockhaven Compose project. If you colocate on
the same VPS, keep project name `nms-idp`, a separate directory, and a
separate Docker network. Prefer a dedicated small VPS when you can.

## MFA and operators

- New `nms` users are asked to enroll TOTP on first sign-in.
- WebAuthn is enabled as an optional action; turn it into a default in the
  admin console if you want passkeys for everyone.
- There is no user directory sync (no SCIM). Offboard by disabling the user
  in this realm, then remove any local Console link by hand.

## Safety

- Never commit passwords, client secrets, realm exports, or inventory.
- Postgres is not published to the host network.
- Rotate `LOCKHAVEN_CLIENT_SECRET` / `TICKETS_CLIENT_SECRET` in `.env` **and**
  in the Keycloak admin console if you change them after the first import.
