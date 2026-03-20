import sys
import os
import yaml
from PySide6.QtCore import Qt, QUrl, QDir, Signal, QFileSystemWatcher, QFileInfo, QSize, QPoint, QTimer
from PySide6.QtSvg import QSvgRenderer
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QDragEnterEvent, QDropEvent, QDesktopServices, QPixmap, QIcon, QPalette, QColor, QAction, QMouseEvent, QPainter, QCursor
from PySide6.QtWidgets import (QApplication, QMainWindow, QStackedWidget, QWidget, QVBoxLayout, 
                              QLabel, QPushButton, QListWidget, QListWidgetItem, QFileDialog, QHBoxLayout, QStyle, QFileIconProvider, QToolBar, QSizePolicy, QLineEdit, QGraphicsDropShadowEffect)

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes
    
    class MARGINS(ctypes.Structure):
        _fields_ = [
            ("cxLeftWidth", ctypes.c_int),
            ("cxRightWidth", ctypes.c_int),
            ("cyTopHeight", ctypes.c_int),
            ("cyBottomHeight", ctypes.c_int),
        ]
    
    class POINT(ctypes.Structure):
        _fields_ = [
            ("x", ctypes.c_long),
            ("y", ctypes.c_long),
        ]
    
    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wparam", wintypes.WPARAM),
            ("lparam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", POINT),
        ]
    
    DwmExtendFrameIntoClientArea = ctypes.windll.dwmapi.DwmExtendFrameIntoClientArea
    DwmExtendFrameIntoClientArea.argtypes = [wintypes.HWND, ctypes.POINTER(MARGINS)]
    DwmExtendFrameIntoClientArea.restype = ctypes.HRESULT
    
    SetWindowLongPtrW = ctypes.windll.user32.SetWindowLongPtrW
    GetWindowLongPtrW = ctypes.windll.user32.GetWindowLongPtrW
    SetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_longlong]
    SetWindowLongPtrW.restype = ctypes.c_longlong
    GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongPtrW.restype = ctypes.c_longlong
    
    GWL_EXSTYLE = -20
    WS_EX_LAYERED = 0x00080000
    WS_EX_TRANSPARENT = 0x00000020
    WM_NCHITTEST = 0x0084
    HTLEFT = 10
    HTRIGHT = 11
    HTTOP = 12
    HTBOTTOM = 15
    HTTOPLEFT = 13
    HTTOPRIGHT = 14
    HTBOTTOMLEFT = 16
    HTBOTTOMRIGHT = 17
    HTCLIENT = 1

