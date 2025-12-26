from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox, QLabel,
    QComboBox, QSpinBox, QPushButton, QProgressBar, QFormLayout,
    QTextEdit, QFileDialog, QMessageBox, QLineEdit, QTreeWidget, QTreeWidgetItem, QHeaderView, QFrame
)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from pathlib import Path
import logging

from src.core.yolo.yolo_trainer import YOLOTrainer

# 添加PIL库用于获取图片尺寸
from PIL import Image

from src.core.i18n.language_manager import tr

class TrainYoloDialog(QDialog):
    """YOLO数据集对话框"""
    
    def __init__(self, project_window, parent=None):
        super().__init__(parent)
        self.project_window = project_window
        self.setWindowTitle(tr("train_yolo_title"))
        self.setMinimumSize(600, 500)
        self.init_ui()
        self.populate_data_stats()  # 初始化时就加载统计数据

    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        
        # 说明标签
        info_label = QLabel(tr("train_select_directory"))
        layout.addWidget(info_label)
        
        # 目录选择
        dir_layout = QHBoxLayout()
        self.dir_line_edit = QLineEdit()
        self.dir_line_edit.setReadOnly(True)
        select_dir_btn = QPushButton(tr("dialog_button_open_project"))
        select_dir_btn.clicked.connect(self.select_directory)
        dir_layout.addWidget(self.dir_line_edit)
        dir_layout.addWidget(select_dir_btn)
        layout.addLayout(dir_layout)
        
        # 标题
        title_label = QLabel(tr("train_statistics_title"))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px; margin-top: 10px;")
        layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 数据统计区域 - 使用树形控件显示详细统计信息
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["类别名称", "类别ID", "标注数量"])
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        layout.addWidget(self.tree)
        
        # 训练参数区域
        params_group = QGroupBox(tr("train_params"))
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
        # 设置默认图片尺寸为项目第一张图片的尺寸
        default_imgsz = self.get_first_image_size()
        self.imgsz_spin.setValue(default_imgsz)
        params_layout.addRow("图片尺寸:", self.imgsz_spin)
        
        # 批次大小
        self.batch_spin = QSpinBox()
        self.batch_spin.setRange(1, 256)
        self.batch_spin.setValue(16)
        params_layout.addRow("批次大小:", self.batch_spin)
        
        params_group.setLayout(params_layout)
        layout.addWidget(params_group)
        
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
        self.cancel_button = QPushButton(tr("button_cancel"))
        self.open_folder_button = QPushButton(tr("button_open_dataset"))
        self.start_button = QPushButton(tr("button_start"))
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.open_folder_button)
        button_layout.addWidget(self.start_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # 设置默认训练目录路径
        project_path = self.project_window.project_info.path
        default_train_dir = project_path.parent / f"train_{project_path.name}"
        self.dir_line_edit.setText(str(default_train_dir))
        self.train_data_dir = default_train_dir
        self.start_button.setEnabled(True)
        
        # 隐藏打开数据集按钮，初始只显示取消和开始按钮
        self.open_folder_button.setVisible(False)
        
        # 连接信号
        self.start_button.clicked.connect(self.prepare_training_data)
        self.cancel_button.clicked.connect(self.reject)
        self.open_folder_button.clicked.connect(self.open_dataset_folder)

    def get_first_image_size(self):
        """获取项目中第一张图片的尺寸"""
        try:
            # 获取项目路径
            project_path = self.project_window.project_info.path
            
            # 查找项目中的图片文件
            image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
            for ext in image_extensions:
                first_image = next(project_path.rglob(f"*{ext}"), None)
                if first_image:
                    # 使用PIL获取图片尺寸
                    with Image.open(first_image) as img:
                        width, height = img.size
                        # 返回较长的一边
                        return max(width, height)
            
            # 如果没找到图片，返回默认值640
            return 640
        except Exception as e:
            logging.warning(f"无法获取第一张图片的尺寸: {e}")
            # 出现异常时返回默认值640
            return 640

    def select_directory(self):
        """选择训练数据目录"""
        directory = QFileDialog.getExistingDirectory(
            self, tr("train_select_directory"), str(self.project_window.project_info.path)
        )
        if directory:
            self.dir_line_edit.setText(directory)
            self.start_button.setEnabled(True)
            self.train_data_dir = Path(directory)

    def populate_data_stats(self):
        """填充数据统计信息"""
        # 清空现有的统计数据
        self.tree.clear()
        
        # 获取所有类别，按order字段排序
        categories = self.project_window.project_info.domain.query_all_categories()
        
        # 创建类别映射和父子关系
        category_map = {cat.class_name: cat for cat in categories}
        parent_children_map = {}
        
        # 构建父子关系映射
        for category in categories:
            if category.parent_name:
                if category.parent_name not in parent_children_map:
                    parent_children_map[category.parent_name] = []
                parent_children_map[category.parent_name].append(category)
            # 确保所有类别都在映射中，即使它们没有子项
            elif category.class_name not in parent_children_map:
                parent_children_map[category.class_name] = []
        
        # 添加顶级类别及其子类别
        for category in categories:
            # 只处理顶级类别（没有父类别的类别）
            if not category.parent_name:
                # 创建顶级项
                top_level_item = QTreeWidgetItem(self.tree)
                top_level_item.setText(0, category.class_name)
                top_level_item.setText(1, str(category.class_id))
                
                # 获取该类别自身的标注数量
                self_count = self.project_window.project_info.domain.count_kilo_items_for_category(category.class_name)
                
                # 统计该类别及其子类别的标注数量
                total_count = self_count
                
                # 添加子类别
                children = parent_children_map.get(category.class_name, [])
                for child in children:
                    child_item = QTreeWidgetItem(top_level_item)
                    child_item.setText(0, "  └─ " + child.class_name)  # 添加缩进来表示层级关系
                    child_item.setText(1, str(child.class_id))
                    
                    # 获取子类别的标注数量
                    child_count = self.project_window.project_info.domain.count_kilo_items_for_category(child.class_name)
                    child_item.setText(2, str(child_count))
                    
                    # 累加到总计数中
                    total_count += child_count
                
                # 显示统计数据：如果有子类别则显示"M - N"格式，否则只显示总数
                if children:
                    top_level_item.setText(2, f"{total_count} - {self_count}")
                else:
                    top_level_item.setText(2, str(total_count))
                
        # 展开所有项
        self.tree.expandAll()

    def prepare_training_data(self):
        """准备训练数据"""
        if not hasattr(self, 'train_data_dir'):
            QMessageBox.warning(self, tr("error_get_project_path"), tr("error_training_data_dir"))
            return
            
        try:
            # 检查目录是否存在
            if self.train_data_dir.exists():
                reply = QMessageBox.question(
                    self, 
                    tr("train_data_exists"), 
                    tr("train_overwrite_confirm", dir=str(self.train_data_dir)),
                    QMessageBox.Yes | QMessageBox.No, 
                    QMessageBox.No
                )
                
                if reply == QMessageBox.No:
                    return
            
            # 禁用开始按钮，启用取消按钮
            self.start_button.setEnabled(False)
            self.cancel_button.setEnabled(True)
            
            # 准备训练数据
            self.progress_bar.setVisible(True)
            self.progress_bar.setFormat(tr("train_preparing"))
            self.log_text_edit.append(tr("train_preparing"))
            
            # 获取类别列表和类别名称
            categories = self.project_window.project_info.domain.query_all_categories()
            
            # 创建训练器
            trainer = YOLOTrainer()
            
            # 用户确认开始生成，现在开始实际生成过程
            self.generate_training_data(trainer, categories)
        except Exception as e:
            QMessageBox.critical(self, tr("error_get_project_path"), tr("error_prepare_training", error=str(e)))
            self.progress_bar.setVisible(False)
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(True)

    def generate_training_data(self, trainer, categories):
        """生成训练数据"""
        try:
            # 更新进度条
            self.progress_bar.setValue(20)
            self.progress_bar.setFormat(tr("train_organizing"))
            self.log_text_edit.append(tr("train_organizing"))
            
            # 确保训练数据目录存在
            self.train_data_dir.mkdir(parents=True, exist_ok=True)
            
            # 组织训练数据
            source_dir = self.project_window.project_info.path
            
            # 定义进度回调函数
            def progress_callback(message, percentage):
                self.progress_bar.setValue(percentage)
                self.progress_bar.setFormat(message)
                # 只有当消息不是进度更新（如'正在处理训练集图片 1/10: image.jpg'）时才添加到日志
                # 避免过多的进度信息刷屏，只显示关键信息
                if not message.startswith("正在处理") or "数据集分割完成" in message or "数据导出完成" in message or "处理完成:" in message:
                    self.log_text_edit.append(message)
                # 处理事件队列，确保UI更新
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()
            
            trainer.organize_training_data(source_dir, self.train_data_dir, 
                                         self.project_window.project_info.domain,
                                         progress_callback=progress_callback)
            
            # 更新进度
            self.progress_bar.setValue(90)
            self.progress_bar.setFormat(tr("train_generating_config"))
            self.log_text_edit.append(tr("train_generating_config"))
            
            # 生成数据集YAML配置文件
            # 如果提供了categories，只使用顶层类别生成yaml
            if categories:
                top_level_class_names = [cat.class_name for cat in categories if cat.parent_name is None]
                class_names = top_level_class_names
            YOLOTrainer.prepare_dataset_yaml(self.train_data_dir, class_names)
            
            # 完成
            self.progress_bar.setValue(100)
            self.progress_bar.setFormat(tr("train_completed"))
            self.log_text_edit.append(tr("train_completed"))
            
            # 显示训练命令而不是直接训练
            self.show_training_command(
                self.train_data_dir,
                class_names
            )
        except Exception as e:
            QMessageBox.critical(self, tr("error_get_project_path"), tr("error_generate_training", error=str(e)))
            self.progress_bar.setVisible(False)
            self.start_button.setEnabled(True)
            self.cancel_button.setEnabled(True)

    def open_dataset_folder(self):
        """打开数据集文件夹"""
        try:
            folder_path = self.train_data_dir.absolute()
            
            import platform
            system = platform.system()
            
            if system == "Windows":
                # Windows系统使用explorer打开文件夹
                import subprocess
                subprocess.Popen(["explorer", str(folder_path)])
            elif system == "Darwin":
                # macOS系统使用open命令在Finder中打开
                import subprocess
                subprocess.Popen(["open", str(folder_path)])
            else:
                # Linux系统使用xdg-open命令打开文件夹
                import subprocess
                subprocess.Popen(["xdg-open", str(folder_path)])
        except Exception as e:
            QMessageBox.critical(self, tr("error_get_project_path"), tr("error_open_folder", error=str(e)))

    def show_training_command(self, data_dir, class_names):
        """显示训练命令"""
        # 构造训练命令
        command = f"yolo detect train model=yolov8s.pt data={data_dir.absolute()}/dataset.yaml epochs=100 imgsz=640 batch=16"
        
        # 在日志中显示命令
        self.log_text_edit.append("=" * 50)
        self.log_text_edit.append(tr("train_completed"))
        self.log_text_edit.append(tr("train_command_info"))
        self.log_text_edit.append("=" * 50)
        self.log_text_edit.append(command)
        self.log_text_edit.append("=" * 50)
        self.log_text_edit.append("注意：您可能需要根据实际情况调整命令参数")
        self.log_text_edit.append(f"数据保存在: {data_dir}")
        
        # 更改按钮状态：隐藏取消按钮，显示打开数据集按钮，启用完成按钮
        self.cancel_button.setVisible(False)
        self.open_folder_button.setVisible(True)
        self.start_button.setText(tr("button_finish"))
        self.start_button.setEnabled(True)
        self.start_button.clicked.disconnect()
        self.start_button.clicked.connect(self.accept)