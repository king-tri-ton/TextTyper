import sys
import time
import threading
import pyautogui
import keyboard
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QTextEdit, QLabel, QPushButton, 
                               QSpinBox, QGroupBox, QMessageBox, QComboBox)
from PySide6.QtCore import Qt, Signal, QObject
from PySide6.QtGui import QFont, QKeySequence

class TypingSignals(QObject):
    """Сигналы для взаимодействия между потоками"""
    started = Signal()
    finished = Signal()
    error = Signal(str)

class TextTyperApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.typing_thread = None
        self.is_typing = False
        self.signals = TypingSignals()

        self.signals.started.connect(self.on_typing_started)
        self.signals.finished.connect(self.on_typing_finished)
        self.signals.error.connect(self.on_typing_error)

        self.init_ui()
        self.setup_hotkey()

    def init_ui(self):
        """Инициализация интерфейса"""
        self.setWindowTitle("Text Typer 2.0 by King Triton")
        self.setGeometry(100, 100, 900, 600)

        from PySide6.QtGui import QIcon
        import os
        icon_path = os.path.join(os.path.dirname(__file__), 'logo.ico')
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        title_label = QLabel("Введите или вставьте текст для автоматической печати:")
        title_label.setFont(QFont("Segoe UI", 11))
        main_layout.addWidget(title_label)

        self.text_edit = QTextEdit()
        self.text_edit.setFont(QFont("Consolas", 10))
        self.text_edit.setPlaceholderText("Вставьте текст сюда...")
        main_layout.addWidget(self.text_edit, stretch=1)

        settings_group = QGroupBox("Настройки")
        settings_layout = QVBoxLayout()

        delay_layout = QHBoxLayout()
        delay_label = QLabel("Задержка перед началом (сек):")
        delay_label.setMinimumWidth(200)
        self.delay_spin = QSpinBox()
        self.delay_spin.setMinimum(1)
        self.delay_spin.setMaximum(30)
        self.delay_spin.setValue(5)
        self.delay_spin.setToolTip("Время для переключения на нужное окно")
        delay_layout.addWidget(delay_label)
        delay_layout.addWidget(self.delay_spin)
        delay_layout.addStretch()
        settings_layout.addLayout(delay_layout)

        speed_layout = QHBoxLayout()
        speed_label = QLabel("Задержка между символами (сек):")
        speed_label.setMinimumWidth(200)
        self.speed_spin = QSpinBox()
        self.speed_spin.setMinimum(1)
        self.speed_spin.setMaximum(1000)
        self.speed_spin.setSingleStep(10)
        self.speed_spin.setValue(100)
        self.speed_spin.setToolTip("Задержка в миллисекундах (100 = 0.1 сек)")
        speed_layout.addWidget(speed_label)
        speed_layout.addWidget(self.speed_spin)
        speed_layout.addWidget(QLabel("мс"))
        speed_layout.addStretch()
        settings_layout.addLayout(speed_layout)

        hotkey_layout = QHBoxLayout()
        hotkey_label = QLabel("Горячая клавиша для старта:")
        hotkey_label.setMinimumWidth(200)
        self.hotkey_combo = QComboBox()
        self.hotkey_combo.addItems([
            "F9",
            "F10",
            "F11",
            "F12",
            "Ctrl+Shift+T",
            "Ctrl+Alt+T"
        ])
        self.hotkey_combo.currentTextChanged.connect(self.update_hotkey)
        hotkey_layout.addWidget(hotkey_label)
        hotkey_layout.addWidget(self.hotkey_combo)
        hotkey_layout.addStretch()
        settings_layout.addLayout(hotkey_layout)

        settings_group.setLayout(settings_layout)
        main_layout.addWidget(settings_group)

        buttons_layout = QHBoxLayout()

        self.start_button = QPushButton("Начать печатать")
        self.start_button.setMinimumHeight(40)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.start_button.clicked.connect(self.start_typing)
        buttons_layout.addWidget(self.start_button)

        self.stop_button = QPushButton("Остановить")
        self.stop_button.setMinimumHeight(40)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.stop_button.clicked.connect(self.stop_typing)
        buttons_layout.addWidget(self.stop_button)

        clear_button = QPushButton("Очистить")
        clear_button.setMinimumHeight(40)
        clear_button.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 5px;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        clear_button.clicked.connect(self.clear_text)
        buttons_layout.addWidget(clear_button)

        main_layout.addLayout(buttons_layout)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("color: gray; font-size: 10pt; padding: 5px;")
        main_layout.addWidget(self.status_label)

    def setup_hotkey(self):
        """Настройка горячей клавиши"""
        hotkey = self.hotkey_combo.currentText().lower().replace('+', '+')
        try:
            keyboard.add_hotkey(hotkey, self.start_typing)
        except:
            pass

    def update_hotkey(self):
        """Обновление горячей клавиши"""
        keyboard.unhook_all_hotkeys()
        self.setup_hotkey()
        self.status_label.setText(f"Горячая клавиша изменена: {self.hotkey_combo.currentText()}")

    def start_typing(self):
        """Запуск печати"""
        if self.is_typing:
            return

        text = self.text_edit.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Предупреждение", "Введите текст для печати!")
            return

        self.is_typing = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)

        self.typing_thread = threading.Thread(target=self.type_text, args=(text,), daemon=True)
        self.typing_thread.start()
        
    def type_text(self, text):
        """Процесс печати текста"""
        try:
            delay = self.delay_spin.value()
            speed = self.speed_spin.value() / 1000.0

            self.signals.started.emit()

            for i in range(delay, 0, -1):
                if not self.is_typing:
                    return
                self.status_label.setText(f"Печать начнется через {i} сек...")
                time.sleep(1)

            for i, char in enumerate(text):
                if not self.is_typing:
                    break

                if char == "\n":
                    pyautogui.press("enter")
                else:
                    keyboard.write(char, delay=speed)

                if i % 10 == 0:
                    progress = int((i / len(text)) * 100)
                    self.status_label.setText(f"Печать... {progress}%")

            self.signals.finished.emit()

        except Exception as e:
            self.signals.error.emit(str(e))
    
    def stop_typing(self):
        """Остановка печати"""
        self.is_typing = False
        self.status_label.setText("Печать остановлена")
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def on_typing_started(self):
        """Обработчик начала печати"""
        self.status_label.setText("Печать началась...")

    def on_typing_finished(self):
        """Обработчик завершения печати"""
        self.is_typing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("Печать завершена!")

    def on_typing_error(self, error_msg):
        """Обработчик ошибки"""
        self.is_typing = False
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText(f"Ошибка: {error_msg}")
        QMessageBox.critical(self, "Ошибка", f"Произошла ошибка:\n{error_msg}")

    def clear_text(self):
        """Очистка текста"""
        self.text_edit.clear()
        self.status_label.setText("Текст очищен")

    def closeEvent(self, event):
        """Обработка закрытия окна"""
        keyboard.unhook_all_hotkeys()
        self.is_typing = False
        event.accept()

def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = TextTyperApp()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()