# Base path for resources (handles both packaged and non-packaged scenarios)
def resource_path(relative_path):
    print(f"resource_path: Getting resource path for {relative_path}")
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
        print("ImportFolderWidget.__init__: Initializing")
        super().__init__()
        self.initUI()
        self.setAcceptDrops(True)
        QApplication.instance().paletteChanged.connect(self.update_icon)

    def initUI(self):
        print("ImportFolderWidget.initUI: Setting up UI")
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
        print(f"ImportFolderWidget.update_icon: Updating icon for theme lightness {palette.color(QPalette.Window).lightness()}")
        is_dark = palette.color(QPalette.Window).lightness() < 128

        # Load icons from assets folder using resource_path
        if is_dark:
            icon_path = resource_path("assets/FolderIconDark.png")
        else:
            icon_path = resource_path("assets/FolderIconLight.png")

        pixmap = QPixmap(icon_path)
        if pixmap.isNull():
            # Fallback to system icon if loading fails
            pixmap = QApplication.style().standardPixmap(QStyle.SP_DirIcon)
            print(f"Warning: Could not load icon at {icon_path}, using fallback.")

        self.icon_label.setPixmap(pixmap.scaled(128, 128, Qt.KeepAspectRatio, Qt.SmoothTransformation))

        if is_dark:
            self.button.setStyleSheet("""
                QPushButton {
                    background-color: #4a7c7c;
                    color: white;
                    border: 1px solid #5a9090;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #5a9494;
                    border-color: #6aa8a8;
                }
                QPushButton:pressed {
                    background-color: #3d6b6b;
                    border-color: #4a7c7c;
                }
            """)
        else:
            self.button.setStyleSheet("""
                QPushButton {
                    background-color: #3a7575;
                    color: white;
                    border: 1px solid #2e6060;
                    border-radius: 6px;
                    padding: 10px 24px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #4a8a8a;
                    border-color: #3a7575;
                }
                QPushButton:pressed {
                    background-color: #2e6060;
                    border-color: #245252;
                }
            """)

    def dragEnterEvent(self, event: QDragEnterEvent):
        print("ImportFolderWidget.dragEnterEvent: Drag enter event occurred")
        if event.mimeData().hasUrls():
            url = event.mimeData().urls()[0]
            if url.isLocalFile() and os.path.isdir(url.toLocalFile()):
                print("ImportFolderWidget.dragEnterEvent: Accepted drag of folder")
                event.accept()
            else:
                print("ImportFolderWidget.dragEnterEvent: Ignored drag: not a local folder")
                event.ignore()
        else:
            print("ImportFolderWidget.dragEnterEvent: Ignored drag: no URLs in mime data")
            event.ignore()

    def dropEvent(self, event: QDropEvent):
        print("ImportFolderWidget.dropEvent: Drop event occurred")
        url = event.mimeData().urls()[0]
        folder_path = url.toLocalFile()
        print(f"ImportFolderWidget.dropEvent: Selected folder via drop: {folder_path}")
        self.folderSelected.emit(folder_path)

    def selectFolder(self):
        print("ImportFolderWidget.selectFolder: Select folder button clicked")
        folder_path = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder_path:
            print(f"ImportFolderWidget.selectFolder: Selected folder via dialog: {folder_path}")
            self.folderSelected.emit(folder_path)

