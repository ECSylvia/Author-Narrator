# Integration 0.2: Manuscript Web Adapter

The existing manuscript parser is reused through POST /manuscripts/preview.
The endpoint accepts only .md and .txt content, returns chapter metadata, and does not save user data.

Next required steps before hosted release:
- Hub-verified authentication and entitlements
- Workspace-scoped project storage and manuscript persistence
- Secure upload limits and malware scanning
- Consent-based voice profiles and new voice engine
- Web UI wiring and shared Doxie Hub navigation

No ElevenLabs code is imported or called by the web adapter.
Run: python -m pytest -q tests/test_hub_integration.py tests/test_web_scaffold.py
