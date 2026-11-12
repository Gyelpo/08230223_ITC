"""Part A hello-world in PyQt6: a greeting and a button that counts presses."""
import sys
from PyQt6.QtWidgets import QApplication, QWidget, QVBoxLayout, QLabel, QPushButton


class Hello(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hello PyQt6 - Tshering Gyelpo (08230223)")
        self.resize(340, 150)
        self.presses = 0
        self.label = QLabel("Welcome to the library!")
        button = QPushButton("Borrow a book")
        button.clicked.connect(self.on_press)          # signal -> slot
        layout = QVBoxLayout(self)                     # layout manager
        layout.addWidget(self.label)
        layout.addWidget(button)

    def on_press(self):                                # slot
        self.presses += 1
        self.label.setText(f"Books borrowed: {self.presses}")


app = QApplication(sys.argv)
window = Hello()
window.show()
sys.exit(app.exec())                                   # event loop
