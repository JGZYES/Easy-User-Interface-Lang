import os
import sys
import time
import requests
import shutil
from PyQt5.QtWidgets import (QApplication, QMainWindow, QLabel, QLineEdit, 
                            QPushButton, QVBoxLayout, QHBoxLayout, QWidget, 
                            QFileDialog, QProgressBar, QMessageBox, QFrame,
                            QCheckBox, QStackedWidget, QTextEdit, QScrollArea)
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QUrl
from PyQt5.QtGui import (QFont, QIcon, QPalette, QColor, QPixmap, 
                         QImageReader, QImage, QIcon as QtGuiQIcon)

# --------------------------- 全局样式配置 ---------------------------
GLOBAL_STYLE = """
/* 主按钮样式：科技蓝底色+圆角 */
QPushButton#PrimaryBtn {
    background-color: #1E88E5;
    color: white;
    border: none;
    border-radius: 4px;
    padding: 8px 16px;
    font-family: "微软雅黑", "Segoe UI";
    font-size: 10pt;
}
QPushButton#PrimaryBtn:hover {
    background-color: #1976D2;
}
QPushButton#PrimaryBtn:disabled {
    background-color: #BBDEFB;
}

/* 次要按钮样式：灰色边框+透明底色 */
QPushButton#SecondaryBtn {
    background-color: transparent;
    color: #333333;
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 8px 16px;
    font-family: "微软雅黑", "Segoe UI";
    font-size: 10pt;
}
QPushButton#SecondaryBtn:hover {
    background-color: #F5F5F5;
}

/* 进度条样式：蓝色进度+圆角 */
QProgressBar {
    border: none;
    border-radius: 4px;
    background-color: #F5F5F5;
    height: 8px;
    font-family: "微软雅黑";
    font-size: 8pt;
}
QProgressBar::chunk {
    background-color: #1E88E5;
    border-radius: 4px;
}

/* 输入框样式：细边框+聚焦高亮 */
QLineEdit {
    border: 1px solid #CCCCCC;
    border-radius: 4px;
    padding: 6px 10px;
    font-family: "微软雅黑";
    font-size: 9pt;
}
QLineEdit:focus {
    border-color: #1E88E5;
}

/* 面板样式：圆角+浅灰底色 */
QFrame#CardFrame {
    background-color: white;
    border-radius: 6px;
    border: 1px solid #EEEEEE;
}

/* 标题样式 */
QLabel#TitleLabel {
    font-family: "微软雅黑", "Segoe UI";
    font-size: 14pt;
    font-weight: bold;
    color: #212121;
}

/* 副标题样式 */
QLabel#SubtitleLabel, QTextEdit {
    font-family: "微软雅黑", "Segoe UI";
    font-size: 10pt;
    color: #666666;
}

/* 滚动区域样式 */
QScrollArea {
    border: none;
}
"""

# --------------------------- 下载线程 ---------------------------
class DownloadThread(QThread):
    progress_updated = pyqtSignal(int, str, float)  # (进度, 文件名, 下载速度MB/s)
    download_finished = pyqtSignal(bool, str, str)  # (成功, 消息, 文件名)
    
    def __init__(self, url, save_path, file_name, max_retries=2):
        super().__init__()
        self.url = url
        self.save_path = save_path
        self.file_name = file_name
        self.max_retries = max_retries  # 最大重试次数
        self.start_time = None

    def run(self):
        retry_count = 0
        while retry_count <= self.max_retries:
            try:
                # 确保保存目录存在
                save_dir = os.path.dirname(self.save_path)
                if not os.path.exists(save_dir):
                    os.makedirs(save_dir)
                
                # 发送请求（增加超时设置）
                self.start_time = time.time()
                response = requests.get(
                    self.url, 
                    stream=True,
                    timeout=15,
                    headers={"User-Agent": "EasyUI-Installer/1.0"}
                )
                response.raise_for_status()  # 触发HTTP错误
                total_size = int(response.headers.get('content-length', 0))
                
                # 下载文件
                with open(self.save_path, 'wb') as file:
                    downloaded_size = 0
                    for data in response.iter_content(chunk_size=8192):  # 增大缓冲区，提升速度
                        if data:
                            file.write(data)
                            downloaded_size += len(data)
                            # 计算进度和下载速度
                            if total_size > 0:
                                progress = int((downloaded_size / total_size) * 100)
                                elapsed = time.time() - self.start_time
                                speed = downloaded_size / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                                self.progress_updated.emit(progress, self.file_name, round(speed, 2))
                
                # 验证文件完整性
                if os.path.exists(self.save_path) and os.path.getsize(self.save_path) > 0:
                    self.download_finished.emit(True, self.save_path, self.file_name)
                else:
                    raise Exception("文件下载不完整或为空")
                break  # 成功则退出重试循环
            
            except Exception as e:
                retry_count += 1
                if retry_count > self.max_retries:
                    self.download_finished.emit(False, f"重试{self.max_retries}次后失败：{str(e)}", self.file_name)
                else:
                    time.sleep(2)  # 重试间隔2秒


