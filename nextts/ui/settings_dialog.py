from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
                             QLineEdit, QPushButton, QFileDialog, QFormLayout)
from PyQt6.QtCore import Qt
from .i18n import TRANSLATIONS

class SettingsDialog(QDialog):
    def __init__(self, config_manager, lang="en", parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.lang = lang
        self.t = TRANSLATIONS[lang]
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(f"{self.t['settings']} - NexTTS")
        self.setMinimumWidth(550)
        layout = QVBoxLayout(self)

        title = QLabel(self.t['settings'])
        title.setObjectName("Title")
        title.setStyleSheet("font-size: 20px;")
        layout.addWidget(title)

        form = QFormLayout()
        
        # OpenAI API Key
        self.openai_key = QLineEdit()
        self.openai_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key.setText(self.config_manager.get_api_key("OpenAI"))
        form.addRow(self.t["openai_key"], self.openai_key)

        # DashScope API Key
        self.dashscope_key = QLineEdit()
        self.dashscope_key.setEchoMode(QLineEdit.EchoMode.Password)
        self.dashscope_key.setText(self.config_manager.get_api_key("DashScope"))
        form.addRow(self.t["dashscope_key"], self.dashscope_key)

        # Google Credentials Path
        self.google_creds = QLineEdit()
        self.google_creds.setText(self.config_manager.get_setting("google_creds_path", ""))
        google_btn = QPushButton(self.t["browse"])
        google_btn.clicked.connect(self.browse_google_creds)
        google_layout = QHBoxLayout()
        google_layout.addWidget(self.google_creds)
        google_layout.addWidget(google_btn)
        form.addRow(self.t["google_json"], google_layout)

        layout.addLayout(form)

        # Buttons
        btn_layout = QHBoxLayout()
        save_btn = QPushButton(self.t["save_settings"])
        save_btn.setObjectName("PrimaryButton")
        save_btn.clicked.connect(self.save)
        cancel_btn = QPushButton(self.t["cancel"])
        cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(cancel_btn)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

    def browse_google_creds(self):
        path, _ = QFileDialog.getOpenFileName(self, "Select Service Account JSON", "", "JSON Files (*.json)")
        if path:
            self.google_creds.setText(path)

    def save(self):
        self.config_manager.set_api_key("OpenAI", self.openai_key.text())
        self.config_manager.set_api_key("DashScope", self.dashscope_key.text())
        self.config_manager.set_setting("google_creds_path", self.google_creds.text())
        self.accept()
