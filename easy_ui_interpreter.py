import sys
import os
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, 
                            QComboBox, QCheckBox, QPushButton, QWidget, 
                            QVBoxLayout, QHBoxLayout, QMessageBox, QFrame,
                            QTextEdit, QSlider, QProgressBar, QCalendarWidget,
                            QGroupBox, QRadioButton)
from PyQt5.QtCore import Qt, QUrl, QTimer, pyqtSlot
from PyQt5.QtGui import QIcon, QIntValidator, QPixmap, QImage
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from urllib.request import urlopen
from io import BytesIO

# ---------------------- 核心解释器类 ----------------------
class EasyUIInterpreter:
    def __init__(self):
        self.app = None
        self.window = None
        self.widgets = {}  # 存储所有组件
        self.variables = {}  # 存储可交互组件
        self.main_layout = None
        self.media_players = {}
        self.timers = {}  # 存储定时器
        self.groups = {}

    def parse_and_run(self, code):
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # 重置UI状态
        self.widgets = {}
        self.variables = {}
        self.media_players = {}
        self.timers = {}
        self.groups = {}
        self.window = None
        self.main_layout = None
        
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        for line in lines:
            self.parse_line(line)
        
        if not self.window:
            self.create_window("EUI默认窗口", 400, 300)
        else:
            self.main_layout.addStretch()
        
        self.window.show()
        sys.exit(self.app.exec_())

    # ---------------------- 解析逻辑 ----------------------
    def parse_line(self, line):
        line = line.strip().rstrip(';')
        if not line:
            return

        # 窗口配置
        window_pattern = r'window\s*=\s*title="([^"]+)"\s*,\s*width=(\d+)\s*,\s*height=(\d+)(?:\s*,\s*icon="([^"]+)")?'
        window_match = re.match(window_pattern, line)
        if window_match:
            title = window_match.group(1)
            width = int(window_match.group(2))
            height = int(window_match.group(3))
            icon_path = window_match.group(4) if window_match.group(4) else None
            self.create_window(title, width, height, icon_path)
            return

        # 文字标签
        label_match = re.match(r'label\s*=\s*text="([^"]+)"\s*,\s*id=(\w+)', line)
        if label_match:
            self.create_label(label_match.group(1), label_match.group(2))
            return

        # 输入框
        entry_pattern = r'entry\s*=\s*hint="([^"]+)"\s*,\s*id=(\w+)(?:\s*,\s*readonly=(true|false))?(?:\s*,\s*type=(number|text))?'
        entry_match = re.match(entry_pattern, line)
        if entry_match:
            hint = entry_match.group(1)
            widget_id = entry_match.group(2)
            readonly = entry_match.group(3).lower() == 'true' if entry_match.group(3) else False
            input_type = entry_match.group(4) if entry_match.group(4) else 'text'
            self.create_entry(hint, widget_id, readonly, input_type)
            return

        # 下拉选择框
        combo_match = re.match(r'combo\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*options=\[(.*?)\]', line)
        if combo_match:
            options = [opt.strip().strip('"') for opt in combo_match.group(3).split(',') if opt.strip()]
            self.create_combobox(combo_match.group(1), combo_match.group(2), options)
            return

        # 多选框组
        check_match = re.match(r'checkbox\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*options=\[(.*?)\]', line)
        if check_match:
            options = [opt.strip().strip('"') for opt in check_match.group(3).split(',') if opt.strip()]
            self.create_checkboxes(check_match.group(1), check_match.group(2), options)
            return

        # 按钮
        button_match = re.match(r'button\s*=\s*text="([^"]+)"\s*,\s*id=(\w+)\s*,\s*click="([^"]+)"', line)
        if button_match:
            self.create_button(button_match.group(1), button_match.group(2), button_match.group(3))
            return

        # 音频播放器
        audio_pattern = r'audio\s*=\s*(url|os)="([^"]+)"\s*,\s*id=(\w+)'
        audio_match = re.match(audio_pattern, line)
        if audio_match:
            self.create_audio_player(audio_match.group(1), audio_match.group(2), audio_match.group(3))
            return

        # 图片组件解析 - 支持path、url、os三种格式
        image_pattern = r'image\s*=\s*(path|url|os)="([^"]+)"\s*,\s*id=(\w+)(?:\s*,\s*width=(\d+))?(?:\s*,\s*height=(\d+))?(?:\s*,\s*tooltip="([^"]+)")?'
        image_match = re.match(image_pattern, line)
        if image_match:
            img_type = image_match.group(1)  # path/url/os
            img_path = image_match.group(2)  # 图片路径/URL
            img_id = image_match.group(3)    # 组件ID
            width = int(image_match.group(4)) if image_match.group(4) else None  # 可选宽度
            height = int(image_match.group(5)) if image_match.group(5) else None  # 可选高度
            tooltip = image_match.group(6) if image_match.group(6) else ""  # 可选提示文本
            self.create_image(img_type, img_path, img_id, width, height, tooltip)
            return

        # 滑块控件
        slider_pattern = r'slider\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*min=(\d+)\s*,\s*max=(\d+)\s*,\s*value=(\d+)'
        slider_match = re.match(slider_pattern, line)
        if slider_match:
            self.create_slider(
                slider_match.group(1), slider_match.group(2),
                int(slider_match.group(3)), int(slider_match.group(4)), int(slider_match.group(5))
            )
            return

        # 文本区域
        textarea_pattern = r'textarea\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*rows=(\d+)(?:\s*,\s*readonly=(true|false))?'
        textarea_match = re.match(textarea_pattern, line)
        if textarea_match:
            readonly = textarea_match.group(4).lower() == 'true' if textarea_match.group(4) else False
            self.create_textarea(textarea_match.group(1), textarea_match.group(2), int(textarea_match.group(3)), readonly)
            return

        # 分隔线
        separator_match = re.match(r'separator\s*=\s*text="([^"]*)"\s*,\s*id=(\w+)', line)
        if separator_match:
            self.create_separator(separator_match.group(1), separator_match.group(2))
            return

        # 进度条
        progress_pattern = r'progress\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*min=(\d+)\s*,\s*max=(\d+)\s*,\s*value=(\d+)'
        progress_match = re.match(progress_pattern, line)
        if progress_match:
            self.create_progressbar(
                progress_match.group(1), progress_match.group(2),
                int(progress_match.group(3)), int(progress_match.group(4)), int(progress_match.group(5))
            )
            return

        # 日历控件
        calendar_match = re.match(r'calendar\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)', line)
        if calendar_match:
            self.create_calendar(calendar_match.group(1), calendar_match.group(2))
            return

        # 单选按钮组
        radio_match = re.match(r'radiogroup\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*options=\[(.*?)\]', line)
        if radio_match:
            options = [opt.strip().strip('"') for opt in radio_match.group(3).split(',') if opt.strip()]
            self.create_radiogroup(radio_match.group(1), radio_match.group(2), options)
            return

        # 分组框
        groupbox_match = re.match(r'groupbox\s*=\s*title="([^"]+)"\s*,\s*id=(\w+)', line)
        if groupbox_match:
            self.create_groupbox(groupbox_match.group(1), groupbox_match.group(2))
            return

        # 定时器
        timer_pattern = r'timer\s*=\s*id=(\w+)\s*,\s*interval=(\d+)\s*,\s*action="([^"]+)"'
        timer_match = re.match(timer_pattern, line)
        if timer_match:
            self.create_timer(timer_match.group(1), int(timer_match.group(2)), timer_match.group(3))
            return

    # ---------------------- 组件创建方法 ----------------------
    def create_window(self, title, width, height, icon_path=None):
        self.window = QMainWindow()
        self.window.setWindowTitle(title)
        self.window.resize(width, height)
        
        if icon_path and os.path.exists(icon_path):
            try:
                self.window.setWindowIcon(QIcon(icon_path))
            except Exception as e:
                QMessageBox.warning(self.window, "警告", f"图标设置失败：{str(e)}")
        
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

    def create_label(self, text, widget_id):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        label = QLabel(text)
        label.setMinimumHeight(30)
        self._get_current_layout().addWidget(label)
        self.widgets[widget_id] = label

    def create_entry(self, hint, widget_id, readonly=False, input_type='text'):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(30)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        label = QLabel(hint)
        entry = QLineEdit()
        entry.setReadOnly(readonly)
        if input_type == 'number':
            entry.setValidator(QIntValidator())
        
        layout.addWidget(label)
        layout.addWidget(entry)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = entry
        self.variables[widget_id] = entry

    def create_combobox(self, label_text, widget_id, options):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(30)
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        label = QLabel(label_text)
        combo = QComboBox()
        combo.addItems(options)
        
        layout.addWidget(label)
        layout.addWidget(combo)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = combo
        self.variables[widget_id] = combo

    def create_checkboxes(self, label_text, widget_id, options):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(60)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        title_label = QLabel(label_text)
        layout.addWidget(title_label)
        
        check_layout = QHBoxLayout()
        check_layout.setSpacing(15)
        checkboxes = []
        for opt in options:
            cb = QCheckBox(opt)
            check_layout.addWidget(cb)
            checkboxes.append(cb)
        
        layout.addLayout(check_layout)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = checkboxes
        self.variables[widget_id] = checkboxes

    def create_button(self, text, widget_id, action):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        button = QPushButton(text)
        button.setMinimumHeight(30)
        button.setMaximumWidth(150)
        button.clicked.connect(lambda checked, a=action: self.handle_button_click(a))
        self._get_current_layout().addWidget(button, alignment=Qt.AlignLeft)
        self.widgets[widget_id] = button

    def create_audio_player(self, audio_type, audio_path, audio_id):
        player = QMediaPlayer()
        self.media_players[audio_id] = player
        
        try:
            if audio_type == "url":
                media = QMediaContent(QUrl(audio_path))
            else:
                abs_path = os.path.abspath(audio_path)
                if not os.path.exists(abs_path):
                    return
                media = QMediaContent(QUrl.fromLocalFile(abs_path))
            
            player.setMedia(media)
        except Exception:
            pass

    # 图片组件创建方法（支持path自动识别）
    def create_image(self, img_type, img_path, img_id, width=None, height=None, tooltip=""):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        # 创建图片标签容器
        container = QWidget()
        container.setMinimumHeight(height if height else 100)
        container.setMinimumWidth(width if width else 100)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 创建图片标签
        img_label = QLabel()
        img_label.setToolTip(tooltip)
        img_label.setAlignment(Qt.AlignCenter)
        
        # 加载图片
        pixmap = None
        try:
            if img_type == "path":
                # 自动识别：以http/https开头的视为网络图片，否则视为本地图片
                if img_path.startswith(('http://', 'https://')):
                    # 网络图片加载
                    with urlopen(img_path) as response:
                        img_data = response.read()
                        image = QImage.fromData(img_data)
                        pixmap = QPixmap.fromImage(image)
                else:
                    # 本地图片加载
                    abs_path = os.path.abspath(img_path)
                    if os.path.exists(abs_path):
                        pixmap = QPixmap(abs_path)
                    else:
                        img_label.setText("图片文件不存在")
                        QMessageBox.warning(self.window, "警告", f"本地图片路径不存在：{abs_path}")
            
            elif img_type == "url":
                # 强制网络图片加载
                with urlopen(img_path) as response:
                    img_data = response.read()
                    image = QImage.fromData(img_data)
                    pixmap = QPixmap.fromImage(image)
            
            elif img_type == "os":
                # 强制本地图片加载
                abs_path = os.path.abspath(img_path)
                if os.path.exists(abs_path):
                    pixmap = QPixmap(abs_path)
                else:
                    img_label.setText("图片文件不存在")
                    QMessageBox.warning(self.window, "警告", f"本地图片路径不存在：{abs_path}")
        
        except Exception as e:
            img_label.setText("图片加载失败")
            QMessageBox.warning(self.window, "警告", f"图片加载失败：{str(e)}")
        
        # 设置图片并调整大小
        if pixmap and not pixmap.isNull():
            if width and height:
                pixmap = pixmap.scaled(width, height, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            elif width:
                pixmap = pixmap.scaledToWidth(width, Qt.SmoothTransformation)
            elif height:
                pixmap = pixmap.scaledToHeight(height, Qt.SmoothTransformation)
                
            img_label.setPixmap(pixmap)
        
        layout.addWidget(img_label)
        self._get_current_layout().addWidget(container)
        self.widgets[img_id] = img_label
        self.variables[img_id] = img_label

    def create_slider(self, label_text, widget_id, min_val, max_val, value):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(60)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        value_label = QLabel(f"{label_text}：{value}")
        slider = QSlider(Qt.Horizontal)
        slider.setRange(min_val, max_val)
        slider.setValue(value)
        slider.setTickInterval(1)
        slider.setTickPosition(QSlider.TicksBelow)
        slider.valueChanged.connect(lambda v: value_label.setText(f"{label_text}：{v}"))
        
        layout.addWidget(value_label)
        layout.addWidget(slider)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = slider
        self.variables[widget_id] = slider

    def create_textarea(self, label_text, widget_id, rows, readonly=False):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel(label_text)
        textarea = QTextEdit()
        textarea.setReadOnly(readonly)
        textarea.setMinimumHeight(rows * 25)
        
        layout.addWidget(label)
        layout.addWidget(textarea)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = textarea
        self.variables[widget_id] = textarea

    def create_separator(self, text, widget_id):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        if text:
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(10)
            
            left_line = QFrame()
            left_line.setFrameShape(QFrame.HLine)
            left_line.setFrameShadow(QFrame.Sunken)
            
            right_line = QFrame()
            right_line.setFrameShape(QFrame.HLine)
            right_line.setFrameShadow(QFrame.Sunken)
            
            label = QLabel(text)
            layout.addWidget(left_line, 1)
            layout.addWidget(label, 0, Qt.AlignCenter)
            layout.addWidget(right_line, 1)
            
            self._get_current_layout().addWidget(container)
            self.widgets[widget_id] = container
        else:
            line = QFrame()
            line.setFrameShape(QFrame.HLine)
            line.setFrameShadow(QFrame.Sunken)
            self._get_current_layout().addWidget(line)
            self.widgets[widget_id] = line

    def create_progressbar(self, label_text, widget_id, min_val, max_val, value):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(50)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel(label_text)
        progress = QProgressBar()
        progress.setRange(min_val, max_val)
        progress.setValue(value)
        progress.setTextVisible(True)
        
        layout.addWidget(label)
        layout.addWidget(progress)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = progress
        self.variables[widget_id] = progress

    def create_calendar(self, label_text, widget_id):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        label = QLabel(label_text)
        calendar = QCalendarWidget()
        calendar.setSelectionMode(QCalendarWidget.SingleSelection)
        
        layout.addWidget(label)
        layout.addWidget(calendar)
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = calendar
        self.variables[widget_id] = calendar

    def create_radiogroup(self, label_text, widget_id, options):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        title_label = QLabel(label_text)
        layout.addWidget(title_label)
        
        radio_buttons = []
        for i, opt in enumerate(options):
            radio = QRadioButton(opt)
            if i == 0:
                radio.setChecked(True)
            layout.addWidget(radio)
            radio_buttons.append(radio)
        
        self._get_current_layout().addWidget(container)
        self.widgets[widget_id] = radio_buttons
        self.variables[widget_id] = radio_buttons

    def create_groupbox(self, title, group_id):
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        groupbox = QGroupBox(title)
        group_layout = QVBoxLayout(groupbox)
        group_layout.setContentsMargins(15, 15, 15, 15)
        group_layout.setSpacing(10)
        
        self._get_current_layout().addWidget(groupbox)
        self.groups[group_id] = group_layout
        self.widgets[group_id] = groupbox

    def create_timer(self, timer_id, interval, action):
        if timer_id in self.timers:
            self.timers[timer_id]['timer'].stop()
            
        timer = QTimer()
        timer.setInterval(interval)
        timer.timeout.connect(lambda: self.handle_timer_timeout(timer_id))
        self.timers[timer_id] = {
            'timer': timer, 
            'action': action
        }

    # ---------------------- 事件处理 ----------------------
    def _get_current_layout(self):
        return list(self.groups.values())[-1] if self.groups else self.main_layout

    @pyqtSlot()
    def handle_timer_timeout(self, timer_id):
        if timer_id not in self.timers:
            return
            
        timer_info = self.timers[timer_id]
        action = timer_info['action']
        
        if action.startswith("update_progress="):
            try:
                progress_part, step_part = action.split(",")
                progress_id = progress_part.split("=")[1].strip()
                step = int(step_part.split("=")[1].strip())
                
                progress_bar = self.widgets.get(progress_id)
                if not progress_bar or not isinstance(progress_bar, QProgressBar):
                    return
                
                current_value = progress_bar.value()
                new_value = current_value + step
                new_value = max(progress_bar.minimum(), min(progress_bar.maximum(), new_value))
                progress_bar.setValue(new_value)
                
                if new_value >= progress_bar.maximum():
                    timer_info['timer'].stop()
                    
            except Exception as e:
                QMessageBox.warning(self.window, "定时器错误", f"更新进度条失败：{str(e)}")

    def handle_button_click(self, action):
        if action.startswith("play_audio="):
            self._control_audio(action.split("=")[1], "play")
            return
        if action.startswith("pause_audio="):
            self._control_audio(action.split("=")[1], "pause")
            return
        if action.startswith("stop_audio="):
            self._control_audio(action.split("=")[1], "stop")
            return
        
        if action.startswith("start_timer="):
            timer_id = action.split("=")[1].strip()
            self._control_timer(timer_id, "start")
            return
        if action.startswith("stop_timer="):
            timer_id = action.split("=")[1].strip()
            self._control_timer(timer_id, "stop")
            return
        
        if action.startswith("set_progress="):
            parts = action.split(",")
            if len(parts) >= 2 and parts[1].startswith("value="):
                try:
                    p_id = parts[0].split("=")[1].strip()
                    val = int(parts[1].split("=")[1].strip())
                    if p_id in self.widgets and isinstance(self.widgets[p_id], QProgressBar):
                        self.widgets[p_id].setValue(val)
                except Exception as e:
                    QMessageBox.warning(self.window, "错误", f"设置进度条失败：{str(e)}")
            return
        
        if action.startswith("显示="):
            self._show_widget_value(action.split("=")[1].strip())
            return

    def _control_audio(self, audio_id, action):
        if audio_id not in self.media_players:
            return
        player = self.media_players[audio_id]
        if action == "play":
            player.play()
        elif action == "pause":
            player.pause()
        elif action == "stop":
            player.stop()

    def _control_timer(self, timer_id, action):
        if timer_id not in self.timers:
            QMessageBox.warning(self.window, "警告", f"定时器ID不存在：{timer_id}")
            return
        timer = self.timers[timer_id]['timer']
        if action == "start":
            timer.start()
        elif action == "stop":
            timer.stop()

    def _show_widget_value(self, widget_id):
        if widget_id not in self.variables:
            QMessageBox.warning(self.window, "警告", f"组件ID不存在：{widget_id}")
            return
        
        target = self.variables[widget_id]
        msg = ""
        
        if isinstance(target, list) and all(isinstance(x, QCheckBox) for x in target):
            selected = [cb.text() for cb in target if cb.isChecked()]
            msg = f"多选框选中项：{', '.join(selected) if selected else '无'}"
        elif isinstance(target, list) and all(isinstance(x, QRadioButton) for x in target):
            selected = [rb.text() for rb in target if rb.isChecked()]
            msg = f"单选框选中项：{', '.join(selected)}"
        elif isinstance(target, QComboBox):
            msg = f"下拉框选中：{target.currentText()}"
        elif isinstance(target, QLineEdit):
            msg = f"输入框内容：{target.text()}"
        elif isinstance(target, QSlider):
            msg = f"滑块值：{target.value()}"
        elif isinstance(target, QTextEdit):
            content = target.toPlainText()
            msg = f"文本区域内容：{content[:100]}..." if len(content) > 100 else f"文本区域内容：{content}"
        elif isinstance(target, QCalendarWidget):
            msg = f"选中日期：{target.selectedDate().toString('yyyy-MM-dd')}"
        elif isinstance(target, QProgressBar):
            msg = f"进度条值：{target.value()}%"
        elif isinstance(target, QLabel) and hasattr(target, 'pixmap') and target.pixmap():
            msg = f"图片信息：已加载图片（{target.pixmap().width()}x{target.pixmap().height()}）"
        
        QMessageBox.information(self.window, "组件值", msg)

# ---------------------- 运行入口 ----------------------
if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                ewui_code = f.read()
                interpreter = EasyUIInterpreter()
                interpreter.parse_and_run(ewui_code)
        except Exception as e:
            print(f"[EUI解释器错误]：{str(e)}", file=sys.stderr)
            sys.exit(1)
    else:
        print("=" * 50)
        print("Easy UI 解释器（支持path图片语法版）")
        print("用法：python easy_ui_interpreter.py <EWUI文件路径>")
        print("图片组件用法示例：")
        print("window=title=\"图片示例\",width=800,height=600")
        print("image=path=\"https://www.baidu.com/img/bd_logo1.png\",id=img1,width=300,tooltip=\"百度Logo\"")
        print("image=path=\"./test.jpg\",id=img2,height=200,tooltip=\"本地图片\"")
        print("button=text=\"显示图片信息\",id=btn_show,click=\"显示=img1\"")
        print("=" * 50)
        sys.exit(0)