class FileListWidget(QWidget):
    backRequested = Signal()

    def __init__(self):
        print("FileListWidget.__init__: Initializing")
        super().__init__()
        self.folder_path = None
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self.handle_folder_change)
        self.icon_provider = QFileIconProvider()
        self.initUI()

    def initUI(self):
        print("FileListWidget.initUI: Setting up UI")
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
        model.rowsRemoved.connect(self.save_yaml)  # Connect rowsRemoved to save_yaml
        self.listWidget.itemChanged.connect(self.save_yaml)

        shortcut = QShortcut(QKeySequence("Ctrl+K"), self)
        shortcut.activated.connect(self.add_header)

        back_shortcut = QShortcut(QKeySequence("Ctrl+Backspace"), self)
        back_shortcut.activated.connect(self.backRequested)
    
    def load_svg_icon(self, filename, size=24):
        svg_path = resource_path(f"assets/{filename}")
        renderer = QSvgRenderer(svg_path)
        if not renderer.isValid():
            return QIcon()
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    
    def set_theme(self, color_scheme):
        print(f"FileListWidget.set_theme: Setting theme to {color_scheme}")
        if color_scheme == Qt.ColorScheme.Dark:
            hover_color = "#404040"
        else:
            hover_color = "#e0e0e0"
        bg_color = "#2b2b2b" if color_scheme == Qt.ColorScheme.Dark else "#ffffff"
        self.listWidget.setStyleSheet(f"""
            QListWidget {{
                background-color: {bg_color};
            }}
            QListWidget::item:hover {{
                background-color: {hover_color};
            }}
        """)

    def create_file_item(self, file_name, file_path):
        print(f"FileListWidget.create_file_item: Creating file item for {file_name}")
        item = QListWidgetItem(file_name)
        item.setData(ItemTypeRole, "file")
        item.setData(FilePathRole, file_path)
        file_info = QFileInfo(file_path)
        icon = self.icon_provider.icon(file_info)
        item.setIcon(icon)
        return item

    def create_header_item(self, header_text):
        print(f"FileListWidget.create_header_item: Creating header item: {header_text}")
        item_widget = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        label = QLabel(header_text)
        font = QFont()
        font.setPointSize(16)
        font.setBold(True)
        label.setFont(font)
        label.setWordWrap(False)

        delete_button = QPushButton()
        delete_button.setFixedSize(20, 20)
        delete_button.setIcon(self.load_svg_icon("icon-delete.svg", 16))
        delete_button.setIconSize(QSize(16, 16))
        delete_button.setVisible(False)
        delete_button.setStyleSheet("""
            QPushButton {
                border: none;
            }
            QPushButton:pressed {
                border: 1px solid gray;
            }
        """)
        delete_button.clicked.connect(lambda: self.delete_header(item_widget))

        item_widget.delete_button = delete_button
        item_widget.enterEvent = lambda e: delete_button.setVisible(True)
        item_widget.leaveEvent = lambda e: delete_button.setVisible(False)

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
        print("FileListWidget.delete_header: Deleting header")
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
        print(f"FileListWidget.setFolderPath: Setting folder path to {folder_path}")
        self.folder_path = folder_path
        self.listWidget.clear()
        yaml_path = os.path.join(folder_path, "file_groups.yaml")

        if os.path.exists(yaml_path):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    print("FileListWidget.setFolderPath: YAML file loaded successfully")
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
                print("FileListWidget.setFolderPath: Failed to load YAML file")
        else:
            print("FileListWidget.setFolderPath: No YAML file found, creating new one")
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
        print("FileListWidget.add_header: Adding new header")
        self.create_header_item("New Header")
        self.save_yaml()

    def onItemDoubleClicked(self, item):
        print(f"FileListWidget.onItemDoubleClicked: Item double-clicked: {item.text()}")
        if item.data(ItemTypeRole) == "file":
            file_path = item.data(FilePathRole)
            print(f"FileListWidget.onItemDoubleClicked: Opening file: {file_path}")
            QDesktopServices.openUrl(QUrl.fromLocalFile(file_path))
        elif item.data(ItemTypeRole) == "header":
            print("FileListWidget.onItemDoubleClicked: Editing header")
            self.edit_header_item(item)

    def edit_header_item(self, item):
        print(f"FileListWidget.edit_header_item: Editing header item: {item.text()}")
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
        else:
            print(f"Warning: Header item at row {self.listWidget.row(item)} has no widget")

    def finish_editing_header(self, item, edit):
        print(f"FileListWidget.finish_editing_header: Finished editing header to '{edit.text().strip()}'")
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
        print("FileListWidget.save_yaml: Saving YAML file")
        if not self.folder_path:
            return
        file_groups = {}
        section_index = 0
        current_section = None
        current_header = None
        current_files = []

        for i in range(self.listWidget.count()):
            item = self.listWidget.item(i)
            item_type = item.data(ItemTypeRole)
            if item_type == "header":
                if current_section is not None:
                    # Save the previous section, even if it has no files
                    file_groups[current_section] = {
                        "header": current_header,
                        "files": current_files
                    }
                # Start a new section
                section_index += 1
                current_section = str(section_index)
                widget = self.listWidget.itemWidget(item)
                if widget:
                    label = widget.findChild(QLabel)
                    if label:
                        current_header = label.text()
                    else:
                        edit = widget.findChild(QLineEdit)
                        if edit:
                            current_header = edit.text().strip()
                            if not current_header:
                                current_header = "Unnamed Header"
                        else:
                            print(f"Warning: Header item at row {i} has neither QLabel nor QLineEdit")
                            current_header = "Unnamed Header"
                else:
                    print(f"Warning: Header item at row {i} has no widget")
                    current_header = "Unnamed Header"
                current_files = []
            elif item_type == "file":
                if current_section is None:
                    # Files before any header go to "default"
                    if "default" not in file_groups:
                        file_groups["default"] = {"header": "", "files": []}
                    file_groups["default"]["files"].append(item.text())
                else:
                    current_files.append(item.text())
            else:
                print(f"Warning: Item at row {i} has unknown type: {item_type}")

        if current_section is not None:
            # Save the last section, even if it has no files
            file_groups[current_section] = {
                "header": current_header,
                "files": current_files
            }

        data = {"file_groups": file_groups}
        yaml_path = os.path.join(self.folder_path, "file_groups.yaml")
        with open(yaml_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, allow_unicode=True, sort_keys=False)

    def handle_folder_change(self):
        print("FileListWidget.handle_folder_change: Handling folder change")
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
                    print(f"FileListWidget.handle_folder_change: Removed file: {file}")
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
            print(f"FileListWidget.handle_folder_change: Added file: {file}")
            insert_pos += 1

    def reset(self):
        print("FileListWidget.reset: Resetting")
        self.folder_path = None
        self.listWidget.clear()
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())

