import sys
from PySide6.QtWidgets import QApplication
from widgets.main_window import MainWindow
from PySide6.QtGui import QFont

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(14)
    app.setFont(font)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())