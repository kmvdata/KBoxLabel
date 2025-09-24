import os
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLabel, QComboBox, QLineEdit, QSizePolicy
)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QPixmap, QImage, QPainter


class NavigationPanel(QWidget):
    # 自定义信号
    image_selected = pyqtSignal(str)  # 图像选择信号（参数：图像路径）
    filter_changed = pyqtSignal(str)  # 过滤条件变化信号（参数：过滤类型）

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(250)  # 最小宽度
        self.image_files = []  # 存储图像路径列表
        self.init_ui()
        self.connect_signals()

    def init_ui(self):
        """初始化界面组件"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # 搜索区域
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("搜索图像...")
        self.search_input.setClearButtonEnabled(True)
        search_layout.addWidget(self.search_input)

        # 过滤下拉框
        self.filter_combo = QComboBox()
        self.filter_combo.addItems(["所有图像", "已标注", "未标注", "部分标注"])
        self.filter_combo.setCurrentIndex(0)
        search_layout.addWidget(self.filter_combo)
        main_layout.addLayout(search_layout)

        # 图像计数标签
        self.count_label = QLabel("0 张图像")
        self.count_label.setAlignment(Qt.AlignCenter)
        self.count_label.setStyleSheet("font-weight: bold; color: #555;")
        main_layout.addWidget(self.count_label)

        # 图像列表
        self.image_list = QListWidget()
        self.image_list.setIconSize(QSize(120, 80))  # 缩略图尺寸
        self.image_list.setResizeMode(QListWidget.Adjust)  # 自适应调整
        self.image_list.setSpacing(5)  # 项间距
        self.image_list.setUniformItemSizes(True)  # 统一尺寸提升性能
        main_layout.addWidget(self.image_list)

        self.setLayout(main_layout)

    def connect_signals(self):
        """连接信号与槽函数"""
        self.search_input.textChanged.connect(self.filter_images)
        self.filter_combo.currentTextChanged.connect(self.filter_changed.emit)
        self.image_list.itemClicked.connect(self.handle_item_click)

    def load_image_list(self, image_paths):
        """加载图像列表"""
        self.image_files = image_paths
        self.image_list.clear()
        self.all_items = []  # 保存所有项用于过滤

        for path in image_paths:
            item = self.create_image_item(path)
            self.all_items.append(item)
            self.image_list.addItem(item)

        self.update_count_label()

    def create_image_item(self, path):
        """创建带缩略图的列表项"""
        # 生成缩略图
        pixmap = self.generate_thumbnail(path)

        # 创建列表项
        filename = os.path.basename(path)
        item = QListWidgetItem(QIcon(pixmap), filename)
        item.setData(Qt.UserRole, path)  # 存储完整路径
        item.setSizeHint(QSize(130, 100))  # 项尺寸

        # 根据标注状态设置背景色
        annotation_state = self.get_annotation_state(path)  # 需实现状态检测
        if annotation_state == "annotated":
            item.setBackground(QColor(230, 255, 230))
        elif annotation_state == "partial":
            item.setBackground(QColor(255, 255, 200))

        return item

    def generate_thumbnail(self, path, size=QSize(120, 80)):
        """生成带标注状态的缩略图"""
        # 加载原始图像
        image = QImage(path)
        if image.isNull():
            return QPixmap(size)  # 返回空白缩略图

        # 创建缩略图
        scaled = image.scaled(size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        pixmap = QPixmap(scaled)

        # 在缩略图上绘制标注状态（示例）
        painter = QPainter(pixmap)
        painter.setPen(Qt.red)

        # 此处添加实际标注状态检测逻辑
        annotation_state = self.get_annotation_state(path)
        if annotation_state == "annotated":
            painter.drawRect(2, 2, pixmap.width() - 4, pixmap.height() - 4)
        elif annotation_state == "partial":
            painter.drawLine(0, 0, pixmap.width(), pixmap.height())
            painter.drawLine(pixmap.width(), 0, 0, pixmap.height())

        painter.end()
        return pixmap

    def get_annotation_state(self, path):
        """检测图像的标注状态（需根据实际项目实现）"""
        # 伪代码：根据实际项目实现状态检测
        # if 有标注文件 and 标注完整: return "annotated"
        # elif 有部分标注: return "partial"
        # else: return "unannotated"
        return "unannotated"  # 默认返回未标注

    def filter_images(self, text):
        """根据搜索文本过滤图像"""
        text = text.strip().lower()
        self.image_list.clear()

        # 应用搜索过滤
        for item in self.all_items:
            filename = item.text().lower()
            if not text or text in filename:
                self.image_list.addItem(item.clone())

        self.update_count_label()

    def update_count_label(self):
        """更新图像计数标签"""
        count = self.image_list.count()
        self.count_label.setText(f"{count}/{len(self.image_files)} 张图像")

    def handle_item_click(self, item):
        """处理图像项点击事件"""
        image_path = item.data(Qt.UserRole)
        self.image_selected.emit(image_path)

        # 高亮当前选中项
        for i in range(self.image_list.count()):
            current_item = self.image_list.item(i)
            current_item.setBackground(
                QColor(173, 216, 230) if current_item == item else Qt.white
            )

    def select_first_image(self):
        """自动选择第一张图像"""
        if self.image_list.count() > 0:
            first_item = self.image_list.item(0)
            self.image_list.setCurrentItem(first_item)
            self.handle_item_click(first_item)

    def clear_selection(self):
        """清除当前选择"""
        self.image_list.clearSelection()
        for i in range(self.image_list.count()):
            self.image_list.item(i).setBackground(Qt.white)
