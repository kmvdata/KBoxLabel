# annotation_view.py
import json
import time  # 导入time模块用于睡眠
from typing import Tuple, Optional

from PyQt5.QtCore import Qt, QRectF
from PyQt5.QtGui import QPen, QPainter, QBrush, QColor
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsItem, QStyle

from src.core.utils.string_util import StringUtil
from src.models.annotation_category import AnnotationCategory


class AnnotationView(QGraphicsRectItem):
    """表示一个可交互的标注项，使用双线绘制以确保在任何背景下可见"""

    HANDLE_SIZE = 9  # 控制点大小
    HANDLE_MARGIN = 0  # 控制点边距
    OUTER_LINE_WIDTH = 1  # 外侧线宽
    INNER_LINE_WIDTH = 3  # 内侧线宽

    # 控制点类型
    NO_HANDLE = 0
    TOP_LEFT = 1
    TOP_MIDDLE = 2
    TOP_RIGHT = 3
    RIGHT_MIDDLE = 4
    BOTTOM_RIGHT = 5
    BOTTOM_MIDDLE = 6
    BOTTOM_LEFT = 7
    LEFT_MIDDLE = 8

    def __init__(self, x: float, y: float, width: float, height: float, category: AnnotationCategory, parent: any):
        super().__init__(x, y, width, height)
        self.opposite_color = None
        self.current_color = None
        self.category = None
        self.selected: bool = False
        self.set_category(category)
        self.setAcceptDrops(True)  # 启用拖放接受

        # 初始状态下不设置ItemIsMovable标志，只在选中时设置
        self.setFlags(QGraphicsItem.ItemIsSelectable | QGraphicsItem.ItemIsFocusable)
        self.setAcceptHoverEvents(True)

        # 控制点
        self.handles = {}
        self.current_handle = self.NO_HANDLE
        self.handle_selected = False
        self.mouse_press_pos = None
        self.mouse_press_rect = None

        # 确保标注框位于顶层（高于临时绘制元素）
        self.setZValue(10)

        # 创建控制点
        self.update_handles()

        from src.ui.widget.image_canvas.image_canvas import ImageCanvas
        self.image_canvas: Optional[ImageCanvas] = None
        if isinstance(parent, ImageCanvas):
            self.image_canvas = parent

    @staticmethod
    def get_opposite_color(color: QColor) -> QColor:
        """获取与给定颜色完全相反的颜色"""
        return QColor(
            255 - color.red(),
            255 - color.green(),
            255 - color.blue(),
            color.alpha()  # 保持透明度不变
        )

    def set_category(self, category: AnnotationCategory):
        self.category = category
        # 保存当前颜色和相反颜色供绘制使用
        self.current_color = self.category.color
        self.opposite_color = self.get_opposite_color(self.current_color)
        self.update()  # 颜色变化时强制重绘

    def get_outer_rect(self) -> QRectF:
        """计算外侧线条的矩形（比内侧适当扩大）"""
        # 外侧线条向外扩展的距离，基于外侧线宽计算
        expand = self.OUTER_LINE_WIDTH / 2
        inner_rect = self.rect()
        # 向外扩展矩形
        return QRectF(
            inner_rect.x() - expand,
            inner_rect.y() - expand,
            inner_rect.width() + expand * 2,
            inner_rect.height() + expand * 2
        )

    def boundingRect(self):
        """返回包含所有线条和控制点的边界矩形"""
        # 计算需要包含外侧线条的额外空间
        line_expand = self.OUTER_LINE_WIDTH / 2
        rect = self.rect().adjusted(-line_expand, -line_expand, line_expand, line_expand)

        if self.is_selected():
            # 计算需要扩展的边距 (控制点半径 + 边距)
            extra = self.HANDLE_SIZE / 2 + self.HANDLE_MARGIN
            return rect.adjusted(-extra, -extra, extra, extra)
        return rect

    def update_handles(self):
        """更新控制点位置"""
        s = self.HANDLE_SIZE
        m = self.HANDLE_MARGIN
        rect = self.rect()
        x, y, w, h = rect.x(), rect.y(), rect.width(), rect.height()

        self.handles = {
            self.TOP_LEFT: QRectF(x - s / 2 - m, y - s / 2 - m, s, s),
            self.TOP_MIDDLE: QRectF(x + w / 2 - s / 2, y - s / 2 - m, s, s),
            self.TOP_RIGHT: QRectF(x + w - s / 2 + m, y - s / 2 - m, s, s),
            self.RIGHT_MIDDLE: QRectF(x + w - s / 2 + m, y + h / 2 - s / 2, s, s),
            self.BOTTOM_RIGHT: QRectF(x + w - s / 2 + m, y + h - s / 2 + m, s, s),
            self.BOTTOM_MIDDLE: QRectF(x + w / 2 - s / 2, y + h - s / 2 + m, s, s),
            self.BOTTOM_LEFT: QRectF(x - s / 2 - m, y + h - s / 2 + m, s, s),
            self.LEFT_MIDDLE: QRectF(x - s / 2 - m, y + h / 2 - s / 2, s, s),
        }

    def handle_at(self, point):
        """返回指定点处的控制点类型"""
        for k, v in self.handles.items():
            if v.contains(point):
                return k
        return self.NO_HANDLE

    def paint(self, painter, option, widget=None):
        """绘制双线矩形和控制点，内外线不重叠，外侧包裹内侧"""
        # 保存原始状态并临时移除Selected状态
        original_state = option.state
        if option.state & QStyle.State_Selected:
            option.state = option.state & ~QStyle.State_Selected

        # 保存画家状态
        painter.save()

        # 1. 绘制内侧线条（当前颜色，原始坐标）
        inner_pen = QPen(self.current_color, self.INNER_LINE_WIDTH)
        inner_pen.setStyle(Qt.SolidLine)
        inner_pen.setCapStyle(Qt.SquareCap)
        inner_pen.setJoinStyle(Qt.MiterJoin)
        inner_pen.setCosmetic(True)
        painter.setPen(inner_pen)
        painter.drawRect(self.rect())

        # 2. 绘制外侧线条（反色，扩大后的坐标）
        outer_rect = self.get_outer_rect()
        outer_pen = QPen(self.opposite_color, self.OUTER_LINE_WIDTH)
        outer_pen.setStyle(Qt.SolidLine)
        outer_pen.setCapStyle(Qt.SquareCap)
        outer_pen.setJoinStyle(Qt.MiterJoin)
        outer_pen.setCosmetic(True)
        painter.setPen(outer_pen)
        painter.drawRect(outer_rect)

        # 恢复画家状态
        painter.restore()

        # 恢复原始状态
        option.state = original_state

        # 如果选中，绘制控制点
        if self.is_selected():
            painter.setRenderHint(QPainter.Antialiasing, True)
            painter.setPen(QPen(Qt.black, 1, Qt.SolidLine))
            painter.setBrush(QBrush(Qt.white))

            for i, handle in self.handles.items():
                painter.drawRect(handle)

    def hoverMoveEvent(self, event):
        """处理鼠标悬停事件，动态改变光标形状"""
        if not self.is_selected():
            self.setCursor(Qt.ArrowCursor)
            return

        handle = self.handle_at(event.pos())
        rect = self.rect()
        pos = event.pos()

        # 设置控制点光标
        if handle != self.NO_HANDLE:
            if handle in [self.TOP_MIDDLE, self.BOTTOM_MIDDLE]:
                self.setCursor(Qt.SizeVerCursor)
            elif handle in [self.LEFT_MIDDLE, self.RIGHT_MIDDLE]:
                self.setCursor(Qt.SizeHorCursor)
            elif handle in [self.TOP_LEFT, self.BOTTOM_RIGHT]:
                self.setCursor(Qt.SizeFDiagCursor)
            elif handle in [self.TOP_RIGHT, self.BOTTOM_LEFT]:
                self.setCursor(Qt.SizeBDiagCursor)
        elif rect.contains(pos):
            self.setCursor(Qt.SizeAllCursor)  # 可移动光标
        else:
            self.setCursor(Qt.ArrowCursor)

    def hoverLeaveEvent(self, event):
        """鼠标离开时恢复默认光标"""
        self.setCursor(Qt.ArrowCursor)

    def mousePressEvent(self, event):
        """鼠标按下事件处理"""
        # 检查是否点击了控制点
        self.current_handle = self.handle_at(event.pos())
        if self.current_handle != self.NO_HANDLE:
            self.handle_selected = True
            self.mouse_press_pos = event.pos()
            self.mouse_press_rect = self.rect()
            event.accept()
            return  # 不触发选择逻辑

        # 强制单选：选中当前项前清除所有AnnotationView项的选择
        scene = self.scene()
        if scene:
            # 获取场景中所有AnnotationView类型的项并取消选择
            for item in scene.items():
                if isinstance(item, AnnotationView) and item != self:
                    item.set_selected(False)

        self.set_selected(True)  # 选中当前项
        self.setFocus(Qt.MouseFocusReason)  # 设置焦点以接收键盘事件
        # 只更新当前项，其他项会在set_selected中更新
        self.update()
        print(f'set_selected: {self.category} - {self.get_outer_rect()}')
        super().mousePressEvent(event)  # 继续默认事件处理

        # 添加100ms睡眠
        time.sleep(0.1)

    def keyPressEvent(self, event):
        """处理键盘按键事件"""
        # 只有在选中状态下才响应方向键
        if self.is_selected():
            move_distance = 1.0  # 移动距离为1像素
            resize_distance = 1.0  # 调整大小距离为1像素
            rect = self.rect()
            
            # 检查是否按住Shift键
            if event.modifiers() & Qt.ShiftModifier:
                # 按住Shift时，方向键用于扩大/缩小标注框
                if event.key() == Qt.Key_Left:
                    # 向左扩展：右边保持不动，向左扩展（x减小，宽度增加）
                    new_rect = QRectF(rect.x() - resize_distance, rect.y(), rect.width() + resize_distance, rect.height())
                    self.setRect(new_rect)
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Right:
                    # 向右扩展：左边保持不动，向右扩展（宽度增加）
                    new_rect = QRectF(rect.x(), rect.y(), rect.width() + resize_distance, rect.height())
                    self.setRect(new_rect)
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Up:
                    # 向上扩展：下边保持不动，向上扩展（y减小，高度增加）
                    new_rect = QRectF(rect.x(), rect.y() - resize_distance, rect.width(), rect.height() + resize_distance)
                    self.setRect(new_rect)
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Down:
                    # 向下扩展：上边保持不动，向下扩展（高度增加）
                    new_rect = QRectF(rect.x(), rect.y(), rect.width(), rect.height() + resize_distance)
                    self.setRect(new_rect)
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
            else:
                # 根据按键方向移动标注框
                if event.key() == Qt.Key_Left:
                    self.setRect(rect.translated(-move_distance, 0))
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Right:
                    self.setRect(rect.translated(move_distance, 0))
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Up:
                    self.setRect(rect.translated(0, -move_distance))
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
                elif event.key() == Qt.Key_Down:
                    self.setRect(rect.translated(0, move_distance))
                    self.update_handles()
                    self.set_needs_save_annotation()
                    event.accept()
                    return
        
        # 如果不是方向键或者未选中，调用父类方法处理
        super().keyPressEvent(event)

    def mouseMoveEvent(self, event):
        """鼠标移动事件处理"""
        if self.handle_selected and self.current_handle != self.NO_HANDLE:
            self.interactive_resize(event.pos())
            # 如果发生形状改变，image_canvas就需保存新的配置
            self.set_needs_save_annotation()
            return

        # 记录移动前的位置
        old_pos = self.pos()
        # 调用父类方法处理移动
        super().mouseMoveEvent(event)
        # 计算移动后的位置变化
        new_pos = self.pos()
        if old_pos != new_pos:
            # 如果位置改变，标记需要保存
            self.set_needs_save_annotation()

    def mouseReleaseEvent(self, event):
        """鼠标释放事件处理"""
        self.handle_selected = False
        self.current_handle = self.NO_HANDLE
        super().mouseReleaseEvent(event)

    def interactive_resize(self, mouse_pos):
        """交互式调整大小（修复对角线控制点固定问题）"""
        # 获取原始矩形
        original_rect = self.mouse_press_rect
        x, y, w, h = original_rect.x(), original_rect.y(), original_rect.width(), original_rect.height()

        # 获取当前鼠标位置在场景中的坐标
        mouse_x, mouse_y = mouse_pos.x(), mouse_pos.y()

        # 计算鼠标移动的偏移量
        dx = mouse_x - self.mouse_press_pos.x()
        dy = mouse_y - self.mouse_press_pos.y()

        # 根据当前选择的控制点调整矩形（固定对角线控制点）
        if self.current_handle == self.TOP_LEFT:
            # 固定右下角，调整左上角
            new_x = min(original_rect.right(), x + dx)
            new_y = min(original_rect.bottom(), y + dy)
            new_width = original_rect.right() - new_x
            new_height = original_rect.bottom() - new_y
            self.setRect(QRectF(new_x, new_y, new_width, new_height))

        elif self.current_handle == self.TOP_MIDDLE:
            # 固定下边中点，调整上边
            new_y = min(original_rect.bottom(), y + dy)
            new_height = original_rect.bottom() - new_y
            self.setRect(QRectF(x, new_y, w, new_height))

        elif self.current_handle == self.TOP_RIGHT:
            # 固定左下角，调整右上角
            new_width = w + dx
            new_y = min(original_rect.bottom(), y + dy)
            new_height = original_rect.bottom() - new_y
            self.setRect(QRectF(x, new_y, new_width, new_height))

        elif self.current_handle == self.RIGHT_MIDDLE:
            # 固定左边中点，调整右边
            new_width = w + dx
            self.setRect(QRectF(x, y, new_width, h))

        elif self.current_handle == self.BOTTOM_RIGHT:
            # 固定左上角，调整右下角
            new_width = w + dx
            new_height = h + dy
            self.setRect(QRectF(x, y, new_width, new_height))

        elif self.current_handle == self.BOTTOM_MIDDLE:
            # 固定上边中点，调整下边
            new_height = h + dy
            self.setRect(QRectF(x, y, w, new_height))

        elif self.current_handle == self.BOTTOM_LEFT:
            # 固定右上角，调整左下角
            new_x = min(original_rect.right(), x + dx)
            new_width = original_rect.right() - new_x
            new_height = h + dy
            self.setRect(QRectF(new_x, y, new_width, new_height))

        elif self.current_handle == self.LEFT_MIDDLE:
            # 固定右边中点，调整左边
            new_x = min(original_rect.right(), x + dx)
            new_width = original_rect.right() - new_x
            self.setRect(QRectF(new_x, y, new_width, h))

        # 确保尺寸不为负
        rect = self.rect()
        if rect.width() <= 0 or rect.height() <= 0:
            # 恢复原始矩形
            self.setRect(original_rect)

        # 更新控制点位置
        self.update_handles()
        self.update()  # 调整大小后强制重绘

    def to_yolo_format(self, img_width: int, img_height: int) -> Tuple[int, float, float, float, float]:
        """转换为YOLO格式"""
        rect = self.rect()
        x_center = (rect.left() + rect.right()) / 2 / img_width
        y_center = (rect.top() + rect.bottom()) / 2 / img_height
        width = rect.width() / img_width
        height = rect.height() / img_height

        return self.category.class_id, x_center, y_center, width, height

    def to_kolo_format(self, img_width: int, img_height: int) -> Tuple[str, float, float, float, float]:
        """转换为KOLO格式"""
        rect = self.rect()
        x_center = (rect.left() + rect.right()) / 2 / img_width
        y_center = (rect.top() + rect.bottom()) / 2 / img_height
        width = rect.width() / img_width
        height = rect.height() / img_height

        return StringUtil.string_to_base64(self.category.class_name), x_center, y_center, width, height

    # 添加拖放事件处理
    def dragEnterEvent(self, event):
        """处理拖入事件"""
        if event.mimeData().hasFormat('application/x-annotation-category'):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """处理放置事件"""
        if event.mimeData().hasFormat('application/x-annotation-category'):
            # 解析拖拽数据
            data = event.mimeData().data('application/x-annotation-category')
            json_data = data.data().decode('utf-8')
            category_data = json.loads(json_data)

            # 创建AnnotationCategory对象
            from src.models.annotation_category import AnnotationCategory
            dropped_category = AnnotationCategory(
                class_id=category_data['class_id'],
                class_name=category_data['class_name']
            )

            # 调用处理方法
            self.handle_dropped_annotation(dropped_category)
            event.acceptProposedAction()
        else:
            event.ignore()

    def handle_dropped_annotation(self, category):
        """处理拖拽的标注类别"""
        self.set_category(category)
        print(f"拖拽成功! 接收到标注: ID={category.class_id}, 名称='{category.class_name}'")
        self.set_needs_save_annotation()
        if self.image_canvas is not None:
            self.image_canvas.save_annotations()

    def set_selected(self, selected: bool) -> None:
        """重写选中状态设置方法，确保状态变化时触发重绘"""
        if self.selected != selected:
            self.selected = selected
            # 只有在选中时才启用移动功能
            if selected:
                self.setFlags(self.flags() | QGraphicsItem.ItemIsMovable)
            else:
                self.setFlags(self.flags() & ~QGraphicsItem.ItemIsMovable)
            self.update()

    def is_selected(self):
        return self.selected

    def set_needs_save_annotation(self):
        if self.image_canvas is not None:
            setattr(self.image_canvas, 'set_needs_save_annotations', True)
