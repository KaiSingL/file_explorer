from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QIcon, QPalette, QColor
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QApplication
from .import_folder import ImportFolderWidget
from .file_list import FileListWidget

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.initUI()
        self.apply_system_theme()
        QApplication.instance().styleHints().colorSchemeChanged.connect(self.apply_system_theme)

        # Set application icon
        app_icon = QIcon("assets/AppIcon.png")
        self.setWindowIcon(app_icon)

    def initUI(self):
        self.stackedWidget = QStackedWidget()
        self.setCentralWidget(self.stackedWidget)
        self.importFolderWidget = ImportFolderWidget()
        self.fileListWidget = FileListWidget()
        self.stackedWidget.addWidget(self.importFolderWidget)
        self.stackedWidget.addWidget(self.fileListWidget)
        self.importFolderWidget.folderSelected.connect(self.onFolderSelected)
        self.fileListWidget.backRequested.connect(self.onBackRequested)
        self.setWindowTitle("Simplified File Explorer")
        self.setGeometry(100, 100, 600, 400)

    def apply_system_theme(self):
        style_hints = QApplication.instance().styleHints()
        color_scheme = style_hints.colorScheme()
        
        palette = QPalette()
        if color_scheme == Qt.ColorScheme.Dark:
            palette.setColor(QPalette.Window, QColor("#2b2b2b"))
            palette.setColor(QPalette.WindowText, Qt.white)
            palette.setColor(QPalette.Base, QColor("#3c3c3c"))
            palette.setColor(QPalette.AlternateBase, QColor("#4a4a4a"))
            palette.setColor(QPalette.Text, Qt.white)
            palette.setColor(QPalette.Button, QColor("#4a4a4a"))
            palette.setColor(QPalette.ButtonText, Qt.white)
        elif color_scheme == Qt.ColorScheme.Light:
            palette.setColor(QPalette.Window, Qt.white)
            palette.setColor(QPalette.WindowText, Qt.black)
            palette.setColor(QPalette.Base, QColor("#f0f0f0"))
            palette.setColor(QPalette.AlternateBase, QColor("#e0e0e0"))
            palette.setColor(QPalette.Text, Qt.black)
            palette.setColor(QPalette.Button, QColor("#e0e0e0"))
            palette.setColor(QPalette.ButtonText, Qt.black)
        else:
            system_palette = QApplication.instance().palette()
            if system_palette.color(QPalette.Window).lightness() < 128:
                palette.setColor(QPalette.Window, QColor("#2b2b2b"))
                palette.setColor(QPalette.WindowText, Qt.white)
                palette.setColor(QPalette.Base, QColor("#3c3c3c"))
                palette.setColor(QPalette.Text, Qt.white)
            else:
                palette.setColor(QPalette.Window, Qt.white)
                palette.setColor(QPalette.WindowText, Qt.black)
                palette.setColor(QPalette.Base, QColor("#f0f0f0"))
                palette.setColor(QPalette.Text, Qt.black)
        QApplication.instance().setPalette(palette)

    def onFolderSelected(self, folder_path):
        self.fileListWidget.setFolderPath(folder_path)
        self.stackedWidget.setCurrentWidget(self.fileListWidget)

    def onBackRequested(self):
        self.fileListWidget.reset()
        self.stackedWidget.setCurrentWidget(self.importFolderWidget)