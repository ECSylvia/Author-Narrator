from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QHBoxLayout, QMessageBox)
from ..core.settings_manager import SettingsManager

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 150)
        self.settings_manager = SettingsManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        lbl_info = QLabel("Enter your ElevenLabs API Key to enable Voice Cloning:")
        lbl_info.setWordWrap(True)
        layout.addWidget(lbl_info)
        
        self.txt_api_key = QLineEdit()
        self.txt_api_key.setPlaceholderText("xi-...")
        self.txt_api_key.setText(self.settings_manager.get_api_key())
        self.txt_api_key.setEchoMode(QLineEdit.Password)
        layout.addWidget(self.txt_api_key)
        
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        
        btn_save = QPushButton("Save")
        btn_save.clicked.connect(self.save_settings)
        btn_layout.addWidget(btn_save)
        
        layout.addLayout(btn_layout)

    def save_settings(self):
        key = self.txt_api_key.text().strip()
        if not key:
            QMessageBox.warning(self, "Invalid Key", "Please enter a valid API Key.")
            return
            
        self.settings_manager.set_api_key(key)
        self.accept()
