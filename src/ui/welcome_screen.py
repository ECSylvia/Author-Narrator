from PySide6.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton, 
                               QHBoxLayout, QListWidget, QFileDialog, QInputDialog, QMessageBox)
from PySide6.QtCore import Signal, Qt
from ..core.project_manager import ProjectManager
import os

class WelcomeScreen(QWidget):
    # Signals to parent window
    project_opened = Signal(object) # passes Project object
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        
        # Logo / Title
        title = QLabel("Author Narrator")
        title.setStyleSheet("font-size: 32px; font-weight: bold; color: #333;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)
        
        subtitle = QLabel("AI-Assisted Audiobook Creation")
        subtitle.setStyleSheet("font-size: 16px; color: #666;")
        subtitle.setAlignment(Qt.AlignCenter)
        layout.addWidget(subtitle)
        
        layout.addSpacing(40)
        
        # Action Buttons
        btn_layout = QHBoxLayout()
        
        self.btn_new = QPushButton("New Project")
        self.btn_new.setMinimumSize(150, 50)
        self.btn_new.clicked.connect(self.handle_new_project)
        self.btn_new.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border-radius: 5px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #106ebe; }
        """)
        
        self.btn_open = QPushButton("Open Project")
        self.btn_open.setMinimumSize(150, 50)
        self.btn_open.clicked.connect(self.handle_open_project)
        self.btn_open.setStyleSheet("""
            QPushButton {
                background-color: #f3f2f1;
                color: #333;
                border: 1px solid #ccc;
                border-radius: 5px;
                font-size: 14px;
            }
            QPushButton:hover { background-color: #e1dfdd; }
        """)
        
        btn_layout.addWidget(self.btn_new)
        btn_layout.addSpacing(20)
        btn_layout.addWidget(self.btn_open)
        btn_layout.setAlignment(Qt.AlignCenter)
        
        layout.addLayout(btn_layout)
        
        layout.addSpacing(40)
        
        # Recent Projects (Placeholder for now)
        lbl_recent = QLabel("Recent Projects")
        lbl_recent.setStyleSheet("font-weight: bold;")
        layout.addWidget(lbl_recent)
        
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        layout.addWidget(self.recent_list)
        
    def handle_new_project(self):
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name:
            # Default location: Documents/AuthorNarratorProjects
            docs_dir = os.path.expanduser("~/Documents")
            base_dir = os.path.join(docs_dir, "AuthorNarratorProjects")
            
            if not os.path.exists(base_dir):
                os.makedirs(base_dir)
                
            try:
                project = ProjectManager.create_project(name, base_dir)
                self.project_opened.emit(project)
            except ValueError as ve:
                if "already exists" in str(ve):
                    reply = QMessageBox.question(
                        self, "Project Exists", 
                        f"A project named '{name}' already exists.\nDo you want to overwrite it? All data will be lost.",
                        QMessageBox.Yes | QMessageBox.No
                    )
                    if reply == QMessageBox.Yes:
                        try:
                            project = ProjectManager.create_project(name, base_dir, overwrite=True)
                            self.project_opened.emit(project)
                        except Exception as e:
                            QMessageBox.critical(self, "Error", str(e))
                else:
                    QMessageBox.critical(self, "Error", str(ve))
            except Exception as e:
                QMessageBox.critical(self, "Error", str(e))

    def handle_open_project(self):
        # Start in Documents or similar
        start_dir = os.path.expanduser("~/Documents")
        path = QFileDialog.getExistingDirectory(self, "Open Project Folder", start_dir)
        
        if path:
            try:
                project = ProjectManager.load_project(path)
                self.project_opened.emit(project)
            except Exception as e:
                QMessageBox.warning(self, "Invalid Project", f"Could not load project: {e}")
