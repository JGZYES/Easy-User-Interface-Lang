import sys
import os
import time
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, 
                            QComboBox, QCheckBox, QPushButton, QWidget, 
                            QVBoxLayout, QHBoxLayout, QMessageBox, QFrame,
                            QTextEdit, QSlider, QProgressBar, QCalendarWidget,
                            QGroupBox, QRadioButton)
from PyQt5.QtCore import Qt, QUrl, QTimer
from PyQt5.QtGui import QIcon, QIntValidator
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
import re

class EasyUIInterpreter:
    """Easy Windows UI解释器，解析并执行EWUI代码"""
    
    def __init__(self):
        self.app = None
        self.window = None
        self.widgets = {}  # 存储所有组件，键为id
        self.variables = {}  # 存储组件关联的变量
        self.main_layout = None
        self.media_players = {}  # 存储音频播放器实例
        self.timers = {}  # 存储定时器实例
        self.groups = {}  # 存储分组框实例
    
    def parse_and_run(self, code):
        """解析并运行EWUI代码"""
        # 确保只有一个QApplication实例
        if not QApplication.instance():
            self.app = QApplication(sys.argv)
        else:
            self.app = QApplication.instance()
        
        # 清除之前的状态
        self.widgets = {}
        self.variables = {}
        self.media_players = {}
        self.timers = {}
        self.groups = {}
        self.window = None
        self.main_layout = None
        
        # 按行解析代码
        lines = [line.strip() for line in code.split('\n') if line.strip()]
        
        for line in lines:
            self.parse_line(line)
        
        # 如果没有创建窗口，创建一个默认窗口
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        else:
            # 添加一个拉伸项，确保所有组件都能显示
            self.main_layout.addStretch()
        
        # 显示窗口并运行应用
        self.window.show()
        sys.exit(self.app.exec_())
    
    def parse_line(self, line):
        """解析单行类HTML语法代码"""
        # 移除行尾的;，统一处理
        line = line.strip().rstrip(';')
        if not line:
            return

        # 1. 匹配窗口标签(支持可选图标参数): window=title="xxx",width=xxx,height=xxx[,icon="xxx"]
        window_pattern = r'window\s*=\s*title="([^"]+)"\s*,\s*width=(\d+)\s*,\s*height=(\d+)(?:\s*,\s*icon="([^"]+)")?'
        window_match = re.match(window_pattern, line)
        if window_match:
            title = window_match.group(1)
            width = int(window_match.group(2))
            height = int(window_match.group(3))
            icon_path = window_match.group(4) if window_match.group(4) else None
            self.create_window(title, width, height, icon_path)
            return

        # 2. 匹配文字标签: label=text="xxx",id=xxx
        label_match = re.match(r'label\s*=\s*text="([^"]+)"\s*,\s*id=(\w+)', line)
        if label_match:
            text = label_match.group(1)
            widget_id = label_match.group(2)
            self.create_label(text, widget_id)
            return

        # 3. 匹配输入框标签(支持只读属性): entry=hint="xxx",id=xxx[,readonly=true/false]
        entry_pattern = r'entry\s*=\s*hint="([^"]+)"\s*,\s*id=(\w+)(?:\s*,\s*readonly=(true|false))?(?:\s*,\s*type=(number|text))?'
        entry_match = re.match(entry_pattern, line)
        if entry_match:
            hint = entry_match.group(1)
            widget_id = entry_match.group(2)
            readonly = entry_match.group(3).lower() == 'true' if entry_match.group(3) else False
            input_type = entry_match.group(4) if entry_match.group(4) else 'text'
            self.create_entry(hint, widget_id, readonly, input_type)
            return

        # 4. 匹配选择框标签: combo=label="xxx",id=xxx,options=[x,x,x]
        combo_match = re.match(r'combo\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*options=\[(.*?)\]', line)
        if combo_match:
            label = combo_match.group(1)
            widget_id = combo_match.group(2)
            options = [opt.strip().strip('"') for opt in combo_match.group(3).split(',') if opt.strip()]
            self.create_combobox(label, widget_id, options)
            return

        # 5. 匹配多选框标签: checkbox=label="xxx",id=xxx,options=[x,x,x]
        check_match = re.match(r'checkbox\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*options=\[(.*?)\]', line)
        if check_match:
            label = check_match.group(1)
            widget_id = check_match.group(2)
            options = [opt.strip().strip('"') for opt in check_match.group(3).split(',') if opt.strip()]
            self.create_checkboxes(label, widget_id, options)
            return

        # 6. 匹配按钮标签: button=text="xxx",id=xxx,click="xxx"
        button_match = re.match(r'button\s*=\s*text="([^"]+)"\s*,\s*id=(\w+)\s*,\s*click="([^"]+)"', line)
        if button_match:
            text = button_match.group(1)
            widget_id = button_match.group(2)
            action = button_match.group(3)
            self.create_button(text, widget_id, action)
            return
        
        # 7. 匹配音频标签: 支持网络URL(audio=url="xxx",id=xxx)和本地文件(audio=os="xxx",id=xxx)
        audio_pattern = r'audio\s*=\s*(url|os)="([^"]+)"\s*,\s*id=(\w+)'
        audio_match = re.match(audio_pattern, line)
        if audio_match:
            audio_type = audio_match.group(1)  # url或os
            audio_path = audio_match.group(2)
            audio_id = audio_match.group(3)
            self.create_audio_player(audio_type, audio_path, audio_id)
            return
        
        # 8. 匹配滑块控件: slider=label="xxx",id=xxx,min=xxx,max=xxx,value=xxx
        slider_pattern = r'slider\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*min=(\d+)\s*,\s*max=(\d+)\s*,\s*value=(\d+)'
        slider_match = re.match(slider_pattern, line)
        if slider_match:
            label = slider_match.group(1)
            widget_id = slider_match.group(2)
            min_val = int(slider_match.group(3))
            max_val = int(slider_match.group(4))
            value = int(slider_match.group(5))
            self.create_slider(label, widget_id, min_val, max_val, value)
            return
        
        # 9. 匹配文本区域: textarea=label="xxx",id=xxx,rows=xxx[,readonly=true/false]
        textarea_pattern = r'textarea\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*rows=(\d+)(?:\s*,\s*readonly=(true|false))?'
        textarea_match = re.match(textarea_pattern, line)
        if textarea_match:
            label = textarea_match.group(1)
            widget_id = textarea_match.group(2)
            rows = int(textarea_match.group(3))
            readonly = textarea_match.group(4).lower() == 'true' if textarea_match.group(4) else False
            self.create_textarea(label, widget_id, rows, readonly)
            return
        
        # 10. 匹配分隔线: separator=text="xxx",id=xxx
        separator_match = re.match(r'separator\s*=\s*text="([^"]*)"\s*,\s*id=(\w+)', line)
        if separator_match:
            text = separator_match.group(1)
            widget_id = separator_match.group(2)
            self.create_separator(text, widget_id)
            return
        
        # 11. 匹配进度条: progress=label="xxx",id=xxx,min=xxx,max=xxx,value=xxx
        progress_pattern = r'progress\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*min=(\d+)\s*,\s*max=(\d+)\s*,\s*value=(\d+)'
        progress_match = re.match(progress_pattern, line)
        if progress_match:
            label = progress_match.group(1)
            widget_id = progress_match.group(2)
            min_val = int(progress_match.group(3))
            max_val = int(progress_match.group(4))
            value = int(progress_match.group(5))
            self.create_progressbar(label, widget_id, min_val, max_val, value)
            return
        
        # 12. 匹配日历控件: calendar=label="xxx",id=xxx
        calendar_match = re.match(r'calendar\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)', line)
        if calendar_match:
            label = calendar_match.group(1)
            widget_id = calendar_match.group(2)
            self.create_calendar(label, widget_id)
            return
        
        # 13. 匹配单选按钮组: radiogroup=label="xxx",id=xxx,options=[x,x,x]
        radio_match = re.match(r'radiogroup\s*=\s*label="([^"]+)"\s*,\s*id=(\w+)\s*,\s*options=\[(.*?)\]', line)
        if radio_match:
            label = radio_match.group(1)
            widget_id = radio_match.group(2)
            options = [opt.strip().strip('"') for opt in radio_match.group(3).split(',') if opt.strip()]
            self.create_radiogroup(label, widget_id, options)
            return
        
        # 14. 匹配分组框: groupbox=title="xxx",id=xxx
        groupbox_match = re.match(r'groupbox\s*=\s*title="([^"]+)"\s*,\s*id=(\w+)', line)
        if groupbox_match:
            title = groupbox_match.group(1)
            group_id = groupbox_match.group(2)
            self.create_groupbox(title, group_id)
            return
        
        # 15. 匹配定时器: timer=id=xxx,interval=xxx,action="xxx"
        timer_pattern = r'timer\s*=\s*id=(\w+)\s*,\s*interval=(\d+)\s*,\s*action="([^"]+)"'
        timer_match = re.match(timer_pattern, line)
        if timer_match:
            timer_id = timer_match.group(1)
            interval = int(timer_match.group(2))
            action = timer_match.group(3)
            self.create_timer(timer_id, interval, action)
            return
    
    def create_window(self, title, width, height, icon_path=None):
        """创建主窗口"""
        self.window = QMainWindow()
        self.window.setWindowTitle(title)
        self.window.resize(width, height)
        
        # 设置窗口图标
        if icon_path:
            icon_path = icon_path.strip()
            if os.path.exists(icon_path):
                try:
                    self.window.setWindowIcon(QIcon(icon_path))
                except Exception as e:
                    QMessageBox.warning(self.window, "警告", f"图标设置失败: {str(e)}")
            else:
                QMessageBox.warning(self.window, "警告", f"图标文件不存在: {icon_path}")
        
        # 创建中心部件和布局
        central_widget = QWidget()
        self.window.setCentralWidget(central_widget)
        
        # 使用QVBoxLayout作为主布局，允许垂直排列组件
        self.main_layout = QVBoxLayout(central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)
    
    def create_label(self, text, widget_id):
        """创建文字显示组件"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        label = QLabel(text)
        label.setMinimumHeight(30)
        current_layout = self._get_current_layout()
        current_layout.addWidget(label)
        self.widgets[widget_id] = label
    
    def create_entry(self, hint, widget_id, readonly=False, input_type='text'):
        """创建输入框组件，支持数字类型"""
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
        
        # 如果是数字类型，设置验证器
        if input_type == 'number':
            entry.setValidator(QIntValidator())
        
        layout.addWidget(label)
        layout.addWidget(entry)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = entry
        self.variables[widget_id] = entry
    
    def create_combobox(self, label_text, widget_id, options):
        """创建选择框组件"""
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
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = combo
        self.variables[widget_id] = combo
    
    def create_checkboxes(self, label_text, widget_id, options):
        """创建多选框组件"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(60)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 添加标题
        title_label = QLabel(label_text)
        layout.addWidget(title_label)
        
        # 创建水平布局放置复选框
        check_layout = QHBoxLayout()
        check_layout.setContentsMargins(0, 0, 0, 0)
        check_layout.setSpacing(15)
        
        checkboxes = []
        for option in options:
            checkbox = QCheckBox(option)
            check_layout.addWidget(checkbox)
            checkboxes.append(checkbox)
        
        layout.addLayout(check_layout)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = checkboxes
        self.variables[widget_id] = checkboxes
    
    def create_button(self, text, widget_id, action):
        """创建按钮组件"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        button = QPushButton(text)
        button.setMinimumHeight(30)
        button.setMaximumWidth(150)
        
        # 绑定点击事件
        button.clicked.connect(lambda: self.handle_button_click(action))
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(button, alignment=Qt.AlignLeft)
        self.widgets[widget_id] = button
    
    def create_audio_player(self, audio_type, audio_path, audio_id):
        """创建音频播放器（支持网络URL和本地文件）"""
        player = QMediaPlayer()
        self.media_players[audio_id] = player  # 存储播放器实例
        
        try:
            if audio_type == "url":
                # 网络音频：使用QUrl构建媒体内容
                media_content = QMediaContent(QUrl(audio_path))
            else:  # audio_type == "os"
                # 本地音频：转换为绝对路径并构建QUrl
                absolute_path = os.path.abspath(audio_path)
                if not os.path.exists(absolute_path):
                    QMessageBox.warning(self.window, "警告", f"本地音频文件不存在: {absolute_path}")
                    return
                media_content = QMediaContent(QUrl.fromLocalFile(absolute_path))
            
            player.setMedia(media_content)
            # 连接错误信号，捕获播放异常
            player.error.connect(lambda err: self.handle_audio_error(audio_id, err))
            QMessageBox.information(self.window, "提示", f"音频播放器创建成功（ID: {audio_id}）")
        except Exception as e:
            QMessageBox.critical(self.window, "错误", f"创建音频播放器失败: {str(e)}")
    
    def create_slider(self, label_text, widget_id, min_val, max_val, value):
        """创建滑块控件"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(60)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 显示当前值的标签
        value_label = QLabel(f"{label_text}: {value}")
        
        # 创建滑块
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(value)
        slider.setTickInterval(1)
        slider.setTickPosition(QSlider.TicksBelow)
        
        # 滑块值变化时更新标签
        def update_value():
            value_label.setText(f"{label_text}: {slider.value()}")
        
        slider.valueChanged.connect(update_value)
        
        layout.addWidget(value_label)
        layout.addWidget(slider)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = slider
        self.variables[widget_id] = slider
    
    def create_textarea(self, label_text, widget_id, rows, readonly=False):
        """创建文本区域"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel(label_text)
        textarea = QTextEdit()
        textarea.setReadOnly(readonly)
        # 设置高度（每行约25像素）
        textarea.setMinimumHeight(rows * 25)
        
        layout.addWidget(label)
        layout.addWidget(textarea)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = textarea
        self.variables[widget_id] = textarea
    
    def create_separator(self, text, widget_id):
        """创建分隔线，支持带文本"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        
        if text:
            # 创建带文本的分隔线
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
            
            current_layout = self._get_current_layout()
            current_layout.addWidget(container)
            self.widgets[widget_id] = container
        else:
            current_layout = self._get_current_layout()
            current_layout.addWidget(line)
            self.widgets[widget_id] = line
    
    def create_progressbar(self, label_text, widget_id, min_val, max_val, value):
        """创建进度条"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        container.setMinimumHeight(50)
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel(label_text)
        progress = QProgressBar()
        progress.setMinimum(min_val)
        progress.setMaximum(max_val)
        progress.setValue(value)
        # 显示百分比
        progress.setTextVisible(True)
        
        layout.addWidget(label)
        layout.addWidget(progress)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = progress
        self.variables[widget_id] = progress
    
    def create_calendar(self, label_text, widget_id):
        """创建日历控件"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        label = QLabel(label_text)
        calendar = QCalendarWidget()
        # 设置日期选择模式
        calendar.setSelectionMode(QCalendarWidget.SingleSelection)
        
        layout.addWidget(label)
        layout.addWidget(calendar)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = calendar
        self.variables[widget_id] = calendar
    
    def create_radiogroup(self, label_text, widget_id, options):
        """创建单选按钮组"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # 添加标题
        title_label = QLabel(label_text)
        layout.addWidget(title_label)
        
        # 创建按钮组
        radio_buttons = []
        for i, option in enumerate(options):
            radio = QRadioButton(option)
            # 选中第一个选项
            if i == 0:
                radio.setChecked(True)
            layout.addWidget(radio)
            radio_buttons.append(radio)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(container)
        
        self.widgets[widget_id] = radio_buttons
        self.variables[widget_id] = radio_buttons
    
    def create_groupbox(self, title, group_id):
        """创建分组框，后续控件会添加到该分组中"""
        if not self.window:
            self.create_window("默认窗口", 400, 300)
        
        groupbox = QGroupBox(title)
        group_layout = QVBoxLayout(groupbox)
        group_layout.setContentsMargins(15, 15, 15, 15)
        group_layout.setSpacing(10)
        
        current_layout = self._get_current_layout()
        current_layout.addWidget(groupbox)
        
        self.groups[group_id] = group_layout
        self.widgets[group_id] = groupbox
    
    def create_timer(self, timer_id, interval, action):
        """创建定时器"""
        timer = QTimer()
        timer.setInterval(interval)  # 毫秒
        timer.timeout.connect(lambda: self.handle_timer_timeout(action))
        
        self.timers[timer_id] = {
            'timer': timer,
            'action': action
        }
        
        QMessageBox.information(self.window, "提示", f"定时器创建成功（ID: {timer_id}，间隔: {interval}ms）")
    
    def _get_current_layout(self):
        """获取当前活动布局（如果有分组框则使用分组框布局，否则使用主布局）"""
        # 如果有分组框，返回最后一个分组框的布局
        if self.groups:
            return list(self.groups.values())[-1]
        return self.main_layout
    
    def handle_audio_error(self, audio_id, error_code):
        """处理音频播放错误"""
        error_msg = f"音频播放错误（ID: {audio_id}），错误码: {error_code}"
        QMessageBox.warning(self.window, "音频错误", error_msg)
    
    def handle_timer_timeout(self, action):
        """处理定时器超时事件"""
        # 支持更新进度条: update_progress=id,value=xxx
        if action.startswith("update_progress="):
            parts = action.split(",")
            if len(parts) >= 2 and parts[0].startswith("update_progress="):
                progress_id = parts[0].split("=")[1].strip()
                value_part = parts[1].strip()
                
                if value_part.startswith("value="):
                    value = int(value_part.split("=")[1].strip())
                    if progress_id in self.widgets and isinstance(self.widgets[progress_id], QProgressBar):
                        progress = self.widgets[progress_id]
                        progress.setValue(value)
                        # 如果达到最大值，停止定时器
                        if value >= progress.maximum():
                            for timer in self.timers.values():
                                if timer['action'] == action:
                                    timer['timer'].stop()
                                    break
            return
    
    def handle_button_click(self, action):
        """处理按钮点击事件"""
        # 音频控制：play_audio=id、pause_audio=id、stop_audio=id
        if action.startswith("play_audio="):
            audio_id = action.split("=")[1].strip()
            if audio_id in self.media_players:
                self.media_players[audio_id].play()
            else:
                QMessageBox.warning(self.window, "警告", f"音频ID不存在: {audio_id}")
            return
        
        if action.startswith("pause_audio="):
            audio_id = action.split("=")[1].strip()
            if audio_id in self.media_players:
                self.media_players[audio_id].pause()
            else:
                QMessageBox.warning(self.window, "警告", f"音频ID不存在: {audio_id}")
            return
        
        if action.startswith("stop_audio="):
            audio_id = action.split("=")[1].strip()
            if audio_id in self.media_players:
                self.media_players[audio_id].stop()
            else:
                QMessageBox.warning(self.window, "警告", f"音频ID不存在: {audio_id}")
            return
        
        # 定时器控制：start_timer=id、stop_timer=id
        if action.startswith("start_timer="):
            timer_id = action.split("=")[1].strip()
            if timer_id in self.timers:
                self.timers[timer_id]['timer'].start()
                QMessageBox.information(self.window, "提示", f"定时器已启动（ID: {timer_id}）")
            else:
                QMessageBox.warning(self.window, "警告", f"定时器ID不存在: {timer_id}")
            return
        
        if action.startswith("stop_timer="):
            timer_id = action.split("=")[1].strip()
            if timer_id in self.timers:
                self.timers[timer_id]['timer'].stop()
                QMessageBox.information(self.window, "提示", f"定时器已停止（ID: {timer_id}）")
            else:
                QMessageBox.warning(self.window, "警告", f"定时器ID不存在: {timer_id}")
            return
        
        # 更新进度条
        if action.startswith("set_progress="):
            parts = action.split(",")
            if len(parts) >= 2 and parts[0].startswith("set_progress="):
                progress_id = parts[0].split("=")[1].strip()
                value_part = parts[1].strip()
                
                if value_part.startswith("value="):
                    try:
                        value = int(value_part.split("=")[1].strip())
                        if progress_id in self.widgets and isinstance(self.widgets[progress_id], QProgressBar):
                            self.widgets[progress_id].setValue(value)
                        else:
                            QMessageBox.warning(self.window, "警告", f"进度条ID不存在: {progress_id}")
                    except ValueError:
                        QMessageBox.warning(self.window, "警告", "无效的进度值")
            return
        
        # 显示组件值
        if action.startswith("显示") and "=" in action:
            _, target_id = action.split("=")
            target_id = target_id.strip()
            
            if target_id in self.variables:
                target = self.variables[target_id]
                
                if isinstance(target, list) and all(isinstance(x, QCheckBox) for x in target):
                    # 处理多选框
                    selected = [checkbox.text() for checkbox in target if checkbox.isChecked()]
                    QMessageBox.information(self.window, "提示", f"选中项: {', '.join(selected)}")
                elif isinstance(target, list) and all(isinstance(x, QRadioButton) for x in target):
                    # 处理单选按钮组
                    selected = [radio.text() for radio in target if radio.isChecked()]
                    QMessageBox.information(self.window, "提示", f"选中项: {', '.join(selected)}")
                elif isinstance(target, QComboBox):
                    # 处理选择框
                    QMessageBox.information(self.window, "提示", f"选择: {target.currentText()}")
                elif isinstance(target, QLineEdit):
                    # 处理输入框
                    QMessageBox.information(self.window, "提示", f"输入: {target.text()}")
                elif isinstance(target, QSlider):
                    # 处理滑块
                    QMessageBox.information(self.window, "提示", f"值: {target.value()}")
                elif isinstance(target, QTextEdit):
                    # 处理文本区域
                    content = target.toPlainText()
                    if len(content) > 100:
                        content = content[:100] + "..."
                    QMessageBox.information(self.window, "提示", f"内容: {content}")
                elif isinstance(target, QCalendarWidget):
                    # 处理日历
                    date = target.selectedDate()
                    QMessageBox.information(self.window, "提示", f"选中日期: {date.toString('yyyy-MM-dd')}")
                elif isinstance(target, QProgressBar):
                    # 处理进度条
                    QMessageBox.information(self.window, "提示", f"进度: {target.value()}%")
                else:
                    QMessageBox.information(self.window, "提示", f"组件值: {str(target)}")


# 允许从命令行接收文件名参数
if __name__ == "__main__":
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                code = f.read()
                interpreter = EasyUIInterpreter()
                interpreter.parse_and_run(code)
        except Exception as e:
            print(f"解释器错误: {str(e)}", file=sys.stderr)
            sys.exit(1)
