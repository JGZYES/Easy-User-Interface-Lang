import sys
import os
import re
import glob
import tempfile
import shutil
import winreg
from PyQt5.QtWidgets import (QApplication, QMainWindow, QTextEdit, QPushButton, 
                            QVBoxLayout, QHBoxLayout, QWidget, QMenuBar, QMenu, 
                            QAction, QFileDialog, QMessageBox, QStatusBar,
                            QSplitter, QListWidget, QTabWidget, QLabel, QDockWidget,
                            QToolBar, QDialog, QRadioButton, QGroupBox,
                            QDialogButtonBox, QCompleter, QTreeWidget, QTreeWidgetItem,
                            QInputDialog, QMenu as QContextMenu, QComboBox)
from PyQt5.QtGui import (QFont, QSyntaxHighlighter, QTextCharFormat, QColor,
                         QTextDocument, QTextCursor, QIcon, QPixmap)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QProcess, QDateTime, QTimer, QStringListModel

# 文件关联相关功能
class FileAssociation:
    @staticmethod
    def is_associated():
        try:
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".eui", 0, winreg.KEY_READ) as key:
                prog_id, _ = winreg.QueryValueEx(key, "")
                if prog_id != "EasyUIEditor.eui":
                    return False
                    
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui\\shell\\open\\command", 0, winreg.KEY_READ) as key:
                command, _ = winreg.QueryValueEx(key, "")
                current_exe = sys.executable
                if current_exe.endswith("python.exe"):
                    script_path = os.path.abspath(sys.argv[0])
                    return script_path in command
                else:
                    return current_exe in command
            return True
        except WindowsError:
            return False
    
    @staticmethod
    def set_association():
        try:
            if getattr(sys, 'frozen', False):
                current_path = sys.executable
            else:
                current_path = os.path.abspath(sys.argv[0])
            
            icon_path = os.path.join(get_base_path(), "icon", "eui.ico")
            if not os.path.exists(icon_path):
                reply = QMessageBox.question(
                    None, "图标文件未找到",
                    f"未找到图标文件: {icon_path}\n仍要继续设置文件关联吗？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    return False
            
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".eui") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "EasyUIEditor.eui")
                winreg.SetValueEx(key, "Content Type", 0, winreg.REG_SZ, "text/plain")
            
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, "Easy UI 文件")
                
                if os.path.exists(icon_path):
                    with winreg.CreateKey(key, "DefaultIcon") as icon_key:
                        winreg.SetValueEx(icon_key, "", 0, winreg.REG_SZ, f"{icon_path},0")
            
            cmd_path = f'"{current_path}" "%1"'
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui\\shell\\open\\command") as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, cmd_path)
            
            with winreg.CreateKey(winreg.HKEY_CLASSES_ROOT, ".eui\\OpenWithProgids") as key:
                winreg.SetValueEx(key, "EasyUIEditor.eui", 0, winreg.REG_NONE, b"")
            
            return True
        except WindowsError as e:
            QMessageBox.critical(None, "文件关联失败", f"设置文件关联时出错：\n{str(e)}\n请尝试以管理员身份运行程序。")
            return False
    
    @staticmethod
    def remove_association():
        try:
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui\\shell\\open\\command")
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui\\shell\\open")
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui\\shell")
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui\\DefaultIcon")
            winreg.DeleteKey(winreg.HKEY_CLASSES_ROOT, "EasyUIEditor.eui")
            
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".eui", 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, "")
            
            with winreg.OpenKey(winreg.HKEY_CLASSES_ROOT, ".eui\\OpenWithProgids", 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, "EasyUIEditor.eui")
            
            return True
        except WindowsError as e:
            QMessageBox.critical(None, "移除关联失败", f"移除文件关联时出错：\n{str(e)}\n请尝试以管理员身份运行程序。")
            return False


class CompleterTextEdit(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.completer = None

    def setCompleter(self, completer):
        if self.completer:
            self.completer.activated.disconnect()
            
        self.completer = completer
        if not self.completer:
            return
            
        self.completer.setWidget(self)
        self.completer.activated.connect(self.insertCompletion)

    def insertCompletion(self, completion):
        if not self.completer:
            return
            
        completion_text = completion.split(" ")[0]
        
        cursor = self.textCursor()
        prefix_length = len(self.completer.completionPrefix())
        cursor.movePosition(QTextCursor.Left, QTextCursor.KeepAnchor, prefix_length)
        cursor.insertText(completion_text)
        self.setTextCursor(cursor)

    def textUnderCursor(self):
        cursor = self.textCursor()
        cursor.select(QTextCursor.WordUnderCursor)
        return cursor.selectedText()

    def focusInEvent(self, event):
        if self.completer:
            self.completer.setWidget(self)
        super().focusInEvent(event)

    def keyPressEvent(self, event):
        if self.completer and self.completer.popup().isVisible():
            if event.key() in (Qt.Key_Enter, Qt.Key_Return, Qt.Key_Escape, Qt.Key_Tab, Qt.Key_Backtab):
                event.ignore()
                return

        super().keyPressEvent(event)

        prefix = self.textUnderCursor()
        if not prefix:
            self.completer.popup().hide()
            return

        if prefix != self.completer.completionPrefix():
            self.completer.setCompletionPrefix(prefix)
            self.completer.popup().setCurrentIndex(self.completer.completionModel().index(0, 0))

        cr = self.cursorRect()
        cr.setWidth(self.completer.popup().sizeHintForColumn(0) + self.completer.popup().verticalScrollBar().sizeHint().width())
        self.completer.complete(cr)


def get_base_path():
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))


class EasyUISyntaxHighlighter(QSyntaxHighlighter):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.highlight_formats = {
            'tag': self._create_format(QColor(30, 144, 255), bold=True),
            'attribute': self._create_format(QColor(144, 238, 144)),
            'string': self._create_format(QColor(255, 165, 0)),
            'keyword': self._create_format(QColor(199, 21, 133)),
            'punctuation': self._create_format(QColor(169, 169, 169))
        }
        
        self.highlight_rules = [
            (r'^\w+(?==)', self.highlight_formats['tag']),
            (r'(?<=[,=])\s*(id|options)(?==)', self.highlight_formats['keyword']),
            (r'(?<==)\s*\w+(?=[=,;])', self.highlight_formats['attribute']),
            (r'"[^"]*"', self.highlight_formats['string']),
            (r'[=,;[\]]', self.highlight_formats['punctuation'])
        ]

    def _create_format(self, color, bold=False):
        text_format = QTextCharFormat()
        text_format.setForeground(color)
        if bold:
            text_format.setFontWeight(QFont.Bold)
        return text_format

    def highlightBlock(self, text):
        for pattern, text_format in self.highlight_rules:
            for match in re.finditer(pattern, text):
                start = match.start()
                length = match.end() - start
                self.setFormat(start, length, text_format)


class InterpreterSelector(QDialog):
    def __init__(self, interpreter_paths, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择解释器")
        self.setGeometry(300, 300, 800, 200)
        
        layout = QVBoxLayout(self)
        
        group_box = QGroupBox("找到以下解释器，请选择一个:")
        group_layout = QVBoxLayout()
        group_box.setLayout(group_layout)
        
        self.interpreter_combo = QComboBox()
        self.interpreter_combo.setMinimumWidth(700)
        self.interpreter_combo.setToolTip("选择要使用的解释器")
        
        for path in interpreter_paths:
            self.interpreter_combo.addItem(path, path)
        
        group_layout.addWidget(self.interpreter_combo)
        
        manual_layout = QHBoxLayout()
        self.manual_check = QRadioButton("手动选择解释器...")
        manual_layout.addWidget(self.manual_check)
        group_layout.addLayout(manual_layout)
        
        layout.addWidget(group_box)
        
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        if interpreter_paths:
            self.interpreter_combo.setCurrentIndex(0)
        else:
            self.manual_check.setChecked(True)
    
    def get_selected_path(self):
        if not self.manual_check.isChecked() and self.interpreter_combo.count() > 0:
            return self.interpreter_combo.currentData()
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择解释器", "", "可执行文件 (*.exe);;Python文件 (*.py);;所有文件 (*)"
        )
        return file_path if file_path else None