# --------------------------- 图标下载线程 ---------------------------
class IconDownloadThread(QThread):
    download_finished = pyqtSignal(bool, QIcon, bytes)  # (成功, 图标对象, 原始数据)
    
    def __init__(self, icon_url):
        super().__init__()
        self.icon_url = icon_url

    def run(self):
        try:
            # 下载图标
            response = requests.get(
                self.icon_url,
                timeout=10,
                headers={"User-Agent": "EasyUI-Installer/1.0"}
            )
            response.raise_for_status()
            
            # 将下载的内容转换为QIcon
            image = QImage()
            if image.loadFromData(response.content):
                icon = QIcon(QPixmap.fromImage(image))
                self.download_finished.emit(True, icon, response.content)
            else:
                self.download_finished.emit(False, QIcon(), b'')
                
        except Exception as e:
            print(f"图标下载失败: {str(e)}")
            self.download_finished.emit(False, QIcon(), b'')


# --------------------------- 多文件下载管理器 ---------------------------
class MultiFileDownloader(QThread):
    overall_progress = pyqtSignal(int)  # 总体进度
    file_progress = pyqtSignal(int, str, float)  # (单个进度, 文件名, 速度)
    file_finished = pyqtSignal(bool, str, str)  # 单个文件完成
    all_finished = pyqtSignal()  # 所有文件完成
    time_remaining = pyqtSignal(str)  # 剩余时间（格式：mm:ss）
    
    def __init__(self, downloads):
        super().__init__()
        self.downloads = downloads  # [(url, save_path, file_name), ...]
        self.total_files = len(downloads)
        self.completed_files = 0
        self.current_file_index = 0
        self.current_thread = None
        self.stopped = False
        self.current_speed = 0  # 当前下载速度（MB/s）
        self.remaining_size = 0  # 剩余文件总大小（MB）

    def run(self):
        # 预计算总大小（用于剩余时间估算）
        self.calc_total_remaining_size()
        
        for i, (url, save_path, file_name) in enumerate(self.downloads):
            if self.stopped:
                break
            
            self.current_file_index = i
            self.file_progress.emit(0, file_name, 0.0)
            
            # 创建当前文件下载线程
            self.current_thread = DownloadThread(url, save_path, file_name)
            self.current_thread.progress_updated.connect(self.on_file_progress)
            self.current_thread.download_finished.connect(self.on_file_complete)
            self.current_thread.start()
            self.current_thread.wait()
        
        self.all_finished.emit()

    def calc_total_remaining_size(self):
        """计算剩余文件总大小（MB）"""
        self.remaining_size = 0
        for url, save_path, file_name in self.downloads:
            try:
                response = requests.head(url, timeout=10)
                file_size = int(response.headers.get('content-length', 0)) / (1024 * 1024)
                self.remaining_size += file_size
            except:
                self.remaining_size += 10  # 估算未知大小文件为10MB

    def on_file_progress(self, progress, file_name, speed):
        self.current_speed = speed
        self.file_progress.emit(progress, file_name, speed)
        
        # 计算总体进度
        completed_size_ratio = (self.completed_files + progress/100) / self.total_files
        overall = int(completed_size_ratio * 100)
        self.overall_progress.emit(overall)
        
        # 估算剩余时间（仅当速度>0时）
        if speed > 0.01:
            # 计算当前文件剩余大小 + 未开始文件大小
            current_file_remaining = (1 - progress/100) * (self.remaining_size / self.total_files)
            unstarted_files_size = (self.total_files - self.current_file_index - 1) * (self.remaining_size / self.total_files)
            total_remaining = current_file_remaining + unstarted_files_size
            
            remaining_seconds = int(total_remaining / speed)
            minutes = remaining_seconds // 60
            seconds = remaining_seconds % 60
            self.time_remaining.emit(f"{minutes:02d}:{seconds:02d}")
        else:
            self.time_remaining.emit("--:--")

    def on_file_complete(self, success, message, file_name):
        self.file_finished.emit(success, message, file_name)
        if success:
            self.completed_files += 1
            # 更新剩余大小
            self.remaining_size -= (self.remaining_size / self.total_files)

    def stop(self):
        self.stopped = True
        if self.current_thread and self.current_thread.isRunning():
            self.current_thread.terminate()


