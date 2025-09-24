import os
import random
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QPushButton, QColorDialog, QLineEdit, QLabel, QInputDialog,
    QMessageBox, QAbstractItemView, QWidget, QSizePolicy
)
from PyQt5.QtGui import QColor, QIcon, QFont, QPixmap, QPainter
from PyQt5.QtCore import Qt, pyqtSignal, QSize


class ClassItemWidget(QWidget):
    """自定义类别项组件"""

    def __init__(self, name, color, parent=None):
        super().__init__(parent)
        self.name = name
        self.color = color

        # 创建布局
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        layout.setSpacing(10)

        # 颜色标签
        self.color_label = QLabel()
        self.color_label.setFixedSize(20, 20)
        self.color_label.setStyleSheet(f"background-color: {color.project_name()}; border-radius: 10px;")

        # 名称输入框
        self.name_edit = QLineEdit(name)
        self.name_edit.setStyleSheet("""
            QLineEdit {
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 4px;
                background-color: #2D2D30;
                color: white;
            }
            QLineEdit:focus {
                border: 1px solid #0078D7;
            }
        """)
        self.name_edit.setMinimumWidth(150)

        # 添加组件到布局
        layout.addWidget(self.color_label)
        layout.addWidget(self.name_edit)
        layout.addStretch()

        self.setLayout(layout)

    def update_color(self, new_color):
        """更新颜色显示"""
        self.color = new_color
        self.color_label.setStyleSheet(
            f"background-color: {new_color.project_name()}; border-radius: 10px;"
        )


