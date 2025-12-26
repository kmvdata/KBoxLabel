# welcome_screen.py
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import Qt, QSize, pyqtSignal
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QListWidget, QListWidgetItem, QLabel, QStatusBar,
    QFileDialog, QMessageBox, QAbstractItemView, QStyle
)

from src.core.ksettings import KSettings
from src.core.i18n.language_manager import tr, LanguageManager
from PyQt5.QtCore import pyqtSlot


class WelcomeScreen(QMainWindow):
    """项目管理器欢迎界面，用于新建、打开项目和显示最近项目列表"""

    # 自定义信号：当项目被打开时触发，携带项目路径参数
    projectOpened = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        """
        初始化欢迎界面

        Args:
            parent: 父窗口部件（可选）
        """
        super().__init__(parent)
        self.list_recent = None
        self.lbl_recent = None
        self.btn_new = None
        self.btn_open_selected = None  # 添加打开选中项目的按钮
        self.setWindowTitle(tr("welcome_window_title"))
        self.setFixedSize(800, 600)  # 固定窗口尺寸

        # 存储最近项目路径列表
        self.recent_projects: List[str] = []

        # 创建Settings实例
        self.settings = KSettings()

        # 加载最近项目数据
        self.load_recent_projects()

        # 设置UI
        self.setup_ui()

        # 应用样式表
        self.apply_stylesheet()
        
        # 连接语言变更信号
        LanguageManager.instance().language_changed.connect(self.on_language_changed)
    
    @pyqtSlot(str)
    def on_language_changed(self, language: str):
        """处理语言变更事件"""
        # 更新窗口标题
        self.setWindowTitle(tr("welcome_window_title"))
        
        # 更新按钮文本
        self.btn_new.setText(tr("new_project"))
        self.btn_open.setText(tr("open_project"))
        
        # 更新标签文本
        self.lbl_recent.setText(tr("recent_projects"))
        self.btn_open_selected.setText(tr("open"))
        
        # 更新状态栏文本
        self.status_bar.showMessage(tr("status_ready"), 5000)
        
        # 重新填充最近项目列表（以更新任何依赖于语言的文本）
        self.populate_recent_projects()

    def setup_ui(self) -> None:
        """设置用户界面布局和组件"""
        # 主窗口中心部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主垂直布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(40, 30, 40, 30)
        main_layout.setSpacing(20)

        # ===== 顶部操作区域 =====
        top_layout = QHBoxLayout()
        top_layout.setSpacing(20)

        # 新建项目按钮
        self.btn_new = QPushButton(tr("new_project"))
        self.btn_new.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogNewFolder', 41)))
        self.btn_new.setIconSize(QSize(20, 20))
        self.btn_new.setFixedWidth(120)
        self.btn_new.setFixedHeight(40)

        # 打开项目按钮
        self.btn_open = QPushButton(tr("open_project"))
        self.btn_open.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DirOpenIcon', 4)))
        self.btn_open.setIconSize(QSize(20, 20))
        self.btn_open.setFixedWidth(120)
        self.btn_open.setFixedHeight(40)

        top_layout.addWidget(self.btn_new)
        top_layout.addWidget(self.btn_open)
        top_layout.addStretch()  # 右侧留白

        # ===== 中间内容区域 =====
        # 标题
        self.lbl_recent = QLabel(tr("recent_projects"))
        self.lbl_recent.setFont(QFont("Arial", 16, QFont.Bold))

        # 最近项目列表
        self.list_recent = QListWidget()
        self.list_recent.setFixedHeight(300)
        self.list_recent.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁止编辑
        self.list_recent.itemClicked.connect(self.handle_recent_project_click)
        # 连接双击信号
        self.list_recent.itemDoubleClicked.connect(self.handle_recent_project_double_click)

        # 填充最近项目列表
        self.populate_recent_projects()

        # ===== 底部区域 =====
        # 创建底部按钮布局
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        
        # 添加打开选中项目的按钮
        self.btn_open_selected = QPushButton(tr("open"))
        self.btn_open_selected.setEnabled(False)  # 默认禁用
        self.btn_open_selected.setFixedWidth(100)
        self.btn_open_selected.setFixedHeight(35)
        self.btn_open_selected.clicked.connect(self.open_selected_project)
        bottom_layout.addWidget(self.btn_open_selected)
        
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage(tr("status_ready"), 5000)
        self.status_bar.setStyleSheet("QStatusBar {background-color: #f5f5f5;}")
        self.setStatusBar(self.status_bar)

        # 将各部分添加到主布局
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.lbl_recent)
        main_layout.addWidget(self.list_recent)
        main_layout.addLayout(bottom_layout)  # 添加底部按钮布局
        main_layout.addStretch()  # 中间留白

        # 连接信号
        self.btn_new.clicked.connect(self.create_new_project)
        self.btn_open.clicked.connect(self.open_existing_project)
        # 连接列表选择变化信号
        self.list_recent.itemSelectionChanged.connect(self.on_item_selection_changed)

    def apply_stylesheet(self) -> None:
        """应用样式表，设置界面外观"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QPushButton {
                font-size: 14px;
                border-radius: 4px;
                padding: 5px 10px;
            }
            QPushButton#btn_new {
                background-color: #0078d7;
                color: white;
                border: none;
            }
            QPushButton#btn_new:hover {
                background-color: #006cc1;
            }
            QPushButton#btn_new:pressed {
                background-color: #005a9e;
            }
            QPushButton#btn_open, QPushButton#btn_open_selected {
                background-color: #f3f3f3;
                color: #333;
                border: 1px solid #d0d0d0;
            }
            QPushButton#btn_open:hover, QPushButton#btn_open_selected:hover {
                background-color: #e6e6e6;
                border-color: #b8b8b8;
            }
            QPushButton#btn_open:pressed, QPushButton#btn_open_selected:pressed {
                background-color: #d9d9d9;
                border-color: #a0a0a0;
            }
            QPushButton#btn_open_selected:disabled {
                background-color: #f3f3f3;
                color: #999;
                border: 1px solid #ddd;
            }
            QLabel {
                color: #333;
            }
            QListWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
                background-color: white;
            }
            QListWidget::item {
                height: 40px;
                padding: 5px 10px;
            }
            QListWidget::item:hover {
                background-color: #f0f7ff;
            }
            QListWidget::item:selected {
                background-color: #d6e8fb;
                color: #000;
            }
        """)

        # 为按钮设置对象名称以便样式表识别
        self.btn_new.setObjectName("btn_new")
        self.btn_open.setObjectName("btn_open")
        self.btn_open_selected.setObjectName("btn_open_selected")

    def load_recent_projects(self) -> None:
        """从Settings加载最近项目列表"""
        self.recent_projects = []
        size = self.settings.beginReadArray("recentProjects")

        for i in range(size):
            self.settings.setArrayIndex(i)
            path = self.settings.value("path", "")
            if path:
                self.recent_projects.append(path)

        self.settings.endArray()

    def save_recent_projects(self) -> None:
        """将最近项目保存到设置文件"""
        self.settings.beginWriteArray("recentProjects")
        for i, path in enumerate(self.recent_projects):
            self.settings.setArrayIndex(i)
            self.settings.setValue("path", path)
        self.settings.endArray()
        self.settings.sync()

    def add_recent_project(self, project_path: str) -> None:
        """
        添加项目到最近项目列表（自动去重并按添加顺序排序）

        Args:
            project_path: 项目路径
        """
        # 规范化路径
        normalized_path = str(Path(project_path).resolve())

        # 检查是否已存在
        if normalized_path in self.recent_projects:
            # 如果已存在，移除旧条目
            self.recent_projects.remove(normalized_path)

        # 添加新条目到开头
        self.recent_projects.insert(0, normalized_path)

        # 限制最多10个项目
        self.recent_projects = self.recent_projects[:10]

        # 保存并更新UI
        self.save_recent_projects()
        self.populate_recent_projects()

    def populate_recent_projects(self) -> None:
        """填充最近项目列表到QListWidget"""
        self.list_recent.clear()

        if not self.recent_projects:
            self.list_recent.addItem(tr("no_recent_projects"))
            self.list_recent.item(0).setFlags(Qt.NoItemFlags)  # 禁用选择
            return

        for project_path in self.recent_projects:
            # 提取项目名称（目录名）
            project_name = Path(project_path).name

            # 格式化显示文本（处理长路径）
            display_path = str(Path(project_path))
            if len(display_path) > 60:
                display_path = display_path[:25] + "..." + display_path[-30:]

            # 创建列表项
            item = QListWidgetItem(f"{project_name} - {display_path}")
            item.setToolTip(project_path)  # 完整路径作为工具提示
            self.list_recent.addItem(item)

    def create_new_project(self) -> None:
        """处理新建项目操作"""
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("select_new_project_location"),
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not directory:
            return  # 用户取消操作

        try:
            # 验证目录是否可写
            test_file = Path(directory) / ".test_permission"
            test_file.touch()
            test_file.unlink()

            # 有效项目，添加到最近列表并打开
            self.add_recent_project(directory)
            self.open_project(directory)

        except (OSError, PermissionError) as e:
            QMessageBox.critical(
                self,
                tr("error_invalid_path"),
                tr("directory_unavailable", error=str(e))
            )

    def open_existing_project(self) -> None:
        """处理打开现有项目操作"""
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(
            self,
            tr("select_project_directory"),
            "",
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if not directory:
            return  # 用户取消操作

        # 有效项目，添加到最近列表并打开
        self.add_recent_project(directory)
        self.open_project(directory)

    def handle_recent_project_click(self, item: QListWidgetItem) -> None:
        """处理最近项目列表单击事件"""
        # 单击只选中项目，不打开
        pass

    def handle_recent_project_double_click(self, item: QListWidgetItem) -> None:
        """处理最近项目列表双击事件"""
        # 如果显示"暂无最近打开的项目"，不执行操作
        if item.text() == "暂无最近打开的项目":
            return

        # 获取对应项目路径
        index = self.list_recent.row(item)
        if index < len(self.recent_projects):
            project_path = self.recent_projects[index]
            self.open_project(project_path)

    def on_item_selection_changed(self) -> None:
        """处理列表项选择变化事件"""
        # 检查是否有选中的项目
        selected_items = self.list_recent.selectedItems()
        if selected_items and selected_items[0].text() != tr("no_recent_projects"): 
            self.btn_open_selected.setEnabled(True)
        else:
            self.btn_open_selected.setEnabled(False)

    def open_selected_project(self) -> None:
        """打开选中的项目"""
        selected_items = self.list_recent.selectedItems()
        if not selected_items:
            return
            
        item = selected_items[0]
        # 如果显示"暂无最近打开的项目"，不执行操作
        if item.text() == "暂无最近打开的项目":
            return

        # 获取对应项目路径
        index = self.list_recent.row(item)
        if index < len(self.recent_projects):
            project_path = self.recent_projects[index]
            self.open_project(project_path)

    def open_project(self, project_path: str) -> None:
        """
        打开指定项目并触发信号

        Args:
            project_path: 要打开的项目路径
        """
        # 验证项目路径
        project_dir = Path(project_path)
        if not project_dir.exists() or not project_dir.is_dir():
            QMessageBox.critical(
                self,
                tr("error_invalid_directory"),
                tr("project_invalid")
            )
            # 从最近项目列表中移除无效项目
            if project_path in self.recent_projects:
                self.recent_projects.remove(project_path)
                self.save_recent_projects()
                self.populate_recent_projects()
            return

        # 添加到最近项目列表（确保最新）
        self.add_recent_project(project_path)

        # 触发项目打开信号（由MainWindow连接处理）
        self.projectOpened.emit(project_path)

        # 关闭欢迎界面
        self.close()