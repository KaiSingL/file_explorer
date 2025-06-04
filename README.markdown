# File View

File View is a simple file explorer application built with PySide6 that allows users to organize files within a selected folder into groups using headers. The grouping information is saved in a YAML file within the folder, making it easy to manage and revisit the organization.

## Features

- Select a folder by dragging and dropping or using the "Select Folder" button.
- View files in the selected folder, organized into groups with headers.
- Add new headers using `Ctrl+K` or the "+" button in the toolbar.
- Edit headers by double-clicking on them.
- Delete headers, which moves the files under that header to the default group.
- Open files by double-clicking on them.
- Go back to the folder selection screen using `Ctrl+Backspace` or the "<" button in the toolbar.
- Automatically updates the file list when files are added or removed from the folder.
- Adapts to the system's light or dark theme.

## Requirements

- Python 3.x
- PySide6
- PyYAML

## Installation

1. Ensure that Python is installed on your system.
2. Install the required modules using pip:
   ```
   pip install PySide6 PyYAML
   ```
3. Place the "assets" folder containing `FolderIconDark.png`, `FolderIconLight.png`, and `AppIcon.ico` in the same directory as the script.

## Usage

1. Run the application by executing:
   ```
   python file_explorer.py
   ```
2. Select a folder by dragging and dropping it onto the application window or by clicking the "Select Folder" button.
3. Once a folder is selected, the files will be displayed. You can add headers to group the files.
4. To add a header, press `Ctrl+K` or click the "+" button in the toolbar.
5. To edit a header, double-click on it and type the new text.
6. To delete a header, click the "×" button next to it. The files under that header will be moved to the default group.
7. To open a file, double-click on it.
8. To go back to the folder selection screen, press `Ctrl+Backspace` or click the "<" button in the toolbar.

## Packaging with PyInstaller

To create a standalone executable for the application, you can use PyInstaller to package the script along with its dependencies and assets. Run the following command in the directory containing `file_explorer.py` and the `assets` folder:

```
pyinstaller --onefile --windowed --add-data "assets;assets" --icon=assets/AppIcon.ico --name "File View" file_explorer.py
```

### Explanation of the command:
- `--onefile`: Packages the application into a single executable file.
- `--windowed`: Runs the application without a console window (suitable for GUI applications).
- `--add-data "assets;assets"`: Includes the `assets` folder in the packaged executable, ensuring icons are available.
- `--icon=assets/AppIcon.ico`: Sets the application icon for the executable.
- `--name "File View"`: Names the output executable "File View".
- `file_explorer.py`: The main script to package.

After running the command, the executable will be created in the `dist` folder as `File View.exe` (on Windows) or `File View` (on other platforms).

## Notes

- The grouping information is saved in a file named `file_groups.yaml` within the selected folder.
- If the YAML file is missing or malformed, the application will create a new one with all files in the default group.
- If the asset icons are missing, the application will use fallback system icons.
- The application watches the selected folder for changes and updates the file list accordingly.