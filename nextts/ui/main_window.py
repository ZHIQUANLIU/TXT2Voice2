import os
import asyncio
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                             QLabel, QPushButton, QComboBox, QFileDialog, 
                             QProgressBar, QListWidget, QListWidgetItem, QMessageBox)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QThread
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl, QTimer
from PyQt6.QtGui import QIcon

from .styles import STYLE_SHEET
from .settings_dialog import SettingsDialog
from .i18n import TRANSLATIONS
from ..core.document_parsers import DocumentParser
from ..core.config_manager import ConfigManager
from ..core.audio_worker import AudioWorker
from ..core.tts_providers import (EdgeTTSProvider, OpenAITTSProvider, 
                                 GoogleTTSProvider, LocalTTSProvider, DashScopeTTSProvider)

class VoiceLoaderThread(QThread):
    voices_loaded = pyqtSignal(list)
    
    def __init__(self, provider):
        super().__init__()
        self.provider = provider
        
    def run(self):
        try:
            # We use a simple way to run async in thread
            voices = asyncio.run(self.provider.get_voices())
            self.voices_loaded.emit(voices)
        except Exception as e:
            print(f"Voice load error: {e}")
            self.voices_loaded.emit([])

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_manager = ConfigManager()
        self.lang = self.config_manager.get_setting("language", "zh")
        self.t = TRANSLATIONS[self.lang]
        
        self.segments = []
        self.worker = None
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Icon path - using the generated one if it exists or a generic one
        icon_path = os.path.join(os.path.dirname(__file__), "..", "resources", "app_icon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.t["title"])
        self.setMinimumSize(1000, 750)
        self.setStyleSheet(STYLE_SHEET)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        # Left Panel: Controls
        left_panel = QVBoxLayout()
        main_layout.addLayout(left_panel, 1)

        header_layout = QHBoxLayout()
        self.app_title = QLabel(self.t["app_name"])
        self.app_title.setObjectName("Title")
        header_layout.addWidget(self.app_title)
        
        header_layout.addStretch()
        self.lang_btn = QPushButton(self.t["lang_toggle"])
        self.lang_btn.setFixedWidth(100)
        self.lang_btn.clicked.connect(self.toggle_language)
        header_layout.addWidget(self.lang_btn)
        
        left_panel.addLayout(header_layout)

        # File Section
        file_group = QVBoxLayout()
        self.file_hint = QLabel(self.t["no_file"])
        self.file_hint.setStyleSheet("color: #94a3b8;")
        self.select_file_btn = QPushButton(self.t["select_file"])
        self.select_file_btn.clicked.connect(self.select_file)
        file_group.addWidget(self.select_file_btn)
        file_group.addWidget(self.file_hint)
        left_panel.addLayout(file_group)

        # Provider Section
        self.prov_label = QLabel(self.t["provider"])
        left_panel.addWidget(self.prov_label)
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["Edge", "OpenAI", "Google", "DashScope", "Local"])
        self.provider_combo.currentTextChanged.connect(self.on_provider_changed)
        left_panel.addWidget(self.provider_combo)

        # Voice Section
        self.voice_label = QLabel(self.t["voice"])
        left_panel.addWidget(self.voice_label)
        self.voice_combo = QComboBox()
        left_panel.addWidget(self.voice_combo)

        # Progress
        left_panel.addStretch()
        self.progress_hint = QLabel(self.t["ready"])
        self.progress_bar = QProgressBar()
        left_panel.addWidget(self.progress_hint)
        left_panel.addWidget(self.progress_bar)

        # Actions
        actions_layout = QHBoxLayout()
        self.convert_btn = QPushButton(self.t["start"])
        self.convert_btn.setObjectName("PrimaryButton")
        self.convert_btn.clicked.connect(self.start_conversion)
        
        self.settings_btn = QPushButton(self.t["settings"])
        self.settings_btn.clicked.connect(self.open_settings)
        
        actions_layout.addWidget(self.settings_btn)
        actions_layout.addWidget(self.convert_btn)
        left_panel.addLayout(actions_layout)

        # Right Panel: Queue / Preview
        right_panel = QVBoxLayout()
        main_layout.addLayout(right_panel, 2)

        self.seg_label = QLabel(self.t["segments"])
        right_panel.addWidget(self.seg_label)
        self.segment_list = QListWidget()
        right_panel.addWidget(self.segment_list)

        preview_layout = QHBoxLayout()
        self.preview_btn = QPushButton(self.t["preview"])
        self.preview_btn.clicked.connect(self.play_sample)
        preview_layout.addWidget(self.preview_btn)
        right_panel.addLayout(preview_layout)

        # Initial load
        self.on_provider_changed("Edge")

    def toggle_language(self):
        self.lang = "zh" if self.lang == "en" else "en"
        self.config_manager.set_setting("language", self.lang)
        self.t = TRANSLATIONS[self.lang]
        self.update_ui_texts()

    def update_ui_texts(self):
        self.setWindowTitle(self.t["title"])
        self.app_title.setText(self.t["app_name"])
        self.lang_btn.setText(self.t["lang_toggle"])
        self.select_file_btn.setText(self.t["select_file"])
        if not hasattr(self, 'source_path'):
            self.file_hint.setText(self.t["no_file"])
        self.prov_label.setText(self.t["provider"])
        self.voice_label.setText(self.t["voice"])
        self.convert_btn.setText(self.t["start"])
        self.settings_btn.setText(self.t["settings"])
        self.seg_label.setText(self.t["segments"])
        self.preview_btn.setText(self.t["preview"])
        if self.worker is None or not self.worker.isRunning():
            self.progress_hint.setText(self.t["ready"])

    def select_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, self.t["select_file"], "", "Documents (*.pdf *.epub *.txt);;All Files (*.*)"
        )
        if path:
            self.file_hint.setText(os.path.basename(path))
            self.source_path = path
            self.load_segments(path)

    def load_segments(self, path):
        try:
            self.segments = DocumentParser.load(path)
            self.segment_list.clear()
            for title, body in self.segments:
                item = QListWidgetItem(f"{title} ({len(body)} chars)")
                self.segment_list.addItem(item)
        except Exception as e:
            QMessageBox.critical(self, self.t["error"], f"Failed: {e}")

    def on_provider_changed(self, provider_name):
        self.voice_combo.clear()
        self.voice_combo.addItem("Loading...")
        
        provider = None
        if provider_name == "Edge":
            provider = EdgeTTSProvider()
        elif provider_name == "OpenAI":
            provider = OpenAITTSProvider(self.config_manager.get_api_key("OpenAI"))
        elif provider_name == "Google":
            provider = GoogleTTSProvider(self.config_manager.get_setting("google_creds_path"))
        elif provider_name == "DashScope":
            provider = DashScopeTTSProvider(self.config_manager.get_api_key("DashScope"))
        elif provider_name == "Local":
            provider = LocalTTSProvider()

        if provider:
            self.voice_loader = VoiceLoaderThread(provider)
            self.voice_loader.voices_loaded.connect(self.update_voice_list)
            self.voice_loader.start()

    def update_voice_list(self, voices):
        self.voice_combo.clear()
        for v in voices:
            self.voice_combo.addItem(v["name"], v["id"])
        
        if not voices:
            self.voice_combo.addItem("No voices found")

    def open_settings(self):
        diag = SettingsDialog(self.config_manager, self.lang, self)
        if diag.exec():
            # Refresh voices if provider uses keys
            self.on_provider_changed(self.provider_combo.currentText())

    def play_sample(self):
        selected = self.segment_list.currentRow()
        if selected < 0:
            QMessageBox.warning(self, self.t["error"], self.t["invalid_file"])
            return
        
        _, body = self.segments[selected]
        sample_text = body[:300]
        
        async def do_sample():
            p_type = self.provider_combo.currentText()
            voice = self.voice_combo.currentData()
            
            p = None
            if p_type == "Edge": p = EdgeTTSProvider()
            elif p_type == "OpenAI": p = OpenAITTSProvider(self.config_manager.get_api_key("OpenAI"))
            elif p_type == "DashScope": p = DashScopeTTSProvider(self.config_manager.get_api_key("DashScope"))
            elif p_type == "Local": p = LocalTTSProvider()
            
            if p:
                temp_path = "sample_preview.mp3"
                success = await p.synthesize(sample_text, voice, temp_path)
                if success:
                    self.player.setSource(QUrl.fromLocalFile(os.path.abspath(temp_path)))
                    self.player.play()
                    QTimer.singleShot(5000, self.player.stop)
            else:
                QMessageBox.information(self, "Info", "Preview not yet supported for this provider.")

        asyncio.run(do_sample())

    def start_conversion(self):
        if not hasattr(self, 'source_path') or not self.segments:
            QMessageBox.warning(self, self.t["error"], self.t["invalid_file"])
            return

        provider = self.provider_combo.currentText()
        voice = self.voice_combo.currentData()
        
        base_name = os.path.splitext(os.path.basename(self.source_path))[0]
        output_dir = os.path.join(os.path.dirname(self.source_path), base_name + "_Audio")
        
        self.worker = AudioWorker(
            provider, self.segments, voice, output_dir, self.config_manager, base_name
        )
        self.worker.progress.connect(self.on_progress)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        
        self.convert_btn.setEnabled(False)
        self.worker.start()

    @pyqtSlot(int, str)
    def on_progress(self, val, msg):
        self.progress_bar.setValue(val)
        # Handle i18n for "Processing"
        if "Processing" in msg:
            title = msg.split(": ", 1)[-1]
            msg = self.t["processing"].format(title)
        self.progress_hint.setText(msg)

    @pyqtSlot(list)
    def on_finished(self, paths):
        self.convert_btn.setEnabled(True)
        self.progress_hint.setText(self.t["success"])
        msg = self.t["done_msg"].format(len(paths), os.path.dirname(paths[0]))
        QMessageBox.information(self, self.t["success"], msg)

    @pyqtSlot(str)
    def on_error(self, err):
        self.convert_btn.setEnabled(True)
        self.progress_hint.setText(self.t["error"])
        QMessageBox.critical(self, self.t["error"], err)
