# about_dialog.py
import sys
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit, QApplication
from PyQt5.QtGui import QPixmap

from src.core.i18n.language_manager import tr

class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("about_title"))
        self.setGeometry(200, 100, 500, 400)
        self.setModal(True)
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建顶部区域（logo、标题、版本号）
        top_layout = QVBoxLayout()
        top_layout.setAlignment(Qt.AlignCenter)
        
        # 加载项目logo
        icon_label = QLabel()
        logo_path = Path(__file__).parent.parent.parent / "resources" / "kmv_logo.jpg"
        if logo_path.exists():
            pixmap = QPixmap(str(logo_path))
            # 缩放图片为正方形以适应对话框
            size = 120  # 正方形大小
            scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
            # 裁剪为正方形
            cropped_pixmap = scaled_pixmap.copy(0, 0, size, size)
            icon_label.setPixmap(cropped_pixmap)
        else:
            # 如果logo不存在，使用占位符
            icon_label.setText("🔍")
            icon_label.setStyleSheet("font-size: 48px;")
        icon_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(icon_label)
        
        # 标题文本
        title_label = QLabel("KBoxLabel")
        title_label.setStyleSheet("font-size: 24px; font-weight: bold; color: #2c3e50;")
        title_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(title_label)
        
        # 版本信息
        version_label = QLabel(tr("about_version"))
        version_label.setStyleSheet("font-size: 14px; color: #7f8c8d;")
        version_label.setAlignment(Qt.AlignCenter)
        top_layout.addWidget(version_label)
        
        layout.addLayout(top_layout)
        
        # 添加分隔线
        separator = QLabel()
        separator.setFrameShape(QLabel.HLine)
        separator.setStyleSheet("color: #bdc3c7; margin: 10px 0px;")
        layout.addWidget(separator)
        
        # 功能介绍
        description_label = QLabel(tr("about_description"))
        description_label.setAlignment(Qt.AlignCenter)
        description_label.setWordWrap(True)
        description_label.setStyleSheet("font-size: 14px; margin: 10px 0px;")
        layout.addWidget(description_label)
        
        # 作者信息
        author_label = QLabel(tr("about_author"))
        author_label.setAlignment(Qt.AlignCenter)
        author_label.setStyleSheet("font-size: 14px; margin: 5px 0px;")
        layout.addWidget(author_label)
        
        # 邮箱信息
        email_label = QLabel(tr("about_email"))
        email_label.setAlignment(Qt.AlignCenter)
        email_label.setStyleSheet("font-size: 14px; margin: 5px 0px;")
        layout.addWidget(email_label)
        
        # 移除底部按钮，用户可以通过默认的关闭按钮退出对话框
        # button_layout = QHBoxLayout()
        # button_layout.addStretch()
        # 
        # ok_button = QPushButton("确定")
        # ok_button.clicked.connect(self.accept)
        # button_layout.addWidget(ok_button)
        # 
        # layout.addLayout(button_layout)
        # layout.addStretch()  # 添加弹性空间
        
        self.setLayout(layout)