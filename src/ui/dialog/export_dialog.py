import os
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel, QComboBox,
    QLineEdit, QPushButton, QProgressBar, QFileDialog, QFormLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal


class ExportDialog(QDialog):
    # 自定义信号
    export_requested = pyqtSignal(str, str)  # 导出格式, 导出路径

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("导出标注数据")
        self.setMinimumWidth(500)
        self.export_path = ""  # 存储导出路径
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """初始化界面组件"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ==================== 导出格式选择区域 ====================
        format_group = QGroupBox("导出设置")
        format_layout = QFormLayout()
        format_layout.setSpacing(10)

        # 导出格式选择
        self.format_combo = QComboBox()
        self.format_combo.addItems(["COCO", "YOLO", "Pascal VOC", "CSV", "TFRecord"])
        format_layout.addRow("导出格式:", self.format_combo)

        # 导出路径选择
        self.path_edit = QLineEdit()
        self.path_edit.setReadOnly(True)
        self.path_edit.setPlaceholderText("请选择导出路径")
        self.path_edit.setStyleSheet("background-color: #2D2D30; padding: 6px;")

        self.browse_button = QPushButton("浏览...")
        self.browse_button.setFixedWidth(80)
        self.browse_button.setStyleSheet(
            "QPushButton { background-color: #3F3F46; padding: 6px; }"
            "QPushButton:hover { background-color: #5C5C5C; }"
        )

        # 路径选择布局
        path_layout = QHBoxLayout()
        path_layout.addWidget(self.path_edit)
        path_layout.addWidget(self.browse_button)
        format_layout.addRow("导出路径:", path_layout)

        format_group.setLayout(format_layout)
        main_layout.addWidget(format_group)

        # ==================== 进度条区域 ====================
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3F3F46;
                border-radius: 4px;
                text-align: center;
                background-color: #2D2D30;
            }
            QProgressBar::chunk {
                background-color: #0078D7;
                border-radius: 2px;
            }
        """)
        main_layout.addWidget(self.progress_bar)

        # ==================== 按钮区域 ====================
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setStyleSheet(
            "QPushButton { background-color: #5C5C5C; color: white; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #4A4A4A; }"
        )

        self.export_button = QPushButton("开始导出")
        self.export_button.setMinimumWidth(100)
        self.export_button.setStyleSheet(
            "QPushButton { background-color: #0078D7; color: white; padding: 8px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #106EBE; }"
            "QPushButton:disabled { background-color: #3F3F46; }"
        )
        self.export_button.setEnabled(False)  # 初始禁用，直到选择路径

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.export_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def connect_signals(self):
        """连接信号与槽函数"""
        self.cancel_button.clicked.connect(self.reject)
        self.export_button.clicked.connect(self.on_export_clicked)
        self.browse_button.clicked.connect(self.browse_export_path)

    def browse_export_path(self):
        """打开文件对话框选择导出路径"""
        # 使用QFileDialog选择目录[7](@ref)
        path = QFileDialog.getExistingDirectory(
            self,
            "选择导出目录",
            os.path.expanduser("~"),
            QFileDialog.ShowDirsOnly | QFileDialog.DontResolveSymlinks
        )

        if path:
            self.export_path = path
            self.path_edit.setText(path)
            self.export_button.setEnabled(True)  # 启用导出按钮

    def on_export_clicked(self):
        """处理导出按钮点击事件"""
        if not self.export_path:
            return

        export_format = self.format_combo.currentText()
        self.export_requested.emit(export_format, self.export_path)

        # 更新UI状态
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("正在准备导出...")
        self.export_button.setEnabled(False)
        self.cancel_button.setEnabled(False)

    def update_progress(self, value, message=None):
        """更新进度条状态"""
        self.progress_bar.setValue(value)
        if message:
            self.progress_bar.setFormat(message)

    def on_export_completed(self, success, message):
        """导出完成处理"""
        if success:
            self.progress_bar.setFormat(f"导出成功! {message}")
            self.accept()  # 自动关闭对话框
        else:
            self.progress_bar.setFormat(f"导出失败: {message}")
            self.export_button.setEnabled(True)
            self.cancel_button.setEnabled(True)
