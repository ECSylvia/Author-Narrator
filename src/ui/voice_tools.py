from PySide6.QtWidgets import (QDialog, QVBoxLayout, QLabel, QPushButton, QTextEdit, 
                               QHBoxLayout, QMessageBox, QFileDialog, QProgressBar, QApplication)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from PySide6.QtCore import QUrl, Qt
import os

class VoiceReviewDialog(QDialog):
    def __init__(self, project_path, parent=None):
        super().__init__(parent)
        self.project_path = project_path
        self.setWindowTitle("Review Voice Sample")
        self.resize(400, 200)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        self.lbl_status = QLabel("Ready to play.")
        layout.addWidget(self.lbl_status)
        
        self.btn_play = QPushButton("▶ Play Recording")
        self.btn_play.clicked.connect(self.play_audio)
        layout.addWidget(self.btn_play)
        
        # Player
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(1.0)
        self.player.mediaStatusChanged.connect(self.on_media_status)

    def play_audio(self):
        wav_path = os.path.join(self.project_path, "voice_profile.wav")
        if not os.path.exists(wav_path):
            self.lbl_status.setText("No voice recording found.")
            return
            
        self.player.setSource(QUrl.fromLocalFile(wav_path))
        self.player.play()
        self.lbl_status.setText("Playing...")
        self.btn_play.setEnabled(False)

    def on_media_status(self, status):
        if status == QMediaPlayer.MediaStatus.EndOfMedia:
            self.lbl_status.setText("Playback finished.")
            self.btn_play.setEnabled(True)

class SamplePageDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Hear a Sample Page")
        self.resize(600, 500)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel("<b>Paste sample text (Max 1000 words):</b>"))
        
        self.editor = QTextEdit()
        self.editor.textChanged.connect(self.check_word_count)
        layout.addWidget(self.editor)
        
        self.lbl_count = QLabel("Words: 0 / 1000")
        layout.addWidget(self.lbl_count)
        
        self.btn_listen = QPushButton("🔊 Listen Now")
        self.btn_listen.clicked.connect(self.play_sample)
        self.btn_listen.setStyleSheet("""
            QPushButton {
                background-color: #0078d4; color: white; border-radius: 4px; padding: 10px; font-weight: bold;
            }
            QPushButton:hover { background-color: #106ebe; }
            QPushButton:disabled { background-color: #ccc; }
        """)
        self.btn_listen.setEnabled(False)
        layout.addWidget(self.btn_listen)
        
    def check_word_count(self):
        text = self.editor.toPlainText()
        words = len(text.split())
        self.lbl_count.setText(f"Words: {words} / 1000")
        
        if 0 < words <= 1000:
            self.btn_listen.setEnabled(True)
            self.lbl_count.setStyleSheet("color: black;")
        else:
            self.btn_listen.setEnabled(False)
            if words > 1000:
                self.lbl_count.setStyleSheet("color: red;")

    def play_sample(self):
        from ..core.settings_manager import SettingsManager
        from .settings_dialog import SettingsDialog
        from ..core.elevenlabs_generator import ElevenLabsGenerator
        
        # 1. Check API Key
        settings = SettingsManager()
        api_key = settings.get_api_key()
        
        if not api_key:
            reply = QMessageBox.question(
                self, "Missing API Key", 
                "You need an ElevenLabs API Key to use this feature.\nOpen Settings to enter it?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.Yes:
                dlg = SettingsDialog(self)
                if dlg.exec():
                    api_key = settings.get_api_key()
                else:
                    return
            else:
                return
        
        if not api_key: return

        # 2. Get Context
        # We need the project path to find the wav file
        # The MainWindow passes 'self' as parent, we can try to access self.parent().current_project
        # Or better, pass project_path in __init__
        
        parent = self.parent()
        if not hasattr(parent, 'current_project') or not parent.current_project:
            QMessageBox.warning(self, "Error", "No active project found.")
            return
            
        project = parent.current_project
        sample_path = os.path.join(project.path, "voice_profile.wav")
        output_path = os.path.join(project.path, "sample_narration.mp3")
        
        # 3. Generate
        self.btn_listen.setEnabled(False)
        self.lbl_count.setText("Generating Audio... Please Wait...")
        QApplication.processEvents() # Force UI update
        
        try:
            generator = ElevenLabsGenerator(api_key)
            # Use Project Name + " Voice" as the voice name to identify it
            voice_name = f"{project.name} Voice"
            
            generator.generate_cloned_speech(
                text=self.editor.toPlainText(),
                voice_name=voice_name,
                sample_path=sample_path,
                output_path=output_path
            )
            
            # 4. Play
            self.lbl_count.setText("Playing...")
            player = QMediaPlayer(self)
            audio_output = QAudioOutput(self)
            player.setAudioOutput(audio_output)
            audio_output.setVolume(1.0)
            player.setSource(QUrl.fromLocalFile(output_path))
            player.play()
            
            # Keep reference to avoid garbage collection
            self._player = player
            self._audio_output = audio_output
            
            QMessageBox.information(self, "Success", "Audio generated and playing!")
            
        except Exception as e:
            QMessageBox.critical(self, "Generation Failed", str(e))
        finally:
            self.btn_listen.setEnabled(True)
            self.check_word_count() # Reset label
