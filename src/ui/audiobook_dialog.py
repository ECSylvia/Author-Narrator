from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QProgressBar, QTreeWidget, QTreeWidgetItem, QMessageBox,
    QFileDialog, QApplication,
)
from PySide6.QtCore import Qt, QThread, Signal
import os
import time


class GeneratorWorker(QThread):
    """Background thread that drives chapter-by-chapter TTS generation."""

    chapter_started = Signal(int, str)          # (index, title)
    chunk_progress = Signal(int, int, int)      # (chapter_idx, current_chunk, total_chunks)
    chapter_finished = Signal(int, str)         # (index, output_path)
    chapter_failed = Signal(int, str)           # (index, error_message)
    all_done = Signal()

    def __init__(self, chapters, generator, voice_name, sample_path, output_dir):
        super().__init__()
        self.chapters = chapters
        self.generator = generator
        self.voice_name = voice_name
        self.sample_path = sample_path
        self.output_dir = output_dir
        self._cancel = False
        self._pause = False

    def cancel(self):
        self._cancel = True

    def pause(self):
        self._pause = True

    def resume(self):
        self._pause = False

    def run(self):
        for i, chapter in enumerate(self.chapters):
            if self._cancel:
                break

            while self._pause and not self._cancel:
                time.sleep(0.2)

            if self._cancel:
                break

            self.chapter_started.emit(i, chapter.title)

            safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in chapter.title).strip()
            filename = f"{i + 1:03d}_{safe_title}.mp3"
            output_path = os.path.join(self.output_dir, filename)

            if os.path.exists(output_path):
                self.chapter_finished.emit(i, output_path)
                continue

            try:
                self.generator.generate_chapter_audio(
                    text=chapter.content,
                    voice_name=self.voice_name,
                    sample_path=self.sample_path,
                    output_path=output_path,
                    on_chunk_progress=lambda cur, tot, idx=i: self.chunk_progress.emit(idx, cur, tot),
                )
                self.chapter_finished.emit(i, output_path)
            except Exception as e:
                self.chapter_failed.emit(i, str(e))

        self.all_done.emit()


