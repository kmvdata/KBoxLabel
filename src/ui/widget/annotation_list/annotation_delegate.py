# annotation_delegate.py

from PyQt5.QtCore import Qt, QSize, QRect
from PyQt5.QtGui import QPen, QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QStyledItemDelegate, QStyle

from src.ui.widget.annotation_list.annotation_item import AnnotationItem


class AnnotationDelegate(QStyledItemDelegate):
    """优化后的委托类，实现垂直居中对齐和布局调整"""
    MARGIN = 4  # 整体边距
    SPACING = 8  # 区域间间距
    INDENT = 32  # 子项缩进像素

    def __init__(self, row_height=56, parent=None):
        super().__init__(parent)
        self.drag_target_index = None
        self.row_height = row_height
        self.hovered_index = None  # 用于高亮显示的索引

    def set_row_height(self, height: int):
        self.row_height = height

    def set_hovered_index(self, index):
        """设置悬停索引以进行高亮显示"""
        self.hovered_index = index

    def set_drag_target_index(self, index):
        """设置拖拽目标索引以进行高亮显示"""
        self.drag_target_index = index

    def sizeHint(self, option, index):
        # 计算最小宽度：color区域 + name最小区域 + id区域 + 间距和边距
        min_width = (self.row_height + self.SPACING) * 2 + 2 * self.row_height + 2 * self.MARGIN
        return QSize(min_width, self.row_height)

    def paint(self, painter, option, index):
        # 获取数据
        category_color = index.data(Qt.UserRole)
        class_id = index.data(Qt.UserRole + 1)
        category_name = index.data(Qt.DisplayRole)
        parent_name = index.data(Qt.UserRole + 3)  # 获取父ID

        if not all([category_color, category_name, class_id is not None]):
            return

        # 处理选中状态和悬停状态
        is_hovered = self.hovered_index and self.hovered_index == index
        # 检查是否是拖拽目标（用于建立父子关系的视觉反馈）
        is_drag_target = getattr(self, 'drag_target_index', None) and self.drag_target_index == index
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        elif is_drag_target:
            # 拖拽目标高亮（建立父子关系时）- 使用更强的高亮
            hover_color = QColor(option.palette.highlight().color())
            hover_color.setAlpha(180)  # 更明显的高亮
            painter.fillRect(option.rect, hover_color)
            painter.setPen(option.palette.highlightedText().color())
        elif is_hovered:
            # 悬停状态使用特殊颜色
            hover_color = QColor(option.palette.highlight().color())
            hover_color.setAlpha(100)  # 半透明
            painter.fillRect(option.rect, hover_color)
            painter.setPen(option.palette.windowText().color())
        else:
            painter.fillRect(option.rect, option.palette.window())
            painter.setPen(option.palette.windowText().color())

        # 计算缩进
        indent = self.INDENT if parent_name is not None else 0

        # 计算各区域尺寸
        # color区域：正方形，宽度和高度等于item高度
        color_size = self.row_height - 2 * self.MARGIN
        color_rect = QRect(
            option.rect.left() + self.MARGIN + indent,
            option.rect.top() + self.MARGIN,
            color_size,
            color_size
        )

        # id区域：与color区域大小相同
        id_rect = QRect(
            option.rect.right() - color_size - self.MARGIN,
            option.rect.top() + self.MARGIN,
            color_size,
            color_size
        )

        # name区域：可伸缩，最小宽度为高度的两倍
        name_min_width = 2 * self.row_height
        available_width = option.rect.width() - (color_size + self.MARGIN + self.SPACING) * 2 - indent
        name_width = max(available_width, name_min_width)

        name_rect = QRect(
            color_rect.right() + self.SPACING,
            option.rect.top(),
            name_width,
            self.row_height
        )

        # 创建带透明度的颜色，与AnnotationView中使用的透明度保持一致（0.35）
        transparent_color = QColor(category_color)
        transparent_color.setAlphaF(0.65)

        # 绘制元素
        painter.fillRect(color_rect, transparent_color)  # 颜色方块（带透明度）
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, category_name)  # 文本
        painter.drawText(id_rect, Qt.AlignCenter, str(class_id))  # 序号

        # 添加颜色方块边框增强可读性
        border_pen = QPen(option.palette.windowText().color(), 1)
        painter.setPen(border_pen)
        painter.drawRect(color_rect)

        # 如果是子项，绘制一个小的指示图标
        if parent_name is not None:
            painter.save()
            painter.setPen(QPen(option.palette.windowText().color(), 2))
            # 绘制一个小的"L"形图标表示子项
            icon_x = option.rect.left() + indent - 10
            icon_y = option.rect.top() + self.row_height // 2
            painter.drawLine(icon_x, icon_y, icon_x + 6, icon_y)  # 水平线
            painter.drawLine(icon_x, icon_y, icon_x, icon_y + 6)  # 垂直线
            painter.restore()

    @staticmethod
    def create_drag_pixmap(annotation_item: AnnotationItem) -> QPixmap:
        """创建用于拖拽的 pixmap"""
        # 创建一个适当大小的 pixmap
        width = 200
        height = 40
        pixmap = QPixmap(width, height)
        pixmap.fill(Qt.transparent)

        # 创建绘图器
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制颜色方块
        color_size = height - 8
        color_rect = QRect(4, 4, color_size, color_size)

        # 使用带透明度的颜色
        transparent_color = QColor(annotation_item.class_color)
        transparent_color.setAlphaF(0.65)
        painter.fillRect(color_rect, transparent_color)

        # 绘制边框
        border_pen = QPen(Qt.black, 1)
        painter.setPen(border_pen)
        painter.drawRect(color_rect)

        # 绘制类别名称
        text_rect = QRect(color_size + 12, 0, width - color_size - 16, height)
        painter.setPen(Qt.black)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, annotation_item.class_name)

        painter.end()
        return pixmap