class CustomTitleBar(QWidget):
    backClicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._drag_position = None
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 0, 5, 0)
        layout.setSpacing(8)
        
        self.back_button = QPushButton()
        self.back_button.setFixedSize(30, 30)
        self.back_button.setIcon(self.load_svg_icon("icon-back.svg"))
        self.back_button.setIconSize(QSize(20, 20))
        self.back_button.setVisible(False)
        self.back_button.setToolTip("Back")
        self.back_button.clicked.connect(self.backClicked)
        
        self.title_label = QLabel("File View")
        self.title_label.setStyleSheet("QLabel { font-weight: bold; }")
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        
        self.add_header_button = QPushButton()
        self.add_header_button.setFixedSize(30, 30)
        self.add_header_button.setIcon(self.load_svg_icon("icon-add.svg"))
        self.add_header_button.setIconSize(QSize(20, 20))
        self.add_header_button.setToolTip("Add new header")
        
        self.minimize_button = QPushButton()
        self.minimize_button.setFixedSize(30, 30)
        self.minimize_button.setIcon(self.load_svg_icon("icon-minimize.svg"))
        self.minimize_button.setIconSize(QSize(20, 20))
        self.minimize_button.setToolTip("Minimize")
        self.minimize_button.clicked.connect(lambda: self.window().showMinimized())
        
        self.maximize_button = QPushButton()
        self.maximize_button.setFixedSize(30, 30)
        self.maximize_button.setIcon(self.load_svg_icon("icon-maximize.svg"))
        self.maximize_button.setIconSize(QSize(20, 20))
        self.maximize_button.setToolTip("Maximize")
        self.maximize_button.clicked.connect(self.toggle_maximize)
        
        self.close_button = QPushButton()
        self.close_button.setObjectName("closeButton")
        self.close_button.setFixedSize(30, 30)
        self.close_button.setIcon(self.load_svg_icon("icon-close.svg"))
        self.close_button.setIconSize(QSize(20, 20))
        self.close_button.setToolTip("Close")
        self.close_button.clicked.connect(lambda: self.window().close())
        
        layout.addWidget(self.back_button)
        layout.addWidget(self.title_label)
        layout.addWidget(spacer)
        layout.addWidget(self.add_header_button)
        layout.addWidget(self.minimize_button)
        layout.addWidget(self.maximize_button)
        layout.addWidget(self.close_button)
        
        self.setFixedHeight(40)
    
    def load_svg_icon(self, filename, color=None):
        svg_path = resource_path(f"assets/{filename}")
        renderer = QSvgRenderer(svg_path)
        if not renderer.isValid():
            return QIcon()
        size = 24
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap)
        renderer.render(painter)
        painter.end()
        return QIcon(pixmap)
    
    def setTitle(self, text):
        self.title_label.setText(text)
    
    def setBackButtonVisible(self, visible):
        self.back_button.setVisible(visible)
    
    def setAddHeaderButtonVisible(self, visible):
        self.add_header_button.setVisible(visible)
    
    def toggle_maximize(self):
        if self.window().isMaximized():
            self.window().showNormal()
            self.maximize_button.setIcon(self.load_svg_icon("icon-maximize.svg"))
            self.maximize_button.setToolTip("Maximize")
        else:
            self.window().showMaximized()
            self.maximize_button.setIcon(self.load_svg_icon("icon-restore.svg"))
            self.maximize_button.setToolTip("Restore")
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_position = event.globalPosition().toPoint()
        super().mousePressEvent(event)
    
    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton and self._drag_position:
            if self.window().isMaximized():
                pass
            else:
                self.window().move(self.window().pos() + event.globalPosition().toPoint() - self._drag_position)
                self._drag_position = event.globalPosition().toPoint()
        super().mouseMoveEvent(event)
    
    def mouseReleaseEvent(self, event):
        self._drag_position = None
        super().mouseReleaseEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        self.toggle_maximize()


