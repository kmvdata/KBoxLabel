from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QDoubleSpinBox, QCheckBox, QPushButton,
    QProgressBar, QFormLayout, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal


class AutoLabelDialog(QDialog):
    # 自定义信号
    start_auto_labeling = pyqtSignal(dict)  # 传递配置参数

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("自动标注设置")
        self.setMinimumWidth(500)
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """初始化界面组件"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # ==================== 模型选择区域 ====================
        model_group = QGroupBox("模型选择")
        model_layout = QFormLayout()
        model_layout.setSpacing(10)

        # 模型类型选择
        self.model_combo = QComboBox()
        self.model_combo.addItems(["YOLOv8 (推荐)", "Mask R-CNN", "DETR", "EfficientDet"])
        model_layout.addRow("模型类型:", self.model_combo)

        # 模型精度选择
        self.precision_combo = QComboBox()
        self.precision_combo.addItems(["高精度 (速度慢)", "均衡", "快速 (精度较低)"])
        model_layout.addRow("精度模式:", self.precision_combo)

        model_group.setLayout(model_layout)
        main_layout.addWidget(model_group)

        # ==================== 参数设置区域 ====================
        params_group = QGroupBox("参数设置")
        params_layout = QFormLayout()
        params_layout.setSpacing(10)

        # 置信度阈值
        self.confidence_spin = QDoubleSpinBox()
        self.confidence_spin.setRange(0.0, 1.0)
        self.confidence_spin.setSingleStep(0.05)
        self.confidence_spin.setValue(0.6)
        self.confidence_spin.setToolTip("过滤低置信度检测结果")
        params_layout.addRow("置信度阈值:", self.confidence_spin)

        # IOU阈值
        self.iou_spin = QDoubleSpinBox()
        self.iou_spin.setRange(0.0, 1.0)
        self.iou_spin.setSingleStep(0.05)
        self.iou_spin.setValue(0.45)
        self.iou_spin.setToolTip("非极大值抑制的交并比阈值")
        params_layout.addRow("IOU阈值:", self.iou_spin)

        # 高级选项
        self.advanced_check = QCheckBox("显示高级选项")
        self.advanced_check.stateChanged.connect(self.toggle_advanced_options)
        params_layout.addRow(self.advanced_check)

        # 高级选项容器（默认隐藏）
        self.advanced_group = QGroupBox("高级选项")
        advanced_layout = QFormLayout()

        # 批次大小
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 64)
        self.batch_spin.setValue(4)
        self.batch_spin.setToolTip("每次处理的图像数量")
        advanced_layout.addRow("批次大小:", self.batch_spin)

        # 图像尺寸
        self.img_size_combo = QComboBox()
        self.img_size_combo.addItems(["原始尺寸", "640x640", "1024x1024"])
        advanced_layout.addRow("输入尺寸:", self.img_size_combo)

        # 设备选择
        self.device_combo = QComboBox()
        self.device_combo.addItems(["自动选择", "CPU", "GPU"])
        advanced_layout.addRow("运行设备:", self.device_combo)

        self.advanced_group.setLayout(advanced_layout)
        self.advanced_group.setVisible(False)
        params_layout.addRow(self.advanced_group)

        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # ==================== 进度条区域 ====================
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("就绪")
        self.progress_bar.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.progress_bar)

        # ==================== 按钮区域 ====================
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumWidth(100)
        self.cancel_button.setStyleSheet(
            "QPushButton { background-color: #5C5C5C; color: white; padding: 8px; }"
            "QPushButton:hover { background-color: #4A4A4A; }"
        )

        self.start_button = QPushButton("开始自动标注")
        self.start_button.setMinimumWidth(150)
        self.start_button.setStyleSheet(
            "QPushButton { background-color: #0078D7; color: white; padding: 8px; font-weight: bold; }"
            "QPushButton:hover { background-color: #106EBE; }"
        )

        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.start_button)
        main_layout.addLayout(button_layout)

        self.setLayout(main_layout)

    def connect_signals(self):
        """连接信号与槽函数"""
        self.cancel_button.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.on_start_clicked)

    def toggle_advanced_options(self, state):
        """切换高级选项的显示状态"""
        self.advanced_group.setVisible(state == Qt.Checked)
        # 调整对话框高度
        self.adjustSize()

    def on_start_clicked(self):
        """处理开始按钮点击事件"""
        # 收集配置参数
        config = {
            "model_type": self.model_combo.currentText().split(" ")[0],
            "precision_mode": self.precision_combo.currentIndex(),
            "confidence_threshold": self.confidence_spin.value(),
            "iou_threshold": self.iou_spin.value(),
            "batch_size": self.batch_spin.value(),
            "image_size": self.img_size_combo.currentText(),
            "device": self.device_combo.currentText()
        }

        # 发送开始信号
        self.start_auto_labeling.emit(config)

        # 更新进度条状态
        self.progress_bar.setFormat("正在初始化模型...")
        self.start_button.setEnabled(False)

    def update_progress(self, value, message=None):
        """更新进度条状态"""
        self.progress_bar.setValue(value)
        if message:
            self.progress_bar.setFormat(message)

    def on_completed(self, success, message):
        """自动标注完成处理"""
        if success:
            self.progress_bar.setFormat(f"完成! {message}")
            self.accept()  # 自动关闭对话框
        else:
            self.progress_bar.setFormat(f"错误: {message}")
            self.start_button.setEnabled(True)
