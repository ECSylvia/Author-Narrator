"""Optional Hub shell around the existing desktop window, never its engine."""
from functools import wraps
from pathlib import Path

from PySide6.QtCore import QTimer, QUrl, Qt
from PySide6.QtGui import QAction, QColor, QDesktopServices, QPalette
from PySide6.QtWidgets import QApplication, QLabel, QMessageBox, QToolBar

from .main_window import MainWindow
from ..core.project_manager import ProjectManager
from ..integrations.doxie_hub import HubIntegrationError, HubSession, ProjectBindings


def _requires_hub_project(method):
    @wraps(method)
    def guarded(self, *args, **kwargs):
        try:
            self.hub_session.require_access()
            if not self.current_project or not self._hub_project_linked:
                raise HubIntegrationError("Open and link a local project before using this feature.")
            linked = self.hub_bindings.lookup(self.hub_session)
            if linked != Path(self.current_project.path).resolve():
                raise HubIntegrationError("The local project does not match this Hub launch.")
        except HubIntegrationError as exc:
            QMessageBox.warning(self, "Doxie Hub access", str(exc))
            return
        return method(self, *args, **kwargs)
    return guarded


class HubMainWindow(MainWindow):
    def __init__(self, session: HubSession, bindings: ProjectBindings,
                 local_project: Path | None = None):
        self.hub_session = session
        self.hub_bindings = bindings
        self._hub_project_linked = False
        self._local_project_argument = local_project
        session.require_access()
        super().__init__()
        self._add_hub_navigation()
        self._apply_hub_preferences()
        if session.context.project_id is None:
            self.welcome_screen.setEnabled(False)
        QTimer.singleShot(0, self._open_linked_project)

    def _add_hub_navigation(self):
        toolbar = QToolBar("Doxie Hub", self)
        toolbar.setObjectName("doxieHubToolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        back = QAction("Back to Doxie Hub", self)
        back.triggered.connect(self.back_to_hub)
        toolbar.addAction(back)
        shell = QAction("Open Hub product section", self)
        shell.triggered.connect(self.open_hub_section)
        toolbar.addAction(shell)
        toolbar.addSeparator()
        context = self.hub_session.context
        name = context.preferences.display_name or "Development account"
        project = context.project_id or "select a project in Hub"
        self.hub_context_label = QLabel(
            f"DEVELOPMENT MOCK ONLY | {name} | Hub project: {project}", self
        )
        self.hub_context_label.setTextFormat(Qt.TextFormat.PlainText)
        self.hub_context_label.setWordWrap(True)
        toolbar.addWidget(self.hub_context_label)
        self.statusBar().showMessage(
            f"Hub section: {self.hub_session.section}. Live Hub authentication is disabled."
        )

    def _apply_hub_preferences(self):
        prefs = self.hub_session.context.preferences
        self.setProperty("hub_notifications_enabled", prefs.notifications_enabled)
        self.setProperty("hub_reduced_motion", prefs.reduced_motion)
        # Context values stay session-scoped; do not write SettingsManager.
        # This shell has no background notifications or animations to suppress.
        if prefs.theme == "system":
            return
        palette = QPalette(QApplication.instance().palette())
        dark = prefs.theme == "dark"
        background, base, foreground = (("#292929", "#202020", "#f5f5f5") if dark
                                        else ("#f5f5f5", "#ffffff", "#202020"))
        for role in (QPalette.ColorRole.Window, QPalette.ColorRole.Button):
            palette.setColor(role, QColor(background))
        palette.setColor(QPalette.ColorRole.Base, QColor(base))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(background))
        for role in (QPalette.ColorRole.WindowText, QPalette.ColorRole.Text,
                     QPalette.ColorRole.ButtonText):
            palette.setColor(role, QColor(foreground))
        self.setPalette(palette)

    def back_to_hub(self):
        # Navigation never closes the project or starts a narration job.
        if not QDesktopServices.openUrl(QUrl(self.hub_session.back_url)):
            QMessageBox.warning(self, "Doxie Hub", "Could not open the local Hub in your browser.")

    def open_hub_section(self):
        if not QDesktopServices.openUrl(QUrl(self.hub_session.shell_url())):
            QMessageBox.warning(self, "Doxie Hub", "Could not open the Hub product section.")

    def _open_linked_project(self):
        try:
            path = self._local_project_argument or self.hub_bindings.lookup(self.hub_session)
            if path is not None:
                path = self.hub_bindings.check(self.hub_session, path)
                self.on_project_opened(ProjectManager.load_project(str(path)))
        except (HubIntegrationError, OSError, ValueError, KeyError) as exc:
            QMessageBox.warning(self, "Doxie Hub project", str(exc))

    def on_project_opened(self, project):
        try:
            path = self.hub_bindings.check(self.hub_session, Path(project.path))
            existing = self.hub_bindings.lookup(self.hub_session)
            if existing is None:
                answer = QMessageBox.question(
                    self, "Link local project to Doxie Hub",
                    "Link this local project to the selected Hub project for development?\n\n"
                    f"Local: {path}\nHub: {self.hub_session.context.project_id}\n\n"
                    "Project files will not be moved or rewritten by this link.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            # Preserve the original voice consent flow and project-open behavior.
            super().on_project_opened(project)
            if self.current_project is project:
                self._hub_project_linked = False
                self.hub_bindings.bind(self.hub_session, path)
                self._hub_project_linked = True
        except HubIntegrationError as exc:
            QMessageBox.warning(self, "Doxie Hub project", str(exc))

    def close_project(self):
        super().close_project()
        self._hub_project_linked = False

    @_requires_hub_project
    def browse_manuscript(self):
        return super().browse_manuscript()

    @_requires_hub_project
    def generate_audiobook(self):
        return super().generate_audiobook()

    @_requires_hub_project
    def generate_current_chapter(self):
        return super().generate_current_chapter()

    @_requires_hub_project
    def sample_current_chapter(self):
        return super().sample_current_chapter()

    @_requires_hub_project
    def record_new_sample(self):
        return super().record_new_sample()

    @_requires_hub_project
    def review_sample(self):
        return super().review_sample()

    @_requires_hub_project
    def hear_sample_page(self):
        return super().hear_sample_page()
