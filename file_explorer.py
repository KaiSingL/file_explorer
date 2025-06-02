import sys
import os
import yaml
from PySide6.QtCore import Qt, QUrl, QDir, Signal, QFileSystemWatcher, QFileInfo, QSize
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QDragEnterEvent, QDropEvent, QDesktopServices, QPixmap, QIcon, QPalette, QColor
from PySide6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
                              QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QHBoxLayout, QStyle, QFileIconProvider)

# Custom roles for QListWidgetItem data
ItemTypeRole = Qt.UserRole + 1
FilePathRole = Qt.UserRole + 2

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

class FileListWidget(QWidget):
    backRequested = Signal()

    def __init__(self):
        super().__init__()
        self.folder_path = None
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self.handle_folder_change)
        self.icon_provider = QFileIconProvider()  # Initialize icon provider
        self.initUI()

    def initUI(self):
        self.listWidget = QListWidget()
        self.listWidget.setDragDropMode(QListWidget.InternalMove)
        self.listWidget.setIconSize(QSize(24, 24))  # Set icon size for consistency

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.listWidget)
        self.setLayout(main_layout)

        self.listWidget.itemDoubleClicked.connect(self.onItemDoubleClicked)
        model = self.listWidget.model()
        model.rowsInserted.connect(self.save_yaml)
        model.rowsMoved.connect(self.save_yaml)
        self.listWidget.itemChanged.connect(self.save_yaml)

        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self.add_header)

        back_shortcut = QShortcut(QKeySequence("Ctrl+Backspace"), self)
        back_shortcut.activated.connect(self.backRequested)

    def set_theme(self, color_scheme):
        """Set the stylesheet for hover effect based on the theme."""
        if color_scheme == Qt.ColorScheme.Dark:
            hover_color = "#404040"  # Slightly lighter for dark mode
        else:
            hover_color = "#e0e0e0"  # Slightly darker for light mode
        self.listWidget.setStyleSheet(f"""
            QListWidget::item:hover {{
                background-color: {hover_color};
            }}
        """)

    def create_file_item(self, file_name, file_path):
        """Create a QListWidgetItem for a file with its corresponding icon."""
        item = QListWidgetItem(file_name)
        item.setData(ItemTypeRole, "file")
        item.setData(FilePathRole, file_path)
        file_info = QFileInfo(file_path)
        icon = self.icon_provider.icon(file_info)
        item.setIcon(icon)
        return item

    def setFolderPath(self, folder_path):
        self.folder_path = folder_path
        self.listWidget.clear()
        yaml_path = os.path.join(folder_path, "file_groups.yaml")

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    file_groups = data.get("file_groups", {})
                    first_header = True
                    for key in sorted(file_groups.keys(), key=lambda x: (x != "top", x)):
                        section = file_groups[key]
                        header_item = QListWidgetItem(section["header"])
                        header_item.setData(ItemTypeRole, "header")
                        font = QFont()
                        if first_header:
                            font.setPointSize(18)
                            first_header = False
                        else:
                            font.setPointSize(16)
                        font.setBold(True)
                        header_item.setFont(font)
                        header_item.setFlags(header_item.flags() | Qt.ItemIsEditable)
                        self.listWidget.addItem(header_item)
                        for file in section["files"]:
                            file_path = os.path.join(folder_path, file)
                            if os.path.exists(file_path):
                                item = self.create_file_item(file, file_path)
                                self.listWidget.addItem(item)
            except Exception:
                pass

        if self.listWidget.count() == 0:
            dir = QDir(folder_path)
            files = [f for f in dir.entryList(QDir.Files) if f != "file_groups.yaml"]
            data = {
                "file_groups": {
                    "top": {
                        "header": "default section",
                        "files": files
                    }
                }
            }
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            header_item = QListWidgetItem("default section")
            header_item.setData(ItemTypeRole, "header")
            font = QFont()
            font.setPointSize(18)
            font.setBold(True)
            header_item.setFont(font)
            header_item.setFlags(header_item.flags() | Qt.ItemIsEditable)
            self.listWidget.addItem(header_item)
            for file in files:
                file_path = os.path.join(folder_path, file)
                item = self.create_file_item(file, file_path)
                self.listWidget.addItem(item)

        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())
        if self.folder_path:
            self.watcher.addPath(self.folder_path)

        self.handle_folder_change()

    def add_header(self):
        item = QListWidgetItem("New Header")
        item.setData(ItemTypeRole, "header")
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        item.setFont(font)
        item.setFlags(item.flags() | Qt.ItemIsEditable)
        self.listWidget.addItem(item)

    def onItemDoubleClicked(self, item):
        if item.data(ItemTypeRole) == "file":
            file_path = item.data(FilePathRole)
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))

    def save_yaml(self):
        if not self.folder_path:
            return
        file_groups = {}
        section_index = 0
        current_section = "top"
        current_header = "default section"
        current_files = []
        in_top_section = True

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.data(ItemTypeRole) == "header":
                if in_top_section:
                    if current_files:
                        file_groups[current_section] = {
                            "header": current_header,
                            "files": current_files
                        }
                    in_top_section = False
                else:
                    file_groups[current_section] = {
                        "header": current_header,
                        "files": current_files
                    }
                current_header = item.text()
                current_files = []
                section_index += 1
                current_section = str(section_index)
            elif item.data(ItemTypeRole) == "file":
                current_files.append(item.text())

        if not in_top_section or current_files:
            file_groups[current_section] = {
                "header": current_header,
                "files": current_files
            }

        data = {"file_groups": file_groups}
        yaml_path = os.path.join(self.folder_path, "file_groups.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def handle_folder_change(self):
        if not self.folder_path:
            return
        dir = QDir(self.folder_path)
        current_files = set(f for f in dir.entryList(QDir.Files) if f != "file_groups.yaml")
        widget_files = set()
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if item.data(ItemTypeRole) == "file":
                widget_files.add(item.text())

        removed_files = widget_files - current_files
        added_files = current_files - widget_files

        for file in removed_files:
            for i in range(self.listWidget.count()):
                item = self.listWidget.item(i)
                if item.data(ItemTypeRole) == "file" and item.text() == file:                     
                    self.listWidget.takeItem(i)
                    break

        insert_pos = 0
        for i in range(self.listWidget.count()):
            if self.listWidget.item(i).data(ItemTypeRole) == "header":
                insert_pos = i
                break
        else:
            insert_pos = self.listWidget.count()

        for file in added_files:
            file_path = os.path.join(self.folder_path, file)
            item = self.create_file_item(file, file_path)
            self.listWidget.insertItem(insert_pos, item)
            insert_pos += 1

        self.save_yaml()

    def reset(self):
        self.folder_path = None
        self.listWidget.clear()
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())

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
        
        # Apply theme to FileListWidget
        self.fileListWidget.set_theme(color_scheme)

    def onFolderSelected(self, folder_path):
        self.fileListWidget.setFolderPath(folder_path)
        self.stackedWidget.setCurrentWidget(self.fileListWidget)

    def onBackRequested(self):
        self.fileListWidget.reset()
        self.stackedWidget.setCurrentWidget(self.importFolderWidget)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(14)
    app.setFont(font)
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())