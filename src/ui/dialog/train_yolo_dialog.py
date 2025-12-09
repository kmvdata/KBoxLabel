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
        
        self.finish_button = QPushButton("完成")
        self.finish_button.setDefault(True)
        
        button_layout.addWidget(self.finish_button)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
        
        # 连接信号
        self.finish_button.clicked.connect(self.accept)

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
        self.start_button = QPushButton("创建训练数据集")
        self.start_button.setEnabled(False)
        button_layout.addWidget(self.start_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 连接信号
        self.start_button.clicked.connect(self.prepare_training_data)

    def select_directory(self):
        """选择训练数据目录"""
        directory = QFileDialog.getExistingDirectory(
            self, "选择训练数据目录", str(self.project_window.project_info.path)
        )
        if directory:
            self.dir_line_edit.setText(directory)
            self.start_button.setEnabled(True)
            self.train_data_dir = Path(directory)

    def prepare_training_data(self):
        """准备训练数据"""
        if not hasattr(self, 'train_data_dir'):
            QMessageBox.warning(self, "错误", "请先选择训练数据目录")
            return
            
        try:
            # 准备训练数据
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat("正在准备训练数据...")
            self.log_text_edit.append("正在准备训练数据...")
            
            # 获取类别列表和类别名称
            categories = self.project_window.project_info.domain.query_all_categories()
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
            
            # 生成数据集YAML配置文件
            self.progress_bar.setValue(40)
            self.log_text_edit.append("正在生成数据集配置文件...")
            # 如果提供了categories，只使用顶层类别生成yaml
            if categories:
                top_level_class_names = [cat.class_name for cat in categories if cat.parent_name is None]
                class_names = top_level_class_names
            YOLOTrainer.prepare_dataset_yaml(self.train_data_dir, class_names)
            
            # 显示配置对话框
            self.progress_bar.setValue(50)
            config_dialog = TrainConfigDialog(
                self.project_window, self.train_data_dir, class_names, self
            )
            
            if config_dialog.exec_() == QDialog.Accepted:
                # 显示训练命令而不是直接训练
                self.show_training_command(
                    self.train_data_dir,
                    config_dialog.model_combo.currentText(),
                    config_dialog.epochs_spin.value(),
                    config_dialog.imgsz_spin.value(),
                    config_dialog.batch_spin.value(),
                    class_names
                )
            else:
                self.progress_bar.setVisible(False)
                self.start_button.setEnabled(True)
        except Exception as e:
            QMessageBox.critical(self, "错误", f"准备训练数据时出错: {str(e)}")
            self.progress_bar.setVisible(False)
            self.start_button.setEnabled(True)

    def show_training_command(self, data_dir, model_name, epochs, imgsz, batch_size, class_names):
        """显示训练命令"""
        self.progress_bar.setValue(100)
        self.progress_bar.setFormat("数据准备完成")
        
        # 构造训练命令
        command = f"yolo detect train model={model_name} data={data_dir.absolute()}/dataset.yaml epochs={epochs} imgsz={imgsz} batch={batch_size}"
        
        # 在日志中显示命令
        self.log_text_edit.append("=" * 50)
        self.log_text_edit.append("数据准备已完成！")
        self.log_text_edit.append("请在终端中运行以下命令来开始训练：")
        self.log_text_edit.append("=" * 50)
        self.log_text_edit.append(command)
        self.log_text_edit.append("=" * 50)
        self.log_text_edit.append("注意：您可能需要根据实际情况调整命令参数")
        
        # 更改按钮文字为"完成"
        self.start_button.setText("完成")
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.accept)
        
        # 提示用户
        QMessageBox.information(self, "数据准备完成", f"训练数据已准备完成，请查看日志获取训练命令。\n数据保存在: {data_dir}")
