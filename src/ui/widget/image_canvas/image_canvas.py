# image_canvas.py
import json
import sys
from pathlib import Path
from typing import Optional

from PyQt5.QtCore import Qt, QRectF, QPointF, QEvent, QSize, pyqtSignal
from PyQt5.QtGui import QPixmap, QPen, QColor, QPainter, QBrush, QKeySequence, QFontMetrics, QIcon
from PyQt5.QtWidgets import (QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QAction,
                             QToolBar, QSizePolicy, QMenu, QFileDialog, QMessageBox, QToolButton)

from src.common.god.korm_base import KOrmBase
from src.core.utils.string_util import StringUtil
from src.models.dto.annotation_category import AnnotationCategory
from src.models.dto.ref_project_info import RefProjectInfo
from src.models.sql import KoloItem
from src.ui.widget.image_canvas.annotation_list import AnnotationList
from src.ui.widget.image_canvas.annotation_view import AnnotationView


class ImageCanvas(QGraphicsView):
    # 定义缩放常量
    MIN_SCALE = 0.3  # 最小缩放比例（30%）
    MAX_SCALE = 2.0  # 最大缩放比例（200%）
    ZOOM_STEP = 0.1  # 每次缩放步长（原始大小的10%）
    annotation_selected = pyqtSignal(AnnotationCategory)  # 选中标注时发射信号

    def __init__(self, project_info: RefProjectInfo):
        super().__init__()
        self.set_needs_save_annotations = False
        self.project_info = project_info
        self.last_scale_factor = None
        self.gesture_start_scale = None
        self.base_scale = None
        self.annotation_list = None
        self.create_annotation_list()

        # 按钮引用
        self.delete_toolbar_action = None
        self.run_tool_button = None  # 运行按钮（QToolButton）
        self.config_menu = None  # 配置菜单
        self.config_button = None  # 配置按钮

        # 添加标志防止递归调用
        self._updating_delete_state = False

        # 连接模型加载完成的信号
        self._connect_model_signals()

        # 加载已保存的模型配置
        self.load_model_config()

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
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)  # 启用框选模式
        self.setInteractive(True)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self.setMouseTracking(True)
        self.setInteractive(True)

        # 设置缩放边界
        self.min_scale = self.MIN_SCALE
        self.max_scale = self.MAX_SCALE
        self.current_scale = 1.0  # 当前缩放比例
        self.toolbar_height = 56  # 工具栏高度

        # 启用Pinch手势（用于触摸板捏合缩放）
        self.grabGesture(Qt.PinchGesture)

        # 图像和标注数据
        self.scene = QGraphicsScene(self)
        self.setScene(self.scene)
        self.image_item: Optional[QGraphicsPixmapItem] = None
        self.current_image_path: Optional[Path] = None

        # 存储标注类别
        self.category_map = {}  # 用于快速查找class_name对应的类别

        # 绘图状态
        self.drawing = False
        self.start_point = QPointF(0, 0)
        self.current_rect_item = None
        self.current_category: Optional[AnnotationCategory] = None

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
        self.delete_action.triggered.connect(self.delete_selected_items)
        self.addAction(self.delete_action)

        # 保存快捷键
        self.save_action = QAction("Save Annotations", self)
        self.save_action.setShortcut(QKeySequence.Save)
        self.save_action.triggered.connect(self.save_annotations)
        self.addAction(self.save_action)

        # 连接场景的选择变化信号
        self.scene.selectionChanged.connect(self.on_selection_changed)

        # 连接列表的选择变化到画布
        if self.annotation_list:
            self.annotation_list.annotation_selected.connect(self.on_list_annotation_selected)

        # 添加上下文菜单策略
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def clear_canvas(self):
        """清空画布，只保留背景"""
        self.scene.clear()
        self.image_item = None
        self.current_image_path = None
        self.resetTransform()
        self.current_scale = 1.0
        self.update_delete_button_state()

    def clear_annotation_views(self):
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

            # 更新删除按钮状态
            self.update_delete_button_state()

            print(f"已清理 {len(annotation_items)} 个标注项")
            return len(annotation_items)
        finally:
            self.scene.blockSignals(False)
            
    def unselect_all_annotations(self):
        """取消所有标注的选中状态"""
        for item in self.scene.items():
            if isinstance(item, AnnotationView):
                item.set_selected(False)

    def load_image(self, image_path: Path):
        """加载指定路径的图片，并显示到画布上"""
        # 加载图片
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            raise ValueError(f"无法加载图片: {image_path}")

        # 清除当前场景
        self.scene.clear()
        self.resetTransform()
        self.current_scale = 1.0

        # 保存标注类别信息
        self.category_map = {category.class_name: category for category in self.categories}

        # 添加图片到场景
        self.image_item = self.scene.addPixmap(pixmap)
        self.scene.setSceneRect(self.image_item.boundingRect())
        self.current_image_path = image_path

        # 设置视图适应图像
        self.fit_to_window()
        self.current_scale = self.transform().m11()

        # 加载对应的txt标注文件
        self._load_kolo_file(image_path, pixmap.width(), pixmap.height())

        # 加载图片后更新删除按钮状态
        self.update_delete_button_state()
        
        # 根据规范，加载图片后需要取消所有标注的选中状态
        self.unselect_all_annotations()

    @property
    def categories(self) -> list[AnnotationCategory]:
        return self.project_info.categories

    def _load_kolo_file(self, image_path: Path, img_width: int, img_height: int):
        """从SQLite数据库加载与图片同名的kolo_item记录"""
        # 获取图片文件名作为查询key
        image_name = image_path.name

        # 创建类名到类别的映射字典
        class_name_map = {category.class_name: category for category in self.category_map.values()}

        # 从数据库中查询所有匹配image_name的KoloItem对象
        try:
            # 定义查询函数
            def query_func(session):
                from src.models.sql.kolo_item import KoloItem
                return session.query(KoloItem).filter(KoloItem.image_name == image_name).all()
            
            # 执行查询
            kolo_items = self.project_info.sqlite_db.execute_in_transaction(query_func)

            # 处理查询结果
            for kolo_item in kolo_items:
                class_name = kolo_item.class_name
                
                # 获取类别对象（如果不存在则创建并添加到映射中）
                category = class_name_map.get(class_name)
                if not category:
                    # 动态创建新类别
                    new_category = AnnotationCategory(
                        class_id=len(self.category_map) + 1,
                        class_name=class_name,
                    )
                    # 添加到类别映射
                    self.category_map[new_category.class_name] = new_category
                    class_name_map[class_name] = new_category
                    category = new_category
                    print(f"信息: 数据库中类别 '{class_name}' 未定义，已创建新类别（ID={new_category.class_id}）")

                # 从KoloItem获取归一化坐标
                x_center = float(kolo_item.x_center)
                y_center = float(kolo_item.y_center)
                width = float(kolo_item.width)
                height = float(kolo_item.height)

                # 转换为绝对坐标
                x1 = (x_center - width / 2) * img_width
                y1 = (y_center - height / 2) * img_height
                rect_width = width * img_width
                rect_height = height * img_height

                # 创建AnnotationView并添加到场景
                item = AnnotationView(x1, y1, rect_width, rect_height, category, self)
                self.scene.addItem(item)

        except Exception as e:
            print(f"从数据库加载标注信息错误: {e}")
            
        # 根据规范，加载完标注后需要取消所有标注的选中状态
        self.unselect_all_annotations()

    def load_kolo_line(self, detection: str):
        """加载单行kolo格式数据并在画布上添加对应的标注"""
        if not self.current_image_path or self.image_item is None:
            return False  # 没有加载图片，无法添加标注

        try:
            # 分割检测结果字符串
            parts = detection.strip().split()
            if len(parts) != 5:
                print(f"无效的kolo格式: {detection}")
                return False

            # 解析各个部分
            class_name_b64 = parts[0]
            x_center = float(parts[1])
            y_center = float(parts[2])
            width = float(parts[3])
            height = float(parts[4])

            # 解码类名
            class_name = StringUtil.base64_to_string(class_name_b64)

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
                new_category = AnnotationCategory(
                    class_id=len(self.category_map) + 1,
                    class_name=class_name,
                )
                self.category_map[new_category.class_name] = new_category
                category = new_category
                # 添加到annotation_list
                self.annotation_list.handle_add_annotation(
                    position=len(self.project_info.categories),
                    reference_id=max((cat.class_id for cat in self.project_info.categories), default=0),
                    default_name=category.class_name
                )

            # 创建并添加AnnotationView
            item = AnnotationView(x1, y1, rect_width, rect_height, category, self)
            self.scene.addItem(item)
            return True

        except Exception as e:
            print(f"加载kolo行时出错: {e}")
            return False

    def set_current_category(self, category: AnnotationCategory):
        """设置当前要绘制的标注类别"""
        self.current_category = category

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

    def event(self, event: QEvent):
        """处理事件，包括手势事件"""
        if event.type() == QEvent.Gesture:
            return self.gestureEvent(event)
        return super().event(event)

    def gestureEvent(self, event: QEvent):
        """处理手势事件（触摸板捏合缩放）"""
        pinch = event.gesture(Qt.PinchGesture)
        if pinch:
            if pinch.state() == Qt.GestureStarted:
                # 记录初始状态
                self.base_scale = self.current_scale
                self.last_scale_factor = 1.0
                self.gesture_start_scale = self.current_scale
            elif pinch.state() == Qt.GestureUpdated:
                # 计算增量缩放因子（相对于上一次更新）
                current_scale_factor = pinch.scaleFactor()
                scale_factor = current_scale_factor / self.last_scale_factor
                self.last_scale_factor = current_scale_factor

                # 获取手势中心点（转换为视图坐标）
                center_point = pinch.centerPoint().toPoint()

                # 执行缩放
                self.zoom(scale_factor, center_point)
            elif pinch.state() == Qt.GestureFinished:
                # 重置手势状态
                self.last_scale_factor = 1.0
            return True
        return False

    def mousePressEvent(self, event):
        self.viewport().update()
        if event.button() == Qt.LeftButton:
            # 检查是否点击在现有标注或其锚点上
            clicked_item = self.itemAt(event.pos())
            is_annotation = isinstance(clicked_item, AnnotationView) or (
                    clicked_item and clicked_item.parentItem() and
                    isinstance(clicked_item.parentItem(), AnnotationView)
            )

            # 点击空白区域时清除选择
            if not is_annotation:
                self.scene.clearSelection()  # 先清除Qt原生项的默认选择状态
                for item in self.scene.items():
                    # 1. 若为自定义的AnnotationView，调用其重写的set_selected方法
                    if isinstance(item, AnnotationView):
                        item.set_selected(False)
                    # 2. 若为Qt原生项，调用标准setSelected方法
                    else:
                        item.setSelected(False)

                # 更新删除按钮状态
                self.update_delete_button_state()

                # 当设置了当前类别时开始绘制新标注
                if self.current_category is not None:
                    self.start_point = self.mapToScene(event.pos())
                    self.drawing = True

                    # 创建临时矩形框
                    self.temp_rect_item = self.scene.addRect(
                        QRectF(self.start_point, self.start_point),
                        QPen(Qt.red, 2, Qt.DashLine)
                    )
                    self.temp_rect_item.setZValue(10)  # 确保在最上层显示
                    return  # 拦截事件，避免默认处理

        super().mousePressEvent(event)  # 继续默认事件处理

    def mouseMoveEvent(self, event):
        """处理鼠标移动事件"""
        # 更新临时矩形框
        if self.drawing and self.temp_rect_item is not None:
            current_point = self.mapToScene(event.pos())
            rect = QRectF(self.start_point, current_point).normalized()
            self.temp_rect_item.setRect(rect)
            return  # 拦截事件，避免默认处理

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """处理鼠标释放事件，无论操作是什么都保存标注"""
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
            if rect.width() >= 10 and rect.height() >= 10:
                # 创建新AnnotationView并设置当前类别
                item = AnnotationView(
                    rect.x(), rect.y(), rect.width(), rect.height(),
                    self.current_category,
                    self
                )
                self.scene.addItem(item)
                self.save_annotations()

                # 新创建的标注未被选中，更新删除按钮状态
                self.update_delete_button_state()

        # 每次鼠标释放都保存标注
        if self.set_needs_save_annotations:
            self.save_annotations()

        super().mouseReleaseEvent(event)

    def delete_selected_items(self):
        """删除所有选中的标注项"""
        # 防止在删除过程中触发过多事件
        self.scene.blockSignals(True)

        try:
            selected_items = [item for item in self.scene.selectedItems()
                              if isinstance(item, AnnotationView)]

            if not selected_items:
                return

            for item in selected_items:
                self.scene.removeItem(item)

            if len(selected_items) > 0:
                # 如果删除了annotation, 立即保存
                self.save_annotations()
            print(f"已删除 {len(selected_items)} 个标注项")

            # 删除后更新删除按钮状态
            self.update_delete_button_state()
        finally:
            self.scene.blockSignals(False)
            self.save_annotations()

    def save_annotations(self):
        """保存当前所有标注到txt文件，按class_id排序"""
        if not self.current_image_path or self.image_item is None:
            return False

        self.set_needs_save_annotations = False

        txt_path = self.current_image_path.with_suffix('.kolo')
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
            
            with open(txt_path, 'w') as f:
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

                    # 对类名进行base64编码
                    class_name_b64 = StringUtil.string_to_base64(item.category.class_name)

                    # 写入文件，保留9位小数
                    # f.write(f"{class_name_b64} {x_center:.9f} {y_center:.9f} {norm_width:.9f} {norm_height:.9f}\n")
                    
                    # 创建KoloItem对象并添加到列表中
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
            self.project_info.sqlite_db.execute_in_transaction(transaction_func)

            print(f"保存标注文件成功: {txt_path}")
            return True
        except Exception as e:
            print(f"保存标注文件时出错: {e}")
            return False

    def create_toolbar(self):
        """创建并返回一个工具栏，包含缩放控制按钮、删除按钮和YOLO相关按钮"""
        toolbar = QToolBar("Image Tools")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QSize(24, 24))
        toolbar.setFixedHeight(self.toolbar_height)  # 应用工具栏高度设置

        # 尝试加载系统主题图标，如果失败则使用文本
        try:
            # Zoom In
            zoom_in_action = QAction("Zoom In", self)
            zoom_in_action.setIcon(self._get_icon("zoom-in", "+"))
            zoom_in_action.setToolTip("Zoom In (10%)")
            zoom_in_action.triggered.connect(self.zoom_in)
            toolbar.addAction(zoom_in_action)

            # Zoom Out
            zoom_out_action = QAction("Zoom Out", self)
            zoom_out_action.setIcon(self._get_icon("zoom-out", "-"))
            zoom_out_action.setToolTip("Zoom Out (10%)")
            zoom_out_action.triggered.connect(self.zoom_out)
            toolbar.addAction(zoom_out_action)

            # 1:1
            reset_zoom_action = QAction("1:1", self)
            reset_zoom_action.setIcon(self._get_icon("zoom-original", "1:1"))
            reset_zoom_action.setToolTip("Reset Zoom to Original Size")
            reset_zoom_action.triggered.connect(self.reset_zoom)
            toolbar.addAction(reset_zoom_action)

            # Fit Width
            fit_width_action = QAction("Fit Width", self)
            fit_width_action.setIcon(self._get_icon("zoom-fit-width", "Fit W"))
            fit_width_action.setToolTip("Fit image width to window")
            fit_width_action.triggered.connect(self.fit_to_width)
            toolbar.addAction(fit_width_action)

            # Fit Height
            fit_height_action = QAction("Fit Height", self)
            fit_height_action.setIcon(self._get_icon("zoom-fit-height", "Fit H"))
            fit_height_action.setToolTip("Fit image height to window")
            fit_height_action.triggered.connect(self.fit_to_height)
            toolbar.addAction(fit_height_action)

            # 添加分隔线
            toolbar.addSeparator()

            # Delete Button
            self.delete_toolbar_action = QAction("Delete", self)
            self.delete_toolbar_action.setIcon(self._get_icon("edit-delete", "X"))
            self.delete_toolbar_action.setToolTip("Delete selected annotations")
            self.delete_toolbar_action.triggered.connect(self.delete_selected_items)
            # 初始状态禁用
            self.delete_toolbar_action.setEnabled(False)
            toolbar.addAction(self.delete_toolbar_action)

            # 添加分隔线
            toolbar.addSeparator()

            # YOLO Run Button - 使用QToolButton
            self.run_tool_button = QToolButton()
            self.run_tool_button.setText("Run")
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
            self.run_tool_button.clicked.connect(self.exec_yolo)
            # 根据是否有模型设置初始状态（通过project_info判断）
            self.run_tool_button.setEnabled(bool(getattr(self.project_info, 'yolo_model_path', None)))
            toolbar.addWidget(self.run_tool_button)

            # 创建YOLO配置菜单
            self.create_yolo_menu()

            # YOLO Config Button - 使用QToolButton，与Run按钮风格一致
            self.config_button = QToolButton()
            self.config_button.setText("Config")
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
            self.config_button.clicked.connect(self.show_config_menu)
            toolbar.addWidget(self.config_button)

        except Exception as e:
            print(f"创建工具栏时出错: {e}")
            # 创建纯文本工具栏作为备选方案
            self._create_text_toolbar(toolbar)

        return toolbar

    def create_yolo_menu(self):
        """创建YOLO配置菜单，包含run, edit, delete选项"""
        self.config_menu = QMenu(self)

        # 运行子菜单
        run_action = QAction("Run", self)
        run_action.triggered.connect(self.exec_yolo)
        # 运行选项状态通过project_info判断
        run_action.setEnabled(bool(getattr(self.project_info, 'yolo_model_path', None)))
        self.config_menu.addAction(run_action)

        # 编辑子菜单
        edit_action = QAction("Edit", self)
        edit_action.triggered.connect(self.select_yolo_model)
        self.config_menu.addAction(edit_action)

        # 删除子菜单
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.delete_yolo_model)
        # 删除选项只在有模型时可用（通过project_info判断）
        delete_action.setEnabled(bool(getattr(self.project_info, 'yolo_model_path', None)))
        self.config_menu.addAction(delete_action)

    def show_config_menu(self):
        """显示配置菜单，在按钮位置弹出"""
        if self.config_menu:
            # 更新菜单状态（通过project_info判断模型是否存在）
            model_exists = bool(getattr(self.project_info, 'yolo_model_path', None))
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

    def _load_yolo_model_async(self, model_path: Path):
        """异步加载YOLO模型"""
        # 显示加载提示
        loading_msg = QMessageBox()
        loading_msg.setWindowTitle("Loading Model")
        loading_msg.setText("Loading YOLO model, please wait...")
        loading_msg.setStandardButtons(QMessageBox.NoButton)
        loading_msg.show()
        
        # 连接加载完成的回调
        def on_model_loaded(success: bool, error_message: str):
            loading_msg.close()
            if success:
                # 保存配置+启用Run按钮
                self.save_model_config()
                if self.run_tool_button:
                    self.run_tool_button.setEnabled(True)

                QMessageBox.information(
                    self, "Success",
                    f"Model '{model_path.name}' selected successfully!\nPath: {model_path}"
                )
            else:
                # 加载失败，显示错误信息
                QMessageBox.warning(
                    self, "Load Failed",
                    f"Failed to load model:\n{error_message}"
                )
        
        # 开始加载模型
        self.project_info.load_yolo(model_path)

    def delete_yolo_model(self):
        """删除已选择的YOLO模型配置"""
        # 通过project_info判断模型是否存在（替代原self.yolo_model_path）
        if not getattr(self.project_info, 'yolo_model_path', None):
            QMessageBox.information(self, "Information", "No YOLO model selected to delete.")
            return

        # 确认删除
        model_name = Path(self.project_info.yolo_model_path).name
        reply = QMessageBox.question(
            self, "Confirm Delete",
            f"Are you sure you want to remove the selected YOLO model '{model_name}'?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            # 清空project_info中的模型路径（替代原self.yolo_model_path = None）
            self.project_info.yolo_model_path = None
            # 更新Run按钮状态为不可用
            if self.run_tool_button:
                self.run_tool_button.setEnabled(False)
            # 删除配置文件
            try:
                config_path = self.project_info.path / "config" / "yolo_config.json"
                if config_path.exists():
                    config_path.unlink()
                    print(f"YOLO model configuration file deleted: {config_path}")
                QMessageBox.information(self, "Success", "YOLO model configuration has been deleted.")
            except Exception as e:
                print(f"Error deleting YOLO model configuration: {e}")
                QMessageBox.warning(self, "Error", f"Failed to delete model configuration: {str(e)}")

    def save_model_config(self):
        """保存模型配置到工程文件"""
        # 通过project_info获取模型路径（替代原self.yolo_model_path）
        model_path = getattr(self.project_info, 'yolo_model_path', None)
        if not model_path:
            return

        try:
            # 确保配置文件目录存在
            config_dir = self.project_info.path / "config"
            config_dir.mkdir(exist_ok=True)

            # 保存模型路径到配置文件（使用project_info中的模型路径）
            config_path = config_dir / "yolo_config.json"
            with open(config_path, 'w') as f:
                json.dump({"model_path": model_path}, f, indent=4)
            print(f"YOLO model configuration saved to {config_path}")
        except Exception as e:
            print(f"Error saving YOLO model configuration: {e}")
            QMessageBox.warning(self, "Error", f"Failed to save model configuration: {str(e)}")

    def load_model_config(self):
        """从工程文件加载模型配置"""
        try:
            # 初始化project_info的模型路径属性（避免AttributeError）
            self.project_info.yolo_model_path = None
            config_path = self.project_info.path / "config" / "yolo_config.json"
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = json.load(f)
                    # 加载模型路径到project_info（替代原self.yolo_model_path）
                    self.project_info.yolo_model_path = config.get("model_path")
                    print(f"Loaded YOLO model from {self.project_info.yolo_model_path}")
                    # 如果有模型，启用Run按钮
                    if self.run_tool_button and self.project_info.yolo_model_path:
                        # 检查模型是否已经加载或者正在加载
                        if self.project_info.is_model_loaded:
                            self.run_tool_button.setEnabled(True)
                        elif self.project_info.is_model_loading:
                            # 模型正在加载，稍后会通过信号启用按钮
                            pass
                        else:
                            # 模型未加载也未在加载，尝试加载
                            model_path = Path(self.project_info.yolo_model_path)
                            if model_path.exists():
                                self._load_yolo_model_async(model_path)
        except Exception as e:
            print(f"Error loading YOLO model configuration: {e}")

    # 然后是调用YOLOExecutor的代码（例如UI类中的方法）
    def exec_yolo(self):
        """执行YOLO模型的方法，识别当前图片目标并按指定格式输出日志"""
        import logging
        # 移除函数内重复导入，统一放在模块顶部

        # 检查模型是否正在加载
        if self.project_info.is_model_loading:
            QMessageBox.warning(self, "Warning", "Model is still loading, please wait.")
            return
            
        # 检查模型是否加载
        if not self.project_info.is_model_loaded:
            QMessageBox.warning(self, "Warning", "No YOLO model selected! Please configure a model first.")
            return

        # 检查是否有当前图片
        if not self.current_image_path or not self.image_item:
            QMessageBox.warning(self, "Warning", "No image loaded! Please load an image first.")
            return

        try:
            self.clear_annotation_views()
            # 调用YOLOExecutor的exec_yolo方法（复用已有实现）
            detection_results = self.project_info.exec_yolo(img_path=self.current_image_path)

            # 输出检测结果并复用load_kolo_line方法
            model_name = self.project_info.model_name
            if detection_results:
                logging.info("YOLO detection results:")
                for line in detection_results:
                    print(line)
                    logging.info(line)
                    self.load_kolo_line(line)  # 复用加载到画布的方法
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

    def update_delete_button_state(self):
        """更新删除按钮的状态：当有选中的标注项时启用，否则禁用"""
        # 防止递归调用
        if self._updating_delete_state:
            return

        self._updating_delete_state = True
        try:
            if self.delete_toolbar_action:
                # 直接迭代所有AnnotationView检查是否有选中项，避免触发额外事件
                has_selected = False
                for item in self.scene.items():
                    if isinstance(item, AnnotationView) and item.isSelected():
                        has_selected = True
                        break

                self.delete_toolbar_action.setEnabled(has_selected)
        finally:
            self._updating_delete_state = False

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

    def _create_text_toolbar(self, toolbar):
        """创建纯文本工具栏作为备选方案"""
        # Zoom In
        zoom_in_action = QAction("+", self)
        zoom_in_action.setToolTip("Zoom In (10%)")
        zoom_in_action.triggered.connect(self.zoom_in)
        toolbar.addAction(zoom_in_action)

        # Zoom Out
        zoom_out_action = QAction("-", self)
        zoom_out_action.setToolTip("Zoom Out (10%)")
        zoom_out_action.triggered.connect(self.zoom_out)
        toolbar.addAction(zoom_out_action)

        # 1:1
        reset_zoom_action = QAction("1:1", self)
        reset_zoom_action.setToolTip("Reset Zoom to Original Size")
        reset_zoom_action.triggered.connect(self.reset_zoom)
        toolbar.addAction(reset_zoom_action)

        # Fit Width
        fit_width_action = QAction("Fit W", self)
        fit_width_action.setToolTip("Fit image width to window")
        fit_width_action.triggered.connect(self.fit_to_width)
        toolbar.addAction(fit_width_action)

        # Fit Height
        fit_height_action = QAction("Fit H", self)
        fit_height_action.setToolTip("Fit image height to window")
        fit_height_action.triggered.connect(self.fit_to_height)
        toolbar.addAction(fit_height_action)

        # 添加分隔线
        toolbar.addSeparator()

        # Delete Button
        self.delete_toolbar_action = QAction("Del", self)
        self.delete_toolbar_action.setToolTip("Delete selected annotations")
        self.delete_toolbar_action.triggered.connect(self.delete_selected_items)
        # 初始状态禁用
        self.delete_toolbar_action.setEnabled(False)
        toolbar.addAction(self.delete_toolbar_action)

        # 添加分隔线
        toolbar.addSeparator()

        # YOLO Run Button (文本备选)
        self.run_tool_button = QToolButton()
        self.run_tool_button.setText("Run")
        self.run_tool_button.setToolTip("Run YOLO model")
        self.run_tool_button.setFixedSize(50, 56)  # 与Config按钮尺寸一致
        self.run_tool_button.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        self.run_tool_button.setStyleSheet("""
            QToolButton {
                text-align: center;
                padding-top: 2px;
                padding-bottom: 2px;
            }
            QToolButton::icon {
                subcontrol-position: top;
                subcontrol-origin: padding;
            }
        """)
        self.run_tool_button.clicked.connect(self.exec_yolo)
        # 根据project_info判断模型是否存在以启用按钮
        self.run_tool_button.setEnabled(bool(getattr(self.project_info, 'yolo_model_path', None)))
        toolbar.addWidget(self.run_tool_button)

        # 创建YOLO配置菜单
        self.create_yolo_menu()

        # YOLO Config Button - 使用QToolButton，与Run按钮风格一致
        self.config_button = QToolButton()
        self.config_button.setText("Config")
        self.config_button.setIcon(self._get_icon("configure", "⋮"))
        self.config_button.setToolTip("YOLO model configuration")
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
            }
        """)  # 与Run按钮样式一致
        self.config_button.clicked.connect(self.show_config_menu)
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
        self.fitInView(self.scene.sceneRect(), Qt.KeepAspectRatio)
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

    def create_annotation_list(self):
        """创建AnnotationList对象，并绑定对应方法"""
        # 创建自定义标注列表组件
        self.annotation_list = AnnotationList(self.project_info)
        self.annotation_list.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Expanding)
        self.annotation_list.load_categories_from_json()

        return self.annotation_list

    def on_selection_changed(self):
        """处理场景中选择变化的事件"""
        # 先获取选中的标注项
        selected_items = [item for item in self.scene.items()
                          if isinstance(item, AnnotationView) and item.isSelected()]

        # 更新删除按钮状态
        self.update_delete_button_state()

        if not selected_items:
            return

        # 获取第一个选中的标注的类别
        first_item = selected_items[0]
        category = first_item.category

        # 检查该类别是否已存在于annotation_list中
        exists = any(c.class_name == category.class_name for c in self.project_info.categories)

        if not exists:
            # 如果不存在，添加到列表末尾
            self.annotation_list.handle_add_annotation(
                position=len(self.project_info.categories),
                reference_id=max((cat.class_id for cat in self.project_info.categories), default=0),
                default_name=category.class_name
            )

        # 发射信号通知选中的标注类别
        self.annotation_selected.emit(category)

        # 选中列表中对应的项
        self.annotation_list.select_category_by_name(category.class_name)

    def on_list_annotation_selected(self, category: AnnotationCategory):
        """处理列表中选中类别变化的事件"""
        # 防止在选择过程中触发过多事件
        self.scene.blockSignals(True)
        try:
            # 清除当前选择
            self.scene.clearSelection()

            # 选中所有同类别标注
            for item in self.scene.items():
                if isinstance(item, AnnotationView) and item.category.class_id == category.class_id:
                    item.setSelected(True)

            # 更新删除按钮状态
            self.update_delete_button_state()
        finally:
            self.scene.blockSignals(False)

    def show_context_menu(self, position):
        """显示上下文菜单"""
        context_menu = QMenu(self)
        
        # 添加"全部清空"选项
        clear_all_action = QAction("全部清空", self)
        clear_all_action.triggered.connect(self.clear_all_annotations)
        context_menu.addAction(clear_all_action)
        
        # 在鼠标位置显示菜单
        context_menu.exec_(self.mapToGlobal(position))

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
        # 检查当前是否有图片路径，即是否有图片正在显示
        if self.current_image_path is not None:
            # 调用已有的load_image方法重新加载当前图片
            self.load_image(self.current_image_path)

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
