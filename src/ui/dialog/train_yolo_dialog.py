from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QSpinBox, QPushButton, QProgressBar, QFormLayout,
    QTextEdit, QFileDialog, QMessageBox, QLineEdit
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
import logging

from src.core.yolo.yolo_trainer import YOLOTrainer


class TrainConfigDialog(QDialog):
    """训练配置确认对话框"""
    
    def __init__(self, project_window, train_data_dir, class_names, parent=None):
        super().__init__(parent)
        self.project_window = project_window
        self.train_data_dir = train_data_dir
        self.class_names = class_names
        self.setWindowTitle("训练配置确认")
        self.setMinimumWidth(500)
        self.init_ui()
        self.populate_data_stats()

    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # 数据统计区域
        stats_group = QGroupBox("数据统计")
        stats_layout = QFormLayout()
        stats_layout.setSpacing(10)
        
        self.total_samples_label = QLabel()
        self.train_samples_label = QLabel()
        self.val_samples_label = QLabel()
        self.classes_label = QLabel()
        
        stats_layout.addRow("总样本数:", self.total_samples_label)
        stats_layout.addRow("训练集数量:", self.train_samples_label)
        stats_layout.addRow("验证集数量:", self.val_samples_label)
        stats_layout.addRow("类别列表:", self.classes_label)
        
        stats_group.setLayout(stats_layout)
        main_layout.addWidget(stats_group)

        # 训练参数区域
        params_group = QGroupBox("训练参数")
        params_layout = QFormLayout()
        params_layout.setSpacing(10)
        
        # 模型类型
        self.model_combo = QComboBox()
        self.model_combo.addItems(["yolov8s.pt", "yolov8n.pt", "yolov8m.pt", "yolov8l.pt", "yolov8x.pt"])
        self.model_combo.setCurrentText("yolov8s.pt")
        params_layout.addRow("模型类型:", self.model_combo)
        
        # 训练轮次
        self.epochs_spin = QSpinBox()
        self.epochs_spin.setRange(1, 1000)
        self.epochs_spin.setValue(100)
        params_layout.addRow("训练轮次:", self.epochs_spin)
        
        # 图片尺寸
        self.imgsz_spin = QSpinBox()
        self.imgsz_spin.setRange(32, 4096)
        self.imgsz_spin.setSingleStep(32)
        self.imgsz_spin.setValue(640)
        params_layout.addRow("图片尺寸:", self.imgsz_spin)
        
        # 批次大小
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 256)
        self.batch_spin.setValue(16)
        params_layout.addRow("批次大小:", self.batch_spin)
        
        params_group.setLayout(params_layout)
        main_layout.addWidget(params_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.cancel_button = QPushButton("取消")
        self.start_button = QPushButton("确认训练")
        self.start_button.setDefault(True)
        
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.start_button)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 连接信号
        self.cancel_button.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.accept)

    def populate_data_stats(self):
        """填充数据统计信息"""
        try:
            # 获取txt文件数量作为样本数
            txt_files = list(self.train_data_dir.glob("*.txt"))
            total_samples = len(txt_files)
            
            # 默认8:2分割
            train_samples = int(total_samples * 0.8)
            val_samples = total_samples - train_samples
            
            self.total_samples_label.setText(str(total_samples))
            self.train_samples_label.setText(str(train_samples))
            self.val_samples_label.setText(str(val_samples))
            self.classes_label.setText(", ".join(self.class_names) if self.class_names else "无类别")
        except Exception as e:
            logging.error(f"Error calculating data stats: {e}")
            self.total_samples_label.setText("未知")
            self.train_samples_label.setText("未知")
            self.val_samples_label.setText("未知")
            self.classes_label.setText("未知")


class TrainingThread(QThread):
    """训练线程，避免界面冻结"""
    progress_updated = pyqtSignal(str)
    training_finished = pyqtSignal(bool, str)

    def __init__(self, trainer, source_dir, model_name, epochs, imgsz, batch_size, data_dir, categories):
        super().__init__()
        self.trainer = trainer
        self.source_dir = source_dir
        self.model_name = model_name
        self.epochs = epochs
        self.imgsz = imgsz
        self.batch_size = batch_size
        self.data_dir = data_dir
        self.categories = categories

    def run(self):
        try:
            self.progress_updated.emit("开始训练...")
            # 从categories中提取类别名称
            class_names = [category.class_name for category in self.categories]
            result = self.trainer.train(
                source_dir=self.source_dir,
                model_name=self.model_name,
                epochs=self.epochs,
                imgsz=self.imgsz,
                batch_size=self.batch_size,
                data_dir=self.data_dir,
                class_names=class_names,
                categories=self.categories
            )
            self.training_finished.emit(True, result)
        except Exception as e:
            logging.error(f"Training error: {e}")
            self.training_finished.emit(False, str(e))


