from PySide6.QtMultimedia import QMediaRecorder, QMediaCaptureSession, QAudioInput, QMediaFormat
from PySide6.QtCore import QUrl, QObject, Signal, Slot
import os

class AudioRecorder(QObject):
    duration_changed = Signal(int) # milliseconds
    levels_changed = Signal(float) # 0.0 to 1.0
    error_occurred = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.session = QMediaCaptureSession()
        self.audio_input = QAudioInput()
        self.recorder = QMediaRecorder()
        
        self.session.setAudioInput(self.audio_input)
        self.session.setRecorder(self.recorder)
        
        self.recorder.durationChanged.connect(self._on_duration_changed)
        self.recorder.errorOccurred.connect(self.handle_error)
        
        # Configure for best quality (WAV)
        media_format = QMediaFormat()
        media_format.setFileFormat(QMediaFormat.Wave)
        media_format.setAudioCodec(QMediaFormat.AudioCodec.Wave)
        self.recorder.setMediaFormat(media_format)

    def _on_duration_changed(self, duration):
        self.duration_changed.emit(duration)

    def start_recording(self, output_path):
        # Ensure directory exists
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        url = QUrl.fromLocalFile(output_path)
        self.recorder.setOutputLocation(url)
        self.recorder.record()
        print(f"Recording to: {output_path}")

    def stop_recording(self):
        self.recorder.stop()
        print("Recording stopped.")
        
    def handle_error(self):
        err = self.recorder.errorString()
        print(f"Recorder Error: {err}")
        self.error_occurred.emit(err)
