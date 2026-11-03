"""Offline integration tests: no credentials, Qt, GPU, paid API or Hub server."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src.integrations.doxie_hub import (
    HubConfig, HubIntegrationError, HubSession, MockHubAdapter,
    ProjectBindings, SECTIONS, prepare_launch,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "doxie_hub" / "dev-context.json"
DEV = {"DOXIE_HUB_MODE": "mock", "AUTHOR_NARRATOR_ENV": "development"}


class HubIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.fixture = self.directory / "context.json"
        self.data = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.save()
        self.config = HubConfig("mock", "development")
        self.adapter = MockHubAdapter(self.config, self.fixture)

    def save(self):
        self.fixture.write_text(json.dumps(self.data), encoding="utf-8")

    def session(self):
        return HubSession(self.adapter, self.adapter.resolve_context("sample"), self.config)

    def launch(self, *extra, env=None):
        return prepare_launch(["--hub-mock-data", str(self.fixture), *extra],
                              DEV if env is None else env)

    def project(self, name="original"):
        directory = self.directory / name
        directory.mkdir()
        (directory / "project.json").write_text(
            '{"name":"Original title","unknown_future_field":true}', encoding="utf-8")
        (directory / "consent.json").write_text('{"accepted":true}', encoding="utf-8")
        (directory / "manuscript.txt").write_text("Author-owned manuscript.", encoding="utf-8")
        (directory / "voice_profile.wav").write_bytes(b"existing-voice-do-not-touch")
        (directory / "chapter.mp3").write_bytes(b"existing-audio-do-not-touch")
        return directory

    def test_standalone_requires_no_fixture_or_hub(self):
        result = prepare_launch([], {})
        self.assertIsNone(result.session)
        self.assertIsNone(result.local_project)

    def test_standalone_preserves_qt_options(self):
        self.assertEqual(prepare_launch(["-platform", "offscreen"], {}).qt_arguments,
                         ["-platform", "offscreen"])

    def test_disabled_by_default(self):
        with self.assertRaises(HubIntegrationError):
            self.launch("--hub-project-id", "sample", env={})

    def test_mock_requires_both_development_switches(self):
        for env in ({"DOXIE_HUB_MODE": "mock"}, {"AUTHOR_NARRATOR_ENV": "development"},
                    {"DOXIE_HUB_MODE": "live", "AUTHOR_NARRATOR_ENV": "development"},
                    {"DOXIE_HUB_MODE": "mock", "AUTHOR_NARRATOR_ENV": "production"}):
            with self.subTest(env=env), self.assertRaises(HubIntegrationError):
                self.launch(env=env)

    def test_explicit_fixture_required(self):
        with self.assertRaises(HubIntegrationError):
            prepare_launch(["--hub-project-id", "sample"], DEV)

    def test_accepts_hub_project_id(self):
        context = self.launch("--hub-project-id", "sample").session.context
        self.assertEqual(context.project_id, "sample")
        self.assertEqual(context.project_name, "Development Audiobook")
        self.assertEqual(context.identity.amr, ("mock",))

    def test_shell_routes_match_catalog_and_preserve_context(self):
        for section in SECTIONS:
            with self.subTest(section=section):
                url = f"http://127.0.0.1:5173/apps/author-narrator/{section}?project_id=sample"
                session = self.launch("--hub-launch-url", url).session
                self.assertEqual(session.section, section)
                self.assertEqual(session.shell_url(), url)
                self.assertEqual(session.back_url, "http://127.0.0.1:5173/")

    def test_overview_without_project_supported(self):
        session = self.launch("--hub-launch-url", "http://127.0.0.1:5173/apps/author-narrator").session
        self.assertIsNone(session.context.project_id)
        self.assertEqual(session.section, "overview")

    def test_bad_shell_urls_rejected(self):
        urls = ["https://evil.invalid/apps/author-narrator?project_id=sample",
                "http://127.0.0.1:5173/apps/harbor?project_id=sample",
                "http://127.0.0.1:5173/apps/author-narrator/admin?project_id=sample",
                "http://127.0.0.1:5173/apps/author-narrator?project_id=sample&project_id=other",
                "http://127.0.0.1:5173/apps/author-narrator?project_id=",
                "http://127.0.0.1:5173/apps/author-narrator?project_id=../escape",
                "http://127.0.0.1:5173/apps/author-narrator?token=secret",
                "http://127.0.0.1:5173/apps/author-narrator?return_url=https://evil.invalid",
                "http://127.0.0.1:5173/apps/author-narrator#token=secret"]
        for url in urls:
            with self.subTest(url=url), self.assertRaises(HubIntegrationError):
                self.launch("--hub-launch-url", url)

    def test_no_remote_origin_in_mock_mode(self):
        for origin in ("https://doxie.invalid", "http://0.0.0.0:5173", "http://127.0.0.1.evil:5173",
                       "http://user@127.0.0.1:5173", "http://127.0.0.1:5173/path",
                       "http://127.0.0.1:bad", "http://127.0.0.1"):
            with self.subTest(origin=origin), self.assertRaises(HubIntegrationError):
                self.launch("--hub-origin", origin)

    def test_registry_entitlement_and_enabled_flag_must_match(self):
        for field, value in (("entitlement", "harbor.access"), ("enabled", False),
                             ("launch_path", "/apps/harbor"), ("slug", "harbor")):
            saved = copy.deepcopy(self.data)
            self.data["application"][field] = value
            self.save()
            with self.subTest(field=field), self.assertRaises(HubIntegrationError):
                self.session()
            self.data = saved

    def test_active_entitlement_required(self):
        for status in ("pending", "on-hold", "cancelled", "expired", "unknown", None):
            self.data["entitlements"][0]["status"] = status
            self.save()
            with self.subTest(status=status), self.assertRaises(HubIntegrationError):
                self.session()

    def test_duplicate_entitlement_fails_closed(self):
        self.data["entitlements"].append(copy.deepcopy(self.data["entitlements"][0]))
        self.save()
        with self.assertRaises(HubIntegrationError):
            self.session()

    def test_other_app_does_not_grant_access(self):
        self.data["entitlements"][0]["app_slug"] = "harbor"
        self.save()
        with self.assertRaises(HubIntegrationError):
            self.session()

    def test_other_workspace_does_not_grant_access(self):
        self.data["entitlements"][0]["workspace_id"] = "someone-else"
        self.save()
        with self.assertRaises(HubIntegrationError):
            self.session()

    def test_project_workspace_and_application_must_match(self):
        for key, value in (("workspace_id", "someone-else"), ("app_slug", "harbor"), ("id", "another")):
            saved = copy.deepcopy(self.data)
            self.data["projects"][0][key] = value
            self.save()
            with self.subTest(key=key), self.assertRaises(HubIntegrationError):
                self.session()
            self.data = saved

    def test_unknown_project_rejected(self):
        with self.assertRaises(HubIntegrationError):
            self.adapter.resolve_context("missing")

    def test_identity_email_is_not_account_link_key(self):
        first = self.session().context.binding_key
        self.data["identity"]["subject"] = "another-subject"
        self.save()
        self.assertNotEqual(first, self.session().context.binding_key)

    def test_verified_claim_cannot_masquerade_as_mock(self):
        self.data["identity"]["email_verified"] = True
        self.save()
        with self.assertRaises(HubIntegrationError):
            self.session()

    def test_preferences_are_session_scoped_and_match_hub(self):
        self.data["settings"] = {"theme": "dark", "notifications_enabled": False, "reduced_motion": True}
        self.save()
        before = self.fixture.read_bytes()
        prefs = self.session().context.preferences
        self.assertEqual((prefs.theme, prefs.notifications_enabled, prefs.reduced_motion), ("dark", False, True))
        self.assertEqual(self.fixture.read_bytes(), before)

    def test_bad_preferences_rejected(self):
        for settings in ({"theme": "purple"}, {"notifications_enabled": "false"}, {"reduced_motion": 1}):
            self.data["settings"] = settings
            self.save()
            with self.subTest(settings=settings), self.assertRaises(HubIntegrationError):
                self.session()

    def test_revoked_access_rechecked(self):
        session = self.session()
        self.data["entitlements"][0]["status"] = "cancelled"
        self.save()
        with self.assertRaises(HubIntegrationError):
            session.require_access()

    def test_identity_change_requires_relaunch(self):
        session = self.session()
        self.data["identity"]["subject"] = "another-subject"
        self.save()
        with self.assertRaises(HubIntegrationError):
            session.require_access()

    def test_linking_preserves_every_project_byte(self):
        project = self.project()
        before = {file.name: file.read_bytes() for file in project.iterdir()}
        store = ProjectBindings(self.directory / "links" / "dev-links.json")
        session = self.session()
        store.bind(session, project)
        self.assertEqual(store.lookup(session), project.resolve())
        self.assertEqual(before, {file.name: file.read_bytes() for file in project.iterdir()})

    def test_links_do_not_cross_accounts(self):
        project = self.project()
        store = ProjectBindings(self.directory / "links.json")
        store.bind(self.session(), project)
        self.data["identity"]["subject"] = "another-subject"
        self.save()
        other = self.session()
        self.assertIsNone(store.lookup(other))
        with self.assertRaises(HubIntegrationError):
            store.bind(other, project)

    def test_relink_requires_explicit_manual_review(self):
        store = ProjectBindings(self.directory / "links.json")
        session = self.session()
        store.bind(session, self.project("one"))
        with self.assertRaises(HubIntegrationError):
            store.bind(session, self.project("two"))

    def test_missing_local_project_is_not_created(self):
        path = self.directory / "missing"
        with self.assertRaises(HubIntegrationError):
            ProjectBindings(self.directory / "links.json").bind(self.session(), path)
        self.assertFalse(path.exists())

    def test_malformed_or_oversized_fixture_is_rejected(self):
        for text in ("not json", "[]", " " * (256 * 1024 + 1)):
            self.fixture.write_text(text, encoding="utf-8")
            with self.subTest(size=len(text)), self.assertRaises(HubIntegrationError):
                self.session()

    def test_conflicting_launch_inputs_rejected(self):
        with self.assertRaises(HubIntegrationError):
            self.launch("--hub-project-id", "sample", "--hub-launch-url",
                        "http://127.0.0.1:5173/apps/author-narrator")

    def test_unknown_hub_option_not_forwarded_to_qt(self):
        with self.assertRaises(HubIntegrationError):
            self.launch("--hub-token", "secret")

    def test_main_rejects_hub_launch_before_loading_qt_or_provider(self):
        environment = dict(os.environ)
        environment.pop("DOXIE_HUB_MODE", None)
        environment.pop("AUTHOR_NARRATOR_ENV", None)
        result = subprocess.run([sys.executable, "src/main.py", "--hub-project-id", "sample"],
                                cwd=ROOT, env=environment, capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2)
        self.assertIn("Live authentication is not implemented", result.stderr)
        self.assertNotIn("ModuleNotFoundError", result.stderr)


if __name__ == "__main__":
    unittest.main()
