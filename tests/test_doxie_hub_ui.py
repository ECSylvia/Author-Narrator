"""Native UI smoke tests. Skip explicitly when desktop dependencies are absent."""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
HAS_DESKTOP = all(importlib.util.find_spec(name) is not None for name in ("PySide6", "elevenlabs"))
ROOT = Path(__file__).resolve().parents[1]


@unittest.skipUnless(HAS_DESKTOP, "PySide6 and elevenlabs are required for native UI smoke tests")
class HubWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from PySide6.QtWidgets import QApplication
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        from src.integrations.doxie_hub import HubConfig, HubSession, MockHubAdapter, ProjectBindings
        from src.ui.hub_window import HubMainWindow
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.fixture = self.root / "fixture.json"
        self.data = json.loads((ROOT / "examples/doxie_hub/dev-context.json").read_text(encoding="utf-8"))
        self.fixture.write_text(json.dumps(self.data), encoding="utf-8")
        config = HubConfig("mock", "development")
        adapter = MockHubAdapter(config, self.fixture)
        session = HubSession(adapter, adapter.resolve_context("sample"), config)
        self.window = HubMainWindow(session, ProjectBindings(self.root / "links.json"))
        self.app.processEvents()
        self.addCleanup(self.window.close)
        self.addCleanup(self.window.deleteLater)

    def _open_project(self):
        from PySide6.QtWidgets import QMessageBox
        from src.core.project_manager import ProjectManager
        directory = self.root / "existing"
        directory.mkdir()
        (directory / "project.json").write_text('{"name":"Existing project"}', encoding="utf-8")
        (directory / "consent.json").write_text('{"accepted":true}', encoding="utf-8")
        with patch("src.ui.hub_window.QMessageBox.question", return_value=QMessageBox.StandardButton.Yes):
            self.window.on_project_opened(ProjectManager.load_project(str(directory)))
        return directory

    def test_wraps_original_window_and_exposes_development_label(self):
        from src.ui.main_window import MainWindow
        self.assertIsInstance(self.window, MainWindow)
        self.assertIn("DEVELOPMENT MOCK ONLY", self.window.hub_context_label.text())
        self.assertIn("sample", self.window.hub_context_label.text())

    def test_back_navigation_preserves_current_project(self):
        self._open_project()
        original = self.window.current_project
        with patch("src.ui.hub_window.QDesktopServices") as browser:
            browser.openUrl.return_value = True
            self.window.back_to_hub()
            self.assertEqual(browser.openUrl.call_args.args[0].toString(), "http://127.0.0.1:5173/")
        self.assertIs(self.window.current_project, original)

    def test_linked_project_delegates_to_existing_functionality(self):
        self._open_project()
        with patch("src.ui.main_window.MainWindow.generate_audiobook") as original:
            self.window.generate_audiobook()
            original.assert_called_once()

    def test_revoked_entitlement_blocks_engine_invocation(self):
        self._open_project()
        self.data["entitlements"][0]["status"] = "cancelled"
        self.fixture.write_text(json.dumps(self.data), encoding="utf-8")
        with patch("src.ui.hub_window.QMessageBox.warning") as warning, \
                patch("src.ui.main_window.MainWindow.generate_audiobook") as original:
            self.window.generate_audiobook()
            original.assert_not_called()
            warning.assert_called_once()

    def test_open_project_keeps_original_metadata_bytes(self):
        directory = self._open_project()
        self.assertEqual((directory / "project.json").read_text(encoding="utf-8"),
                         '{"name":"Existing project"}')
        self.assertTrue(self.window._hub_project_linked)
        self.window.close_project()
        self.assertFalse(self.window._hub_project_linked)


if __name__ == "__main__":
    unittest.main()
