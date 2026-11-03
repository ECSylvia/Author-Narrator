# Doxie Hub integration: development adapter

Status: development only. No deployment, live authentication, customer registration,
billing, subscription management, new voice engine, or Hub repository changes.

## Baseline and contract provenance

Product baseline: `ECSylvia/Author-Narrator` commit
`8e8d402489cded057657a5bbe18461b74491d7d3`.

Hub reference: `ECSylvia/doxie-hub`, branch
`feature/sprint0-product-shells`, observed tree
`9635e420c14d8453c21cb737f0f6233dbc4dc14e`.

Read-only contract sources in that branch:

| Hub source | Product connection |
| --- | --- |
| `backend/registry.py` | `author-narrator`, `/apps/author-narrator`, `author_narrator.access`, enabled flag |
| `frontend/productCatalog.js` | `overview`, `voices`, `manuscripts`, `narration`, `exports` |
| `frontend/ProductShell.jsx`, `docs/INCREMENT_0_9.md` | Shell URL, optional `project_id`, back-to-Hub navigation |
| `backend/identity/contracts.py` | Identity fields and issuer + subject account identity, never email alone |
| `backend/app.py` | Profile, settings, project and workspace field names |
| `backend/commerce/entitlements.py` | Only `active` grants access; unknown or inactive status fails closed |
| `docs/SPRINT_0_HANDOFF.md` | Live identity, entitlement enforcement and security remain blockers |

The Hub branch does NOT define a finished authenticated desktop-launch exchange or
an entitlement-read endpoint. Its shell explicitly says product integration is
pending. This change does not invent either endpoint, reuse browser cookies,
accept tokens in URLs, or pretend that a mock fixture is verified authentication.

`examples/doxie_hub/dev-context.json` is a PRODUCT-SIDE TEST ENVELOPE assembling
those fields. It is not a published Hub HTTP response or a production wire format.
The fixture's project `workspace_id` and entitlement records represent Hub backend
model data; the existing public project JSON does not expose `workspace_id`.

## What changes and what stays unchanged

`src/main.py` recognizes optional Hub launch arguments. With no Hub arguments it
opens the same original `MainWindow`. The engine, recorder, parser, consent wizard,
project manager, settings file and original UI files are unchanged.

`src/integrations/doxie_hub.py` provides:

- A provider-neutral `HubAdapter.resolve_context(project_id)` boundary.
- A local `MockHubAdapter` with explicit development gating and no network calls.
- Registry, identity, workspace, entitlement, project and preference checks.
- Safe parsing of existing Hub product-shell URLs.
- Separate, scoped local-project links that do not modify project files.

`src/ui/hub_window.py` subclasses the original window. It adds a visible
DEVELOPMENT MOCK ONLY label, Back to Doxie Hub and Open Hub product section actions.
Existing narration and recording methods are delegated to the original class,
after rechecking the current development context and local-project association.

No new dependencies or credentials are required for the adapter. The existing
application still requires its documented desktop dependencies. Existing engine
behavior is preserved: deliberately generating narration can still invoke the
configured ElevenLabs engine. The integration itself does not generate audio,
upload a voice, or call a paid service.

## Development launch

From the Author-Narrator repository root, using the project's supported Python
environment with its existing dependencies installed:

```powershell
$env:AUTHOR_NARRATOR_ENV = "development"
$env:DOXIE_HUB_MODE = "mock"

python -m src.main `
  --hub-mock-data examples/doxie_hub/dev-context.json `
  --hub-project-id sample
```

A URL matching the established Hub shell can be supplied instead:

```powershell
python -m src.main `
  --hub-mock-data examples/doxie_hub/dev-context.json `
  --hub-launch-url "http://127.0.0.1:5173/apps/author-narrator/narration?project_id=sample"
```

Use `--hub-origin http://localhost:5173` when the development Hub uses localhost.
Launch URL origin must match that configured origin exactly. Only loopback HTTP
origins with a port are accepted. Credentials, arbitrary return URLs, duplicate
project IDs, unknown applications and unknown sections are rejected.

Do not combine `--hub-project-id` with `--hub-launch-url`. The root product route
without a project is supported as an overview; opening a local project is disabled
until a Hub project is selected.

The Hub shell does not yet launch the desktop binary. These are explicit developer
commands using its route contract, not a claim that browser-to-desktop launch has
been installed. No OS URL protocol handler is registered by this change.

## Existing local projects

Use the existing project picker, or add this option to a development launch:

```powershell
--hub-local-project "C:\Authors\ExistingBook"
```

A Hub project ID is required. The local folder must already contain a valid
`project.json`. First association requires explicit confirmation in the UI; the
existing voice consent wizard still runs when the original application requires it.
No project is automatically created, renamed, moved, merged, or overwritten.

