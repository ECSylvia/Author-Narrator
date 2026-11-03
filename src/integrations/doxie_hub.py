"""Development-only Doxie Hub adapter, based on sprint0-product-shells.

No OIDC, payment, registration, HTTP client, or token handling is implemented.
The fixture envelope is a product-side test harness, NOT a live Hub wire format.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Mapping, Protocol
from urllib.parse import parse_qs, urlencode, urlsplit

APP_SLUG = "author-narrator"
ENTITLEMENT = "author_narrator.access"
LAUNCH_PATH = "/apps/author-narrator"
SECTIONS = ("overview", "voices", "manuscripts", "narration", "exports")
MAX_JSON_BYTES = 256 * 1024


class HubIntegrationError(ValueError):
    """A safe, user-facing integration failure."""


def _text(value: object, label: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > maximum:
        raise HubIntegrationError(f"Invalid {label}.")
    if any(ord(c) < 32 for c in value):
        raise HubIntegrationError(f"Invalid {label}.")
    return value


def _identifier(value: object, label: str) -> str:
    value = _text(value, label, 128)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", value):
        raise HubIntegrationError(f"Invalid {label}.")
    return value


def _object(value: object, label: str) -> dict:
    if not isinstance(value, dict):
        raise HubIntegrationError(f"Invalid {label}.")
    return value


def _read_json(path: Path) -> dict:
    try:
        with path.open("rb") as handle:
            data = handle.read(MAX_JSON_BYTES + 1)
        if len(data) > MAX_JSON_BYTES:
            raise HubIntegrationError("Integration JSON exceeds the size limit.")
        return _object(json.loads(data), "integration JSON")
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise HubIntegrationError("Cannot read valid integration JSON.") from exc


@dataclass(frozen=True)
class HubConfig:
    mode: str = "disabled"
    environment: str = "production"
    origin: str = "http://127.0.0.1:5173"

    def require_development(self) -> None:
        if self.mode != "mock" or self.environment != "development":
            raise HubIntegrationError(
                "Hub integration is disabled. Live authentication is not implemented. "
                "Development requires DOXIE_HUB_MODE=mock and "
                "AUTHOR_NARRATOR_ENV=development."
            )
        try:
            parsed = urlsplit(self.origin)
            valid = (
                parsed.scheme == "http" and parsed.hostname in ("127.0.0.1", "localhost")
                and parsed.port is not None and 1 <= parsed.port <= 65535
                and not parsed.username and not parsed.password
                and parsed.path in ("", "/") and not parsed.query and not parsed.fragment
                and not any(c.isspace() for c in self.origin)
            )
        except ValueError:
            valid = False
        if not valid:
            raise HubIntegrationError("Development Hub origin must be a loopback HTTP origin with a port.")

    @property
    def base_url(self) -> str:
        self.require_development()
        return self.origin.rstrip("/")


@dataclass(frozen=True)
class HubIdentity:
    # Field names follow backend/identity/contracts.py. This instance is a MOCK,
    # not a claim that an OIDC identity was cryptographically verified.
    issuer: str
    subject: str
    email: str | None
    email_verified: bool
    auth_time: int | None
    amr: tuple[str, ...]
    acr: str | None


@dataclass(frozen=True)
class HubPreferences:
    theme: str
    notifications_enabled: bool
    reduced_motion: bool
    display_name: str = ""

    @classmethod
    def parse(cls, settings: dict, profile: dict) -> HubPreferences:
        theme = settings.get("theme", "system")
        if theme not in ("light", "dark", "system"):
            raise HubIntegrationError("Invalid Hub theme.")
        notifications = settings.get("notifications_enabled", True)
        motion = settings.get("reduced_motion", False)
        if type(notifications) is not bool or type(motion) is not bool:
            raise HubIntegrationError("Hub preference flags must be booleans.")
        name = profile.get("display_name", "")
        if not isinstance(name, str) or len(name) > 100 or any(ord(c) < 32 for c in name):
            raise HubIntegrationError("Invalid Hub display name.")
        return cls(theme, notifications, motion, name)


@dataclass(frozen=True)
class HubContext:
    identity: HubIdentity
    user_id: str
    workspace_id: str
    project_id: str | None
    project_name: str | None
    preferences: HubPreferences

    @property
    def binding_key(self) -> str:
        # Account identity is issuer + subject, NEVER an email address.
        value = [self.identity.issuer, self.identity.subject, self.user_id,
                 self.workspace_id, APP_SLUG, self.project_id]
        return hashlib.sha256(json.dumps(value).encode("utf-8")).hexdigest()


class HubAdapter(Protocol):
    def resolve_context(self, project_id: str | None) -> HubContext:
        """Resolve Hub identity, active entitlement, project access and preferences."""
        ...


class MockHubAdapter:
    """Explicit local fixture adapter. No HTTP requests and no account creation."""

    def __init__(self, config: HubConfig, fixture: Path):
        config.require_development()
        self.config = config
        self.fixture = Path(fixture)

    def resolve_context(self, project_id: str | None) -> HubContext:
        self.config.require_development()
        data = _read_json(self.fixture)
        if data.get("schema_version") != 1 or data.get("mode") != "mock":
            raise HubIntegrationError("Only version 1 development mock fixtures are supported.")
        application = _object(data.get("application"), "Hub application registry record")
        if (application.get("slug") != APP_SLUG or application.get("enabled") is not True
                or application.get("entitlement") != ENTITLEMENT
                or application.get("launch_path") != LAUNCH_PATH):
            raise HubIntegrationError("The Hub application registry does not enable Author-Narrator access.")
        identity = _object(data.get("identity"), "mock identity")
        issuer = _text(identity.get("issuer"), "identity issuer")
        subject = _text(identity.get("subject"), "identity subject")
        if issuer != "urn:doxie-hub:development":
            raise HubIntegrationError("Mock fixtures must use the development issuer.")
        if identity.get("amr") != ["mock"] or identity.get("email_verified") is not False:
            raise HubIntegrationError("Mock identity must be unverified and labelled mock.")
        if identity.get("auth_time") is not None or identity.get("acr") is not None:
            raise HubIntegrationError("Mock identity cannot assert production authentication.")
        email = identity.get("email")
        if email is not None:
            _text(email, "display email")
        profile = _object(data.get("profile"), "Hub profile")
        user_id = _identifier(profile.get("id"), "Hub user identifier")
        workspace_id = _identifier(data.get("workspace_id"), "Hub workspace identifier")
        entitlements = data.get("entitlements")
        if not isinstance(entitlements, list):
            raise HubIntegrationError("Missing Hub entitlements.")
        # Mirror Hub commerce/entitlements.py: ONLY active grants access.
        matching = [item for item in entitlements if isinstance(item, dict)
                    and item.get("workspace_id") == workspace_id
                    and item.get("app_slug") == APP_SLUG]
        if len(matching) != 1 or matching[0].get("status") != "active":
            raise HubIntegrationError("An active Author-Narrator Hub entitlement is required.")
        project_name = None
        if project_id is not None:
            _identifier(project_id, "Hub project identifier")
            projects = data.get("projects")
            if not isinstance(projects, list):
                raise HubIntegrationError("Missing Hub projects.")
            matches = [item for item in projects if isinstance(item, dict)
                       and item.get("id") == project_id
                       and item.get("app_slug") == APP_SLUG
                       and item.get("workspace_id") == workspace_id]
            if len(matches) != 1:
                raise HubIntegrationError("Hub project is unavailable for this account and application.")
            project_name = _text(matches[0].get("name"), "Hub project name")
        prefs = HubPreferences.parse(_object(data.get("settings", {}), "Hub settings"), profile)
        return HubContext(HubIdentity(issuer, subject, email, False, None, ("mock",), None),
                          user_id, workspace_id, project_id, project_name, prefs)


@dataclass
class HubSession:
    adapter: HubAdapter
    context: HubContext
    config: HubConfig
    section: str = "overview"

    def require_access(self) -> HubContext:
        self.config.require_development()
        current = self.adapter.resolve_context(self.context.project_id)
        if current.binding_key != self.context.binding_key:
            raise HubIntegrationError("Hub account context changed. Close and relaunch the application.")
        return current

    def shell_url(self, section: str | None = None) -> str:
        section = section or self.section
        if section not in SECTIONS:
            raise HubIntegrationError("Unknown Author-Narrator section.")
        url = f"{self.config.base_url}/apps/{APP_SLUG}/{section}"
        if self.context.project_id:
            url += "?" + urlencode({"project_id": self.context.project_id})
        return url

    @property
    def back_url(self) -> str:
        # Never accept return URLs from fixtures or query parameters.
        return self.config.base_url + "/"


def parse_shell_url(value: str, config: HubConfig) -> tuple[str | None, str]:
    config.require_development()
    if not isinstance(value, str) or any(c.isspace() for c in value):
        raise HubIntegrationError("Invalid Hub launch URL.")
    parsed = urlsplit(value)
    if f"{parsed.scheme}://{parsed.netloc}" != config.base_url or parsed.fragment:
        raise HubIntegrationError("Launch URL must use the configured development Hub origin.")
    parts = parsed.path.strip("/").split("/")
    if len(parts) not in (2, 3) or parts[:2] != ["apps", APP_SLUG]:
        raise HubIntegrationError("Launch URL is not an Author-Narrator shell route.")
    section = parts[2] if len(parts) == 3 else "overview"
    if section not in SECTIONS:
        raise HubIntegrationError("Unknown Author-Narrator section.")
    query = parse_qs(parsed.query, keep_blank_values=True)
    if set(query) - {"project_id"} or len(query.get("project_id", [])) > 1:
        raise HubIntegrationError("Only one project_id parameter is accepted; credentials are not accepted.")
    project_id = query.get("project_id", [None])[0]
    if project_id is not None:
        _identifier(project_id, "Hub project identifier")
    return project_id, section


@dataclass
class HubLaunch:
    session: HubSession | None
    qt_arguments: list[str]
    local_project: Path | None = None


def prepare_launch(arguments: list[str], environment: Mapping[str, str] | None = None) -> HubLaunch:
    env = os.environ if environment is None else environment
    parser = argparse.ArgumentParser(description="Author-Narrator (optional development Hub integration)")
    parser.add_argument("--hub-project-id")
    parser.add_argument("--hub-launch-url")
    parser.add_argument("--hub-mock-data", type=Path)
    parser.add_argument("--hub-origin", default="http://127.0.0.1:5173")
    parser.add_argument("--hub-local-project", type=Path)
    options, qt_arguments = parser.parse_known_args(arguments)
    if any(item.startswith("--hub-") for item in qt_arguments):
        raise HubIntegrationError("Unknown Hub option; credentials must not be passed on the command line.")
    requested = any(item.startswith("--hub-") for item in arguments)
    if not requested:
        return HubLaunch(None, qt_arguments)
    config = HubConfig(env.get("DOXIE_HUB_MODE", "disabled"),
                       env.get("AUTHOR_NARRATOR_ENV", "production"), options.hub_origin)
    config.require_development()
    if options.hub_mock_data is None:
        raise HubIntegrationError("An explicit --hub-mock-data fixture is required for development.")
    if options.hub_launch_url and options.hub_project_id:
        raise HubIntegrationError("Choose --hub-launch-url OR --hub-project-id, not both.")
    project_id, section = options.hub_project_id, "overview"
    if options.hub_launch_url:
        project_id, section = parse_shell_url(options.hub_launch_url, config)
    if options.hub_local_project and not project_id:
        raise HubIntegrationError("A Hub project identifier is required before selecting a local project.")
    adapter = MockHubAdapter(config, options.hub_mock_data)
    context = adapter.resolve_context(project_id)
    return HubLaunch(HubSession(adapter, context, config, section), qt_arguments,
                     options.hub_local_project)


class ProjectBindings:
    """Development convenience links, NOT an OS security boundary.

    Only this sidecar is written. Existing project metadata, manuscripts, voice
    samples and audio are never rewritten by the integration adapter.
    """

    def __init__(self, path: Path):
        self.path = Path(path)

    def _records(self) -> dict:
        if not self.path.exists():
            return {}
        data = _read_json(self.path)
        if data.get("schema_version") != 1:
            raise HubIntegrationError("Unsupported Hub project-link version.")
        return _object(data.get("links"), "Hub project links")

    @staticmethod
    def validate_local_project(path: Path) -> Path:
        resolved = Path(path).expanduser().resolve()
        data = _read_json(resolved / "project.json")
        _text(data.get("name"), "local project name")
        return resolved

    def lookup(self, session: HubSession) -> Path | None:
        context = session.require_access()
        if context.project_id is None:
            return None
        value = self._records().get(context.binding_key)
        if value is None:
            return None
        if not isinstance(value, str):
            raise HubIntegrationError("Invalid saved Hub project link.")
        return self.validate_local_project(Path(value))

    def check(self, session: HubSession, path: Path) -> Path:
        context = session.require_access()
        if context.project_id is None:
            raise HubIntegrationError("Select a project in Doxie Hub before linking a local project.")
        resolved = self.validate_local_project(path)
        links = self._records()
        previous = links.get(context.binding_key)
        if previous is not None and Path(previous).resolve() != resolved:
            raise HubIntegrationError("This Hub project is already linked to another local project.")
        if any(key != context.binding_key and Path(value).resolve() == resolved
               for key, value in links.items() if isinstance(value, str)):
            raise HubIntegrationError("This local project is already linked to another Hub context.")
        return resolved

    def bind(self, session: HubSession, path: Path) -> None:
        resolved = self.check(session, path)
        links = self._records()
        links[session.context.binding_key] = str(resolved)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=self.path.parent,
                                             prefix=".hub-links-", delete=False) as handle:
                temporary = Path(handle.name)
                json.dump({"schema_version": 1, "links": links}, handle, indent=2)
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, self.path)
        except OSError as exc:
            raise HubIntegrationError("Cannot save the Hub project link. Original project files are unchanged.") from exc
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