class AudiobookDialog(QDialog):
    """Full-audiobook generation dialog with per-chapter progress."""

    def __init__(self, chapters, project, parent=None):
        super().__init__(parent)
        self.chapters = chapters
        self.project = project
        self.worker = None
        self.setWindowTitle("Generate Audiobook")
        self.resize(720, 560)
        self._build_ui()

    def _build_ui(self):
        root = QVBoxLayout(self)

        header = QLabel(
            f"<b>{len(self.chapters)} chapters</b> will be converted to audio using your cloned voice."
        )
        header.setWordWrap(True)
        root.addWidget(header)

        # Output directory picker
        dir_row = QHBoxLayout()
        self.lbl_output = QLabel("")
        self._output_dir = os.path.join(self.project.path, "audio")
        self.lbl_output.setText(self._output_dir)
        dir_row.addWidget(QLabel("Output:"))
        dir_row.addWidget(self.lbl_output, 1)
        btn_browse = QPushButton("Browse…")
        btn_browse.clicked.connect(self._pick_output_dir)
        dir_row.addWidget(btn_browse)
        root.addLayout(dir_row)

        # Chapter tree
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["#", "Chapter", "Status"])
        self.tree.setColumnWidth(0, 40)
        self.tree.setColumnWidth(1, 380)
        self.tree.setRootIsDecorated(False)
        for i, ch in enumerate(self.chapters):
            item = QTreeWidgetItem([str(i + 1), ch.title, "Pending"])
            self.tree.addTopLevelItem(item)
        root.addWidget(self.tree)

        # Overall progress
        self.progress = QProgressBar()
        self.progress.setRange(0, len(self.chapters))
        self.progress.setValue(0)
        self.progress.setFormat("%v / %m chapters")
        root.addWidget(self.progress)

        self.lbl_status = QLabel("Ready")
        root.addWidget(self.lbl_status)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self.btn_start = QPushButton("Generate Audiobook")
        self.btn_start.setStyleSheet(
            "QPushButton { background-color: #0078d4; color: white; border-radius: 4px; "
            "padding: 10px 24px; font-weight: bold; }"
            "QPushButton:hover { background-color: #106ebe; }"
            "QPushButton:disabled { background-color: #ccc; }"
        )
        self.btn_start.clicked.connect(self._start)
        btn_row.addWidget(self.btn_start)

        self.btn_pause = QPushButton("Pause")
        self.btn_pause.setEnabled(False)
        self.btn_pause.clicked.connect(self._toggle_pause)
        btn_row.addWidget(self.btn_pause)

        self.btn_cancel = QPushButton("Cancel")
        self.btn_cancel.setEnabled(False)
        self.btn_cancel.clicked.connect(self._cancel)
        btn_row.addWidget(self.btn_cancel)

        root.addLayout(btn_row)

    def _pick_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "Choose Output Directory", self._output_dir)
        if d:
            self._output_dir = d
            self.lbl_output.setText(d)

    def _start(self):
        from ..core.settings_manager import SettingsManager
        from ..core.elevenlabs_generator import ElevenLabsGenerator
        from .settings_dialog import SettingsDialog

        settings = SettingsManager()
        api_key = settings.get_api_key()

        if not api_key:
            reply = QMessageBox.question(
                self, "Missing API Key",
                "You need an ElevenLabs API Key.\nOpen Settings to enter it?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.Yes:
                dlg = SettingsDialog(self)
                if dlg.exec():
                    api_key = settings.get_api_key()
            if not api_key:
                return

        sample_path = os.path.join(self.project.path, "voice_profile.wav")
        if not os.path.exists(sample_path):
            QMessageBox.warning(
                self, "No Voice Sample",
                "Record a voice sample first via Voice → Record New Sample.",
            )
            return

        os.makedirs(self._output_dir, exist_ok=True)

        generator = ElevenLabsGenerator(api_key)
        voice_name = f"{self.project.name} Voice"

        self.worker = GeneratorWorker(
            self.chapters, generator, voice_name, sample_path, self._output_dir,
        )
        self.worker.chapter_started.connect(self._on_chapter_started)
        self.worker.chunk_progress.connect(self._on_chunk_progress)
        self.worker.chapter_finished.connect(self._on_chapter_finished)
        self.worker.chapter_failed.connect(self._on_chapter_failed)
        self.worker.all_done.connect(self._on_all_done)

        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_cancel.setEnabled(True)
        self.lbl_status.setText("Generating…")

        self._completed = 0
        self.worker.start()

    def _on_chapter_started(self, idx, title):
        item = self.tree.topLevelItem(idx)
        if item:
            item.setText(2, "Generating…")
            self.tree.scrollToItem(item)
        self.lbl_status.setText(f"Chapter {idx + 1}: {title}")

    def _on_chunk_progress(self, idx, cur, total):
        item = self.tree.topLevelItem(idx)
        if item:
            item.setText(2, f"Chunk {cur}/{total}")

    def _on_chapter_finished(self, idx, path):
        item = self.tree.topLevelItem(idx)
        if item:
            item.setText(2, "Done ✓")
        self._completed += 1
        self.progress.setValue(self._completed)

    def _on_chapter_failed(self, idx, error):
        item = self.tree.topLevelItem(idx)
        if item:
            item.setText(2, f"Failed: {error[:40]}")
        self._completed += 1
        self.progress.setValue(self._completed)

    def _on_all_done(self):
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_cancel.setEnabled(False)
        self.lbl_status.setText(f"Complete — files saved to {self._output_dir}")
        QMessageBox.information(self, "Done", "Audiobook generation finished!")

    def _toggle_pause(self):
        if not self.worker:
            return
        if self.btn_pause.text() == "Pause":
            self.worker.pause()
            self.btn_pause.setText("Resume")
            self.lbl_status.setText("Paused")
        else:
            self.worker.resume()
            self.btn_pause.setText("Pause")
            self.lbl_status.setText("Generating…")

    def _cancel(self):
        if self.worker:
            self.worker.cancel()
            self.lbl_status.setText("Cancelling…")

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            reply = QMessageBox.question(
                self, "Cancel Generation?",
                "Audio generation is still running. Cancel and close?",
                QMessageBox.Yes | QMessageBox.No,
            )
            if reply == QMessageBox.No:
                event.ignore()
                return
            self.worker.cancel()
            self.worker.wait(5000)
        event.accept()
