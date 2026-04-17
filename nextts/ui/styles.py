STYLE_SHEET = """
QMainWindow {
    background-color: #0f172a;
}

QWidget {
    color: #e2e8f0;
    font-family: 'Inter', 'Segoe UI', sans-serif;
    font-size: 14px;
}

QLabel#Title {
    font-size: 28px;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 10px;
}

QPushButton {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 10px 20px;
    font-weight: 600;
}

QPushButton:hover {
    background-color: #334155;
    border-color: #38bdf8;
}

QPushButton#PrimaryButton {
    background-color: #0284c7;
    color: white;
    border: none;
}

QPushButton#PrimaryButton:hover {
    background-color: #0369a1;
}

QPushButton#PrimaryButton:disabled {
    background-color: #1e293b;
    color: #64748b;
}

QLineEdit, QComboBox {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 6px;
    padding: 8px;
    selection-background-color: #0369a1;
}

QLineEdit:focus, QComboBox:focus {
    border-color: #38bdf8;
}

QProgressBar {
    background-color: #1e293b;
    border: none;
    border-radius: 4px;
    text-align: center;
    height: 8px;
}

QProgressBar::chunk {
    background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #38bdf8, stop:1 #818cf8);
    border-radius: 4px;
}

QListWidget {
    background-color: #1e293b;
    border: 1px solid #334155;
    border-radius: 8px;
    outline: none;
}

QListWidget::item {
    padding: 10px;
    border-bottom: 1px solid #334155;
}

QListWidget::item:selected {
    background-color: #334155;
    color: #38bdf8;
}

QGroupBox {
    border: 1px solid #334155;
    border-radius: 8px;
    margin-top: 20px;
    padding-top: 15px;
    font-weight: bold;
}

QScrollBar:vertical {
    border: none;
    background: #0f172a;
    width: 8px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    min-height: 20px;
    border-radius: 4px;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}
"""