class ClassManagerDialog(QDialog):
    # 自定义信号
    classes_updated = pyqtSignal(list)  # 类别列表更新信号

    def __init__(self, dataset_manager, parent=None):
        super().__init__(parent)
        self.dataset_manager = dataset_manager
        self.classes = dataset_manager.classes.copy()  # 复制类别列表
        self.colors = self.load_class_colors()  # 加载类别颜色

        self.setWindowTitle("类别管理器")
        self.setMinimumSize(600, 400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self.init_ui()
        self.load_classes()

    def init_ui(self):
        """初始化界面组件"""
        main_layout = QVBoxLayout()
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 标题标签
        title_label = QLabel("管理标注类别")
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #E1E1E1;")
        main_layout.addWidget(title_label)

        # 类别列表区域
        list_group = QWidget()
        list_layout = QVBoxLayout(list_group)
        list_layout.setContentsMargins(0, 0, 0, 0)

        # 类别列表
        self.class_list = QListWidget()
        self.class_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.class_list.setDragDropMode(QAbstractItemView.InternalMove)
        self.class_list.setStyleSheet("""
            QListWidget {
                background-color: #252526;
                border: 1px solid #3F3F46;
                border-radius: 4px;
                padding: 5px;
            }
            QListWidget::item {
                height: 40px;
            }
            QListWidget::item:selected {
                background-color: #2A2D2E;
            }
        """)

        list_layout.addWidget(self.class_list)
        main_layout.addWidget(list_group)

        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 添加按钮
        self.add_button = QPushButton("添加类别")
        self.add_button.setIcon(self.create_color_icon(QColor("#0078D7")))
        self.add_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
            QPushButton:pressed {
                background-color: #005A9E;
            }
        """)
        self.add_button.clicked.connect(self.add_class)

        # 编辑颜色按钮
        self.edit_color_button = QPushButton("编辑颜色")
        self.edit_color_button.setIcon(self.create_color_icon(QColor("#BA68C8")))
        self.edit_color_button.setStyleSheet("""
            QPushButton {
                background-color: #68217A;
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #7A3D8C;
            }
            QPushButton:disabled {
                background-color: #3F3F46;
                color: #888;
            }
        """)
        self.edit_color_button.setEnabled(False)
        self.edit_color_button.clicked.connect(self.edit_class_color)

        # 删除按钮
        self.delete_button = QPushButton("删除")
        self.delete_button.setIcon(QIcon(":/icons/delete.png"))
        self.delete_button.setStyleSheet("""
            QPushButton {
                background-color: #A12622;
                color: white;
                padding: 8px 12px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #C13530;
            }
            QPushButton:disabled {
                background-color: #3F3F46;
                color: #888;
            }
        """)
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_class)

        # 确定/取消按钮
        self.ok_button = QPushButton("确定")
        self.ok_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """)
        self.ok_button.clicked.connect(self.save_classes)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #5C5C5C;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #4A4A4A;
            }
        """)
        self.cancel_button.clicked.connect(self.reject)

        # 添加操作按钮
        button_layout.addWidget(self.add_button)
        button_layout.addWidget(self.edit_color_button)
        button_layout.addWidget(self.delete_button)
        button_layout.addStretch()

        # 添加确定/取消按钮
        button_layout.addWidget(self.cancel_button)
        button_layout.addWidget(self.ok_button)

        main_layout.addLayout(button_layout)
        self.setLayout(main_layout)

        # 连接列表选择变化信号
        self.class_list.itemSelectionChanged.connect(self.update_button_state)

    def create_color_icon(self, color, size=16):
        """创建颜色图标"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)
        painter.setBrush(color)
        painter.drawEllipse(0, 0, size - 1, size - 1)
        painter.end()

        return QIcon(pixmap)

    def load_class_colors(self):
        """加载类别颜色，如果不存在则生成随机颜色"""
        colors = {}

        # 预设一组美观的颜色
        preset_colors = [
            QColor("#FF5252"), QColor("#FF4081"), QColor("#E040FB"),
            QColor("#7C4DFF"), QColor("#536DFE"), QColor("#448AFF"),
            QColor("#40C4FF"), QColor("#18FFFF"), QColor("#64FFDA"),
            QColor("#69F0AE"), QColor("#B2FF59"), QColor("#EEFF41"),
            QColor("#FFFF00"), QColor("#FFD740"), QColor("#FFAB40"),
            QColor("#FF6E40")
        ]

        # 为每个类别分配颜色
        for i, class_name in enumerate(self.classes):
            if i < len(preset_colors):
                colors[class_name] = preset_colors[i]
            else:
                # 生成随机但鲜艳的颜色
                hue = random.randint(0, 359)
                colors[class_name] = QColor.fromHsv(hue, 150, 230)

        return colors

    def load_classes(self):
        """加载类别到列表"""
        self.class_list.clear()

        for class_name in self.classes:
            color = self.colors.get(class_name, QColor("#0078D7"))
            self.add_class_item(class_name, color)

    def add_class_item(self, name, color):
        """添加类别项到列表"""
        item = QListWidgetItem(self.class_list)
        widget = ClassItemWidget(name, color)
        item.setSizeHint(widget.sizeHint())
        self.class_list.addItem(item)
        self.class_list.setItemWidget(item, widget)
        return item

    def add_class(self):
        """添加新类别"""
        new_name, ok = QInputDialog.getText(
            self, "添加新类别", "请输入类别名称:"
        )

        if ok and new_name:
            if new_name in self.classes:
                QMessageBox.warning(
                    self, "重复类别",
                    f"类别 '{new_name}' 已存在，请使用不同的名称！"
                )
                return

            # 生成新颜色
            hue = random.randint(0, 359)
            new_color = QColor.fromHsv(hue, 150, 230)

            # 添加到列表
            self.classes.append(new_name)
            self.colors[new_name] = new_color
            self.add_class_item(new_name, new_color)

    def edit_class_color(self):
        """编辑当前选中类别的颜色"""
        selected_items = self.class_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        widget = self.class_list.itemWidget(item)

        color = QColorDialog.getColor(
            widget.color, self, "选择类别颜色"
        )

        if color.isValid():
            widget.update_color(color)
            self.colors[widget.name_edit.text()] = color

    def delete_class(self):
        """删除选中的类别"""
        selected_items = self.class_list.selectedItems()
        if not selected_items:
            return

        item = selected_items[0]
        widget = self.class_list.itemWidget(item)
        class_name = widget.name_edit.text()

        # 确认对话框
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除类别 '{class_name}' 吗?",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            row = self.class_list.row(item)
            self.class_list.takeItem(row)
            self.classes.remove(class_name)
            del self.colors[class_name]

    def update_button_state(self):
        """更新按钮状态（根据选择项）"""
        has_selection = len(self.class_list.selectedItems()) > 0
        self.edit_color_button.setEnabled(has_selection)
        self.delete_button.setEnabled(has_selection)

    def save_classes(self):
        """保存类别设置"""
        # 更新类别名称（允许在列表中直接编辑）
        updated_classes = []
        updated_colors = {}

        for i in range(self.class_list.count()):
            item = self.class_list.item(i)
            widget = self.class_list.itemWidget(item)

            new_name = widget.name_edit.text().strip()
            if not new_name:
                QMessageBox.warning(
                    self, "无效名称", "类别名称不能为空！"
                )
                return

            if new_name in updated_classes:
                QMessageBox.warning(
                    self, "重复类别",
                    f"类别 '{new_name}' 已存在，请使用不同的名称！"
                )
                return

            updated_classes.append(new_name)
            updated_colors[new_name] = widget.color

        # 更新数据集管理器
        self.dataset_manager.classes = updated_classes
        self.dataset_manager.class_colors = updated_colors
        self.classes_updated.emit(updated_classes)

        # 保存数据集（包含类别更新）
        self.dataset_manager.save_dataset()

        self.accept()

    def get_class_colors(self):
        """获取类别颜色映射"""
        return self.colors