class TrainYoloDialog(QDialog):
    """YOLO训练主对话框"""
    
    def __init__(self, project_window, parent=None):
        super().__init__(parent)
        self.project_window = project_window
        self.setWindowTitle("训练YOLO模型")
        self.setMinimumSize(600, 500)
        self.init_ui()

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 说明标签
        info_label = QLabel("请选择训练数据保存目录:")
        layout.addWidget(info_label)
        
        # 目录选择
        dir_layout = QHBoxLayout()
        self.dir_line_edit = QLineEdit()
        self.dir_line_edit.setReadOnly(True)
        select_dir_btn = QPushButton("选择目录")
        select_dir_btn.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_line_edit)
        dir_layout.addWidget(select_dir_btn)
        layout.addLayout(dir_layout)
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # 日志输出
        self.log_text_edit = QTextEdit()
        self.log_text_edit.setReadOnly(True)
        layout.addWidget(self.log_text_edit)
        
        # 按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        self.cancel_button = QPushButton("取消")
        self.start_button = QPushButton("开始准备数据")
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.start_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.cancel_button.clicked.connect(self.reject)
        self.start_button.clicked.connect(self.start_training_process)

    def select_directory(self):
        """选择训练数据目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择训练数据目录", str(self.project_window.project_info.path)
        )
        if directory:
            self.dir_line_edit.setText(directory)
            self.start_button.setEnabled(True)
            self.train_data_dir = Path(directory)

    def start_training_process(self):
        """开始训练流程"""
        if not hasattr(self, 'train_data_dir'):
            QMessageBox.warning(self, "错误", "请先选择训练数据目录")
            return
            
        try:
            # 准备训练数据
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat("正在准备训练数据...")
            self.log_text_edit.append("正在准备训练数据...")
            
            # 获取类别列表和类别名称
            categories = self.project_window.project_info.categories
            class_names = [category.class_name for category in categories]
            
            # 创建训练器
            trainer = YOLOTrainer()
            
            # 组织训练数据
            source_dir = self.project_window.project_info.path
            self.progress_bar.setValue(20)
            self.log_text_edit.append("正在组织训练数据...")
            # 确保训练数据目录存在
            self.train_data_dir.mkdir(parents=True, exist_ok=True)
            trainer.organize_training_data(source_dir, self.train_data_dir, categories=categories)
            
            # 显示配置对话框
            self.progress_bar.setValue(50)
            config_dialog = TrainConfigDialog(
                self.project_window, self.train_data_dir, class_names, self
            )
            
            if config_dialog.exec_() == QDialog.Accepted:
                # 开始训练
                self.start_button.setEnabled(False)
                self.progress_bar.setValue(60)
                self.progress_bar.setFormat("正在训练...")
                self.log_text_edit.append("正在开始训练...")
                
                # 在单独线程中进行训练
                self.training_thread = TrainingThread(
                    trainer,
                    source_dir,
                    config_dialog.model_combo.currentText(),
                    config_dialog.epochs_spin.value(),
                    config_dialog.imgsz_spin.value(),
                    config_dialog.batch_spin.value(),
                    self.train_data_dir,
                    class_names
                )
                self.training_thread.progress_updated.connect(self.update_progress)
                self.training_thread.training_finished.connect(self.on_training_finished)
                self.training_thread.start()
            else:
                self.progress_bar.setVisible(False)
                self.start_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"准备训练数据时出错: {str(e)}")
            self.progress_bar.setVisible(False)
            self.start_button.setEnabled(True)

    def update_progress(self, message):
        """更新进度"""
        self.log_text_edit.append(message)

    def on_training_finished(self, success, result):
        """训练完成处理"""
        self.progress_bar.setValue(100)
        if success:
            self.progress_bar.setFormat("训练完成")
            self.log_text_edit.append(f"训练完成: {result}")
            QMessageBox.information(self, "训练完成", f"训练已完成，结果保存在: {result}")
        else:
            self.progress_bar.setFormat("训练失败")
            self.log_text_edit.append(f"训练失败: {result}")
            QMessageBox.critical(self, "训练失败", f"训练过程中出现错误: {result}")
        self.start_button.setEnabled(True)