Mappings are stored separately at:

```text
~/.author_narrator_hub/dev-links.json
```

The mapping key includes issuer, subject, user ID, workspace, application and Hub
project ID. Email is never used as an account-linking key. A local project cannot
be silently rebound to another Hub account or project. Review the development
sidecar manually before changing an association; never delete the actual project.
Missing linked folders produce an error rather than being recreated.

The sidecar uses atomic replacement but is a single-process development convenience,
not a multi-user authorization boundary or a concurrent production database. The
local OS account still controls access to local files. Production must enforce
resource authorization in Hub-backed services, not rely on this sidecar.

## Shared preferences and navigation

- `display_name` appears in the Hub toolbar as plain text.
- `theme` (`system`, `light`, `dark`) applies to the Hub window's palette for the
  current session. Existing hardcoded widget styles may need a later visual review.
- `notifications_enabled` and `reduced_motion` are validated, retained in the
  context and exposed as window properties. This integration shell emits no
  background notifications or animations. Existing product dialogs are not
  silently rewritten to change their behavior.
- No preference or identity data is written into the existing SettingsManager.
- Back to Doxie Hub opens the configured local Hub root without closing the project.
- Open Hub product section preserves the selected section and project identifier.
- Section context is preserved, not represented as five newly implemented desktop
  screens. Existing native functionality remains in its original menus and panels.

## Authentication and entitlement boundaries

Both environment switches must be explicit. Default mode is disabled. `live`,
`production`, missing identity, wrong application, wrong workspace, unknown project,
missing entitlement, duplicate grants and every non-active entitlement status fail
closed for Hub launches. The registry must specify `author_narrator.access`.

Fixtures must identify themselves as mocks, use `urn:doxie-hub:development`, have
unverified email and mock authentication metadata. Real identity providers are not
contacted. No tokens, browser sessions or WooCommerce webhooks are accepted here.

Entitlements and account scope are re-read before opening/linking a project and
starting an existing product action. Revocation blocks subsequent actions. This is
not an in-flight job cancellation mechanism or a substitute for production backend
authorization. The existing standalone product remains available without Hub login,
as required to preserve existing functionality.

## Tests

Run the dependency-free integration suite:

```powershell
python -m unittest discover -s tests -p "test_doxie_hub_integration.py" -v
```

Run all new tests, including optional native UI smoke tests:

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
python -m unittest discover -s tests -p "test_doxie_hub*.py" -v
```

The UI tests require the existing PySide6 and elevenlabs packages. They mock engine
invocations and browser opening; they do not generate paid narration. Without those
packages they explicitly skip, rather than reporting a false GUI pass.

Implementation validation: 31 dependency-free tests passed; five native UI tests
were skipped because desktop dependencies were unavailable in the implementation
runtime. Python syntax compilation passed. No live Hub, real voice synthesis,
Windows desktop session or end-to-end browser launch was tested.

Coverage includes exact registry entitlement, all shell sections, scope checks,
revocation, disabled/live-mode rejection, unsafe URLs, preference validation,
account-separated mapping, and byte-for-byte preservation of existing project
metadata, consent, manuscripts, voice samples and generated audio.

## Manual desktop acceptance before merge

1. Start the original application with no Hub arguments; verify existing features.
2. Launch with the fixture and `sample`; verify the development banner and toolbar.
3. Link a COPY of an existing project; decline once, then approve. Check that the
   original metadata, manuscript, voice and audio bytes remain unchanged.
4. Restart with the same Hub context and verify the saved local association.
5. Try a different subject/workspace, missing entitlement and cancelled entitlement.
   Confirm access is denied without modifying files or starting the engine.
6. Use both Hub navigation buttons with a local Hub running. Check project context
   is preserved in the product link and the native project remains open.
7. Change theme and display name; confirm shared preferences are session-only.
8. Remove the environment switches and repeat a Hub launch; it must refuse to run.

## Production connection points and release blockers

Hub security work must finish FIRST. After that, a separate reviewed change must
replace the mock provider with an authenticated Hub transport behind `HubAdapter`.
The Hub team must define and approve the session/handoff mechanism, token audience
and replay protection, entitlement-read API, workspace/project authorization,
expiry/revocation, permitted origins, and privacy/retention behavior.

Keep registration, billing, subscription management and identity-provider exchange
in Hub. Never derive grants from unverified browser data, email or local fixtures.
Do not enable production by changing an environment variable: no live adapter is
implemented in this branch. Do not expose the current Hub mock backend publicly.

The browser-to-product launch bridge, cloud service hosting, production project sync
and secure shared identity are future work, not completed by this development adapter.
