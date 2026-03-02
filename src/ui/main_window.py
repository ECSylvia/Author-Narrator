from PySide6.QtWidgets import (
    QMainWindow, QApplication, QMessageBox, QLabel, QVBoxLayout, QWidget,
    QStackedWidget, QSplitter, QListWidget, QTextEdit, QHBoxLayout,
    QPushButton, QFileDialog, QGroupBox, QFrame,
)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt
from ..core.version_manager import load_version
from ..core.manuscript_parser import ManuscriptParser
from ..core.elevenlabs_generator import estimate_cost, estimate_cost_for_chapters
from .welcome_screen import WelcomeScreen
from .consent_wizard import ConsentWizard
from .voice_tools import VoiceReviewDialog, SamplePageDialog
from .audiobook_dialog import AudiobookDialog
from .settings_dialog import SettingsDialog
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.version = load_version()
        self.setWindowTitle(f"Author Narrator {self.version}")
        self.resize(1200, 800)

        self.statusBar().showMessage(f"Ready - {self.version}")

        self.current_project = None
        self.chapters = []

        self.init_ui()
        self.create_menus()

    # ------------------------------------------------------------------ UI
    def init_ui(self):
        self.stack = QStackedWidget()
        self.setCentralWidget(self.stack)

        # View 1: Welcome Screen
        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.project_opened.connect(self.on_project_opened)
        self.stack.addWidget(self.welcome_screen)

        # View 2: Project Workspace
        self.project_view = QWidget()
        pv_layout = QVBoxLayout(self.project_view)

        # Toolbar row
        toolbar = QHBoxLayout()
        self.lbl_project_name = QLabel("No Project Loaded")
        self.lbl_project_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        toolbar.addWidget(self.lbl_project_name)
        toolbar.addStretch()

        btn_import = QPushButton("Import Manuscript")
        btn_import.clicked.connect(self.browse_manuscript)
        toolbar.addWidget(btn_import)

        self.btn_generate_all = QPushButton("Generate Full Audiobook")
        self.btn_generate_all.setStyleSheet(
            "QPushButton { background-color: #0078d4; color: white; border-radius: 4px; "
            "padding: 6px 16px; font-weight: bold; }"
            "QPushButton:hover { background-color: #106ebe; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.btn_generate_all.setEnabled(False)
        self.btn_generate_all.clicked.connect(self.generate_audiobook)
        toolbar.addWidget(self.btn_generate_all)

        pv_layout.addLayout(toolbar)

        # Main 3-pane splitter: Chapters | Editor | Cost sidebar
        main_splitter = QSplitter(Qt.Horizontal)

        # --- Left pane: chapter list ---
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)

        sidebar_layout.addWidget(QLabel("Chapters"))
        self.chapter_list = QListWidget()
        self.chapter_list.currentRowChanged.connect(self.display_chapter)
        sidebar_layout.addWidget(self.chapter_list)

        main_splitter.addWidget(sidebar_widget)

        # --- Center pane: editor + per-chapter buttons ---
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(0, 0, 0, 0)

        center_layout.addWidget(QLabel("Manuscript Text"))
        self.editor = QTextEdit()
        self.editor.setReadOnly(True)
        center_layout.addWidget(self.editor)

        # Per-chapter action row
        ch_actions = QHBoxLayout()

        self.btn_sample_chapter = QPushButton("Preview Sample (first ~1000 chars)")
        self.btn_sample_chapter.setEnabled(False)
        self.btn_sample_chapter.clicked.connect(self.sample_current_chapter)
        ch_actions.addWidget(self.btn_sample_chapter)

        self.btn_generate_chapter = QPushButton("Generate This Chapter")
        self.btn_generate_chapter.setEnabled(False)
        self.btn_generate_chapter.clicked.connect(self.generate_current_chapter)
        ch_actions.addWidget(self.btn_generate_chapter)

        ch_actions.addStretch()
        center_layout.addLayout(ch_actions)

        main_splitter.addWidget(center_widget)

        # --- Right pane: cost sidebar ---
        self.cost_panel = self._build_cost_panel()
        main_splitter.addWidget(self.cost_panel)

        main_splitter.setStretchFactor(0, 1)
        main_splitter.setStretchFactor(1, 4)
        main_splitter.setStretchFactor(2, 1)
        main_splitter.setSizes([180, 700, 220])

        pv_layout.addWidget(main_splitter)

        self.stack.addWidget(self.project_view)
        self.stack.setCurrentWidget(self.welcome_screen)

    def _build_cost_panel(self):
        panel = QFrame()
        panel.setFrameShape(QFrame.StyledPanel)
        layout = QVBoxLayout(panel)

        title = QLabel("ElevenLabs Cost Estimate")
        title.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(title)

        layout.addSpacing(8)

        self.lbl_total_chars = QLabel("Total characters: —")
        layout.addWidget(self.lbl_total_chars)

        self.lbl_total_cost = QLabel("Estimated cost: —")
        self.lbl_total_cost.setStyleSheet("font-size: 16px; font-weight: bold; color: #0078d4;")
        layout.addWidget(self.lbl_total_cost)

        layout.addSpacing(12)

        sep = QFrame()
        sep.setFrameShape(QFrame.HLine)
        sep.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep)

        layout.addSpacing(4)

        lbl_sel = QLabel("Selected Chapter")
        lbl_sel.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_sel)

        self.lbl_ch_name = QLabel("—")
        self.lbl_ch_name.setWordWrap(True)
        layout.addWidget(self.lbl_ch_name)

        self.lbl_ch_chars = QLabel("Characters: —")
        layout.addWidget(self.lbl_ch_chars)

        self.lbl_ch_cost = QLabel("Est. cost: —")
        self.lbl_ch_cost.setStyleSheet("font-weight: bold;")
        layout.addWidget(self.lbl_ch_cost)

        self.lbl_ch_sample_cost = QLabel("Sample cost: —")
        layout.addWidget(self.lbl_ch_sample_cost)

        layout.addSpacing(12)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.HLine)
        sep2.setFrameShadow(QFrame.Sunken)
        layout.addWidget(sep2)

        layout.addSpacing(4)

        note = QLabel(
            "<small>Costs are estimates based on $0.30 / 1K chars "
            "(ElevenLabs Starter tier, Multilingual v2). "
            "Actual cost depends on your plan.</small>"
        )
        note.setWordWrap(True)
        note.setStyleSheet("color: #888;")
        layout.addWidget(note)

        layout.addStretch()
        return panel

    # ------------------------------------------------------------------ Menus
    def create_menus(self):
        menu = self.menuBar()

        # --- File Menu ---
        file_menu = menu.addMenu("File")

        close_proj_action = QAction("Close Project", self)
        close_proj_action.triggered.connect(self.close_project)
        file_menu.addAction(close_proj_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # --- Edit Menu (Settings lives here so macOS doesn't swallow it) ---
        edit_menu = menu.addMenu("Edit")

        settings_action = QAction("Preferences…", self)
        settings_action.setMenuRole(QAction.MenuRole.NoRole)
        settings_action.triggered.connect(self.show_settings)
        edit_menu.addAction(settings_action)

        # --- Voice Menu ---
        self.voice_menu = menu.addMenu("Voice")

        act_record = QAction("Record New Sample", self)
        act_record.triggered.connect(self.record_new_sample)
        self.voice_menu.addAction(act_record)

        act_review = QAction("Review Voice Sample", self)
        act_review.triggered.connect(self.review_sample)
        self.voice_menu.addAction(act_review)

        self.voice_menu.addSeparator()

        act_hear = QAction("Hear a Sample Page", self)
        act_hear.triggered.connect(self.hear_sample_page)
        self.voice_menu.addAction(act_hear)

        self.voice_menu.addSeparator()

        act_generate = QAction("Generate Full Audiobook…", self)
        act_generate.triggered.connect(self.generate_audiobook)
        self.voice_menu.addAction(act_generate)

        # --- About Menu ---
        about_menu = menu.addMenu("About")
        about_action = QAction("About Author Narrator", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)

    # ------------------------------------------------------------------ Manuscript
    def browse_manuscript(self):
        if not self.current_project:
            return

        fname, _ = QFileDialog.getOpenFileName(
            self, "Import Manuscript", "",
            "Markdown/Text (*.md *.txt);;All Files (*)",
        )
        if fname:
            try:
                self.chapters = ManuscriptParser.parse_file(fname)
                self.update_chapter_list()
                QMessageBox.information(self, "Success", f"Imported {len(self.chapters)} chapters.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to parse: {e}")

    def update_chapter_list(self):
        self.chapter_list.clear()
        for chap in self.chapters:
            self.chapter_list.addItem(f"{chap.order}. {chap.title}")

        has_chapters = bool(self.chapters)
        self.btn_generate_all.setEnabled(has_chapters)

        if has_chapters:
            self.chapter_list.setCurrentRow(0)
            self._update_total_cost()
        else:
            self._clear_cost_panel()

    def display_chapter(self, row):
        if 0 <= row < len(self.chapters):
            ch = self.chapters[row]
            self.editor.setPlainText(ch.content)
            self.btn_sample_chapter.setEnabled(True)
            self.btn_generate_chapter.setEnabled(True)
            self._update_chapter_cost(ch)
        else:
            self.btn_sample_chapter.setEnabled(False)
            self.btn_generate_chapter.setEnabled(False)

    # ------------------------------------------------------------------ Cost panel
    def _update_total_cost(self):
        total_chars, total_cost = estimate_cost_for_chapters(self.chapters)
        self.lbl_total_chars.setText(f"Total characters: {total_chars:,}")
        self.lbl_total_cost.setText(f"Estimated cost: ${total_cost:,.2f}")

    def _update_chapter_cost(self, ch):
        chars = len(ch.content)
        cost = estimate_cost(ch.content)
        sample_chars = min(chars, 1000)
        sample_cost = (sample_chars / 1000) * 0.30

        self.lbl_ch_name.setText(ch.title)
        self.lbl_ch_chars.setText(f"Characters: {chars:,}")
        self.lbl_ch_cost.setText(f"Est. cost: ${cost:,.2f}")
        self.lbl_ch_sample_cost.setText(f"Sample cost (~{sample_chars:,} chars): ${sample_cost:,.2f}")

    def _clear_cost_panel(self):
        self.lbl_total_chars.setText("Total characters: —")
        self.lbl_total_cost.setText("Estimated cost: —")
        self.lbl_ch_name.setText("—")
        self.lbl_ch_chars.setText("Characters: —")
        self.lbl_ch_cost.setText("Est. cost: —")
        self.lbl_ch_sample_cost.setText("Sample cost: —")

    # ------------------------------------------------------------------ Project lifecycle
    def on_project_opened(self, project):
        consent_path = os.path.join(project.path, "consent.json")
        if not os.path.exists(consent_path):
            wizard = ConsentWizard(project.path, self)
            if not wizard.exec():
                return

        self.current_project = project
        self.lbl_project_name.setText(f"Active Project: {project.name}")
        self.setWindowTitle(f"Author Narrator {self.version} - {project.name}")

        self.chapters = []
        self.chapter_list.clear()
        self.editor.clear()
        self._clear_cost_panel()

        self.stack.setCurrentWidget(self.project_view)

    def close_project(self):
        self.current_project = None
        self.chapters = []
        self.btn_generate_all.setEnabled(False)
        self.btn_sample_chapter.setEnabled(False)
        self.btn_generate_chapter.setEnabled(False)
        self._clear_cost_panel()
        self.lbl_project_name.setText("No Project Loaded")
        self.setWindowTitle(f"Author Narrator {self.version}")
        self.stack.setCurrentWidget(self.welcome_screen)

    # ------------------------------------------------------------------ Generation
    def generate_audiobook(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open or create a project first.")
            return
        if not self.chapters:
            QMessageBox.warning(self, "No Manuscript", "Import a manuscript before generating audio.")
            return

        dlg = AudiobookDialog(self.chapters, self.current_project, self)
        dlg.exec()

    def generate_current_chapter(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open or create a project first.")
            return

        row = self.chapter_list.currentRow()
        if row < 0 or row >= len(self.chapters):
            return

        ch = self.chapters[row]
        dlg = AudiobookDialog([ch], self.current_project, self)
        dlg.setWindowTitle(f"Generate Chapter: {ch.title}")
        dlg.exec()

    def sample_current_chapter(self):
        """Generate a short TTS preview of the selected chapter's opening text."""
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open or create a project first.")
            return

        row = self.chapter_list.currentRow()
        if row < 0 or row >= len(self.chapters):
            return

        ch = self.chapters[row]
        preview_text = ch.content[:1000]
        if len(ch.content) > 1000:
            last_period = preview_text.rfind('.')
            if last_period > 500:
                preview_text = preview_text[:last_period + 1]

        dlg = SamplePageDialog(self)
        dlg.editor.setPlainText(preview_text)
        dlg.setWindowTitle(f"Sample Preview: {ch.title}")
        dlg.exec()

    # ------------------------------------------------------------------ Voice
    def record_new_sample(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open or create a project first.")
            return
        wizard = ConsentWizard(self.current_project.path, self)
        wizard.exec()

    def review_sample(self):
        if not self.current_project:
            QMessageBox.warning(self, "No Project", "Please open or create a project first.")
            return
        dlg = VoiceReviewDialog(self.current_project.path, self)
        dlg.exec()

    def hear_sample_page(self):
        dlg = SamplePageDialog(self)
        dlg.exec()

    # ------------------------------------------------------------------ Settings / About
    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def show_about(self):
        text = (
            f"Author Narrator {self.version}\n\n"
            "This is not a free app.\n\n"
            "Copyright © Doxie Enterprises, LLC 2026\n"
            "All Rights Reserved.\n\n"
            "For pricing info please contact: Eric.sylvia@bamecs.com"
        )
        QMessageBox.about(self, "About Author Narrator", text)