class InterpreterThread(QThread):
    error_occurred = pyqtSignal(str)
    output_received = pyqtSignal(str)
    finished = pyqtSignal()
    timeout_occurred = pyqtSignal()
    
    def __init__(self, code, file_path, interpreter_path, timeout=30):
        super().__init__()
        self.code = code
        self.file_path = file_path
        self.interpreter_path = interpreter_path
        self.process = None
        self.timeout = timeout * 1000
        self.timeout_timer = None
    
    def run(self):
        try:
            with open(self.file_path, 'w', encoding='utf-8-sig') as f:
                f.write(self.code)
            
            if not os.path.exists(self.interpreter_path):
                self.error_occurred.emit(f"解释器文件不存在: {self.interpreter_path}")
                self.finished.emit()
                return
            
            self.process = QProcess()
            self.process.setProcessChannelMode(QProcess.SeparateChannels)
            self.process.setReadChannel(QProcess.StandardOutput)
            
            self.process.readyReadStandardOutput.connect(self.handle_output)
            self.process.readyReadStandardError.connect(self.handle_error)
            self.process.finished.connect(self.on_process_finished)
            self.process.errorOccurred.connect(self.on_process_error)
            
            self.timeout_timer = QTimer()
            self.timeout_timer.setSingleShot(True)
            self.timeout_timer.timeout.connect(self.on_timeout)
            self.timeout_timer.start(self.timeout)
            
            if self.interpreter_path.endswith('.exe'):
                self.process.start(self.interpreter_path, [self.file_path])
            else:
                self.process.start(sys.executable, [self.interpreter_path, self.file_path])
            
            if not self.process.waitForStarted(5000):
                self.error_occurred.emit(f"进程启动失败，可能是解释器路径错误或权限不足")
                self.cleanup()
                self.finished.emit()
                return
                
        except Exception as e:
            self.error_occurred.emit(f"线程初始化错误: {str(e)}")
            self.cleanup()
            self.finished.emit()
    
    def handle_output(self):
        if self.timeout_timer and self.timeout_timer.isActive():
            self.timeout_timer.start(self.timeout)
            
        while self.process and self.process.canReadLine():
            try:
                output = self.process.readLine().data().decode('utf-8').rstrip('\n')
            except UnicodeDecodeError:
                output = self.process.readLine().data().decode('gbk', errors='replace').rstrip('\n')
            
            if output:
                self.output_received.emit(f"[输出] {output}")
    
    def handle_error(self):
        while self.process and self.process.canReadLine(QProcess.StandardError):
            try:
                error = self.process.readLine(QProcess.StandardError).data().decode('utf-8').rstrip('\n')
            except UnicodeDecodeError:
                error = self.process.readLine(QProcess.StandardError).data().decode('gbk', errors='replace').rstrip('\n')
            
            if error:
                self.error_occurred.emit(f"[错误] {error}")
    
    def on_process_finished(self, exit_code, exit_status):
        self.cleanup()
        
        if exit_status == QProcess.CrashExit:
            self.error_occurred.emit(f"进程崩溃，可能是代码语法错误或解释器异常")
        elif exit_code != 0:
            self.error_occurred.emit(f"进程异常退出，退出代码: {exit_code}")
        else:
            self.output_received.emit(f"[提示] 进程正常结束，退出代码: {exit_code}")
        
        self.finished.emit()
    
    def on_process_error(self, error):
        error_messages = {
            QProcess.FailedToStart: "进程启动失败 - 可能是解释器不存在或权限不足",
            QProcess.Crashed: "进程已崩溃",
            QProcess.Timedout: "进程超时",
            QProcess.ReadError: "读取错误",
            QProcess.WriteError: "写入错误",
            QProcess.UnknownError: "未知错误"
        }
        
        self.error_occurred.emit(f"[进程错误] {error_messages.get(error, f'发生错误: {error}')}")
        self.cleanup()
        self.finished.emit()
    
    def on_timeout(self):
        self.error_occurred.emit(f"[超时] 代码运行时间超过 {self.timeout/1000} 秒，已自动终止")
        self.stop()
        self.timeout_occurred.emit()
        self.finished.emit()
    
    def stop(self):
        if self.process and self.process.state() == QProcess.Running:
            self.process.terminate()
            if not self.process.waitForFinished(2000):
                self.process.kill()
            self.error_occurred.emit(f"[提示] 进程已手动终止")
        self.cleanup()
    
    def cleanup(self):
        if self.timeout_timer and self.timeout_timer.isActive():
            self.timeout_timer.stop()
            self.timeout_timer = None