class MainWindow(QMainWindow):
    def __init__(self):
        print("MainWindow.__init__: Initializing")
        super().__init__()
        self.setWindowFlags(Qt.WindowFlags(Qt.FramelessWindowHint))
        self.setAttribute(Qt.WA_TranslucentBackground)
        self._resize_margin = 8
        self._minimum_width = 600
        self._minimum_height = 400
        self.setMinimumSize(self._minimum_width, self._minimum_height)
        self.setMouseTracking(True)
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
        print("MainWindow.initUI: Setting up UI")
        self.setWindowTitle("File View")
        self.setGeometry(100, 100, 600, 400)
        
        self.central_container = QWidget()
        self.central_container.setObjectName("centralContainer")
        self.setCentralWidget(self.central_container)
        
        container_layout = QVBoxLayout(self.central_container)
        container_layout.setContentsMargins(1, 1, 1, 1)
        container_layout.setSpacing(0)
        
        self.titleBar = CustomTitleBar(self)
        container_layout.addWidget(self.titleBar)
        self.titleBar.backClicked.connect(self.onBackRequested)
        
        self.stackedWidget = QStackedWidget()
        container_layout.addWidget(self.stackedWidget)
        self.importFolderWidget = ImportFolderWidget()
        self.fileListWidget = FileListWidget()
        self.stackedWidget.addWidget(self.importFolderWidget)
        self.stackedWidget.addWidget(self.fileListWidget)
        self.importFolderWidget.folderSelected.connect(self.onFolderSelected)
        self.fileListWidget.backRequested.connect(self.onBackRequested)
        self.add_header_action = QAction("+", self)
        self.add_header_action.setToolTip("Add new header")
        self.add_header_action.triggered.connect(self.fileListWidget.add_header)
        self.titleBar.add_header_button.clicked.connect(self.fileListWidget.add_header)
        
        self.stackedWidget.currentChanged.connect(self.updateTitleBar)
        self.updateTitleBar(self.stackedWidget.currentIndex())

    def updateTitleBar(self, index):
        print(f"MainWindow.updateTitleBar: Updating title bar for widget index {index}")
        if index == 1:
            self.titleBar.setBackButtonVisible(True)
            self.titleBar.setAddHeaderButtonVisible(True)
            self.titleBar.setTitle(self.titleBar.window().windowTitle() if self.titleBar.window().windowTitle() != "File View" else os.path.basename(self.fileListWidget.folder_path))
        else:
            self.titleBar.setBackButtonVisible(False)
            self.titleBar.setAddHeaderButtonVisible(False)
            self.titleBar.setTitle("File View")

    def enable_windows_shadow(self):
        hwnd = int(self.winId())
        ex_style = GetWindowLongPtrW(hwnd, GWL_EXSTYLE)
        SetWindowLongPtrW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_LAYERED)
        margins = MARGINS(-1, -1, -1, -1)
        DwmExtendFrameIntoClientArea(hwnd, ctypes.byref(margins))

    def showEvent(self, event):
        super().showEvent(event)
        if sys.platform == "win32":
            QTimer.singleShot(0, self.enable_windows_shadow)
    
    def nativeEvent(self, eventType, message):
        if sys.platform == "win32" and eventType == "windows_generic_MSG":
            try:
                msg_address = int(message)
                msg = ctypes.cast(msg_address, ctypes.POINTER(MSG)).contents
                
                if msg.message == WM_NCHITTEST:
                    if self.isMaximized():
                        return False, HTCLIENT
                    
                    pos = QPoint(msg.lparam & 0xFFFF, (msg.lparam >> 16) & 0xFFFF)
                    window_pos = self.mapFromGlobal(pos)
                    
                    width = self.width()
                    height = self.height()
                    margin = self._resize_margin
                    titlebar_height = self.titleBar.height() if hasattr(self, 'titleBar') else 40
                    
                    on_left = window_pos.x() < margin
                    on_right = window_pos.x() > width - margin
                    on_top = window_pos.y() < margin
                    on_bottom = window_pos.y() > height - margin
                    
                    if on_top and on_left:
                        return True, HTTOPLEFT
                    elif on_top and on_right:
                        return True, HTTOPRIGHT
                    elif on_bottom and on_left:
                        return True, HTBOTTOMLEFT
                    elif on_bottom and on_right:
                        return True, HTBOTTOMRIGHT
                    elif on_left:
                        return True, HTLEFT
                    elif on_right:
                        return True, HTRIGHT
                    elif on_top:
                        return True, HTTOP
                    elif on_bottom:
                        return True, HTBOTTOM
            except Exception:
                pass
        return False, 0
    
    def mouseMoveEvent(self, event):
        if self.isMaximized():
            self.setCursor(Qt.ArrowCursor)
            return
        
        pos = event.position().toPoint()
        width = self.width()
        height = self.height()
        margin = self._resize_margin
        on_left = pos.x() < margin
        on_right = pos.x() > width - margin
        on_top = pos.y() < margin
        on_bottom = pos.y() > height - margin
        
        if on_top and on_left:
            self.setCursor(Qt.SizeFDiagCursor)
        elif on_top and on_right:
            self.setCursor(Qt.SizeBDiagCursor)
        elif on_bottom and on_left:
            self.setCursor(Qt.SizeBDiagCursor)
        elif on_bottom and on_right:
            self.setCursor(Qt.SizeFDiagCursor)
        elif on_left or on_right:
            self.setCursor(Qt.SizeHorCursor)
        elif on_top or on_bottom:
            self.setCursor(Qt.SizeVerCursor)
        else:
            self.setCursor(Qt.ArrowCursor)
        
        super().mouseMoveEvent(event)
    
    def leaveEvent(self, event):
        self.setCursor(Qt.ArrowCursor)
        super().leaveEvent(event)
    
    def changeEvent(self, event):
        super().changeEvent(event)
        if event.type() == event.Type.WindowStateChange:
            self.update_border_radius()
    
    def update_border_radius(self):
        window_color = QApplication.instance().palette().color(QPalette.Window)
        if self.isMaximized():
            self.central_container.setStyleSheet(f"""
                #centralContainer {{
                    background-color: {window_color.name()};
                    border-radius: 0px;
                }}
            """)
        else:
            border_color = "#404040" if window_color.lightness() < 128 else "#d0d0d0"
            self.central_container.setStyleSheet(f"""
                #centralContainer {{
                    background-color: {window_color.name()};
                    border-radius: 8px;
                    border: 1px solid {border_color};
                }}
            """)

    def apply_system_theme(self):
        print("MainWindow.apply_system_theme: Applying system theme")
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
        
        window_color = palette.color(QPalette.Window)
        text_color = palette.color(QPalette.WindowText)
        
        self.update_border_radius()
        
        self.titleBar.setStyleSheet(f"""
            QWidget {{
                background-color: {window_color.name()};
                color: {text_color.name()};
            }}
            QPushButton {{
                background-color: transparent;
                border: none;
            }}
            QPushButton:hover {{
                background-color: rgba(128, 128, 128, 0.3);
                border-radius: 4px;
            }}
            QPushButton#closeButton:hover {{
                background-color: red;
                border-radius: 4px;
            }}
        """)

    def onFolderSelected(self, folder_path):
        print(f"MainWindow.onFolderSelected: Folder selected: {folder_path}")
        self.fileListWidget.setFolderPath(folder_path)
        self.stackedWidget.setCurrentWidget(self.fileListWidget)
        self.titleBar.setTitle(os.path.basename(folder_path))

    def onBackRequested(self):
        print("MainWindow.onBackRequested: Back requested")
        self.fileListWidget.reset()
        self.stackedWidget.setCurrentWidget(self.importFolderWidget)
        self.titleBar.setTitle("File View")

if __name__ == "__main__":
    print("main: Starting application")
    app = QApplication(sys.argv)
    font = QFont()
    font.setPointSize(14)
    app.setFont(font)
    app.setStyleSheet("QToolTip { font-size: 10pt; }")
    mainWindow = MainWindow()
    mainWindow.show()
    sys.exit(app.exec())