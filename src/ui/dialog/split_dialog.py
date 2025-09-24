from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QSpinBox, QPushButton, QFormLayout
)
from PyQt5.QtCore import Qt


class SplitDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("划分数据集")
        self.setMinimumWidth(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """初始化界面组件"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 比例设置区域
        form_layout = QFormLayout()
        form_layout.setSpacing(10)

        # 训练集比例
        self.train_spin = QSpinBox()
        self.train_spin.setRange(0, 100)
        self.train_spin.setValue(70)
        self.train_spin.setSuffix("%")
        form_layout.addRow("训练集比例:", self.train_spin)

        # 验证集比例
        self.val_spin = QSpinBox()
        self.val_spin.setRange(0, 100)
        self.val_spin.setValue(20)
        self.val_spin.setSuffix("%")
        form_layout.addRow("验证集比例:", self.val_spin)

        # 测试集比例（自动计算）
        self.test_label = QLabel("10%")
        self.test_label.setStyleSheet("color: #888; font-style: italic;")
        form_layout.addRow("测试集比例:", self.test_label)

        # 更新比例显示
        self.update_test_percentage()
        main_layout.addLayout(form_layout)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setStyleSheet(
            "QPushButton { background-color: #5C5C5C; color: white; padding: 8px; border-radius: 4px; }"
            "QPushButton:hover { background-color: #4A4A4A; }"
        )

        self.confirm_button = QPushButton("确定")
        self.confirm_button.setMinimumWidth(100)
        self.confirm_button.setStyleSheet(
            "QPushButton { background-color: #0078D7; color: white; padding: 8px; border-radius: 4px; font-weight: bold; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.confirm_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def connect_signals(self):
        """连接信号与槽函数"""
        self.cancel_button.clicked.connect(self.reject)
        self.confirm_button.clicked.connect(self.accept)

        # 当比例变化时更新测试集比例
        self.train_spin.valueChanged.connect(self.update_test_percentage)
        self.val_spin.valueChanged.connect(self.update_test_percentage)

    def update_test_percentage(self):
        """更新测试集比例显示"""
        train_percent = self.train_spin.value()
        val_percent = self.val_spin.value()
        test_percent = 100 - train_percent - val_percent

        # 设置文本颜色（根据是否有效）
        if test_percent < 0:
            self.test_label.setText(f"<font color='red'>无效比例: {test_percent}%</font>")
            self.confirm_button.setEnabled(False)
        else:
            self.test_label.setText(f"{test_percent}%")
            self.confirm_button.setEnabled(True)

    def get_split_ratios(self):
        """获取划分比例"""
        return {
            "train": self.train_spin.value() / 100.0,
            "val": self.val_spin.value() / 100.0,
            "test": (100 - self.train_spin.value() - self.val_spin.value()) / 100.0
        }
