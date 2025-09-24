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
        self.setWindowTitle("Project Manager - Welcome")
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
        self.btn_new = QPushButton("新建项目")
        self.btn_new.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_FileDialogNewFolder', 41)))
        self.btn_new.setIconSize(QSize(20, 20))
        self.btn_new.setFixedWidth(120)
        self.btn_new.setFixedHeight(40)

        # 打开项目按钮
        self.btn_open = QPushButton("打开项目")
        self.btn_open.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_DirOpenIcon', 4)))
        self.btn_open.setIconSize(QSize(20, 20))
        self.btn_open.setFixedWidth(120)
        self.btn_open.setFixedHeight(40)

        top_layout.addWidget(self.btn_new)
        top_layout.addWidget(self.btn_open)
        top_layout.addStretch()  # 右侧留白

        # ===== 中间内容区域 =====
        # 标题
        self.lbl_recent = QLabel("最近打开的项目")
        self.lbl_recent.setFont(QFont("Arial", 16, QFont.Bold))

        # 最近项目列表
        self.list_recent = QListWidget()
        self.list_recent.setFixedHeight(300)
        self.list_recent.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁止编辑
        self.list_recent.itemClicked.connect(self.handle_recent_project_click)

        # 填充最近项目列表
        self.populate_recent_projects()

        # ===== 底部区域 =====
        # 状态栏
        self.status_bar = QStatusBar()
        self.status_bar.showMessage("Version 1.0.0", 5000)
        self.status_bar.setStyleSheet("QStatusBar {background-color: #f5f5f5;}")
        self.setStatusBar(self.status_bar)

        # 将各部分添加到主布局
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.lbl_recent)
        main_layout.addWidget(self.list_recent)
        main_layout.addStretch()  # 中间留白

        # 连接信号
        self.btn_new.clicked.connect(self.create_new_project)
        self.btn_open.clicked.connect(self.open_existing_project)

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
            QPushButton#btn_open {
                background-color: #f3f3f3;
                color: #333;
                border: 1px solid #d0d0d0;
            }
            QPushButton#btn_open:hover {
                background-color: #e6e6e6;
                border-color: #b8b8b8;
            }
            QPushButton#btn_open:pressed {
                background-color: #d9d9d9;
                border-color: #a0a0a0;
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
            self.list_recent.addItem("暂无最近打开的项目")
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
            "选择新项目位置",
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

        except Exception as e:
            QMessageBox.critical(
                self,
                "目录不可用",
                f"所选目录不可用: {str(e)}\n请选择其他目录。"
            )

    def open_existing_project(self) -> None:
        """处理打开现有项目操作"""
        # 打开目录选择对话框
        directory = QFileDialog.getExistingDirectory(
            self,
            "选择项目目录",
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
                "项目无效",
                "所选项目路径无效或不存在。\n请选择其他项目。"
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


