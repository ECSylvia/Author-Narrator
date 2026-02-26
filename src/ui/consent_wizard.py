from PySide6.QtWidgets import (QWizard, QWizardPage, QVBoxLayout, QLabel, QCheckBox, 
                               QTextEdit, QProgressBar, QPushButton, QHBoxLayout, QMessageBox)
from PySide6.QtCore import Qt, QTimer
from ..core.audio_recorder import AudioRecorder
import os
import json
from datetime import datetime

class ConsentWizard(QWizard):
    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.setWindowTitle("Voice Profile Creation Wizard")
        self.resize(700, 500)
        
        self.addPage(ConsentPage())
        self.addPage(InstructionsPage())
        self.addPage(RecordingPage(project_path))
        
    def accept(self):
        # Save consent JSON
        consent_data = {
            "accepted": True,
            "timestamp": datetime.now().isoformat(),
            "project_path": self.project_path
        }
        
        with open(os.path.join(self.project_path, "consent.json"), 'w') as f:
            json.dump(consent_data, f, indent=4)
            
        super().accept()

class ConsentPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Voice Ownership & Consent")
        
        layout = QVBoxLayout(self)
        
        info = QLabel(
            "<h3>Non-Negotiable Principles</h3>"
            "<ul>"
            "<li><b>The author owns the voice</b></li>"
            "<li><b>The author owns the text</b></li>"
            "<li><b>The author owns the output</b></li>"
            "</ul>"
            "<p>By proceeding, you certify that you are the owner of the voice being recorded, "
            "and you consent to generating an AI voice model derived from this recording "
            "solely for use within this project.</p>"
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        
        self.chk_agree = QCheckBox("I Certify and Agree")
        self.chk_agree.stateChanged.connect(self.completeChanged)
        layout.addWidget(self.chk_agree)
        
    def isComplete(self):
        return self.chk_agree.isChecked()

class InstructionsPage(QWizardPage):
    def __init__(self):
        super().__init__()
        self.setTitle("Recording Instructions")
        
        layout = QVBoxLayout(self)
        
        lbl = QLabel(
            "<b>Please prepare to record.</b><br><br>"
            "1. Read in your normal speaking voice.<br>"
            "2. Stay relaxed.<br>"
            "3. If you make a mistake, pause, and start the sentence again.<br>"
            "4. Keep 6-10 inches from your microphone.<br><br>"
            "You will read the script shown on the next page."
        )
        lbl.setWordWrap(True)
        layout.addWidget(lbl)

class RecordingPage(QWizardPage):
    def __init__(self, project_path):
        super().__init__()
        self.project_path = project_path
        self.setTitle("Voice Sample Recording")
        self.recorder = AudioRecorder(self)
        self.recording_started = False
        
        layout = QVBoxLayout(self)
        
        # Script View
        self.script_view = QTextEdit()
        self.script_view.setReadOnly(True)
        self.load_script()
        layout.addWidget(self.script_view)
        
        # Controls
        ctrl_layout = QHBoxLayout()
        
        self.btn_rec = QPushButton("🔴 Record")
        self.btn_rec.clicked.connect(self.toggle_record)
        ctrl_layout.addWidget(self.btn_rec)
        
        self.lbl_timer = QLabel("00:00")
        ctrl_layout.addWidget(self.lbl_timer)
        
        layout.addLayout(ctrl_layout)
        
        self.progress = QProgressBar()
        self.progress.setRange(0, 0) # Pulse when recording
        self.progress.setVisible(False)
        layout.addWidget(self.progress)
        
        # Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_duration)
        self.duration_ms = 0

    def load_script(self):
        try:
            # Try to find src/assets/voice_script.txt
            # We are in src/ui/, so assets is ../assets/
            path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'assets', 'voice_script.txt'))
            with open(path, 'r') as f:
                self.script_view.setPlainText(f.read())
        except Exception:
            self.script_view.setPlainText("Script file not found. Please read a book excerpt.")

    def toggle_record(self):
        if not self.recording_started:
            # Start
            out_path = os.path.join(self.project_path, "voice_profile.wav")
            self.recorder.start_recording(out_path)
            self.btn_rec.setText("⏹ Stop")
            self.progress.setVisible(True)
            self.timer.start(100)
            self.recording_started = True
            self.completeChanged.emit() # Make sure we can't click next yet? Actually we want finish only after stop.
        else:
            # Stop
            self.recorder.stop_recording()
            self.btn_rec.setText("🔴 Re-Record")
            self.progress.setVisible(False)
            self.timer.stop()
            self.recording_started = False
            self.completeChanged.emit()

    def update_duration(self):
        self.duration_ms += 100
        sec = (self.duration_ms // 1000) % 60
        min = (self.duration_ms // 1000) // 60
        self.lbl_timer.setText(f"{min:02d}:{sec:02d}")

    def isComplete(self):
        # Allow finish if we have recorded something (duration > 0 and stopped)
        # For full spec, need > 180s. For now, just > 5s
        return self.duration_ms > 5000 and not self.recording_started
