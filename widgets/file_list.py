import os
import yaml
from PySide6.QtCore import Qt, Signal, QDir, QFileSystemWatcher
from PySide6.QtGui import QFont, QShortcut, QKeySequence, QDesktopServices
from PySide6.QtWidgets import QWidget, QVBoxLayout, QListWidget, QListWidgetItem

# Custom roles for QListWidgetItem data
ItemTypeRole = Qt.UserRole + 1
FilePathRole = Qt.UserRole + 2

class FileListWidget(QWidget):
    backRequested = Signal()

    def __init__(self):
        super().__init__()
        self.folder_path = None
        self.watcher = QFileSystemWatcher(self)
        self.watcher.directoryChanged.connect(self.handle_folder_change)
        self.initUI()

    def initUI(self):
        self.listWidget = QListWidget()
        self.listWidget.setDragDropMode(QListWidget.InternalMove)

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
                                item = QListWidgetItem(file)
                                item.setData(ItemTypeRole, "file")
                                item.setData(FilePathRole, file_path)
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
                item = QListWidgetItem(file)
                item.setData(ItemTypeRole, "file")
                item.setData(FilePathRole, file_path)
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
            item = QListWidgetItem(file)
            item.setData(ItemTypeRole, "file")
            file_path = os.path.join(self.folder_path, file)
            item.setData(FilePathRole, file_path)
            self.listWidget.insertItem(insert_pos, item)
            insert_pos += 1

        self.save_yaml()

    def reset(self):
        self.folder_path = None
        self.listWidget.clear()
        if self.watcher.directories():
            self.watcher.removePaths(self.watcher.directories())