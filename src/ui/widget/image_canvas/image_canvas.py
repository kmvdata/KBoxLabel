# image_canvas.py
import sys
from decimal import Decimal
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QRectF, QPointF, QSize
from PyQt5.QtGui import QPixmap, QPen, QColor, QPainter, QBrush, QKeySequence, QFontMetrics, QIcon
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QAction,
                             QToolBar, QSizePolicy, QMenu, QFileDialog, QMessageBox, QToolButton, QGraphicsItem)

from src.common.god.korm_base import KOrmBase
from src.models.dto.annotation_category_dto import AnnotationCategoryDTO
from src.core.project_info import ProjectInfo
from src.common.domain.models.kolo_item import KoloItem
from src.ui.widget.annotation_list.annotation_item import AnnotationItem
from src.ui.widget.annotation_list.annotation_list import AnnotationList
from src.ui.widget.image_canvas.annotation_view import AnnotationView


class ImageCanvas(QGraphicsView):
    # 定义缩放常量
    MIN_SCALE = 0.3  # 最小缩放比例（30%）
    MAX_SCALE = 2.0  # 最大缩放比例（200%）
    ZOOM_STEP = 0.1  # 每次缩放步长（原始大小的10%）

    def __init__(self, project_info: ProjectInfo):
        super().__init__()
        self.run_action = None
        self.set_needs_save_annotations = False
        self.project_info = project_info
        self.last_scale_factor = None
        self.gesture_start_scale = None
        self.base_scale = None

        # 初始化annotation list
        self.annotation_list = AnnotationList(self.project_info)
        self.annotation_list.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)

        # 按钮引用
        self.delete_toolbar_action = None
        self.run_tool_button = None  # 运行按钮（QToolButton）
        self.config_menu = None  # 配置菜单
        self.config_button = None  # 配置按钮

        # 添加标志防止递归调用
        self._updating_delete_state = False

        # 添加标志跟踪框选操作
        self._is_rubber_band_selection = False

        # 连接模型加载完成的信号
        self._connect_model_signals()

        # 创建棋盘格背景，模拟透明背景
        checkerboard = QPixmap(20, 20)
        checkerboard.fill(QColor(200, 200, 200))  # 浅灰色背景
        painter = QPainter(checkerboard)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QColor(230, 230, 230))  # 稍深的灰色
        painter.drawRect(0, 0, 10, 10)
        painter.drawRect(10, 10, 10, 10)
        painter.end()

        # 设置棋盘格背景
        self.setBackgroundBrush(QBrush(checkerboard))

        # 设置视图属性
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag) # 启用框选模式
        self.setInteractive(True)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.setInteractive(True)

        # 设置缩放边界
        self.min_scale = self.MIN_SCALE
        self.max_scale = self.MAX_SCALE
        self.current_scale = 1.0  # 当前缩放比例
        self.toolbar_height = 56  # 工具栏高度

        # 启用Pinch手势（用于触摸板捏合缩放）
        self.grabGesture(Qt.GestureType.PinchGesture)

        # 图像和标注数据
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.image_item: Optional[QGraphicsPixmapItem] = None
        self.current_image_path: Optional[Path] = None

        # 绘图状态
        self.drawing = False
        self.start_point = QPointF(0, 0)
        self.current_rect_item = None

        # 临时绘制状态
        self.temp_start_point = None
        self.temp_rect_item = None

        # 设置删除操作 - 快捷键方案
        self.delete_action = QAction("Delete", self)
        delete_shortcuts = [
            QKeySequence.Delete,
            QKeySequence.Back,
            QKeySequence("Backspace")
        ]

        # 为 macOS 添加额外快捷键
        if sys.platform == "darwin":
            delete_shortcuts.extend([
                QKeySequence("Fn+Backspace"),
                QKeySequence("Ctrl+H")
            ])

        self.delete_action.setShortcuts(delete_shortcuts)
        self.delete_action.triggered.connect(self.delete_selected_items) # type: ignore
        self.addAction(self.delete_action)

        # 保存快捷键
        self.save_action = QAction("Save Annotations", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_annotations)  # type: ignore
        self.addAction(self.save_action)

        # 连接场景的选择变化信号
        self.scene.selectionChanged.connect(self.on_selection_changed) # type: ignore

        # 添加上下文菜单策略
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

        # 改为使用QTimer延迟调用
        from PyQt5.QtCore import QTimer
        QTimer.singleShot(1000, lambda: self._load_yolo_model_async())

    def clear_canvas(self):
        """清空画布，只保留背景"""
        self.scene.clear()
        self.image_item = None
        self.current_image_path = None
        self.resetTransform()
        self.current_scale = 1.0

    def clear_annotation_views(self, save_annotations=True):
        """清理场景中所有的AnnotationView标注"""
        # 防止在删除过程中触发过多事件
        self.scene.blockSignals(True)
        try:
            # 收集所有AnnotationView类型的项目
            annotation_items = [item for item in self.scene.items()
                                if isinstance(item, AnnotationView)]

            # 移除所有标注项
            for item in annotation_items:
                self.scene.removeItem(item)

            print(f"已清理 {len(annotation_items)} 个标注项")
            if save_annotations:
                self.save_annotations()
            return len(annotation_items)
        finally:
            self.scene.blockSignals(False)

    def unselect_all_annotations(self):
        """取消所有标注的选中状态"""
        self.scene.clearSelection()  # 先清除Qt原生项的默认选择状态
        for item in self.scene.items():
            if isinstance(item, AnnotationView):
                item.set_selected_flag_internal(False)

    def load_image(self, image_path: Path, reload = False):
        """加载指定路径的图片，并显示到画布上"""
        # 加载图片
        if not image_path.exists():
            raise FileNotFoundError(f"图片文件不存在: {image_path}")
        if not reload and image_path == self.current_image_path:
            print("图片已加载，无需重复加载")
            return
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            raise ValueError(f"无法加载图片: {image_path}")

        # 清除当前场景
        self.scene.clear()
        self.resetTransform()
        self.current_scale = 1.0

        # 添加图片到场景
        self.image_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.current_image_path = image_path

        # 设置视图适应图像
        self.fit_to_window()
        self.current_scale = self.transform().m11()

        # 加载对应的txt标注文件
        self.load_annotations_on_image(image_path, pixmap.width(), pixmap.height())


    # @property
    # def categories(self) -> list[AnnotationCategoryDTO]:
    #     return self.project_info.categories

    def load_annotations_on_image(self, image_path: Path, img_width: int, img_height: int):
        """从SQLite数据库加载与图片同名的kolo_item记录"""
        # 从数据库中查询所有匹配image_name的KoloItem对象
        try:
            # 执行查询
            kolo_items = self.project_info.domain.load_kolo_items_for_image(image_path.name)

            # 处理查询结果
            for kolo_item in kolo_items:
                class_name = kolo_item.class_name

                # 获取类别对象（如果不存在则创建并添加到映射中）
                annotation_item = self.annotation_list.source_model.get_item_by_class_name(class_name)
                if not annotation_item:
                    annotation_item = self.annotation_list.source_model.append_new_category(class_name)

                # 从KoloItem获取归一化坐标
                x_center = Decimal(kolo_item.x_center)
                y_center = Decimal(kolo_item.y_center)
                width = Decimal(kolo_item.width)
                height = Decimal(kolo_item.height)

                # 转换为绝对坐标
                x1 = (x_center - width / 2) * img_width
                y1 = (y_center - height / 2) * img_height
                rect_width = width * img_width
                rect_height = height * img_height

                # 创建AnnotationView并添加到场景
                item = AnnotationView(x1, y1, rect_width, rect_height, category, self)
                self.scene.addItem(item)

                # 把category_map转换为数组，调用 self.project_info.domain.add_categories(new_categories)
                # 确保新增的类别被保存到数据库中
                new_categories = [category for category in self.category_map.values()]
                self.project_info.domain.add_categories(new_categories)

        except Exception as e:
            print(f"从数据库加载标注信息错误: {e}")


    def load_annotation_view_from_kilo_item(self, kolo_item: KoloItem):
        """根据KoloItem对象在画布上添加对应的标注"""
        if not self.current_image_path or self.image_item is None:
            return False  # 没有加载图片，无法添加标注

        try:
            # 从KoloItem对象获取数据
            class_name = kolo_item.class_name
            x_center = Decimal(kolo_item.x_center)
            y_center = Decimal(kolo_item.y_center)
            width = Decimal(kolo_item.width)
            height = Decimal(kolo_item.height)

            # 获取图像尺寸
            img_width = self.image_item.pixmap().width()
            img_height = self.image_item.pixmap().height()

            # 转换为绝对坐标
            x1 = (x_center - width / 2) * img_width
            y1 = (y_center - height / 2) * img_height
            rect_width = width * img_width
            rect_height = height * img_height

            # 获取或创建类别
            category = self.category_map.get(class_name)
            if not category:
                # 创建新类别
                new_category = AnnotationCategoryDTO(
                    class_id=len(self.category_map) + 1,
                    class_name=class_name,
                )
                self.category_map[new_category.class_name] = new_category
                category = new_category
                # 添加到annotation_list
                self.annotation_list.append_category(category)


            # 创建并添加AnnotationView
            item = AnnotationView(x1, y1, rect_width, rect_height, category, self)
            self.scene.addItem(item)
            item.setFlags(item.flags() & ~QGraphicsItem.GraphicsItemFlag.ItemIsMovable)
            item.selected = False
            item.setSelected(False)
            return True

        except Exception as e:
            print(f"加载kolo行时出错: {e}")
            return False

    @property
    def current_annotation_item(self) -> Optional[AnnotationItem]:
        """获取当前要绘制的标注类别，从annotation list中获取当前选中item对应的category，如果没有选中任何item，则返回none"""
        if self.annotation_list:
            return self.annotation_list.get_selected_annotation_item()
        return None

    def wheelEvent(self, event):
        """处理鼠标滚轮事件，支持CTRL+滚轮进行缩放"""
        # 检查是否按下了CTRL键
        if event.modifiers() & Qt.CTRL:
            # 计算缩放因子
            zoom_in_factor = 1.15
            zoom_out_factor = 1 / zoom_in_factor

            # 获取滚轮方向
            if event.angleDelta().y() > 0:
                zoom_factor = zoom_in_factor
            else:
                zoom_factor = zoom_out_factor

            # 以鼠标位置为中心进行缩放
            self.zoom(zoom_factor, event.pos())

            # 阻止事件继续传递
            event.accept()
        else:
            # 不是Ctrl+滚轮，执行默认的滚动行为
            super().wheelEvent(event)

    def zoom(self, factor: float, center_pos=None):
        """执行缩放操作，使用更精确的变换方法"""
        # 计算新的缩放比例
        new_scale = self.current_scale * factor
        # 限制缩放范围
        new_scale = max(self.MIN_SCALE, min(new_scale, self.MAX_SCALE))

        # 计算缩放因子
        scale_factor = new_scale / self.current_scale
        self.current_scale = new_scale

        # 如果提供了中心点，以该点为中心缩放
        if center_pos:
            # 计算缩放中心点的场景坐标
            scene_center = self.mapToScene(center_pos)

            # 保存当前视图中心点
            old_view_center = self.viewport().rect().center()
            old_scene_center = self.mapToScene(old_view_center)

            # 应用缩放
            self.scale(scale_factor, scale_factor)

            # 计算新的视图中心点
            new_view_center = self.viewport().rect().center()
            new_scene_center = self.mapToScene(new_view_center)

            # 计算需要平移的距离（以场景坐标）
            delta = scene_center - (new_scene_center - (old_scene_center - scene_center))

            # 平移视图使缩放中心点保持不变
            self.translate(delta.x(), delta.y())
        else:
            # 直接缩放
            self.scale(scale_factor, scale_factor)

    def mousePressEvent(self, event):
        self.viewport().update()
        if event.button() == Qt.LeftButton:
            # 检查是否点击在现有标注或其锚点上
            clicked_item = self.itemAt(event.pos())
            is_annotation = isinstance(clicked_item, AnnotationView) or (
                    clicked_item and clicked_item.parentItem() and
                    isinstance(clicked_item.parentItem(), AnnotationView)
            )

            # 检查是否按住Shift键
            shift_pressed = event.modifiers() & Qt.ShiftModifier
            
            # 只有在点击的不是标注且没有按住Shift键且不是框选操作时才取消所有选中状态
            if not is_annotation and not shift_pressed and not self._is_rubber_band_selection:
                self.unselect_all_annotations()

            # 当设置了当前类别时开始绘制新标注，但按住Shift键时不创建新标注
            if not is_annotation and self.current_annotation_item is not None and not shift_pressed:
                self.start_point = self.mapToScene(event.pos())
                self.drawing = True

                # 创建临时矩形框
                self.temp_rect_item = self.scene.addRect(
                    QRectF(self.start_point, self.start_point),
                    QPen(Qt.red, 2, Qt.DashLine)
                )
                self.temp_rect_item.setZValue(10000)  # 确保在最上层显示
                return  # 拦截事件，避免默认处理

            # 如果点击在标注上且按住Shift键，切换该标注的选中状态
            if is_annotation and shift_pressed:
                if isinstance(clicked_item, AnnotationView):
                    clicked_item.clicked_with_shift()
                elif clicked_item.parentItem() and isinstance(clicked_item.parentItem(), AnnotationView):
                    _parent_item = clicked_item.parentItem()
                    if hasattr(_parent_item, 'clicked_with_shift'):
                        _parent_item.clicked_with_shift()
                return  # 拦截事件，避免默认处理

        super().mousePressEvent(event)  # 继续默认事件处理

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件，无论操作是什么都保存标注"""
        created_new_annotation = False
        # 检查是否按住Shift键
        shift_pressed = event.modifiers() & Qt.ShiftModifier
        
        if self.drawing and event.button() == Qt.LeftButton:
            self.drawing = False
            current_point = self.mapToScene(event.pos())

            # 获取最终矩形框
            rect = QRectF(self.start_point, current_point).normalized()

            # 确保矩形在图像范围内
            scene_rect = self.scene.sceneRect()
            rect = rect.intersected(scene_rect)

            # 无论尺寸是否满足，先移除临时矩形（避免残留）
            if self.temp_rect_item:
                self.scene.removeItem(self.temp_rect_item)
                self.temp_rect_item = None

            # 检查矩形尺寸：宽度和高度都必须至少为10px
            # 但按住Shift键时不创建新标注
            if rect.width() >= 10 and rect.height() >= 10 and not shift_pressed:
                # 创建新AnnotationView并设置当前类别
                item = AnnotationView(
                    Decimal(rect.x()), Decimal(rect.y()), Decimal(rect.width()), Decimal(rect.height()),
                    self.current_annotation_item,
                    self
                )
                self.scene.addItem(item)
                self.save_annotations()

                # 自动选中新创建的标注
                item.select_annotation_view()
                created_new_annotation = True

        # 如果没有创建新的标注，则处理选择逻辑
        if not created_new_annotation:
            # 检查是否点击在现有标注或其锚点上
            clicked_item = self.itemAt(event.pos())
            is_annotation = isinstance(clicked_item, AnnotationView) or (
                    clicked_item and clicked_item.parentItem() and
                    isinstance(clicked_item.parentItem(), AnnotationView)
            )
            
            # 只有点击空白区域且未按住Shift键时才清除选择
            if not is_annotation and not shift_pressed:
                # 取消annotation_list中的选中状态
                if self.annotation_list and self.annotation_list.selectionModel():
                    self.annotation_list.selectionModel().clearSelection()
                # 取消画布上所有标注的选中状态
                self.unselect_all_annotations()

        # 处理框选完成后的标注选择
        if self.rubberBandRect().isValid() and not self.drawing:
            # 获取框选区域
            rubber_band_rect = self.rubberBandRect()
            if not rubber_band_rect.isNull() and rubber_band_rect.width() > 1 and rubber_band_rect.height() > 1:
                # 将视图坐标转换为场景坐标
                scene_top_left = self.mapToScene(rubber_band_rect.topLeft())
                scene_bottom_right = self.mapToScene(rubber_band_rect.bottomRight())
                scene_rect = QRectF(scene_top_left, scene_bottom_right)
                
                # 查找框选区域内的所有标注
                items_in_rect = self.scene.items(scene_rect, Qt.ItemSelectionMode.IntersectsItemShape, 
                                                Qt.SortOrder.AscendingOrder, self.transform())
                
                # 检查是否按住Shift键进行多选
                shift_pressed = event.modifiers() & Qt.ShiftModifier
                
                # 如果没有按住Shift键，先清除所有选中状态
                if not shift_pressed:
                    self.unselect_all_annotations()
                
                # 选择框选区域内的所有AnnotationView
                selected_count = 0
                for item in items_in_rect:
                    if isinstance(item, AnnotationView):
                        # 直接设置选中状态，而不是调用select_annotation_view方法
                        # 因为select_annotation_view会取消其他项的选中状态，不适合多选场景
                        item.set_selected_flag_internal(True)
                        selected_count += 1
                        
                # 更新annotation_list的选中状态
                self._update_annotation_list_selection()
                        
        # 重置框选标志（无论是否进行了框选操作）
        self._is_rubber_band_selection = False
                        
        # 每次鼠标释放都保存标注
        if self.set_needs_save_annotations:
            self.save_annotations()

        super().mouseReleaseEvent(event)
        
        # 每次鼠标释放时刷新画布
        self.viewport().update()

    def mouseDoubleClickEvent(self, event):
        """处理鼠标双击事件"""
        if event.button() == Qt.LeftButton:
            # 获取双击位置的项
            clicked_item = self.itemAt(event.pos())
            
            # 检查是否是AnnotationView且当前已选中
            if isinstance(clicked_item, AnnotationView) and clicked_item.isSelected():
                # 调用send_selected_to_back方法
                self.send_selected_to_back()
                
                # 重新选择双击位置的项
                scene_pos = self.mapToScene(event.pos())
                items_at_pos = self.scene.items(scene_pos)
                
                # 查找AnnotationView项并选中第一个
                for item in items_at_pos:
                    if isinstance(item, AnnotationView):
                        # 修改这里，使用select_single_annotation确保同步
                        self.select_single_annotation(item)
                        break

                return
                
        super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        # 更新临时矩形框
        if self.drawing and self.temp_rect_item is not None:
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.temp_rect_item.setRect(rect)
            return  # 拦截事件，避免默认处理

        # 如果开始框选，设置标志
        if not self._is_rubber_band_selection and self.dragMode() == QGraphicsView.DragMode.RubberBandDrag:
            self._is_rubber_band_selection = True

        super().mouseMoveEvent(event)


    def delete_selected_items(self):
        """删除所有选中的标注项"""
        # 防止在删除过程中触发过多事件
        self.scene.blockSignals(True)

        try:
            # 获取通过Qt标准选择机制选中的项
            qt_selected_items = self.scene.selectedItems()
            
            # 获取选中的项
            custom_selected_items = [item for item in self.scene.items()
                                     if isinstance(item, AnnotationView) and item.isSelected()]
            
            # 合并两种方式选中的项并去重
            selected_items = list(set(qt_selected_items + custom_selected_items))

            if not selected_items:
                return

            for item in selected_items:
                self.scene.removeItem(item)

            if len(selected_items) > 0:
                # 如果删除了annotation, 立即保存
                self.save_annotations()
                
            # 清除annotation_list中的选中状态
            if self.annotation_list and self.annotation_list.selectionModel():
                self.annotation_list.selectionModel().clearSelection()
                
            print(f"已删除 {len(selected_items)} 个标注项")

        finally:
            self.scene.blockSignals(False)
            self.save_annotations()

    def save_annotations(self):
        """保存当前所有标注到txt文件，按class_id排序"""
        if not self.current_image_path or self.image_item is None:
            return False

        self.set_needs_save_annotations = False

        img_width = self.image_item.pixmap().width()
        img_height = self.image_item.pixmap().height()

        try:
            # 收集所有AnnotationView并按class_id排序
            annotations = []
            for item in self.scene.items():
                if isinstance(item, AnnotationView):
                    annotations.append(item)

            # 按class_id排序
            annotations.sort(key=lambda _item: _item.category.class_name)

            # 创建kolo_item_list用于存储KoloItem对象
            kolo_item_list = []

            for item in annotations:
                # 获取当前在场景中的绝对位置和大小（修复：使用sceneBoundingRect获取最新位置）
                rect = item.sceneBoundingRect()
                x = rect.x()
                y = rect.y()
                width = rect.width()
                height = rect.height()

                # 计算归一化坐标
                x_center = (x + width / 2) / img_width
                y_center = (y + height / 2) / img_height
                norm_width = width / img_width
                norm_height = height / img_height

                # 从当前图片路径获取图片名称
                image_name = self.current_image_path.name
                kolo_item_list.append(KoloItem(
                    kid=KOrmBase.snowflake.gen_kid(),
                    image_name=image_name,
                    class_name=item.category.class_name,
                    x_center=x_center,
                    y_center=y_center,
                    width=norm_width,
                    height=norm_height
                ))

            # 在事务中删除所有image_name的kolo_item, 然后插入新的kolo_item_list中的对象
            def transaction_func(session):
                # 删除所有与当前图片相关的旧记录
                session.query(KoloItem).filter(KoloItem.image_name == self.current_image_path.name).delete()

                # 插入新的KoloItem对象
                for kolo_item in kolo_item_list:
                    session.add(kolo_item)

            # 执行事务
            self.project_info.domain.execute_in_transaction(transaction_func)
            
            return True
        except Exception as e:
            print(f"保存标注文件时出错: {e}")
            return False

    def create_yolo_menu(self):
        """创建YOLO配置菜单，包含run, edit, delete选项"""
        self.config_menu = QMenu(self)

        # 运行子菜单
        self.run_action = QAction("Run", self)
        self.run_action.triggered.connect(self.on_run_clicked)  # type: ignore
        # 运行选项状态通过project_info判断
        self.run_action.setEnabled(self.project_info.is_model_loaded)
        self.config_menu.addAction(self.run_action)

        # 编辑子菜单
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self.select_yolo_model)  # type: ignore
        self.config_menu.addAction(edit_action)

        # 删除子菜单
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_yolo_model)  # type: ignore
        # 删除选项只在有模型时可用（通过project_info判断）
        delete_action.setEnabled(self.project_info.is_model_loaded)
        self.config_menu.addAction(delete_action)

    def show_config_menu(self):
        """显示配置菜单，在按钮位置弹出"""
        if self.config_menu:
            # 更新菜单状态（通过project_info判断模型是否存在）
            model_exists = self.project_info.is_model_loaded
            for action in self.config_menu.actions():
                if action.text() == "Run" or action.text() == "Delete":
                    action.setEnabled(model_exists)
            # 在按钮下方显示菜单
            self.config_menu.exec_(self.config_button.mapToGlobal(self.config_button.rect().bottomLeft()))

    def select_yolo_model(self):
        """选择YOLO模型的pt文件，直接引用原位置文件"""
        # 获取上次打开的目录
        from src.core.ksettings import KSettings
        settings = KSettings()
        last_directory = settings.get_last_opened_directory()

        # 打开文件选择对话框，使用上次打开的目录作为默认目录
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select YOLO Model", last_directory, "YOLO Model Files (*.pt)"
        )

        if file_path:
            # 保存当前选择的目录
            settings.set_last_opened_directory(str(Path(file_path).parent))

            model_path = Path(file_path)  # 模型文件路径

            try:
                # 直接引用原位置的模型文件
                self.project_info.yolo_model_path = str(model_path)
                # 异步加载模型到project_info的yolo_executor
                self._load_yolo_model_async(model_path)

            except Exception as e:
                # 捕获加载异常
                QMessageBox.warning(
                    self, "Load Failed",
                    f"Failed to load model:\n{str(e)}"
                )
        else:
            QMessageBox.information(self, "Cancelled", "Model selection cancelled.")

    def _load_yolo_model_async(self, model_path: Optional[Path] =None):
        # 开始加载模型
        self.project_info.load_yolo_model(model_path)
        self.run_action.setEnabled(self.project_info.is_model_loaded)
        self.run_tool_button.setEnabled(self.project_info.is_model_loaded)

    def delete_yolo_model(self):
        """删除已选择的YOLO模型配置"""
        self.project_info.delete_yolo_model()

    # 然后是调用YOLOExecutor的代码（例如UI类中的方法）
    def on_run_clicked(self):
        """执行YOLO模型的方法，识别当前图片目标并按指定格式输出日志"""
        import logging
        # 检查模型是否加载
        if not self.project_info.is_model_loaded:
            QMessageBox.warning(self, "Warning", "No YOLO model selected! Please configure a model first.")
            return

        # 检查是否有当前图片
        if not self.current_image_path or not self.image_item:
            QMessageBox.warning(self, "Warning", "No image loaded! Please load an image first.")
            return

        try:
            self.clear_annotation_views(save_annotations=False)
            # 调用YOLOExecutor的exec_yolo方法（复用已有实现）
            detection_results = self.project_info.exec_yolo(img_path=self.current_image_path, save_to_db=True)

            # 输出检测结果并复用load_kolo_line方法
            model_name = self.project_info.model_name
            if detection_results:
                logging.info("YOLO detection results:")
                for kolo_item in detection_results:
                    logging.info(kolo_item)
                    self.load_annotation_view_from_kilo_item(kolo_item)  # 复用加载到画布的方法
                
                # 保存自动生成的标注结果
                self.save_annotations()
            else:
                logging.info("No objects detected by YOLO model")
                QMessageBox.information(
                    self, "Detection Complete",
                    f"No objects detected using {model_name}"
                )

        except ImportError:
            QMessageBox.critical(
                self, "Library Missing",
                "Please install ultralytics library first: pip install ultralytics"
            )
        except Exception as e:
            error_msg = f"Error executing YOLO model: {str(e)}"
            logging.error(error_msg)
            QMessageBox.critical(self, "Execution Error", error_msg)

    @staticmethod
    def _get_icon(theme_name, fallback_text):
        """获取系统主题图标，如果不存在则创建一个简单的文本图标"""
        icon = QIcon.fromTheme(theme_name)
        if icon.isNull():
            # 创建一个简单的文本图标
            pixmap = QPixmap(24, 24)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.Antialiasing)
            painter.setPen(QPen(Qt.black, 1))
            painter.setBrush(QBrush(Qt.white))
            painter.drawRoundedRect(0, 0, 23, 23, 4, 4)

            font = painter.font()
            font.setBold(True)
            font.setPointSize(10)
            painter.setFont(font)

            # 计算文本位置以居中
            metrics = QFontMetrics(font)
            text_width = metrics.width(fallback_text)
            text_height = metrics.height()
            x = (24 - text_width) / 2
            y = (24 + text_height) / 2 - 2  # 减2是为了垂直居中

            painter.drawText(int(x), int(y), fallback_text)
            painter.end()
            return QIcon(pixmap)
        return icon


    def create_toolbar(self):
        """创建并返回一个工具栏，包含缩放控制按钮、删除按钮和YOLO相关按钮"""
        toolbar = QToolBar("Image Tools")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setFixedHeight(self.toolbar_height)  # 应用工具栏高度设置

        # 尝试加载系统主题图标，如果失败则使用文本
        try:
            # 创建缩放相关按钮
            self._create_zoom_actions(toolbar)

            # 添加分隔线
            toolbar.addSeparator()

            # 创建YOLO相关按钮
            self._create_yolo_actions(toolbar, use_icons=True)

        except Exception as e:
            print(f"创建工具栏时出错: {e}")
            # 创建纯文本工具栏作为备选方案
            self._create_text_toolbar(toolbar)

        return toolbar

    def _create_text_toolbar(self, toolbar):
        """创建纯文本工具栏作为备选方案"""
        # 创建缩放相关按钮
        self._create_zoom_actions(toolbar)

        # 添加分隔线
        toolbar.addSeparator()

        # 创建YOLO相关按钮
        self._create_yolo_actions(toolbar, use_icons=False)

    def _create_zoom_actions(self, toolbar):
        """创建缩放相关的动作按钮"""
        # Zoom In
        zoom_in_action = QAction("Zoom In", self)
        zoom_in_action.setIcon(self._get_icon("zoom-in", "+"))
        zoom_in_action.setToolTip("Zoom In (10%)")
        zoom_in_action.triggered.connect(self.zoom_in)  # type: ignore
        toolbar.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("Zoom Out", self)
        zoom_out_action.setIcon(self._get_icon("zoom-out", "-"))
        zoom_out_action.setToolTip("Zoom Out (10%)")
        zoom_out_action.triggered.connect(self.zoom_out)  # type: ignore
        toolbar.addAction(zoom_out_action)

        # 1:1
        reset_zoom_action = QAction("1:1", self)
        reset_zoom_action.setIcon(self._get_icon("zoom-original", "1:1"))
        reset_zoom_action.setToolTip("Reset Zoom to Original Size")
        reset_zoom_action.triggered.connect(self.reset_zoom) # type: ignore
        toolbar.addAction(reset_zoom_action)

        # Fit Width
        fit_width_action = QAction("Fit Width", self)
        fit_width_action.setIcon(self._get_icon("zoom-fit-width", "Fit W"))
        fit_width_action.setToolTip("Fit image width to window")
        fit_width_action.triggered.connect(self.fit_to_width)  # type: ignore
        toolbar.addAction(fit_width_action)

        # Fit Height
        fit_height_action = QAction("Fit Height", self)
        fit_height_action.setIcon(self._get_icon("zoom-fit-height", "Fit H"))
        fit_height_action.setToolTip("Fit image height to window")
        fit_height_action.triggered.connect(self.fit_to_height)  # type: ignore
        toolbar.addAction(fit_height_action)

    def _create_yolo_actions(self, toolbar, use_icons=True):
        """创建YOLO相关的动作按钮"""
        # YOLO Run Button - 使用QToolButton
        self.run_tool_button = QToolButton()
        self.run_tool_button.setText("Run")
        if use_icons:
            self.run_tool_button.setIcon(self._get_icon("system-run", "▶"))
        self.run_tool_button.setToolTip("Run YOLO model")
        self.run_tool_button.setIconSize(QSize(24, 24))
        self.run_tool_button.setFixedSize(50, 56)  # 与Config按钮尺寸一致
        self.run_tool_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)  # 文本在图标下方
        self.run_tool_button.setStyleSheet("""
            QToolButton {
                text-align: center;
                padding-top: 2px;
                padding-bottom: 2px;
            }
            QToolButton::icon {
                subcontrol-position: top;
                subcontrol-origin: padding;
                margin-bottom: 4px;  /* 图标和文字之间的间距 */
            }
            QToolButton::text {
                padding: 0px;
            }
            QToolButton:disabled {
                color: #888888;
                icon-size: 24px;
            }
        """)
        self.run_tool_button.clicked.connect(self.on_run_clicked)  # type: ignore
        # 根据是否有模型设置初始状态（通过project_info判断）
        self.run_tool_button.setEnabled(bool(getattr(self.project_info, 'yolo_model_path', None)))
        toolbar.addWidget(self.run_tool_button)

        # 创建YOLO配置菜单
        self.create_yolo_menu()

        # YOLO Config Button - 使用QToolButton，与Run按钮风格一致
        self.config_button = QToolButton()
        self.config_button.setText("Config")
        if use_icons:
            self.config_button.setIcon(self._get_icon("configure", "⋮"))
        self.config_button.setToolTip("YOLO model configuration")
        self.config_button.setIconSize(QSize(24, 24))
        self.config_button.setFixedSize(50, 56)  # 与Run按钮尺寸一致
        self.config_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)  # 文本在图标下方
        self.config_button.setStyleSheet("""
            QToolButton {
                text-align: center;
                padding-top: 2px;
                padding-bottom: 2px;
            }
            QToolButton::icon {
                subcontrol-position: top;
                subcontrol-origin: padding;
                margin-bottom: 4px;  /* 图标和文字之间的间距 */
            }
            QToolButton::text {
                padding: 0px;
            }
        """)  # 确保文字在图标正下方且垂直居中
        self.config_button.clicked.connect(self.show_config_menu)  # type: ignore
        toolbar.addWidget(self.config_button)

    def zoom_in(self):
        """放大10%，最多放大至200%"""
        # 计算目标缩放比例（相对于原始大小）
        target_scale = self.current_scale + self.ZOOM_STEP
        if target_scale > self.MAX_SCALE:
            target_scale = self.MAX_SCALE

        # 如果已经达到最大，不执行操作
        if target_scale <= self.current_scale:
            return

        # 计算相对于当前缩放的缩放因子
        scale_factor = target_scale / self.current_scale

        # 以视图中心为缩放中心
        center_pos = self.viewport().rect().center()
        self.zoom(scale_factor, center_pos)

    def zoom_out(self):
        """缩小10%，最多缩小至30%"""
        # 计算目标缩放比例（相对于原始大小）
        target_scale = self.current_scale - self.ZOOM_STEP
        if target_scale < self.MIN_SCALE:
            target_scale = self.MIN_SCALE

        # 如果已经达到最小，不执行操作
        if target_scale >= self.current_scale:
            return

        # 计算相对于当前缩放的缩放因子
        scale_factor = target_scale / self.current_scale

        # 以视图中心为缩放中心
        center_pos = self.viewport().rect().center()
        self.zoom(scale_factor, center_pos)

    def reset_zoom(self):
        """重置为1:1原始比例"""
        self.resetTransform()
        self.current_scale = 1.0

    def fit_to_window(self):
        """将图片调整到最适合窗口的大小（保持宽高比）"""
        self.fitInView(self.scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.current_scale = self.transform().m11()

    def fit_to_width(self):
        """将图片宽度调整到匹配窗口宽度，高度按比例缩放"""
        if self.image_item is None:
            return

        # 重置变换
        self.resetTransform()

        # 计算宽度缩放因子
        view_width = self.viewport().width()
        scene_width = self.scene.sceneRect().width()
        if scene_width <= 0:
            return

        scale_factor = view_width / scene_width
        self.scale(scale_factor, scale_factor)
        self.current_scale = scale_factor

        # 确保图片居中显示
        self.centerOn(self.scene.sceneRect().center())

    def fit_to_height(self):
        """将图片高度调整到匹配窗口高度，宽度按比例缩放"""
        if self.image_item is None:
            return

        # 重置变换
        self.resetTransform()

        # 计算高度缩放因子
        view_height = self.viewport().height()
        scene_height = self.scene.sceneRect().height()
        if scene_height <= 0:
            return

        scale_factor = view_height / scene_height
        self.scale(scale_factor, scale_factor)
        self.current_scale = scale_factor

        # 确保图片居中显示
        self.centerOn(self.scene.sceneRect().center())

    def on_selection_changed(self):
        """处理场景中选择变化的事件"""
        # 先获取选中的标注项
        selected_items = [item for item in self.scene.items()
                          if isinstance(item, AnnotationView) and item.isSelected()]

        # 如果选中多个项，清除annotation_list中的选中状态
        if len(selected_items) > 1:
            if self.annotation_list and self.annotation_list.selectionModel():
                self.annotation_list.selectionModel().clearSelection()
            return
            
        # 如果没有选中项，也清除annotation_list中的选中状态
        if not selected_items:
            return

        # 获取第一个选中的标注的类别
        first_item = selected_items[0]

        # 检查该类别是否已存在于annotation_list中
        exists = self.annotation_list.source_model.get_item_by_class_name(first_item.class_name)

        if not exists:
            # 如果不存在，添加到列表末尾
            self.annotation_list.source_model.append_new_category(first_item.class_name)

        # 发射信号通知选中的标注类别
        # self.annotation_selected.emit(category)

        # 选中列表中对应的项
        if self.annotation_list:
            self.annotation_list.select_category_by_name(first_item.class_name)

    def show_context_menu(self, position):
        """显示上下文菜单"""
        context_menu = QMenu(self)
        scene_pos = self.mapToScene(position)

        # 检查是否有选中的标注项
        selected_items = [item for item in self.scene.items()
                          if isinstance(item, AnnotationView) and item.isSelected()]
        
        # 如果有选中的标注项，添加"放置最底层"选项
        if selected_items:
            send_to_back_action = QAction("放置最底层", self)
            send_to_back_action.triggered.connect(self.send_selected_to_back)   # type: ignore
            context_menu.addAction(send_to_back_action)
            
            # 添加删除选项
            delete_action = QAction("删除", self)
            delete_action.triggered.connect(self.delete_selected_items)   # type: ignore
            context_menu.addAction(delete_action)
            
            # 添加分隔线
            context_menu.addSeparator()

        # 添加"全部清空"选项
        clear_all_action = QAction("全部清空", self)
        clear_all_action.triggered.connect(self.clear_all_annotations)  # type: ignore
        context_menu.addAction(clear_all_action)
        
        # 查找点击位置下的所有AnnotationView对象
        items_at_pos = self.scene.items(scene_pos)
        annotation_views_at_pos = [item for item in items_at_pos 
                                  if isinstance(item, AnnotationView)]
        
        # 如果点击位置有AnnotationView，则添加图层菜单项
        if annotation_views_at_pos:
            # 添加分隔线
            context_menu.addSeparator()
            
            # 按zValue排序，从高到低显示
            sorted_annotations = sorted(annotation_views_at_pos, 
                                     key=lambda item: item.zValue(), reverse=True)
            
            # 为每个AnnotationView添加菜单项到一级菜单
            for annotation in sorted_annotations:
                action = QAction(annotation.category.class_name, self)
                # 确保在选择时取消其他项的选中状态，并同步更新annotation_list
                action.triggered.connect(  # type: ignore
                    lambda checked, ann=annotation: self.select_single_annotation(ann) or print('kkkkkkk')
                )
                context_menu.addAction(action)

        # 在鼠标位置显示菜单
        context_menu.exec_(self.mapToGlobal(position))

    def send_selected_to_back(self):
        """将选中的标注项放置到最底层"""
        # 获取所有AnnotationView项
        annotation_items = [item for item in self.scene.items() 
                           if isinstance(item, AnnotationView)]

        if not annotation_items:
            return

        # 把选中的item值设置为最小值
        for item in annotation_items:
            if item.isSelected():
                item.send_to_back()

        # 操作完成后刷新画布
        self.viewport().update()

    def clear_all_annotations(self):
        """清空所有标注并删除对应的.kolo文件"""
        if not self.current_image_path or self.image_item is None:
            return

        # 确认操作
        reply = QMessageBox.question(
            self, "确认清空", "确定要清空所有标注并删除标注文件吗？",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清空画布上的所有标注
            self.clear_annotation_views()

            # 删除对应的.kolo文件
            kolo_path = self.current_image_path.with_suffix('.kolo')
            if kolo_path.exists():
                try:
                    kolo_path.unlink()
                    print(f"已删除标注文件: {kolo_path}")
                except Exception as e:
                    print(f"删除标注文件时出错: {e}")
                    QMessageBox.warning(self, "错误", f"删除标注文件时出错:\n{str(e)}")

            # 保存状态更新
            self.set_needs_save_annotations = False

    def reload_image(self):
        """重新加载当前显示的图片（如果存在）"""
        self.load_image(self.current_image_path, reload=True)

    def _connect_model_signals(self):
        """连接模型加载相关的信号"""
        # 为了确保能接收到模型加载完成的信号，我们需要在project_info中添加信号连接
        pass  # 实际的信号连接在RefProjectInfo中处理

    def _on_model_load_finished(self, success: bool, error_message: str):
        """缓存模型加载完成的回调"""
        if success:
            # 模型加载成功，启用Run按钮
            if self.run_tool_button:
                self.run_tool_button.setEnabled(True)
            print("缓存的YOLO模型加载成功")
        else:
            print(f"缓存的YOLO模型加载失败: {error_message}")

    def _update_annotation_list_selection(self):
        """更新annotation_list的选中状态以匹配画布上的选中项"""
        # 获取画布上所有选中的标注项
        selected_items = [item for item in self.scene.items()
                         if isinstance(item, AnnotationView) and item.isSelected()]
                         
        # 如果选中多个项或没有选中项，清除annotation_list中的选中状态
        if len(selected_items) != 1:
            if self.annotation_list and self.annotation_list.selectionModel():
                self.annotation_list.selectionModel().clearSelection()
        else:
            # 如果只选中一个项，更新annotation_list中的选中状态
            selected_item = selected_items[0]
            self.annotation_list.select_category_by_name(selected_item.class_name)

    def select_single_annotation(self, annotation_view):
        """选中单个标注视图，取消其他所有标注视图的选中状态，并同步更新annotation_list"""
        # 取消所有其他标注的选中状态
        for item in self.scene.items():
            if isinstance(item, AnnotationView) and item != annotation_view:
                item.set_selected_flag_internal(False)
        
        # 选中指定的标注视图
        annotation_view.select_annotation_view()
        
        # 同步更新annotation_list
        if self.annotation_list:
            self.annotation_list.select_category_by_name(annotation_view.class_name)

        # 刷新画布
        self.viewport().update()