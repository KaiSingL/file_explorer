import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDropEvent, QPixmap, QIcon, QPalette, QColor
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QFileDialog, QApplication

class ImportFolderWidget(QWidget):
    folderSelected = Signal(str)

    def __init__(self):
        super().__init__()
        self.initUI()
        self.setAcceptDrops(True)
        QApplication.instance().paletteChanged.connect(self.update_icon)

    def initUI(self):
        layout = QVBoxLayout()
        layout.addStretch(1)

        self.icon_label = QLabel()
        self.icon_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.icon_label)

        self.label = QLabel("Drag and drop a folder here or click the button to select a folder.")
        self.label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.label)

        self.button = QPushButton("Select Folder")
        self.button.setFixedWidth(200)
        layout.addWidget(self.button, alignment=Qt.AlignCenter)

        layout.addStretch(1)
        self.setLayout(layout)

        self.button.clicked.connect(self.selectFolder)

        # Set initial icon based on current palette
        self.update_icon(QApplication.instance().palette())

    def update_icon(self, palette):
        if palette.color(QPalette.Window).lightness() < 128:
            icon_path = "assets/FolderIconDark.png"
        else:
            icon_path = "assets/FolderIconLight.png"
        
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            pixmap = QApplication.style().standardPixmap(QStyle.SP_DirIcon)
        
        self.icon_label.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and os.path.isdir(url.toLocalFile()):
                event.accept()
            else:
                event.ignore()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        url = event.mimeData().urls()[0]
        folder_path = url.toLocalFile()
        self.folderSelected.emit(folder_path)

    def selectFolder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            self.folderSelected.emit(folder_path)