class InterpreterSearchThread(QThread):
    progress_updated = pyqtSignal(object)
    search_complete = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.searching = True
        self.found_paths = set()
        self.search_names = [
            "easy_ui_interpreter.exe",
            "easy_ui_interpreter.py"
        ]
    
    def run(self):
        try:
            drives = self.get_available_drives()
            total_drives = len(drives)
            drive_count = 0
            
            self.search_quick_paths()
            
            for drive in drives:
                if not self.searching:
                    break
                    
                self.progress_updated.emit(f"正在扫描驱动器: {drive}（{drive_count+1}/{total_drives}）")
                self.search_directory(drive)
                
                drive_count += 1
                progress = int((drive_count / total_drives) * 100) if total_drives > 0 else 0
                self.progress_updated.emit(progress)
            
            sorted_paths = sorted(list(self.found_paths))
            self.search_complete.emit(sorted_paths)
            
        except Exception as e:
            print(f"搜索解释器时出错: {str(e)}")
            self.search_complete.emit(list(self.found_paths))
    
    def get_available_drives(self):
        drives = []
        seen = set()
        
        if sys.platform.startswith('win'):
            try:
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as key:
                    for i in range(winreg.QueryInfoKey(key)[1]):
                        try:
                            value_name, value_data, _ = winreg.EnumValue(key, i)
                            if value_data and len(value_data) >= 3 and value_data[1] == ':' and value_data[2] == '\\':
                                drive = value_data[:3].upper()
                                if drive not in seen and os.path.exists(drive) and os.access(drive, os.R_OK):
                                    seen.add(drive)
                                    drives.append(drive)
                        except WindowsError:
                            continue
            except Exception:
                for drive_letter in 'ABCDEFGHIJKLMNOPQRSTUVWXYZ':
                    drive = f"{drive_letter}:\\"
                    if os.path.exists(drive) and os.access(drive, os.R_OK):
                        drive_upper = drive.upper()
                        if drive_upper not in seen:
                            seen.add(drive_upper)
                            drives.append(drive_upper)
        else:
            return ["/", os.path.expanduser("~")]
        
        drives.sort()
        return drives
    
    def search_quick_paths(self):
        base_path = get_base_path()
        
        quick_paths = [
            base_path,
            os.path.join(base_path, "interpreters"),
            "D:\\Easy-Windows-UI-Lang",
            os.path.join(os.environ.get("ProgramFiles", ""), "Easy-Windows-UI-Lang"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Easy-Windows-UI-Lang"),
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~\\Downloads")
        ]
        
        for path in os.environ.get("PATH", "").split(os.pathsep):
            if path and path not in quick_paths:
                quick_paths.append(path)
        
        for path in quick_paths:
            if os.path.exists(path) and os.path.isdir(path):
                self.search_directory(path, depth_limit=None)
    
    def search_directory(self, root_dir, depth_limit=None, current_depth=0):
        if depth_limit is not None and current_depth > depth_limit:
            return
            
        try:
            if not os.access(root_dir, os.R_OK):
                return
                
            for name in self.search_names:
                file_path = os.path.join(root_dir, name)
                if os.path.exists(file_path) and os.path.isfile(file_path):
                    self.found_paths.add(file_path)
            
            for item in os.listdir(root_dir):
                if not self.searching:
                    return
                    
                item_path = os.path.join(root_dir, item)
                if os.path.isdir(item_path):
                    if self.should_skip_directory(item_path):
                        continue
                    self.search_directory(item_path, depth_limit, current_depth + 1)
                    
        except Exception as e:
            pass
    
    def should_skip_directory(self, dir_path):
        dir_name = os.path.basename(dir_path).lower()
        full_path = dir_path.lower()
        
        system_blacklist = [
            "windows\\system32", "windows\\syswow64", "windows\\system",
            "$recycle.bin", "system volume information", "windows\\recovery"
        ]
        
        if any(black_dir in full_path for black_dir in system_blacklist):
            return True
        if dir_name in ["node_modules", "venv", "env"]:
            return True
        return False
    
    def stop_search(self):
        self.searching = False


class FileTreeWidget(QTreeWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setHeaderLabel("文件目录")
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)
        self.itemDoubleClicked.connect(self.on_item_double_clicked)
        
        self.init_icons()
        self.current_dir = get_base_path()
        self.refresh_tree()
    
    def init_icons(self):
        self.dir_icon = QIcon()
        self.dir_icon.addPixmap(QPixmap(":/icons/folder.png"), QIcon.Normal, QIcon.Off)
        
        self.python_icon = QIcon()
        self.python_icon.addPixmap(QPixmap(":/icons/python.png"), QIcon.Normal, QIcon.Off)
        
        self.cpp_icon = QIcon()
        self.cpp_icon.addPixmap(QPixmap(":/icons/cpp.png"), QIcon.Normal, QIcon.Off)
        
        self.java_icon = QIcon()
        self.java_icon.addPixmap(QPixmap(":/icons/java.png"), QIcon.Normal, QIcon.Off)
        
        self.eui_icon = QIcon()
        eui_icon_path = os.path.join(get_base_path(), "icon", "eui.ico")
        
        if os.path.exists(eui_icon_path):
            self.eui_icon.addPixmap(QPixmap(eui_icon_path), QIcon.Normal, QIcon.Off)
        else:
            self.eui_icon = None
            self.eui_text = "📝"
            
        self.file_icon = QIcon()
        self.file_icon.addPixmap(QPixmap(":/icons/file.png"), QIcon.Normal, QIcon.Off)
        
        self.dir_text = "📁"
        self.python_text = "🐍"
        self.cpp_text = "++"
        self.java_text = "☕"
        self.file_text = "📄"

    def get_file_icon(self, file_name):
        lower_name = file_name.lower()
        
        if lower_name.endswith('.eui'):
            if self.eui_icon:
                return self.eui_icon
            return self.eui_text
        elif lower_name.endswith('.py'):
            if not self.python_icon.isNull():
                return self.python_icon
            return self.python_text
        elif lower_name.endswith(('.cpp', '.h', '.c', '.hpp')):
            if not self.cpp_icon.isNull():
                return self.cpp_icon
            return self.cpp_text
        elif lower_name.endswith('.java'):
            if not self.java_icon.isNull():
                return self.java_icon
            return self.java_text
        else:
            if not self.file_icon.isNull():
                return self.file_icon
            return self.file_text

    def refresh_tree(self):
        self.clear()
        if not self.current_dir or not os.path.isdir(self.current_dir):
            return
            
        root = QTreeWidgetItem([os.path.basename(self.current_dir)])
        root.setData(0, Qt.UserRole, self.current_dir)
        if not self.dir_icon.isNull():
            root.setIcon(0, self.dir_icon)
        root.setExpanded(True)
        self.addTopLevelItem(root)
        
        self.add_directory_items(root, self.current_dir)
        
        self.parent.status_bar.showMessage(f"显示目录: {self.current_dir}")

    def add_directory_items(self, parent_item, directory):
        try:
            items = os.listdir(directory)
            dirs = []
            files = []
            
            for item in items:
                item_path = os.path.join(directory, item)
                if os.path.isdir(item_path) and not item.startswith('.'):
                    dirs.append(item)
                elif os.path.isfile(item_path):
                    files.append(item)
            
            for dir_name in sorted(dirs):
                dir_path = os.path.join(directory, dir_name)
                dir_item = QTreeWidgetItem([dir_name])
                dir_item.setData(0, Qt.UserRole, dir_path)
                if not self.dir_icon.isNull():
                    dir_item.setIcon(0, self.dir_icon)
                parent_item.addChild(dir_item)
                
                self.add_directory_items(dir_item, dir_path)
                dir_item.setExpanded(False)
            
            for file_name in sorted(files):
                file_path = os.path.join(directory, file_name)
                file_item = QTreeWidgetItem([file_name])
                file_item.setData(0, Qt.UserRole, file_path)
                
                icon = self.get_file_icon(file_name)
                if isinstance(icon, QIcon) and not icon.isNull():
                    file_item.setIcon(0, icon)
                else:
                    file_item.setText(0, f"{icon} {file_name}")
                
                parent_item.addChild(file_item)
                
        except Exception as e:
            pass

    def on_item_double_clicked(self, item, column):
        item_path = item.data(0, Qt.UserRole)
        if not item_path:
            return
            
        if os.path.isdir(item_path):
            if item.childCount() == 0:
                self.add_directory_items(item, item_path)
            item.setExpanded(not item.isExpanded())
        elif os.path.isfile(item_path):
            if item_path.lower().endswith(('.eui', '.txt', '.py', '.cpp', '.h', '.java')):
                self.parent.open_file_from_path(item_path)
            else:
                self.parent.status_bar.showMessage(f"不支持的文件类型: {os.path.basename(item_path)}")

    def show_context_menu(self, position):
        item = self.itemAt(position)
        if not item:
            self.show_empty_context_menu(position)
            return
            
        item_path = item.data(0, Qt.UserRole)
        if not item_path:
            return
            
        menu = QContextMenu()
        
        open_action = menu.addAction("打开")
        open_action.triggered.connect(lambda: self.open_item(item))
        
        if os.path.isdir(item_path):
            menu.addSeparator()
            
            new_file_action = menu.addAction("新建文件")
            new_file_action.triggered.connect(lambda: self.new_file(item))
            
            new_folder_action = menu.addAction("新建文件夹")
            new_folder_action.triggered.connect(lambda: self.new_folder(item))
            
            set_as_root_action = menu.addAction("设为根目录")
            set_as_root_action.triggered.connect(lambda: self.set_as_root(item))
            
            add_file_action = menu.addAction("添加文件到此处")
            add_file_action.triggered.connect(lambda: self.add_file_to_directory(item))
        else:
            menu.addSeparator()
            
            rename_action = menu.addAction("重命名")
            rename_action.triggered.connect(lambda: self.rename_item(item))
            
            delete_action = menu.addAction("删除")
            delete_action.triggered.connect(lambda: self.delete_item(item))
            
            copy_action = menu.addAction("复制")
            copy_action.triggered.connect(lambda: self.copy_item(item))
            
            cut_action = menu.addAction("剪切")
            cut_action.triggered.connect(lambda: self.cut_item(item))
        
        menu.exec_(self.viewport().mapToGlobal(position))
    
    def show_empty_context_menu(self, position):
        menu = QContextMenu()
        
        new_file_action = menu.addAction("新建文件")
        new_file_action.triggered.connect(lambda: self.new_file_in_current_dir())
        
        new_folder_action = menu.addAction("新建文件夹")
        new_folder_action.triggered.connect(lambda: self.new_folder_in_current_dir())
        
        menu.addSeparator()
        
        refresh_action = menu.addAction("刷新")
        refresh_action.triggered.connect(self.refresh_tree)
        
        menu.exec_(self.viewport().mapToGlobal(position))
    
    def new_file_in_current_dir(self):
        self.new_file(None)
    
    def new_folder_in_current_dir(self):
        self.new_folder(None)
    
    def open_item(self, item):
        item_path = item.data(0, Qt.UserRole)
        if os.path.isdir(item_path):
            if item.childCount() == 0:
                self.add_directory_items(item, item_path)
            item.setExpanded(True)
        else:
            self.parent.open_file_from_path(item_path)

    def set_as_root(self, item):
        item_path = item.data(0, Qt.UserRole)
        if os.path.isdir(item_path):
            self.current_dir = item_path
            self.refresh_tree()

    def new_folder(self, item):
        if item:
            item_path = item.data(0, Qt.UserRole)
        else:
            item_path = self.current_dir
            
        if not os.path.isdir(item_path):
            return
            
        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "文件夹名称:")
        if ok and folder_name:
            new_folder_path = os.path.join(item_path, folder_name)
            try:
                os.makedirs(new_folder_path)
                self.refresh_tree()
                self.parent.status_bar.showMessage(f"已创建文件夹: {folder_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建文件夹: {str(e)}")

    def new_file(self, item):
        if item:
            dir_path = item.data(0, Qt.UserRole)
        else:
            dir_path = self.current_dir
            
        if not os.path.isdir(dir_path):
            return
            
        file_name, ok = QInputDialog.getText(self, "新建文件", "文件名称(例如: myfile.eui):")
        if ok and file_name:
            file_path = os.path.join(dir_path, file_name)
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    pass
                    
                self.refresh_tree()
                self.parent.status_bar.showMessage(f"已创建文件: {file_name}")
                self.parent.open_file_from_path(file_path)
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法创建文件: {str(e)}")

    def add_file_to_directory(self, item):
        if not item:
            return
            
        dir_path = item.data(0, Qt.UserRole)
        if not os.path.isdir(dir_path):
            return
            
        file_paths, _ = QFileDialog.getOpenFileNames(
            self, "选择要添加的文件", "", "所有文件 (*)"
        )
        
        if file_paths:
            success_count = 0
            fail_count = 0
            
            for file_path in file_paths:
                try:
                    dest_path = os.path.join(dir_path, os.path.basename(file_path))
                    
                    if os.path.exists(dest_path):
                        reply = QMessageBox.question(
                            self, "文件已存在",
                            f"{os.path.basename(file_path)} 已存在，是否覆盖？",
                            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                        )
                        if reply != QMessageBox.Yes:
                            fail_count += 1
                            continue
                    
                    shutil.copy2(file_path, dest_path)
                    success_count += 1
                except Exception as e:
                    print(f"复制文件失败: {str(e)}")
                    fail_count += 1
            
            self.refresh_tree()
            self.parent.status_bar.showMessage(
                f"添加完成: 成功 {success_count} 个，失败 {fail_count} 个"
            )

    def rename_item(self, item):
        item_path = item.data(0, Qt.UserRole)
        old_name = os.path.basename(item_path)
        new_name, ok = QInputDialog.getText(self, "重命名", "新名称:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            parent_dir = os.path.dirname(item_path)
            new_path = os.path.join(parent_dir, new_name)
            
            try:
                os.rename(item_path, new_path)
                self.refresh_tree()
                self.parent.status_bar.showMessage(f"已重命名为: {new_name}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法重命名: {str(e)}")

    def delete_item(self, item):
        item_path = item.data(0, Qt.UserRole)
        if not item_path:
            return
            
        reply = QMessageBox.question(
            self, "确认删除", 
            f"确定要删除 {os.path.basename(item_path)} 吗？\n此操作不可恢复。",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                if os.path.isfile(item_path):
                    os.remove(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                
                self.refresh_tree()
                self.parent.status_bar.showMessage(f"已删除: {os.path.basename(item_path)}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法删除: {str(e)}")

    def copy_item(self, item):
        item_path = item.data(0, Qt.UserRole)
        if not item_path:
            return
            
        self.parent.copied_path = item_path
        self.parent.is_cut = False
        self.parent.status_bar.showMessage(f"已复制: {os.path.basename(item_path)}")

    def cut_item(self, item):
        item_path = item.data(0, Qt.UserRole)
        if not item_path:
            return
            
        self.parent.copied_path = item_path
        self.parent.is_cut = True
        self.parent.status_bar.showMessage(f"已剪切: {os.path.basename(item_path)}")

    def change_directory(self, new_dir):
        if os.path.isdir(new_dir):
            self.current_dir = new_dir
            self.refresh_tree()
            return True
        return False


class EasyUIEditor(QMainWindow):
    def __init__(self):
        super().__init__()
        self.current_file = None
        self.temp_file = os.path.join(tempfile.gettempdir(), "temp_ewui_code.eui")
        self.status_bar = None
        self.interpreter_path = None
        self.run_timeout = 30
        self.search_thread = None
        self.search_in_progress = False
        self.copied_path = None
        self.is_cut = False
        
        self.cmd_line_file = sys.argv[1] if len(sys.argv) > 1 and sys.argv[1].lower().endswith('.eui') else None
        
        self.init_completion_words()
        self.init_status_bar()
        self.init_ui()
        self.check_file_association()
        
        self.scan_interpreters(quick_scan=True)
        self.full_scan_interpreters_in_background()
        
        if self.cmd_line_file:
            self.open_file_from_path(self.cmd_line_file)
    
    def init_completion_words(self):
        self.completion_words = [
            ("window", "标签 - 窗口"),
            ("label", "标签 - 文字显示"),
            ("entry", "标签 - 输入框"),
            ("combo", "标签 - 选择框"),
            ("checkbox", "标签 - 多选框"),
            ("button", "标签 - 按钮"),
            ("audio", "标签 - 音频组件"),
            ("slider", "标签 - 滑块控件"),
            ("textarea", "标签 - 文本区域"),
            ("separator", "标签 - 分隔线"),
            ("progress", "标签 - 进度条"),
            ("calendar", "标签 - 日历控件"),
            ("radiogroup", "标签 - 单选按钮组"),
            ("groupbox", "标签 - 分组框"),
            ("timer", "标签 - 定时器"),
            ("title", "属性 - 窗口标题"),
            ("width", "属性 - 宽度"),
            ("height", "属性 - 高度"),
            ("icon", "属性 - 窗口图标路径"),
            ("text", "属性 - 显示文本"),
            ("id", "属性 - 组件ID（必选）"),
            ("hint", "属性 - 输入框提示文本"),
            ("readonly", "属性 - 输入框只读（true/false）"),
            ("label", "属性 - 选择框/多选框标题"),
            ("options", "属性 - 选项列表（如[\"选项1\",\"选项2\"]）"),
            ("click", "属性 - 按钮触发动作"),
            ("url", "属性 - 网络音频地址"),
            ("os", "属性 - 本地音频文件路径"),
            ("min", "属性 - 最小值"),
            ("max", "属性 - 最大值"),
            ("value", "属性 - 当前值"),
            ("rows", "属性 - 文本区域行数"),
            ("interval", "属性 - 定时器间隔(毫秒)"),
            ("action", "属性 - 定时器动作"),
            ("true", "值 - 布尔值（只读/启用）"),
            ("false", "值 - 布尔值（可写/禁用）"),
            ("显示=", "动作 - 显示组件内容（如显示=组件ID）"),
            ("play_audio=", "动作 - 播放音频（如play_audio=音频ID）"),
            ("pause_audio=", "动作 - 暂停音频（如pause_audio=音频ID）"),
            ("stop_audio=", "动作 - 停止音频（如stop_audio=音频ID）"),
            ("start_timer=", "动作 - 启动定时器（如start_timer=定时器ID）"),
            ("stop_timer=", "动作 - 停止定时器（如stop_timer=定时器ID）"),
            ("set_progress=", "动作 - 设置进度条（如set_progress=进度条ID,value=50）"),
            (";", "符号 - 语句结束符"),
            (",", "符号 - 属性分隔符"),
            ("=[", "符号 - 选项列表开始（如options=[）"),
            ("]", "符号 - 选项列表结束")
        ]
    
    def init_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("初始化中...")
    
    def check_file_association(self):
        if not FileAssociation.is_associated():
            reply = QMessageBox.question(
                self, "文件关联",
                "尚未设置.eui文件关联，是否将.eui文件默认用此程序打开并设置图标？\n(需要管理员权限)",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                if FileAssociation.set_association():
                    QMessageBox.information(self, "成功", "文件关联设置成功！\n可能需要重启资源管理器才能看到图标变化。")
                    self.status_bar.showMessage("已成功设置.eui文件关联")
        else:
            self.status_bar.showMessage(".eui文件已关联到此程序")
    
    def init_ui(self):
        self.setWindowTitle("Easy Windows UI Editor - [未命名]")
        self.setGeometry(100, 100, 1400, 800)
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
                color: #d4d4d4;
            }
            QTextEdit, CompleterTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QLabel {
                color: #d4d4d4;
            }
            QPushButton {
                background-color: #3c3c3c;
                color: #d4d4d4;
                border: 1px solid #5e5e5e;
                padding: 5px 10px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #4a4a4a;
            }
            QPushButton:pressed {
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #d4d4d4;
                padding: 8px 16px;
                border: 1px solid #5e5e5e;
                border-bottom: none;
            }
            QTabBar::tab:selected {
                background-color: #1e1e1e;
                border-top: 2px solid #007acc;
            }
            QListWidget, QTreeWidget {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #3c3c3c;
            }
            QTreeWidget::item {
                border-bottom: 1px solid #3c3c3c;
            }
            QTreeWidget::item:selected {
                background-color: #3c3c3c;
            }
            QStatusBar {
                background-color: #1e1e1e;
                color: #858585;
                border-top: 1px solid #3c3c3c;
            }
            QMenuBar {
                background-color: #1e1e1e;
                color: #d4d4d4;
                border-bottom: 1px solid #3c3c3c;
            }
            QToolBar {
                background-color: #1e1e1e;
                border-bottom: 1px solid #3c3c3c;
                spacing: 5px;
            }
            QDockWidget {
                color: #d4d4d4;
                titlebar-close-icon: url();
                titlebar-normal-icon: url();
            }
            QDockWidget::title {
                background-color: #2d2d2d;
                padding: 5px;
                border-bottom: 1px solid #3c3c3c;
            }
            QCompleter QListView {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #5e5e5e;
                padding: 2px;
            }
            QCompleter QListView::item:selected {
                background-color: #007acc;
                color: white;
            }
            QMenu {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #5e5e5e;
            }
            QMenu::item:selected {
                background-color: #3c3c3c;
            }
            QComboBox {
                background-color: #2d2d2d;
                color: #d4d4d4;
                border: 1px solid #5e5e5e;
                padding: 3px;
                min-width: 500px;
            }
            QComboBox::drop-down {
                border-left: 1px solid #5e5e5e;
            }
            QComboBox::down-arrow {
                image: url(:/icons/arrow-down.png);
                width: 12px;
                height: 12px;
            }
        """)
        
        self.create_menu_bar()
        self.create_tool_bar()
        
        main_splitter = QSplitter(Qt.Horizontal)
        
        self.file_tree = FileTreeWidget(self)
        self.file_tree.setMaximumWidth(300)
        main_splitter.addWidget(self.file_tree)
        
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        
        interpreter_layout = QHBoxLayout()
        interpreter_layout.addWidget(QLabel("当前解释器:"))
        
        self.interpreter_combo = QComboBox()
        self.interpreter_combo.setToolTip("选择要使用的解释器")
        self.interpreter_combo.currentIndexChanged.connect(self.on_interpreter_changed)
        
        interpreter_layout.addWidget(self.interpreter_combo)
        interpreter_layout.addStretch()
        
        refresh_interpreter_btn = QPushButton("刷新解释器列表")
        refresh_interpreter_btn.setToolTip("重新扫描可用的解释器")
        refresh_interpreter_btn.clicked.connect(lambda: self.scan_interpreters(quick_scan=True))
        interpreter_layout.addWidget(refresh_interpreter_btn)
        
        right_layout.addLayout(interpreter_layout)
        
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)
        self.add_new_tab()
        
        right_layout.addWidget(self.tab_widget)
        
        self.output_panel = QTextEdit()
        self.output_panel.setReadOnly(True)
        self.output_panel.setMaximumHeight(150)
        self.output_panel.setAcceptRichText(True)
        self.output_panel.setHtml('<span style="color:#888888;">[提示] 输出面板将显示代码运行日志和报错信息（按F5运行代码）</span>')
        right_layout.addWidget(self.output_panel)
        
        main_splitter.addWidget(right_container)
        main_splitter.setSizes([250, 1150])
        
        self.setCentralWidget(main_splitter)
        
        self.add_help_dock()
    
    def on_interpreter_changed(self, index):
        if index >= 0 and self.interpreter_combo.count() > 0:
            self.interpreter_path = self.interpreter_combo.currentData()
            self.status_bar.showMessage(f"已选择解释器: {os.path.basename(self.interpreter_path)}")
    
    def update_interpreter_combo(self, interpreter_paths):
        current_path = self.interpreter_path
        
        self.interpreter_combo.clear()
        
        for path in interpreter_paths:
            self.interpreter_combo.addItem(path, path)
        
        if current_path and os.path.exists(current_path):
            for i in range(self.interpreter_combo.count()):
                if self.interpreter_combo.itemData(i) == current_path:
                    self.interpreter_combo.setCurrentIndex(i)
                    return
        
        if self.interpreter_combo.count() > 0:
            self.interpreter_combo.setCurrentIndex(0)
            self.interpreter_path = self.interpreter_combo.currentData()
    
    def create_menu_bar(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("文件(&F)")
        
        new_action = QAction("新建(&N)", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.add_new_tab)
        file_menu.addAction(new_action)
        
        open_action = QAction("打开(&O)", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_file)
        file_menu.addAction(open_action)
        
        change_dir_action = QAction("更改目录(&C)", self)
        change_dir_action.triggered.connect(self.change_directory)
        file_menu.addAction(change_dir_action)
        
        save_action = QAction("保存(&S)", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_file)
        file_menu.addAction(save_action)
        
        save_as_action = QAction("另存为(&A)", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_file_as)
        file_menu.addAction(save_as_action)
        
        paste_action = QAction("粘贴(&P)", self)
        paste_action.setShortcut("Ctrl+V")
        paste_action.triggered.connect(self.paste_file)
        file_menu.addAction(paste_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("退出(&X)", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        run_menu = menubar.addMenu("运行(&R)")
        
        run_action = QAction("运行代码(&R)", self)
        run_action.setShortcut("F5")
        run_action.triggered.connect(self.run_code)
        run_menu.addAction(run_action)
        
        stop_action = QAction("停止运行(&S)", self)
        stop_action.setShortcut("Ctrl+F5")
        stop_action.triggered.connect(self.stop_running)
        run_menu.addAction(stop_action)
        
        timeout_menu = run_menu.addMenu("运行超时设置")
        self.timeout_actions = {}
        for timeout in [10, 30, 60, 120]:
            act = QAction(f"{timeout}秒", self, checkable=True)
            act.setData(timeout)
            if timeout == self.run_timeout:
                act.setChecked(True)
            act.triggered.connect(self.set_timeout)
            self.timeout_actions[timeout] = act
            timeout_menu.addAction(act)
        
        tool_menu = menubar.addMenu("工具(&T)")
        
        assoc_action = QAction("设置.eui文件关联", self)
        assoc_action.triggered.connect(self.set_file_association)
        tool_menu.addAction(assoc_action)
        
        unassoc_action = QAction("取消.eui文件关联", self)
        unassoc_action.triggered.connect(self.remove_file_association)
        tool_menu.addAction(unassoc_action)
        
        tool_menu.addSeparator()
        
        interpreter_action = QAction("选择解释器(&I)", self)
        interpreter_action.triggered.connect(self.choose_interpreter)
        tool_menu.addAction(interpreter_action)
        
        scan_action = QAction("快速扫描解释器(&S)", self)
        scan_action.triggered.connect(lambda: self.scan_interpreters(quick_scan=True))
        tool_menu.addAction(scan_action)
        
        full_scan_action = QAction("全电脑扫描解释器(&F)", self)
        full_scan_action.triggered.connect(self.full_scan_interpreters_in_background)
        tool_menu.addAction(full_scan_action)
        
        help_menu = menubar.addMenu("帮助(&H)")
        
        example_action = QAction("示例代码(&E)", self)
        example_action.triggered.connect(self.load_example_code)
        help_menu.addAction(example_action)
        
        about_action = QAction("关于(&A)", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def set_file_association(self):
        if FileAssociation.is_associated():
            reply = QMessageBox.question(
                self, "已关联",
                ".eui文件已关联到此程序，是否重新设置？",
                QMessageBox.Yes | QMessageBox.No, QMessageBox.No
            )
            if reply != QMessageBox.Yes:
                return
                
        if FileAssociation.set_association():
            QMessageBox.information(self, "成功", "文件关联设置成功！\n可能需要重启资源管理器才能看到图标变化。")
    
    def remove_file_association(self):
        if not FileAssociation.is_associated():
            QMessageBox.information(self, "未关联", ".eui文件尚未关联到此程序")
            return
            
        reply = QMessageBox.question(
            self, "确认取消",
            "确定要取消.eui文件与本程序的关联吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            if FileAssociation.remove_association():
                QMessageBox.information(self, "成功", "已取消.eui文件关联")
    
    def paste_file(self):
        if not self.copied_path or not os.path.exists(self.copied_path):
            self.status_bar.showMessage("没有可粘贴的内容")
            return
            
        target_dir = self.file_tree.current_dir
        
        try:
            item_name = os.path.basename(self.copied_path)
            target_path = os.path.join(target_dir, item_name)
            
            if os.path.exists(target_path):
                reply = QMessageBox.question(
                    self, "文件已存在",
                    f"{item_name} 已存在，是否覆盖？",
                    QMessageBox.Yes | QMessageBox.No, QMessageBox.No
                )
                if reply != QMessageBox.Yes:
                    self.status_bar.showMessage("粘贴已取消")
                    return
            
            if self.is_cut:
                if os.path.isdir(self.copied_path):
                    shutil.move(self.copied_path, target_path)
                else:
                    os.rename(self.copied_path, target_path)
                self.status_bar.showMessage(f"已移动: {item_name}")
                self.copied_path = None
                self.is_cut = False
            else:
                if os.path.isdir(self.copied_path):
                    shutil.copytree(self.copied_path, target_path)
                else:
                    shutil.copy2(self.copied_path, target_path)
                self.status_bar.showMessage(f"已复制: {item_name}")
            
            self.file_tree.refresh_tree()
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"粘贴失败: {str(e)}")
    
    def set_timeout(self):
        sender = self.sender()
        if sender:
            self.run_timeout = sender.data()
            for act in self.timeout_actions.values():
                act.setChecked(act.data() == self.run_timeout)
            self.status_bar.showMessage(f"已设置运行超时时间为 {self.run_timeout} 秒")
    
    def stop_running(self):
        if hasattr(self, 'interpreter_thread') and self.interpreter_thread.isRunning():
            self.interpreter_thread.stop()
            self.run_finished()
        else:
            self.status_bar.showMessage("没有正在运行的进程")
    
    def create_tool_bar(self):
        toolbar = QToolBar("主工具栏")
        self.addToolBar(toolbar)
        
        new_btn = QPushButton("新建")
        new_btn.setToolTip("新建文件 (Ctrl+N)")
        new_btn.clicked.connect(self.add_new_tab)
        toolbar.addWidget(new_btn)
        
        open_btn = QPushButton("打开")
        open_btn.setToolTip("打开文件 (Ctrl+O)")
        open_btn.clicked.connect(self.open_file)
        toolbar.addWidget(open_btn)
        
        change_dir_btn = QPushButton("更改目录")
        change_dir_btn.setToolTip("更改文件树显示的目录")
        change_dir_btn.clicked.connect(self.change_directory)
        toolbar.addWidget(change_dir_btn)
        
        save_btn = QPushButton("保存")
        save_btn.setToolTip("保存文件 (Ctrl+S)")
        save_btn.clicked.connect(self.save_file)
        toolbar.addWidget(save_btn)
        
        toolbar.addSeparator()
        
        run_btn = QPushButton("运行")
        run_btn.setToolTip("运行代码 (F5)")
        run_btn.clicked.connect(self.run_code)
        run_btn.setStyleSheet("color: green; font-weight: bold;")
        toolbar.addWidget(run_btn)
        
        stop_btn = QPushButton("停止")
        stop_btn.setToolTip("停止运行 (Ctrl+F5)")
        stop_btn.clicked.connect(self.stop_running)
        stop_btn.setStyleSheet("color: red; font-weight: bold;")
        toolbar.addWidget(stop_btn)
        
        interpreter_btn = QPushButton("解释器")
        interpreter_btn.setToolTip("选择解释器")
        interpreter_btn.clicked.connect(self.choose_interpreter)
        toolbar.addWidget(interpreter_btn)
        
        full_scan_btn = QPushButton("全扫描")
        full_scan_btn.setToolTip("全电脑后台搜索解释器")
        full_scan_btn.clicked.connect(self.full_scan_interpreters_in_background)
        full_scan_btn.setStyleSheet("color: #00ccff; font-weight: bold;")
        toolbar.addWidget(full_scan_btn)
        
        force_scan_btn = QPushButton("强制全扫")
        force_scan_btn.setToolTip("无限制扫描所有驱动器（确保找到全部解释器）")
        force_scan_btn.setStyleSheet("color: orange; font-weight: bold;")
        force_scan_btn.clicked.connect(self.force_full_scan)
        toolbar.addWidget(force_scan_btn)
        
        clear_btn = QPushButton("清空")
        clear_btn.setToolTip("清空编辑区")
        clear_btn.clicked.connect(self.clear_current_tab)
        toolbar.addWidget(clear_btn)
    
    def add_help_dock(self):
        dock = QDockWidget("语法帮助", self)
        dock.setAllowedAreas(Qt.RightDockWidgetArea)
        
        help_content = QTextEdit()
        help_content.setReadOnly(True)
        help_content.setHtml("""
        <h3>Easy Windows UI 语法参考 (类HTML格式)</h3>
        <p>语法格式: <strong>标签名=属性1,属性2,...;</strong></p>
        <p>每条语句以分号(;)结尾，属性之间用逗号(,)分隔</p>
        
        <table border="1" cellpadding="5" style="border-collapse:collapse; margin:10px 0;">
            <tr style="background-color:#2d2d2d;">
                <th>组件类型</th>
                <th>标签名</th>
                <th>必选属性</th>
                <th>可选属性</th>
                <th>示例</th>
            </tr>
            <tr>
                <td>窗口</td>
                <td>window</td>
                <td>title="窗口标题", width=数值, height=数值</td>
                <td>icon="图标文件路径"</td>
                <td>window=title="用户信息页",width=500,height=400,icon="icon.png";</td>
            </tr>
            <tr>
                <td>文字显示</td>
                <td>label</td>
                <td>text="显示内容", id=组件ID</td>
                <td>-</td>
                <td>label=text="用户名",id=name_label;</td>
            </tr>
            <tr>
                <td>输入框</td>
                <td>entry</td>
                <td>hint="提示文本", id=组件ID</td>
                <td>readonly=true/false, type=number/text</td>
                <td>entry=hint="请输入姓名",id=name_input,readonly=false;</td>
            </tr>
            <tr>
                <td>选择框</td>
                <td>combo</td>
                <td>label="选择标题", id=组件ID, options=[选项1,选项2]</td>
                <td>-</td>
                <td>combo=label="性别",id=gender_combo,options=["男","女","其他"];</td>
            </tr>
            <tr>
                <td>多选框</td>
                <td>checkbox</td>
                <td>label="多选标题", id=组件ID, options=[选项1,选项2]</td>
                <td>-</td>
                <td>checkbox=label="兴趣爱好",id=hobby_check,options=["读书","运动","编程"];</td>
            </tr>
            <tr>
                <td>按钮</td>
                <td>button</td>
                <td>text="按钮文本", id=组件ID, click="触发动作"</td>
                <td>-</td>
                <td>button=text="提交",id=submit_btn,click="显示=name_input";</td>
            </tr>
            <tr>
                <td>音频（网络）</td>
                <td>audio</td>
                <td>url="音乐网址", id=音频ID</td>
                <td>-</td>
                <td>audio=url="https://xxx.mp3",id=net_audio;</td>
            </tr>
            <tr>
                <td>音频（本地）</td>
                <td>audio</td>
                <td>os="本地文件路径", id=音频ID</td>
                <td>-</td>
                <td>audio=os="music.mp3",id=local_audio;</td>
            </tr>
            <tr>
                <td>滑块</td>
                <td>slider</td>
                <td>label="标题", id=ID, min=值, max=值, value=值</td>
                <td>-</td>
                <td>slider=label="音量",id=vol_slider,min=0,max=100,value=50;</td>
            </tr>
            <tr>
                <td>文本区域</td>
                <td>textarea</td>
                <td>label="标题", id=ID, rows=行数</td>
                <td>readonly=true/false</td>
                <td>textarea=label="备注",id=note_area,rows=5,readonly=false;</td>
            </tr>
            <tr>
                <td>分隔线</td>
                <td>separator</td>
                <td>id=ID</td>
                <td>text="分隔文本"</td>
                <td>separator=text="操作区",id=sep1;</td>
            </tr>
            <tr>
                <td>进度条</td>
                <td>progress</td>
                <td>label="标题", id=ID, min=值, max=值, value=值</td>
                <td>-</td>
                <td>progress=label="完成度",id=prog_bar,min=0,max=100,value=30;</td>
            </tr>
            <tr>
                <td>日历</td>
                <td>calendar</td>
                <td>label="标题", id=ID</td>
                <td>-</td>
                <td>calendar=label="选择日期",id=cal;</td>
            </tr>
            <tr>
                <td>单选按钮组</td>
                <td>radiogroup</td>
                <td>label="标题", id=ID, options=[选项1,...]</td>
                <td>-</td>
                <td>radiogroup=label="学历",id=edu_radio,options=["本科","硕士","博士"];</td>
            </tr>
            <tr>
                <td>分组框</td>
                <td>groupbox</td>
                <td>title="标题", id=ID</td>
                <td>-</td>
                <td>groupbox=title="用户信息",id=user_group;</td>
            </tr>
            <tr>
                <td>定时器</td>
                <td>timer</td>
                <td>id=ID, interval=毫秒, action="动作"</td>
                <td>-</td>
                <td>timer=id=timer1,interval=1000,action="update_progress=prog_bar,value=+1";</td>
            </tr>
        </table>
        
        <h4>按钮动作说明:</h4>
        <ul>
            <li>显示组件内容: click="显示=组件ID"（支持输入框、选择框、多选框等）</li>
            <li>播放音频: click="play_audio=音频ID"</li>
            <li>暂停音频: click="pause_audio=音频ID"</li>
            <li>停止音频: click="stop_audio=音频ID"</li>
            <li>启动定时器: click="start_timer=定时器ID"</li>
            <li>停止定时器: click="stop_timer=定时器ID"</li>
            <li>设置进度条: click="set_progress=进度条ID,value=数值"</li>
        </ul>
        """)
        
        dock.setWidget(help_content)
        self.addDockWidget(Qt.RightDockWidgetArea, dock)
    
    def scan_interpreters(self, quick_scan=False):
        self.status_bar.showMessage("正在快速扫描解释器...")
        
        interpreter_paths = []
        base_path = get_base_path()
        target_names = {"easy_ui_interpreter.exe", "easy_ui_interpreter.py"}
        
        search_paths = [
            base_path,
            os.path.join(base_path, "interpreters"),
            os.path.expanduser("~\\Desktop"),
            os.path.expanduser("~\\Documents"),
            os.path.expanduser("~\\Downloads"),
            "D:\\Easy-Windows-UI-Lang",
            os.path.join(os.environ.get("ProgramFiles", ""), "Easy-Windows-UI-Lang"),
            os.path.join(os.environ.get("ProgramFiles(x86)", ""), "Easy-Windows-UI-Lang")
        ]
        
        for path in os.environ.get("PATH", "").split(os.pathsep):
            if path and path not in search_paths:
                search_paths.append(path)
        
        for path in search_paths:
            if not os.path.exists(path) or not os.path.isdir(path):
                continue
            for root, dirs, files in os.walk(path):
                for file in files:
                    if file.lower() in target_names:
                        full_path = os.path.join(root, file)
                        if full_path not in interpreter_paths:
                            interpreter_paths.append(full_path)
        
        interpreter_paths = sorted(list(set(interpreter_paths)))
        
        self.update_interpreter_combo(interpreter_paths)
        
        if interpreter_paths:
            self.status_bar.showMessage(f"快速扫描找到 {len(interpreter_paths)} 个解释器")
            return interpreter_paths
        else:
            self.status_bar.showMessage("快速扫描未找到解释器，建议进行全电脑扫描")
            return []
    
    def full_scan_interpreters_in_background(self):
        if self.search_in_progress and self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop_search()
            self.search_thread.wait()
            self.search_in_progress = False
            self.status_bar.showMessage("全电脑搜索已取消")
            return
        
        self.search_thread = InterpreterSearchThread()
        self.search_in_progress = True
        
        self.search_thread.progress_updated.connect(self.update_search_progress)
        self.search_thread.search_complete.connect(self.on_search_complete)
        
        self.search_thread.start()
        self.status_bar.showMessage("全电脑搜索已在后台启动，不影响正常操作...")
    
    def update_search_progress(self, progress):
        if self.search_in_progress:
            if isinstance(progress, str):
                self.status_bar.showMessage(progress)
            else:
                self.status_bar.showMessage(f"后台搜索中... 整体进度: {progress}%")
    
    def on_search_complete(self, interpreter_paths):
        self.search_in_progress = False
        
        self.update_interpreter_combo(interpreter_paths)
        
        if interpreter_paths:
            count = len(interpreter_paths)
            self.status_bar.showMessage(f"后台搜索完成，找到 {count} 个解释器")
        else:
            self.status_bar.showMessage("后台搜索完成，未找到任何解释器，请手动选择")
    
    def choose_interpreter(self):
        interpreters = []
        if self.search_thread and hasattr(self.search_thread, 'found_paths'):
            interpreters = list(self.search_thread.found_paths)
        
        if not interpreters:
            interpreters = self.scan_interpreters(quick_scan=True)
        
        dialog = InterpreterSelector(interpreters, self)
        
        if dialog.exec_():
            selected_path = dialog.get_selected_path()
            if selected_path and os.path.exists(selected_path):
                file_name = os.path.basename(selected_path)
                if file_name.lower() in ["easy_ui_interpreter.exe", "easy_ui_interpreter.py"]:
                    self.interpreter_path = selected_path
                    for i in range(self.interpreter_combo.count()):
                        if self.interpreter_combo.itemData(i) == selected_path:
                            self.interpreter_combo.setCurrentIndex(i)
                            return
                    self.interpreter_combo.addItem(selected_path, selected_path)
                    self.interpreter_combo.setCurrentIndex(self.interpreter_combo.count() - 1)
                    self.status_bar.showMessage(f"已选择解释器: {os.path.basename(selected_path)}")
                else:
                    QMessageBox.warning(self, "警告", "请选择easy_ui_interpreter.exe或easy_ui_interpreter.py文件")
            else:
                QMessageBox.warning(self, "警告", "无效的解释器路径")
    
    def force_full_scan(self):
        reply = QMessageBox.question(
            self, "强制全扫", "此操作将扫描所有驱动器的所有目录，可能耗时5-10分钟，是否继续？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return
        
        if self.search_in_progress and self.search_thread:
            self.search_thread.stop_search()
            self.search_thread.wait()
        
        self.search_thread = InterpreterSearchThread()
        self.search_in_progress = True
        
        def skip_none(dir_path):
            system_blacklist = ["windows\\system32", "windows\\syswow64", "$recycle.bin"]
            return any(black in dir_path.lower() for black in system_blacklist)
        self.search_thread.should_skip_directory = skip_none
        
        self.search_thread.progress_updated.connect(self.update_search_progress)
        self.search_thread.search_complete.connect(self.on_search_complete)
        self.search_thread.start()
        self.status_bar.showMessage("强制全扫已启动，请勿关闭程序...")
    
    def change_directory(self):
        new_dir = QFileDialog.getExistingDirectory(
            self, "选择目录", self.file_tree.current_dir
        )
        if new_dir:
            self.file_tree.change_directory(new_dir)
    
    def add_new_tab(self):
        editor = CompleterTextEdit()
        editor.setFont(QFont("Consolas", 12))
        editor.setAcceptRichText(False)
        
        self.highlighter = EasyUISyntaxHighlighter(editor.document())
        self.setup_completer(editor)
        
        index = self.tab_widget.addTab(editor, "未命名")
        self.tab_widget.setCurrentIndex(index)
        
        if self.tab_widget.count() == 1:
            self.load_example_code()
    
    def setup_completer(self, editor):
        completion_texts = [word[0] for word in self.completion_words]
        display_texts = [f"{word[0]} ({word[1]})" for word in self.completion_words]
        
        completer_model = QStringListModel()
        completer_model.setStringList(display_texts)
        
        completer = QCompleter()
        completer.setModel(completer_model)
        completer.setCompletionMode(QCompleter.PopupCompletion)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setCompletionPrefix("")
        completer.setMaxVisibleItems(10)
        
        editor.setCompleter(completer)
    
    def close_tab(self, index):
        if self.tab_widget.count() > 1:
            self.tab_widget.removeTab(index)
        else:
            self.tab_widget.widget(index).clear()
            self.tab_widget.setTabText(index, "未命名")
            self.current_file = None
            self.setWindowTitle("Easy Windows UI Editor - [未命名]")
    
    def get_current_editor(self):
        return self.tab_widget.currentWidget()
    
    def run_code(self):
        if not self.interpreter_path or not os.path.exists(self.interpreter_path):
            QMessageBox.warning(self, "解释器未找到", "请先选择有效的解释器")
            self.choose_interpreter()
            return
        
        file_name = os.path.basename(self.interpreter_path)
        if file_name.lower() not in ["easy_ui_interpreter.exe", "easy_ui_interpreter.py"]:
            QMessageBox.warning(self, "无效解释器", "请选择easy_ui_interpreter.exe或easy_ui_interpreter.py作为解释器")
            self.choose_interpreter()
            return
            
        editor = self.get_current_editor()
        code = editor.toPlainText()
        
        if not code.strip():
            QMessageBox.warning(self, "警告", "代码不能为空！")
            return
        
        if hasattr(self, 'interpreter_thread') and self.interpreter_thread.isRunning():
            self.show_error("已有进程在运行，请先等待其结束")
            return
        
        self.output_panel.clear()
        self.status_bar.showMessage(f"正在运行代码...（超时时间: {self.run_timeout}秒，按Ctrl+F5可停止）")
        self.show_output("=== 代码运行开始 ===")
        
        self.interpreter_thread = InterpreterThread(code, self.temp_file, self.interpreter_path, self.run_timeout)
        self.interpreter_thread.error_occurred.connect(self.show_error)
        self.interpreter_thread.output_received.connect(self.show_output)
        self.interpreter_thread.finished.connect(self.run_finished)
        self.interpreter_thread.timeout_occurred.connect(lambda: self.status_bar.showMessage("代码运行超时已终止"))
        self.interpreter_thread.start()
    
    def show_error(self, message):
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        error_msg = f"[{timestamp}] {message}"
        self.status_bar.showMessage(message.split(']')[-1].strip()[:50])
        self.output_panel.append(f'<span style="color:#ff4444;">{error_msg}</span>')
        self.output_panel.verticalScrollBar().setValue(self.output_panel.verticalScrollBar().maximum())

    def show_output(self, message):
        timestamp = QDateTime.currentDateTime().toString("HH:mm:ss")
        output_msg = f"[{timestamp}] {message}"
        self.output_panel.append(f'<span style="color:#ffffff;">{output_msg}</span>')
        self.output_panel.verticalScrollBar().setValue(self.output_panel.verticalScrollBar().maximum())

    def run_finished(self):
        self.show_output("=== 代码运行结束 ===")
        self.status_bar.showMessage("代码运行完成（输出已更新）")
    
    def clear_current_tab(self):
        editor = self.get_current_editor()
        editor.clear()
        self.status_bar.showMessage("已清空当前编辑区")
    
    def open_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "打开文件", self.file_tree.current_dir, "Easy UI Files (*.eui);;Python Files (*.py);;C++ Files (*.cpp *.h);;Java Files (*.java);;All Files (*)"
        )
        
        if file_path:
            self.open_file_from_path(file_path)
    
    def open_file_from_path(self, file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                code = file.read()
                
                for i in range(self.tab_widget.count()):
                    if self.tab_widget.tabText(i) == os.path.basename(file_path):
                        self.tab_widget.setCurrentIndex(i)
                        self.tab_widget.currentWidget().setPlainText(code)
                        self.current_file = file_path
                        return
                
                editor = CompleterTextEdit()
                editor.setFont(QFont("Consolas", 12))
                editor.setAcceptRichText(False)
                editor.setPlainText(code)
                
                EasyUISyntaxHighlighter(editor.document())
                self.setup_completer(editor)
                
                index = self.tab_widget.addTab(editor, os.path.basename(file_path))
                self.tab_widget.setCurrentIndex(index)
                
                self.current_file = file_path
                self.setWindowTitle(f"Easy Windows UI Editor - {os.path.basename(file_path)}")
                self.status_bar.showMessage(f"已打开文件: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"无法打开文件: {str(e)}")
            self.status_bar.showMessage("打开文件失败")
    
    def save_file(self):
        if self.current_file:
            try:
                editor = self.get_current_editor()
                with open(self.current_file, 'w', encoding='utf-8') as file:
                    file.write(editor.toPlainText())
                self.status_bar.showMessage(f"已保存文件: {self.current_file}")
                self.file_tree.refresh_tree()
                return True
            except Exception as e:
                QMessageBox.critical(self, "错误", f"无法保存文件: {str(e)}")
                self.status_bar.showMessage("保存文件失败")
                return False
        else:
            return self.save_file_as()
    
    def save_file_as(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "保存文件", self.file_tree.current_dir, "Easy UI Files (*.eui);;Python Files (*.py);;Text Files (*.txt);;All Files (*)"
        )
        
        if file_path:
            self.current_file = file_path
            current_index = self.tab_widget.currentIndex()
            self.tab_widget.setTabText(current_index, os.path.basename(file_path))
            self.setWindowTitle(f"Easy Windows UI Editor - {os.path.basename(file_path)}")
            result = self.save_file()
            if result:
                self.file_tree.refresh_tree()
            return result
        return False
    
    def load_example_code(self):
        example = """window=title="多媒体信息窗口",width=600,height=600,icon="app_icon.ico";
label=text="多媒体演示程序",id=title_label;
separator=text="用户信息",id=sep1;
label=text="请输入您的昵称:",id=nickname_label;
entry=hint="昵称",id=nickname_input;
combo=label="喜欢的音乐类型",id=music_type,options=["流行","摇滚","古典","民谣"];
checkbox=label="音乐功能",id=music_func,options=["播放网络音乐","播放本地音乐"];
radiogroup=label="音质选择",id=quality_radio,options=["标准","高清","无损"];
slider=label="音量调节",id=vol_slider,min=0,max=100,value=70;
separator=text="音乐控制",id=sep2;
audio=url="https://example.com/music.mp3",id=net_music;
audio=os="local_music.mp3",id=local_music;
button=text="显示信息",id=show_info,click="显示=nickname_input";
button=text="播放网络音乐",id=play_net,click="play_audio=net_music";
button=text="播放本地音乐",id=play_local,click="play_audio=local_music";
button=text="暂停音乐",id=pause_music,click="pause_audio=net_music";
button=text="停止音乐",id=stop_music,click="stop_audio=local_music";
separator=text="进度演示",id=sep3;
progress=label="播放进度",id=prog_bar,min=0,max=100,value=0;
timer=id=progress_timer,interval=1000,action="update_progress=prog_bar,value=+1";
button=text="开始进度",id=start_progress,click="start_timer=progress_timer";
button=text="重置进度",id=reset_progress,click="set_progress=prog_bar,value=0";"""
        
        editor = self.get_current_editor()
        editor.setPlainText(example)
        self.status_bar.showMessage("已加载带多媒体功能的示例代码")
    
    def show_about(self):
        QMessageBox.about(self, "关于 Easy Windows UI", 
                         "Easy Windows UI 1.8\n\n新增功能：全电脑扫描所有解释器\n一个简单易用的UI创建工具，让您用极少的代码创建Windows界面。")
    
    def closeEvent(self, event):
        if hasattr(self, 'interpreter_thread') and self.interpreter_thread.isRunning():
            self.interpreter_thread.stop()
        
        if self.search_thread and self.search_thread.isRunning():
            self.search_thread.stop_search()
            self.search_thread.wait()
        
        if os.path.exists(self.temp_file):
            try:
                os.remove(self.temp_file)
            except Exception as e:
                print(f"清理临时文件失败: {e}")
        
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    font = app.font()
    font.setFamily("SimHei")
    app.setFont(font)
    
    editor = EasyUIEditor()
    editor.show()
    sys.exit(app.exec_())