import sys
import os
import yaml
from PySide6.QtCore import Qt, QUrl, QDir, Signal, QFileSystemWatcher, QFileInfo, QSize
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QDragEnterEvent, QDropEvent, QDesktopServices, QPixmap, QIcon, QPalette, QColor, QAction
from PySide6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
                              QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QHBoxLayout, QStyle, QFileIconProvider, QToolBar, QSizePolicy, QLineEdit)

# Base path for resources (handles both packaged and non-packaged scenarios)
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller."""
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath(os.path.dirname(__file__)), relative_path)

# Fix for taskbar icon on Windows
if sys.platform == "win32":
    import ctypes
    myappid = 'com.mycompany.fileexplorer.1.0'  # Unique identifier
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(myappid)

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
        self.label.setWordWrap(True)
        layout.addWidget(self.label)

        self.button = QPushButton("Select Folder")
        self.button.setFixedWidth(200)
        layout.addWidget(self.button, alignment=Qt.AlignCenter)

        layout.addStretch(1)
        self.setLayout(layout)

        self.button.clicked.connect(self.selectFolder)

        self.update_icon(QApplication.instance().palette())

    def update_icon(self, palette):
        # Load icons from assets folder using resource_path
        if palette.color(QPalette.Window).lightness() < 128:
            icon_path = resource_path("assets/FolderIconDark.png")
        else:
            icon_path = resource_path("assets/FolderIconLight.png")
        
        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            # Fallback to system icon if loading fails
            pixmap = QApplication.style().standardPixmap(QStyle.SP_DirIcon)
            print(f"Warning: Could not load icon at {icon_path}, using fallback.")
        
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
        self.icon_provider = QFileIconProvider()
        self.initUI()

    def initUI(self):
        self.listWidget = QListWidget()
        self.listWidget.setDragDropMode(QListWidget.InternalMove)
        self.listWidget.setIconSize(QSize(24, 24))

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
        if color_scheme == Qt.ColorScheme.Dark:
            hover_color = "#404040"
        else:
            hover_color = "#e0e0e0"
        self.listWidget.setStyleSheet(f"""
            QListWidget::item:hover {{
                background-color: {hover_color};
            }}
        """)

    def create_file_item(self, file_name, file_path):
        item = QListWidgetItem(file_name)
        item.setData(ItemTypeRole, "file")
        item.setData(FilePathRole, file_path)
        file_info = QFileInfo(file_path)
        icon = self.icon_provider.icon(file_info)
        item.setIcon(icon)
        return item

    def create_header_item(self, header_text):
        item_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(header_text)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        label.setFont(font)
        label.setWordWrap(True)

        delete_button = QPushButton("×")
        delete_button.setFixedSize(20, 20)
        delete_button.setStyleSheet("""
            QPushButton {
                border: none;
            }
            QPushButton:pressed {
                border: 1px solid gray;
            }
        """)
        delete_button.clicked.connect(lambda: self.delete_header(item_widget))

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(delete_button)
        item_widget.setLayout(layout)

        item = QListWidgetItem()
        item.setData(ItemTypeRole, "header")
        item.setSizeHint(item_widget.sizeHint())
        self.listWidget.addItem(item)
        self.listWidget.setItemWidget(item, item_widget)
        return item

    def delete_header(self, item_widget):
        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            if self.listWidget.itemWidget(item) == item_widget:
                start_idx = i
                end_idx = i + 1
                while end_idx < self.listWidget.count() and self.listWidget.item(end_idx).data(ItemTypeRole) == "file":
                    end_idx += 1

                # Collect files to move
                num_files = end_idx - start_idx - 1
                files_to_move = []
                for _ in range(num_files):
                    item = self.listWidget.takeItem(start_idx + 1)
                    files_to_move.append(item)

                # Remove the header
                self.listWidget.takeItem(start_idx)

                # Find target position
                target_pos = 0
                for j in range(start_idx - 1, -1, -1):
                    if self.listWidget.item(j).data(ItemTypeRole) == "header":
                        target_pos = j + 1
                        break

                # Insert files at target position
                for file_item in files_to_move:
                    self.listWidget.insertItem(target_pos, file_item)
                    target_pos += 1

                self.save_yaml()
                break

    def setFolderPath(self, folder_path):
        self.folder_path = folder_path
        self.listWidget.clear()
        yaml_path = os.path.join(folder_path, "file_groups.yaml")

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    file_groups = data.get("file_groups", {})
                    for key in sorted(file_groups.keys(), key=lambda x: (x != "default", x)):
                        section = file_groups[key]
                        if key != "default":
                            self.create_header_item(section["header"])
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
                    "default": {
                        "header": "",
                        "files": files
                    }
                }
            }
            with open(yaml_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
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
        self.create_header_item("New Header")
        self.save_yaml()

    def onItemDoubleClicked(self, item):
        if item.data(ItemTypeRole) == "file":
            file_path = item.data(FilePathRole)
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        elif item.data(ItemTypeRole) == "header":
            self.edit_header_item(item)

    def edit_header_item(self, item):
        widget = self.listWidget.itemWidget(item)
        if widget:
            label = widget.findChild(QLabel)
            if label:
                edit = QLineEdit(label.text())
                edit.setFont(label.font())
                edit.setFrame(False)
                edit.selectAll()
                edit.setFocusPolicy(Qt.StrongFocus)
                edit.editingFinished.connect(lambda: self.finish_editing_header(item, edit))
                layout = widget.layout()
                # Store the label's alignment
                label_alignment = label.alignment()
                # Replace the label with the line edit
                layout.replaceWidget(label, edit)
                label.setParent(None)
                edit.setParent(widget)
                # Match alignment and ensure minimum size
                edit.setAlignment(label_alignment)
                edit.setMinimumSize(label.sizeHint())
                # Allow the line edit to stretch in the layout
                layout.setStretchFactor(edit, layout.stretchFactor(label) if hasattr(layout, 'stretchFactor') else 1)
                # Update size dynamically as text changes
                edit.textChanged.connect(lambda: edit.setMinimumWidth(edit.sizeHint().width()))
                edit.setFocus()  # Set focus last
            else:
                print(f"Warning: Header item at row {self.listWidget.row(item)} has no QLabel")

    def finish_editing_header(self, item, edit):
        new_text = edit.text().strip()
        if not new_text:
            new_text = "Unnamed Header"
        widget = self.listWidget.itemWidget(item)
        if widget:
            layout = widget.layout()
            label = QLabel(new_text)
            font = QFont()
            font.setPointSize(16)
            font.setBold(True)
            label.setFont(font)
            label.setWordWrap(True)
            layout.replaceWidget(edit, label)
            edit.setParent(None)
            label.setParent(widget)
            self.save_yaml()

    def save_yaml(self):
        if not self.folder_path:
            return
        file_groups = {}
        current_section = "default"
        current_header = ""
        current_files = []
        section_index = 0

        file_groups["default"] = {"header": "", "files": []}

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            item_type = item.data(ItemTypeRole)
            if item_type == "header":
                widget = self.listWidget.itemWidget(item)
                if widget:
                    label = widget.findChild(QLabel)
                    if label:
                        if current_files:
                            file_groups[current_section] = {
                                "header": current_header,
                                "files": current_files
                            }
                        current_header = label.text()
                        current_files = []
                        section_index += 1
                        current_section = str(section_index)
                    else:
                        edit = widget.findChild(QLineEdit)
                        if edit:
                            if current_files:
                                file_groups[current_section] = {
                                    "header": current_header,
                                    "files": current_files
                                }
                            current_header = edit.text().strip()
                            if not current_header:
                                current_header = "Unnamed Header"
                            current_files = []
                            section_index += 1
                            current_section = str(section_index)
                        else:
                            print(f"Warning: Header item at row {i} has neither QLabel nor QLineEdit")
                            continue
                else:
                    print(f"Warning: Header item at row {i} has no widget")
                    continue
            elif item_type == "file":
                current_files.append(item.text())
            else:
                print(f"Warning: Item at row {i} has unknown type: {item_type}")

        if current_files:
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
                break
            insert_pos += 1

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
        app_icon_path = resource_path("assets/AppIcon.ico")
        app_icon = QIcon(app_icon_path)
        if app_icon.isNull():
            print(f"Warning: Could not load application icon at {app_icon_path}")
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
        self.setWindowTitle("File View")
        self.setGeometry(100, 100, 600, 400)

        # Create toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Create actions
        self.back_action = QAction("<", self)
        self.back_action.setToolTip("Back to folder selection")
        self.add_header_action = QAction("+", self)
        self.add_header_action.setToolTip("Add new header")

        # Connect actions
        self.back_action.triggered.connect(self.onBackRequested)
        self.add_header_action.triggered.connect(self.fileListWidget.add_header)

        # Add actions to toolbar with a spacer
        self.toolbar.addAction(self.back_action)
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        self.toolbar.addWidget(spacer)
        self.toolbar.addAction(self.add_header_action)

        # Initially hide the toolbar
        self.toolbar.setVisible(False)

        # Connect stacked widget's currentChanged signal
        self.stackedWidget.currentChanged.connect(self.updateToolbar)

    def updateToolbar(self, index):
        if index == 1:  # fileListWidget
            self.toolbar.setVisible(True)
            self.back_action.setEnabled(True)
            self.add_header_action.setEnabled(True)
        else:  # importFolderWidget
            self.toolbar.setVisible(False)
            self.back_action.setEnabled(False)
            self.add_header_action.setEnabled(False)

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