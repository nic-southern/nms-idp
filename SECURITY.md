# Security

Report credential leaks or identity bugs privately. Do not open a public
issue that includes secrets, user lists, or environment files.

This repository must never contain:

- `.env` files
- generated realm JSON (`realm/generated/`)
- realm exports (`realm/exported/`)
- TLS private keys
- real client secrets or admin passwords