# --------------------------- 主安装窗口 ---------------------------
class EasyUIInstaller(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Easy UI 安装程序")
        self.setGeometry(300, 200, 700, 500)
        self.setMinimumSize(700, 500)
        self.setStyleSheet(GLOBAL_STYLE)
        
        # 图标配置 - 使用网络图标
        self.icon_url = "https://sunshinetown.oss-cn-shenzhen.aliyuncs.com/eui.ico"  # 网络图标路径
        self.app_icon = QIcon()  # 初始化空图标
        self.icon_data = b''  # 存储图标原始数据，用于创建快捷方式
        self.download_icon()  # 启动图标下载
        
        # 核心数据初始化
        self.default_install_dir = os.path.join(os.path.expanduser("~"), "Easy UI")
        self.resources = {
            "interpreter": {
                "name": "Easy UI 解释器",
                "url": "https://sunshinetown.oss-cn-shenzhen.aliyuncs.com/easy_ui_interpreter.exe",
                "default_path": os.path.join(self.default_install_dir, "easy_ui_interpreter.exe")
            },
            "editor": {
                "name": "Easy UI 编辑器",
                "url": "https://sunshinetown.oss-cn-shenzhen.aliyuncs.com/EasyUI_Editor.exe",
                "default_path": os.path.join(self.default_install_dir, "EasyUI_Editor.exe")
            }
        }
        self.download_queue = []
        self.download_manager = None

        # 初始化分步容器
        self.init_stacked_widget()

    def download_icon(self):
        """下载网络图标"""
        print(f"正在下载图标: {self.icon_url}")
        self.icon_thread = IconDownloadThread(self.icon_url)
        self.icon_thread.download_finished.connect(self.on_icon_downloaded)
        self.icon_thread.start()

    def on_icon_downloaded(self, success, icon, data):
        """图标下载完成回调"""
        if success and not icon.isNull():
            print("图标下载成功")
            self.app_icon = icon
            self.icon_data = data  # 保存图标原始数据
            self.setWindowIcon(self.app_icon)
            
            # 更新界面上的图标
            if hasattr(self, 'logo_label'):
                pixmap = self.app_icon.pixmap(
                    self.logo_label.width(), 
                    self.logo_label.height(),
                    mode=QtGuiQIcon.Normal,
                    state=QtGuiQIcon.On
                )
                self.logo_label.setPixmap(pixmap)
                
            if hasattr(self, 'complete_icon'):
                pixmap = self.app_icon.pixmap(
                    self.complete_icon.width(), 
                    self.complete_icon.height(),
                    mode=QtGuiQIcon.Normal,
                    state=QtGuiQIcon.On
                )
                self.complete_icon.setPixmap(pixmap)
        else:
            print("图标下载失败，使用默认图标")
            self.app_icon = QIcon.fromTheme("application-x-executable")
            self.setWindowIcon(self.app_icon)

    def init_stacked_widget(self):
        """创建分步容器"""
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QVBoxLayout(self.central_widget)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(20)

        # 1. 顶部Logo区域
        self.logo_layout = QHBoxLayout()
        self.logo_label = QLabel()
        self.logo_label.setFixedSize(40, 40)  # 固定Logo大小
        
        # 初始显示默认图标，下载完成后会更新
        if self.app_icon.isNull():
            palette = QPalette()
            palette.setColor(QPalette.Background, QColor("#1E88E5"))
            self.logo_label.setAutoFillBackground(True)
            self.logo_label.setPalette(palette)
        else:
            pixmap = self.app_icon.pixmap(
                self.logo_label.width(), 
                self.logo_label.height()
            )
            self.logo_label.setPixmap(pixmap)
        
        self.app_name_label = QLabel("Easy UI")
        self.app_name_label.setStyleSheet("font-size: 16pt; font-weight: bold; color: #1E88E5;")
        self.logo_layout.addWidget(self.logo_label)
        self.logo_layout.addWidget(self.app_name_label)
        self.logo_layout.addStretch()
        self.main_layout.addLayout(self.logo_layout)

        # 2. 分步内容容器
        self.stacked_widget = QStackedWidget()
        self.main_layout.addWidget(self.stacked_widget, 1)  # 占主要空间

        # 3. 底部按钮区域
        self.btn_layout = QHBoxLayout()
        self.btn_layout.setSpacing(10)
        self.main_layout.addLayout(self.btn_layout)

        # 初始化各页面
        self.init_welcome_page()
        self.init_license_page()
        self.init_component_page()
        self.init_progress_page()
        self.init_complete_page()

        # 默认显示欢迎页
        self.stacked_widget.setCurrentIndex(0)
        self.update_buttons_by_page(0)

    # --------------------------- 页面1：欢迎页 ---------------------------
    def init_welcome_page(self):
        self.welcome_page = QWidget()
        self.welcome_layout = QVBoxLayout(self.welcome_page)
        self.welcome_layout.setAlignment(Qt.AlignCenter)
        self.welcome_layout.setSpacing(30)

        # 标题和副标题
        self.welcome_title = QLabel("欢迎使用 Easy UI 安装程序")
        self.welcome_title.setObjectName("TitleLabel")
        self.welcome_title.setAlignment(Qt.AlignCenter)
        
        self.welcome_subtitle = QLabel("本程序将引导您完成 Easy UI 的安装，预计耗时2-5分钟")
        self.welcome_subtitle.setObjectName("SubtitleLabel")
        self.welcome_subtitle.setAlignment(Qt.AlignCenter)

        # 系统要求提示
        self.system_require_label = QLabel("""
系统要求：
• Windows 10 及以上版本（64位）
• 至少 100MB 可用磁盘空间
• 稳定的网络连接（用于下载组件）
        """)
        self.system_require_label.setObjectName("SubtitleLabel")
        self.system_require_label.setAlignment(Qt.AlignLeft)

        self.welcome_layout.addWidget(self.welcome_title)
        self.welcome_layout.addWidget(self.welcome_subtitle)
        self.welcome_layout.addWidget(self.system_require_label)
        self.stacked_widget.addWidget(self.welcome_page)

    # --------------------------- 页面2：许可协议（可滚动版本） ---------------------------
    def init_license_page(self):
        self.license_page = QWidget()
        self.license_layout = QVBoxLayout(self.license_page)
        self.license_layout.setSpacing(20)

        # 标题
        self.license_title = QLabel("软件许可协议")
        self.license_title.setObjectName("TitleLabel")
        self.license_layout.addWidget(self.license_title)

        # 协议内容面板（带滚动功能）
        self.license_frame = QFrame()
        self.license_frame.setObjectName("CardFrame")
        self.license_frame.setFixedHeight(250)
        self.license_inner_layout = QVBoxLayout(self.license_frame)
        
        # 添加滚动区域
        self.license_scroll = QScrollArea()
        self.license_scroll.setWidgetResizable(True)
        self.license_scroll_content = QWidget()
        self.license_scroll_layout = QVBoxLayout(self.license_scroll_content)
        
        # 协议文本
        self.license_text = QTextEdit()
        self.license_text.setReadOnly(True)
        self.license_text.setText("""
Easy UI 软件许可协议

1. 许可范围
本软件仅供个人非商业使用，禁止未经授权用于商业用途、盈利活动或非法行为。

2. 用户权利
• 免费使用软件的全部功能及更新服务
• 在许可范围内修改个人使用的软件副本
• 获得软件相关的技术支持（限非商业用途）

3. 用户义务
• 不得传播经过篡改、破解或植入恶意代码的软件版本
• 不得利用软件侵犯他人知识产权、隐私或其他合法权益
• 不得违反国家法律法规及相关政策使用软件

4. 免责声明
• 软件按“现状”提供，开发者不保证无故障运行或完全满足用户需求
• 开发者不对软件使用过程中产生的任何直接或间接损失承担责任
• 因用户违反本协议导致的法律风险，由用户自行承担

5. 协议生效与终止
• 用户点击“同意”即表示完全接受本协议所有条款
• 若用户违反本协议，开发者有权终止其使用许可
        """)
        self.license_scroll_layout.addWidget(self.license_text)
        self.license_scroll.setWidget(self.license_scroll_content)
        
        self.license_inner_layout.addWidget(self.license_scroll)
        self.license_layout.addWidget(self.license_frame)

        # 同意勾选框
        self.agree_check = QCheckBox("我已阅读并同意上述许可协议")
        self.agree_check.setObjectName("SubtitleLabel")
        self.agree_check.setChecked(False)
        self.license_layout.addWidget(self.agree_check)

        self.license_layout.addStretch()
        self.stacked_widget.addWidget(self.license_page)

    # --------------------------- 页面3：组件选择 ---------------------------
    def init_component_page(self):
        self.component_page = QWidget()
        self.component_layout = QVBoxLayout(self.component_page)
        self.component_layout.setSpacing(20)

        # 标题和副标题
        self.component_title = QLabel("选择安装组件")
        self.component_title.setObjectName("TitleLabel")
        self.component_layout.addWidget(self.component_title)
        
        self.component_subtitle = QLabel("默认安装所有组件，您可根据需求取消不需要的选项")
        self.component_subtitle.setObjectName("SubtitleLabel")
        self.component_layout.addWidget(self.component_subtitle)

        # 组件选择面板
        self.component_frame = QFrame()
        self.component_frame.setObjectName("CardFrame")
        self.component_inner_layout = QVBoxLayout(self.component_frame)
        self.component_inner_layout.setContentsMargins(20, 20, 20, 20)
        self.component_inner_layout.setSpacing(25)

        # 解释器组件
        self.interpreter_group = QWidget()
        self.interpreter_group_layout = QVBoxLayout(self.interpreter_group)
        self.interpreter_group_layout.setSpacing(10)
        
        self.interpreter_check = QCheckBox(f"{self.resources['interpreter']['name']} (必需组件)")
        self.interpreter_check.setObjectName("SubtitleLabel")
        self.interpreter_check.setChecked(True)
        self.interpreter_check.setEnabled(False)
        self.interpreter_group_layout.addWidget(self.interpreter_check)
        
        # 解释器路径选择
        self.interpreter_path_layout = QHBoxLayout()
        self.interpreter_path_label = QLabel("安装位置：")
        self.interpreter_path_label.setObjectName("SubtitleLabel")
        self.interpreter_path = QLineEdit(self.resources['interpreter']['default_path'])
        self.interpreter_browse_btn = QPushButton("浏览...")
        self.interpreter_browse_btn.setObjectName("SecondaryBtn")
        self.interpreter_browse_btn.clicked.connect(lambda: self.browse_path("interpreter"))
        
        self.interpreter_path_layout.addWidget(self.interpreter_path_label)
        self.interpreter_path_layout.addWidget(self.interpreter_path, 1)
        self.interpreter_path_layout.addWidget(self.interpreter_browse_btn)
        self.interpreter_group_layout.addLayout(self.interpreter_path_layout)
        self.component_inner_layout.addWidget(self.interpreter_group)

        # 编辑器组件
        self.editor_group = QWidget()
        self.editor_group_layout = QVBoxLayout(self.editor_group)
        self.editor_group_layout.setSpacing(10)
        
        self.editor_check = QCheckBox(f"{self.resources['editor']['name']} (推荐组件)")
        self.editor_check.setObjectName("SubtitleLabel")
        self.editor_check.setChecked(True)
        self.editor_group_layout.addWidget(self.editor_check)
        
        # 编辑器路径选择
        self.editor_path_layout = QHBoxLayout()
        self.editor_path_label = QLabel("安装位置：")
        self.editor_path_label.setObjectName("SubtitleLabel")
        self.editor_path = QLineEdit(self.resources['editor']['default_path'])
        self.editor_browse_btn = QPushButton("浏览...")
        self.editor_browse_btn.setObjectName("SecondaryBtn")
        self.editor_browse_btn.clicked.connect(lambda: self.browse_path("editor"))
        
        self.editor_path_layout.addWidget(self.editor_path_label)
        self.editor_path_layout.addWidget(self.editor_path, 1)
        self.editor_path_layout.addWidget(self.editor_browse_btn)
        self.editor_group_layout.addLayout(self.editor_path_layout)
        self.component_inner_layout.addWidget(self.editor_group)

        self.component_layout.addWidget(self.component_frame)
        self.stacked_widget.addWidget(self.component_page)

    # --------------------------- 页面4：安装进度 ---------------------------
    def init_progress_page(self):
        self.progress_page = QWidget()
        self.progress_layout = QVBoxLayout(self.progress_page)
        self.progress_layout.setSpacing(20)

        # 标题
        self.progress_title = QLabel("正在安装")
        self.progress_title.setObjectName("TitleLabel")
        self.progress_layout.addWidget(self.progress_title)

        # 进度面板
        self.progress_frame = QFrame()
        self.progress_frame.setObjectName("CardFrame")
        self.progress_inner_layout = QVBoxLayout(self.progress_frame)
        self.progress_inner_layout.setContentsMargins(20, 20, 20, 20)
        self.progress_inner_layout.setSpacing(15)

        # 当前任务提示
        self.current_task_label = QLabel("准备下载安装组件...")
        self.current_task_label.setObjectName("SubtitleLabel")
        self.progress_inner_layout.addWidget(self.current_task_label)

        # 总体进度条
        self.overall_progress_bar = QProgressBar()
        self.overall_progress_bar.setValue(0)
        self.progress_inner_layout.addWidget(self.overall_progress_bar)

        # 进度详情
        self.progress_detail_layout = QHBoxLayout()
        self.speed_label = QLabel("速度：0.00 MB/s")
        self.speed_label.setObjectName("SubtitleLabel")
        self.time_remaining_label = QLabel("剩余时间：--:--")
        self.time_remaining_label.setObjectName("SubtitleLabel")
        self.progress_detail_layout.addWidget(self.speed_label)
        self.progress_detail_layout.addStretch()
        self.progress_detail_layout.addWidget(self.time_remaining_label)
        self.progress_inner_layout.addLayout(self.progress_detail_layout)

        self.progress_layout.addWidget(self.progress_frame)
        self.stacked_widget.addWidget(self.progress_page)

    # --------------------------- 页面5：安装完成 ---------------------------
    def init_complete_page(self):
        self.complete_page = QWidget()
        self.complete_layout = QVBoxLayout(self.complete_page)
        self.complete_layout.setSpacing(25)
        self.complete_layout.setAlignment(Qt.AlignCenter)

        # 完成图标
        self.complete_icon = QLabel()
        self.complete_icon.setFixedSize(80, 80)
        
        # 初始显示默认图标
        if self.app_icon.isNull():
            palette = QPalette()
            palette.setColor(QPalette.Background, QColor("#4CAF50"))
            self.complete_icon.setAutoFillBackground(True)
            self.complete_icon.setPalette(palette)
            self.complete_icon.setStyleSheet("border-radius: 40px;")
        else:
            pixmap = self.app_icon.pixmap(
                self.complete_icon.width(), 
                self.complete_icon.height()
            )
            self.complete_icon.setPixmap(pixmap)
        
        self.complete_layout.addWidget(self.complete_icon, alignment=Qt.AlignCenter)

        # 完成标题
        self.complete_title = QLabel("安装完成！")
        self.complete_title.setObjectName("TitleLabel")
        self.complete_layout.addWidget(self.complete_title, alignment=Qt.AlignCenter)

        # 完成提示
        self.complete_subtitle = QLabel("Easy UI 已成功安装到您的电脑中")
        self.complete_subtitle.setObjectName("SubtitleLabel")
        self.complete_layout.addWidget(self.complete_subtitle, alignment=Qt.AlignCenter)

        # 后续操作选项
        self.complete_options_layout = QVBoxLayout()
        self.run_check = QCheckBox("立即运行 Easy UI 编辑器")
        self.run_check.setObjectName("SubtitleLabel")
        self.run_check.setChecked(True)
        
        self.desktop_shortcut_check = QCheckBox("创建桌面快捷方式")
        self.desktop_shortcut_check.setObjectName("SubtitleLabel")
        self.desktop_shortcut_check.setChecked(True)
        
        self.complete_options_layout.addWidget(self.run_check)
        self.complete_options_layout.addWidget(self.desktop_shortcut_check)
        self.complete_layout.addLayout(self.complete_options_layout)

        self.stacked_widget.addWidget(self.complete_page)

    # --------------------------- 核心交互逻辑 ---------------------------
    def update_buttons_by_page(self, page_index):
        """根据当前页面更新底部按钮"""
        # 清空现有按钮
        for i in range(self.btn_layout.count()):
            widget = self.btn_layout.itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 根据页面索引添加按钮
        if page_index == 0:  # 欢迎页：仅“下一步”
            self.next_btn = QPushButton("下一步")
            self.next_btn.setObjectName("PrimaryBtn")
            self.next_btn.clicked.connect(lambda: self.switch_page(1))
            self.btn_layout.addStretch()
            self.btn_layout.addWidget(self.next_btn)

        elif page_index == 1:  # 许可协议：“上一步”+“下一步”
            self.prev_btn = QPushButton("上一步")
            self.prev_btn.setObjectName("SecondaryBtn")
            self.prev_btn.clicked.connect(lambda: self.switch_page(0))
            
            self.next_btn = QPushButton("下一步")
            self.next_btn.setObjectName("PrimaryBtn")
            self.next_btn.setEnabled(False)
            self.next_btn.clicked.connect(lambda: self.switch_page(2))
            
            # 勾选框联动按钮状态
            self.agree_check.stateChanged.connect(
                lambda state: self.next_btn.setEnabled(state == Qt.Checked)
            )
            
            self.btn_layout.addWidget(self.prev_btn)
            self.btn_layout.addStretch()
            self.btn_layout.addWidget(self.next_btn)

        elif page_index == 2:  # 组件选择：“上一步”+“安装”
            self.prev_btn = QPushButton("上一步")
            self.prev_btn.setObjectName("SecondaryBtn")
            self.prev_btn.clicked.connect(lambda: self.switch_page(1))
            
            self.install_btn = QPushButton("开始安装")
            self.install_btn.setObjectName("PrimaryBtn")
            self.install_btn.clicked.connect(self.start_install)
            
            self.btn_layout.addWidget(self.prev_btn)
            self.btn_layout.addStretch()
            self.btn_layout.addWidget(self.install_btn)

        elif page_index == 3:  # 安装进度：“取消”
            self.cancel_btn = QPushButton("取消安装")
            self.cancel_btn.setObjectName("SecondaryBtn")
            self.cancel_btn.clicked.connect(self.cancel_install)
            self.btn_layout.addStretch()
            self.btn_layout.addWidget(self.cancel_btn)

        elif page_index == 4:  # 安装完成：“完成”
            self.finish_btn = QPushButton("完成")
            self.finish_btn.setObjectName("PrimaryBtn")
            self.finish_btn.clicked.connect(self.finish_install)
            self.btn_layout.addStretch()
            self.btn_layout.addWidget(self.finish_btn)

    def switch_page(self, target_index):
        """切换页面并更新按钮"""
        self.stacked_widget.setCurrentIndex(target_index)
        self.update_buttons_by_page(target_index)

    def browse_path(self, resource_type):
        """浏览选择安装路径"""
        resource = self.resources[resource_type]
        default_path = self.interpreter_path.text() if resource_type == "interpreter" else self.editor_path.text()
        
        # 选择文件保存路径
        file_path, _ = QFileDialog.getSaveFileName(
            self, f"选择{resource['name']}安装位置",
            default_path,
            "可执行文件 (*.exe);;所有文件 (*)"
        )
        
        if file_path:
            if not file_path.endswith(".exe"):
                file_path += ".exe"
            if resource_type == "interpreter":
                self.interpreter_path.setText(file_path)
                # 联动更新编辑器路径
                editor_path = os.path.join(os.path.dirname(file_path), "EasyUI_Editor.exe")
                self.editor_path.setText(editor_path)
            else:
                self.editor_path.setText(file_path)

    def start_install(self):
        """验证组件并开始安装"""
        # 构建下载队列
        self.download_queue = []
        if self.interpreter_check.isChecked():
            inter_path = self.interpreter_path.text().strip()
            if not inter_path.endswith(".exe"):
                inter_path += ".exe"
            self.download_queue.append((
                self.resources['interpreter']['url'],
                inter_path,
                self.resources['interpreter']['name']
            ))
        
        if self.editor_check.isChecked():
            edit_path = self.editor_path.text().strip()
            if not edit_path.endswith(".exe"):
                edit_path += ".exe"
            self.download_queue.append((
                self.resources['editor']['url'],
                edit_path,
                self.resources['editor']['name']
            ))

        # 验证路径权限
        if not self.verify_path_permission():
            return

        # 跳转到进度页并启动下载
        self.switch_page(3)
        self.download_manager = MultiFileDownloader(self.download_queue)
        self.download_manager.overall_progress.connect(self.overall_progress_bar.setValue)
        self.download_manager.file_progress.connect(self.update_progress_detail)
        self.download_manager.time_remaining.connect(self.time_remaining_label.setText)
        self.download_manager.file_finished.connect(self.on_file_finished)
        self.download_manager.all_finished.connect(self.on_all_finished)
        self.download_manager.start()

    def verify_path_permission(self):
        """验证安装路径是否有写入权限"""
        for url, path, name in self.download_queue:
            try:
                test_dir = os.path.dirname(path)
                if not os.path.exists(test_dir):
                    os.makedirs(test_dir)
                
                # 测试写入
                test_file = os.path.join(test_dir, "test_permission.tmp")
                with open(test_file, 'w') as f:
                    f.write("test")
                os.remove(test_file)
            except Exception as e:
                QMessageBox.warning(
                    self, "路径权限错误",
                    f"无法写入{name}的安装路径：\n{str(e)}\n建议选择其他目录（如桌面）重试。"
                )
                return False
        return True

    def update_progress_detail(self, progress, file_name, speed):
        """更新进度详情"""
        self.current_task_label.setText(f"正在安装 {file_name}... ({progress}%)")
        self.speed_label.setText(f"速度：{speed:.2f} MB/s")

    def on_file_finished(self, success, message, file_name):
        """单个文件安装完成回调"""
        if not success:
            QMessageBox.warning(self, f"{file_name}安装失败", message)

    def on_all_finished(self):
        """所有文件安装完成"""
        # 创建桌面快捷方式（如果勾选）
        if self.desktop_shortcut_check.isChecked():
            self.create_desktop_shortcut()
        self.switch_page(4)

    def create_desktop_shortcut(self):
        """创建桌面快捷方式（提供多种方案确保成功）"""
        editor_path = self.editor_path.text()
        if not os.path.exists(editor_path):
            QMessageBox.warning(self, "创建失败", "未找到Easy UI编辑器可执行文件，无法创建快捷方式")
            return

        # 方案1：使用win32com.client（最佳方案）
        try:
            import pythoncom
            import win32com.client
            from winshell import desktop
            
            # 初始化COM
            pythoncom.CoInitialize()
            
            # 获取桌面路径
            desktop_path = desktop()
            shortcut_path = os.path.join(desktop_path, "Easy UI 编辑器.lnk")
            
            # 保存图标到本地临时文件（确保图标可用）
            icon_temp_path = os.path.join(os.path.dirname(editor_path), "eui_icon.ico")
            if self.icon_data:
                with open(icon_temp_path, 'wb') as f:
                    f.write(self.icon_data)
            
            # 创建快捷方式
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(shortcut_path)
            shortcut.TargetPath = editor_path
            shortcut.WorkingDirectory = os.path.dirname(editor_path)
            shortcut.Description = "Easy UI 编辑器"
            shortcut.Hotkey = "Ctrl+Alt+E"  # 添加快捷键
            
            # 设置图标
            if os.path.exists(icon_temp_path):
                shortcut.IconLocation = icon_temp_path
            else:
                shortcut.IconLocation = editor_path  # 使用程序自身图标
            
            shortcut.save()
            pythoncom.CoUninitialize()
            print("方案1：使用win32com创建快捷方式成功")
            return
            
        except ImportError as e:
            print(f"方案1不可用：缺少依赖 {str(e)}")
        except Exception as e:
            print(f"方案1失败：{str(e)}")

        # 方案2：使用PowerShell命令（备用方案）
        try:
            import subprocess
            import tempfile
            
            # 获取桌面路径
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            shortcut_path = os.path.join(desktop_path, "Easy UI 编辑器.lnk")
            
            # 保存图标到临时文件
            icon_temp_path = os.path.join(tempfile.gettempdir(), "eui_icon.ico")
            if self.icon_data:
                with open(icon_temp_path, 'wb') as f:
                    f.write(self.icon_data)
            
            # PowerShell命令创建快捷方式
            ps_command = f'''
            $WshShell = New-Object -ComObject WScript.Shell
            $shortcut = $WshShell.CreateShortcut("{shortcut_path}")
            $shortcut.TargetPath = "{editor_path}"
            $shortcut.WorkingDirectory = "{os.path.dirname(editor_path)}"
            $shortcut.Description = "Easy UI 编辑器"
            {f'$shortcut.IconLocation = "{icon_temp_path}"' if os.path.exists(icon_temp_path) else ''}
            $shortcut.Save()
            '''
            
            # 执行PowerShell命令
            subprocess.run(
                ["powershell", "-Command", ps_command],
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("方案2：使用PowerShell创建快捷方式成功")
            return
            
        except Exception as e:
            print(f"方案2失败：{str(e)}")

        # 方案3：创建批处理文件作为最后的备用方案
        try:
            desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
            bat_path = os.path.join(desktop_path, "启动 Easy UI 编辑器.bat")
            
            # 创建批处理文件
            with open(bat_path, 'w', encoding='utf-8') as f:
                f.write(f'@echo off\nstart "" "{editor_path}"\nexit')
            
            # 设置文件属性为隐藏（可选）
            if os.name == 'nt':
                subprocess.run(['attrib', '+H', bat_path], check=True)
                
            print("方案3：创建批处理文件作为快捷方式成功")
            QMessageBox.information(
                self, "快捷方式创建成功",
                "已在桌面创建启动批处理文件，双击即可运行Easy UI编辑器"
            )
            return
            
        except Exception as e:
            print(f"方案3失败：{str(e)}")

        # 所有方案都失败时
        QMessageBox.warning(
            self, "创建失败",
            "无法创建桌面快捷方式，您可以手动创建：\n"
            f"1. 找到文件：{editor_path}\n"
            "2. 右键点击文件，选择'发送到'->'桌面快捷方式'"
        )

    def cancel_install(self):
        """取消安装"""
        if self.download_manager and self.download_manager.isRunning():
            confirm = QMessageBox.question(
                self, "确认取消",
                "取消安装将终止当前下载，已下载的文件可能不完整，是否继续？",
                QMessageBox.Yes | QMessageBox.No
            )
            if confirm == QMessageBox.Yes:
                self.download_manager.stop()
                self.switch_page(2)  # 回到组件选择页

    def finish_install(self):
        """完成安装"""
        # 运行程序（如果勾选）
        if self.run_check.isChecked():
            editor_path = self.editor_path.text()
            if os.path.exists(editor_path):
                os.startfile(editor_path)
        # 关闭安装程序
        self.close()


# 程序入口
if __name__ == "__main__":
    # 先设置高DPI属性
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
    
    # 确保中文显示正常
    app = QApplication(sys.argv)
    app.setFont(QFont("微软雅黑", 9))
        
    window = EasyUIInstaller()
    window.show()
    
    sys.exit(app.exec_())
    