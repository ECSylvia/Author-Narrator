from PySide6.QtWidgets import (QMainWindow, QApplication, QMessageBox, QLabel, QVBoxLayout, QWidget, QStackedWidget, 
                               QSplitter, QListWidget, QTextEdit, QHBoxLayout, QPushButton, QFileDialog)
from PySide6.QtGui import QAction, QIcon
from PySide6.QtCore import Qt
from ..core.version_manager import load_version
from ..core.manuscript_parser import ManuscriptParser
from .welcome_screen import WelcomeScreen
from .consent_wizard import ConsentWizard
from .voice_tools import VoiceReviewDialog, SamplePageDialog
from .settings_dialog import SettingsDialog
import os

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.version = load_version()
        self.setWindowTitle(f"Author Narrator {self.version}")
        self.resize(1200, 800)
        
        # Status Bar for Persistent Version
        self.statusBar().showMessage(f"Ready - {self.version}")
        
        self.current_project = None
        self.chapters = []
        
        self.init_ui()
        self.create_menus()
        
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
        
        # Toolbar
        toolbar = QHBoxLayout()
        self.lbl_project_name = QLabel("No Project Loaded")
        self.lbl_project_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        toolbar.addWidget(self.lbl_project_name)
        
        toolbar.addStretch()
        
        btn_import = QPushButton("Import Manuscript")
        btn_import.clicked.connect(self.browse_manuscript)
        toolbar.addWidget(btn_import)
        
        pv_layout.addLayout(toolbar)
        
        # Splitter (Sidebar | Content)
        splitter = QSplitter(Qt.Horizontal)
        
        # Sidebar
        sidebar_widget = QWidget()
        sidebar_layout = QVBoxLayout(sidebar_widget)
        sidebar_layout.setContentsMargins(0,0,0,0)
        
        sidebar_layout.addWidget(QLabel("Chapters"))
        self.chapter_list = QListWidget()
        self.chapter_list.currentRowChanged.connect(self.display_chapter)
        sidebar_layout.addWidget(self.chapter_list)
        
        splitter.addWidget(sidebar_widget)
        
        # Content Editor
        editor_widget = QWidget()
        editor_layout = QVBoxLayout(editor_widget)
        editor_layout.setContentsMargins(0,0,0,0)
        
        editor_layout.addWidget(QLabel("Manuscript Text"))
        self.editor = QTextEdit()
        self.editor.setReadOnly(True) 
        editor_layout.addWidget(self.editor)
        
        splitter.addWidget(editor_widget)
        
        # Sizing
        splitter.setStretchFactor(1, 4) 
        splitter.setSizes([200, 800])
        
        pv_layout.addWidget(splitter)
        
        self.stack.addWidget(self.project_view)
        
        self.stack.setCurrentWidget(self.welcome_screen)
    
    def browse_manuscript(self):
        if not self.current_project:
            return
            
        fname, _ = QFileDialog.getOpenFileName(self, "Import Manuscript", "", "Markdown/Text (*.md *.txt);;All Files (*)")
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
            
        if self.chapters:
            self.chapter_list.setCurrentRow(0)

    def display_chapter(self, row):
        if 0 <= row < len(self.chapters):
            self.editor.setPlainText(self.chapters[row].content)

    def on_project_opened(self, project):
        # Check for Consent
        consent_path = os.path.join(project.path, "consent.json")
        if not os.path.exists(consent_path):
            # Launch Wizard
            wizard = ConsentWizard(project.path, self)
            if wizard.exec():
                pass
            else:
                return

        self.current_project = project
        self.lbl_project_name.setText(f"Active Project: {project.name}")
        self.setWindowTitle(f"Author Narrator {self.version} - {project.name}")
        
        # Clear previous state
        self.chapters = []
        self.chapter_list.clear()
        self.editor.clear()
        
        self.stack.setCurrentWidget(self.project_view)

    def create_menus(self):
        menu = self.menuBar()
        
        # --- File Menu ---
        file_menu = menu.addMenu("File")
        
        # Settings
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        close_proj_action = QAction("Close Project", self)
        close_proj_action.triggered.connect(self.close_project)
        file_menu.addAction(close_proj_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # --- Voice Menu ---
        self.voice_menu = menu.addMenu("Voice")
        # self.voice_menu.setEnabled(False) # Changed: Always enabled, actions check context
        
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

        # --- About Menu ---
        about_menu = menu.addMenu("About") 
        about_action = QAction("About Author Narrator", self)
        about_action.triggered.connect(self.show_about)
        about_menu.addAction(about_action)

    def close_project(self):
        self.current_project = None
        self.chapters = []
        self.lbl_project_name.setText("No Project Loaded")
        self.setWindowTitle(f"Author Narrator {self.version}")
        self.stack.setCurrentWidget(self.welcome_screen)
        
    def show_about(self):
        text = (
            f"Author Narrator {self.version}\n\n"
            "This is not a free app.\n\n"
            "Copyright © Doxie Enterprises, LLC 2026\n"
            "All Rights Reserved.\n\n"
            "For pricing info please contact: Eric.sylvia@bamecs.com"
        )
        QMessageBox.about(self, "About Author Narrator", text)

    def record_new_sample(self):
        if not self.current_project: 
            QMessageBox.warning(self, "No Project", "Please open or create a project first.")
            return
        # Force re-record
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

    def show_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()
