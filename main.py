import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QTextEdit, QLabel, QMessageBox, QHBoxLayout, QSizePolicy
)
from PyQt6.QtGui import QIcon, QFont, QColor, QTextCharFormat, QTextCursor
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtWidgets import QGraphicsDropShadowEffect


LOG_FILE = "installer.log"
PS1_FILE = "installer.ps1"


def is_admin():
    try:
        import ctypes
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False


if not is_admin():
    import ctypes
    params = " ".join([f'"{arg}"' for arg in sys.argv])
    ctypes.windll.shell32.ShellExecuteW(
        None, "runas", sys.executable, params, None, 1
    )
    sys.exit(0)


class InstallerThread(QThread):
    output_signal = pyqtSignal(str)
    finished_signal = pyqtSignal(int)

    def run(self):
        ps1_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), PS1_FILE)

        if not os.path.exists(ps1_path):
            self.output_signal.emit(f"Error: {PS1_FILE} not found!")
            self.finished_signal.emit(-1)
            return

        cmd = [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy", "Bypass",
            "-File", ps1_path
        ]

        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                shell=True
            )
        except Exception as e:
            self.output_signal.emit(f"Failed to start installer: {e}")
            self.finished_signal.emit(-1)
            return

        with open(LOG_FILE, "w", encoding="utf-8") as log_file:
            for line in process.stdout:
                self.output_signal.emit(line.rstrip())
                log_file.write(line)

        process.wait()
        self.finished_signal.emit(process.returncode)


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Windows Dev Tools Installer - WDT")
        self.setMinimumSize(750, 500)
        self.setWindowIcon(QIcon("icon.png"))

        self.layout = QVBoxLayout()
        self.setLayout(self.layout)

        # Title
        self.title = QLabel("Windows Dev Tools Installer (WDT)")
        self.title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        self.title.setStyleSheet("color: #00aaff;")
        self.layout.addWidget(self.title)

        # Log output area
        self.output = QTextEdit()
        self.output.setReadOnly(True)
        self.output.setStyleSheet("""
            background-color: #121212;
            color: #e0e0e0;
            border-radius: 10px;
            font-family: Consolas, monospace;
            font-size: 11pt;
            padding: 10px;
        """)
        self.output.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.layout.addWidget(self.output, 1)

        # Buttons row
        buttons_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Installation")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setFont(QFont("Segoe UI", 13))
        self.start_btn.setFixedHeight(45)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #007ACC, stop:1 #005F9E);
                color: white;
                border-radius: 14px;
                padding: 10px 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #005F9E;
            }
            QPushButton:pressed {
                background-color: #003F6B;
            }
            QPushButton:disabled {
                background-color: #444444;
                color: #888888;
            }
        """)
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(25)
        shadow.setXOffset(0)
        shadow.setYOffset(6)
        shadow.setColor(QColor(0, 122, 204, 180))
        self.start_btn.setGraphicsEffect(shadow)
        buttons_layout.addWidget(self.start_btn)

        self.clear_btn = QPushButton("Clear Log")
        self.clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.clear_btn.setFont(QFont("Segoe UI", 13))
        self.clear_btn.setFixedHeight(45)
        self.clear_btn.setStyleSheet("""
            QPushButton {
                background-color: #444444;
                color: #cccccc;
                border-radius: 14px;
                padding: 10px 25px;
                border: none;
            }
            QPushButton:hover {
                background-color: #555555;
            }
            QPushButton:pressed {
                background-color: #333333;
            }
        """)
        buttons_layout.addWidget(self.clear_btn)

        self.layout.addLayout(buttons_layout)

        self.start_btn.clicked.connect(self.start_installation)
        self.clear_btn.clicked.connect(self.output.clear)

        self.installer_thread = InstallerThread()
        self.installer_thread.output_signal.connect(self.append_output)
        self.installer_thread.finished_signal.connect(self.installation_finished)

    def append_output(self, text):
        # تلوين بعض الكلمات المهمة
        cursor = self.output.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        fmt = QTextCharFormat()

        lower = text.lower()
        if "error" in lower or "failed" in lower or "not found" in lower:
            fmt.setForeground(QColor("#ff5555"))  # أحمر للأخطاء
        elif "success" in lower or "completed" in lower or "done" in lower:
            fmt.setForeground(QColor("#55ff55"))  # أخضر للنجاح
        elif "warning" in lower:
            fmt.setForeground(QColor("#ffaa00"))  # برتقالي للتحذيرات
        else:
            fmt.setForeground(QColor("#e0e0e0"))  # رمادي فاتح للنص العادي

        cursor.setCharFormat(fmt)
        cursor.insertText(text + "\n")
        self.output.setTextCursor(cursor)
        self.output.ensureCursorVisible()

    def start_installation(self):
        self.output.clear()
        self.start_btn.setDisabled(True)
        self.append_output("Starting installation...\n")
        self.installer_thread.start()

    def installation_finished(self, code):
        if code == 0:
            self.append_output("\nInstallation completed successfully.")
        else:
            self.append_output(f"\nInstallation finished with errors. Exit code: {code}")
        self.start_btn.setDisabled(False)


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")  # لازم تحطها الأول عشان الـ qss يشتغل صح
    qss_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "more.qss")
    if os.path.exists(qss_path):
        with open(qss_path, "r", encoding="utf-8") as f:
            app.setStyleSheet(f.read())

    window = MainWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
