# Author Narrator | Doxie Hub Integration 0.1

## Objective
Prepare Author Narrator for Doxie Hub while preserving the existing desktop application's manuscript parser, project manager, and current source files.

## Shared platform ownership
- Doxie Hub owns customer identity, MFA, subscription entitlements, customer settings and billing.
- Author Narrator owns manuscripts, voice profiles, narration jobs and audio exports.
- WooCommerce remains the payment system of record.
- Voice synthesis is an independent OpenAI-oriented workstream; no new ElevenLabs integration is permitted.

## Integration 0.1
- Hub principal, project and entitlement contracts.
- Fail-closed project context authorization.
- Local project metadata adapter, preserving existing project.json.
- Standalone FastAPI web scaffold with status and launch placeholder.
- Voice engine protocol without an implementation.
- Unit tests for access decisions.

## Local setup
Python 3.12+:
```bash
pip install -r requirements-web.txt
pytest -q tests/test_hub_integration.py
uvicorn web_scaffold.app:app --reload --host 127.0.0.1 --port 8010
```
Endpoints: /health, /integration, /launch (501 until Hub auth is implemented).

## Integration 0.2 next
- Verified Hub OIDC/session integration, never trust browser-supplied identity.
- Real entitlement verification and tenant isolation.
- Hosted project storage with migration path for existing local projects.
- Web manuscript upload and chapter listing using existing parser.
- Product-specific navigation and return-to-Hub.
- Voice engine integration only after its separate contract is approved.

## Security and deployment
- Do not deploy publicly. No real login, account linking, or entitlement enforcement is implemented.
- Voice generation and payment processing are not implemented.
- Existing desktop ElevenLabs code is untouched in this increment; deprecation/removal belongs to a separately tested migration.
- Never store API keys or voice consent material in source control.
