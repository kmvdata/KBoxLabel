# annotation_list.py
import json
from typing import Tuple

from PyQt5.QtCore import Qt, QSize, QRect, QItemSelectionModel, QMimeData, \
    QSortFilterProxyModel, QPoint, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPen, QDrag, QColor, QPainter, QPixmap
from PyQt5.QtWidgets import QLineEdit, QSpinBox, QListView, QStyledItemDelegate, QAbstractItemView, \
    QStyle, QToolBar, QWidget, QHBoxLayout, QMenu, QAction, QApplication
from ultralytics import YOLO

from src.models.dto.annotation_category import AnnotationCategory
from src.core.project_info import ProjectInfo


class AnnotationDelegate(QStyledItemDelegate):
    """优化后的委托类，实现垂直居中对齐和布局调整"""
    MARGIN = 4  # 整体边距
    SPACING = 8  # 区域间间距
    INDENT = 32  # 子项缩进像素

    def __init__(self, row_height=56, parent=None):
        super().__init__(parent)
        self.row_height = row_height
        self.hovered_index = None  # 用于高亮显示的索引

    def set_row_height(self, height: int):
        self.row_height = height

    def set_hovered_index(self, index):
        """设置悬停索引以进行高亮显示"""
        self.hovered_index = index

    def sizeHint(self, option, index):
        # 计算最小宽度：color区域 + name最小区域 + id区域 + 间距和边距
        min_width = (self.row_height + self.SPACING) * 2 + 2 * self.row_height + 2 * self.MARGIN
        return QSize(min_width, self.row_height)

    def paint(self, painter, option, index):
        # 获取数据
        category_color = index.data(Qt.UserRole)
        class_id = index.data(Qt.UserRole + 1)
        category_name = index.data(Qt.DisplayRole)
        parent_id = index.data(Qt.UserRole + 2)  # 获取父ID

        if not all([category_color, category_name, class_id is not None]):
            return

        # 处理选中状态和悬停状态
        is_hovered = self.hovered_index and self.hovered_index == index
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
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
        indent = self.INDENT if parent_id is not None else 0

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
        if parent_id is not None:
            painter.save()
            painter.setPen(QPen(option.palette.windowText().color(), 2))
            # 绘制一个小的"L"形图标表示子项
            icon_x = option.rect.left() + indent - 10
            icon_y = option.rect.top() + self.row_height // 2
            painter.drawLine(icon_x, icon_y, icon_x + 6, icon_y)  # 水平线
            painter.drawLine(icon_x, icon_y, icon_x, icon_y + 6)   # 垂直线
            painter.restore()

    def create_drag_pixmap(self, category: AnnotationCategory) -> QPixmap:
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
        transparent_color = QColor(category.color)
        transparent_color.setAlphaF(0.65)
        painter.fillRect(color_rect, transparent_color)
        
        # 绘制边框
        border_pen = QPen(Qt.black, 1)
        painter.setPen(border_pen)
        painter.drawRect(color_rect)
        
        # 绘制类别名称
        text_rect = QRect(color_size + 12, 0, width - color_size - 16, height)
        painter.setPen(Qt.black)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, category.class_name)
        
        painter.end()
        return pixmap


class EditableAnnotationDelegate(AnnotationDelegate):
    """支持编辑的委托类，通过右键菜单触发编辑"""
    EDIT_TYPE_TEXT = "text"
    EDIT_TYPE_ID = "id"

    def __init__(self, row_height=56, parent=None):
        super().__init__(row_height, parent)
        self.current_edit_type = None
        self.original_name = None

    def createEditor(self, parent, option, index):
        """创建编辑器"""
        if not self.current_edit_type:
            return None

        if self.current_edit_type == self.EDIT_TYPE_TEXT:
            editor = QLineEdit(parent)
            editor.setFrame(False)
            editor.setPlaceholderText("输入类别名称")
            return editor

        elif self.current_edit_type == self.EDIT_TYPE_ID:
            editor = QSpinBox(parent)
            editor.setMinimum(1)
            editor.setButtonSymbols(QSpinBox.NoButtons)
            return editor

        return None

    def get_edit_rects(self, option, index):
        """计算可编辑区域"""
        # 获取数据
        category_color = index.data(Qt.UserRole)
        class_id = index.data(Qt.UserRole + 1)
        category_name = index.data(Qt.DisplayRole)

        if not all([category_color, category_name, class_id is not None]):
            return {"text": QRect(), "id": QRect()}

        # 计算各区域尺寸
        color_size = self.row_height - 2 * self.MARGIN

        # name区域
        name_min_width = 2 * self.row_height
        available_width = option.rect.width() - (color_size + self.MARGIN + self.SPACING) * 2
        name_width = max(available_width, name_min_width)

        name_rect = QRect(
            option.rect.left() + color_size + self.MARGIN + self.SPACING,
            option.rect.top(),
            name_width,
            self.row_height
        )

        # id区域
        id_rect = QRect(
            option.rect.right() - color_size - self.MARGIN,
            option.rect.top() + self.MARGIN,
            color_size,
            color_size
        )

        return {"text": name_rect, "id": id_rect}

    def setEditorData(self, editor, index):
        """设置编辑器数据"""
        if isinstance(editor, QLineEdit):
            editor.setText(index.data(Qt.DisplayRole))
        elif isinstance(editor, QSpinBox):
            editor.setValue(index.data(Qt.UserRole + 1))

    def setModelData(self, editor, model, index):
        """将编辑器数据保存到模型"""
        success = False
        if isinstance(editor, QLineEdit):
            category_name = editor.text().strip()
            if category_name:
                # 检查是否有重复名称（排除自身）
                is_duplicate = False
                if category_name != self.original_name:
                    # 遍历所有项目检查是否有重复名称
                    for row in range(model.rowCount()):
                        if row != index.row():  # 排除自身
                            other_name = model.data(model.index(row, 0), Qt.DisplayRole)
                            if other_name == category_name:
                                is_duplicate = True
                                break
                
                if not is_duplicate:
                    success = model.setData(index, category_name, Qt.DisplayRole)
                else:
                    # 名称重复，显示警告对话框
                    from PyQt5.QtWidgets import QMessageBox
                    view = self.parent()
                    if view is not None:
                        QMessageBox.warning(QWidget(view), "重命名失败", f"名称 '{category_name}' 已存在，请使用其他名称。")
                    # 名称重复，不保存更改
                    pass

        elif isinstance(editor, QSpinBox):
            class_id = editor.value()
            if class_id > 0:
                success = model.setData(index, class_id, Qt.UserRole + 1)

        # 只有在设置数据成功时才保存
        if success:
            view = self.parent()
            if view is not None and hasattr(view, 'save_categories'):
                view.save_categories()  # 调用AnnotationList的save_categories方法

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何形状"""
        edit_rects = self.get_edit_rects(option, index)

        if self.current_edit_type == self.EDIT_TYPE_TEXT:
            editor.setGeometry(edit_rects["text"])
        elif self.current_edit_type == self.EDIT_TYPE_ID:
            editor.setGeometry(edit_rects["id"])

        editor.setVisible(True)
        editor.setFocus()


class AnnotationListModel(QStandardItemModel):
    """自定义模型，存储带序号的标注类别数据"""

    def __init__(self, parent=None):
        super().__init__(0, 1, parent)
        self._category_items = {}  # class_id -> QStandardItem 映射

    def add_annotation(self, category: AnnotationCategory):
        """添加带序号的标注项"""
        item = QStandardItem(category.class_name)
        item.setData(category.color, Qt.UserRole)
        item.setData(category.class_id, Qt.UserRole + 1)
        item.setData(category.parent_id, Qt.UserRole + 2)  # 存储父ID
        item.setEditable(True)
        self.appendRow(item)
        self._category_items[category.class_id] = item

    def insert_annotation(self, category: AnnotationCategory, row: int):
        """在指定位置插入标注项"""
        item = QStandardItem(category.class_name)
        item.setData(category.color, Qt.UserRole)
        item.setData(category.class_id, Qt.UserRole + 1)
        item.setData(category.parent_id, Qt.UserRole + 2)  # 存储父ID
        item.setEditable(True)
        self.insertRow(row, item)
        self._category_items[category.class_id] = item

    def clear_annotations(self):
        """清除所有标注"""
        self.clear()
        self.setColumnCount(1)
        self._category_items.clear()

    def update_from_categories(self, categories: list[AnnotationCategory]):
        """从类别列表更新模型"""
        self.clear_annotations()
        for category in categories:
            self.add_annotation(category)
            
    def get_item_by_class_id(self, class_id: int) -> QStandardItem:
        """根据class_id获取对应的item"""
        return self._category_items.get(class_id)
        
    def get_class_id_by_row(self, row: int) -> int:
        """根据行号获取class_id"""
        index = self.index(row, 0)
        return self.data(index, Qt.UserRole + 1)


class AnnotationList(QListView):
    # 可配置的工具栏高度变量（默认56px）
    TOOLBAR_HEIGHT = 56
    DROP_INDICATOR_HEIGHT = 2  # 拖拽指示器高度

    def __init__(self, project_info: ProjectInfo, row_height=56):
        super().__init__()
        self.search_edit = None
        self.project_info = project_info
        self.row_height = row_height
        self.setObjectName("YOLOAnnotationList")
        self.right_click_index = None  # 记录右键点击的索引位置
        self.setAcceptDrops(True)  # 启用拖放

        # 拖拽相关属性
        self.drag_target_row = -1  # 拖拽目标行
        self.drop_indicator_pos = QPoint()  # 拖拽指示器位置
        self.is_dragging_child_to_gap = False  # 是否是子项拖拽到间隙
        self.drag_hover_index = None  # 拖拽悬停索引

        # 设置最小宽度，确保能显示所有区域
        self.setMinimumWidth(self.calculate_min_width())

        # 创建工具栏
        self.toolbar = self.create_toolbar()

        # 创建模型
        self.source_model = AnnotationListModel(self)

        # 创建代理模型用于过滤
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterKeyColumn(0)
        self.setModel(self.proxy_model)

        # 设置视图行为 - 移除双击编辑触发
        self.setEditTriggers(QAbstractItemView.EditTrigger.EditKeyPressed)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragDrop)  # 改为支持拖放
        self.setDefaultDropAction(Qt.DropAction.MoveAction)  # 使用移动操作
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_AlwaysShowToolTips)

        # 设置委托
        self.delegate = EditableAnnotationDelegate(row_height, self)
        self.setItemDelegate(self.delegate)

        # 连接信号
        self.clicked.connect(self._handle_item_click)  # type: ignore
        self.selectionModel().selectionChanged.connect(self._handle_selection_change)  # type: ignore
        self.source_model.dataChanged.connect(self._handle_model_data_changed)

    def calculate_min_width(self):
        """计算最小宽度"""
        # color区域 + name最小区域 + id区域 + 间距和边距
        return (self.row_height + AnnotationDelegate.SPACING) * 2 + 2 * self.row_height + 2 * AnnotationDelegate.MARGIN

    def set_row_height(self, height: int):
        """设置行高并更新最小宽度"""
        self.row_height = height
        self.delegate.set_row_height(height)
        self.setMinimumWidth(self.calculate_min_width())

    def set_toolbar_height(self, height: int):
        """动态设置工具栏高度并刷新界面"""
        self.TOOLBAR_HEIGHT = height
        if self.toolbar:
            # 更新工具栏高度
            self.toolbar.setStyleSheet(f"""
                QToolBar {{
                    min-height: {height}px;
                    max-height: {height}px;
                    padding: 0px;
                }}
            """)
            # 更新搜索框高度
            if self.search_edit:
                self._configure_search_edit()

    def _configure_search_edit(self):
        """配置搜索框样式和尺寸"""
        if not self.search_edit:
            return

        # 设置与工具栏等高的固定高度
        self.search_edit.setFixedHeight(self.TOOLBAR_HEIGHT)

        # 设置样式：居中、无边框、透明背景
        self.search_edit.setStyleSheet(f"""
            QLineEdit {{
                border: none;
                background-color: transparent;
                color: palette(windowText);
                text-align: center;
                min-height: {self.TOOLBAR_HEIGHT}px;
                max-height: {self.TOOLBAR_HEIGHT}px;
                padding: 0px 8px;
                outline: none;
            }}
            QLineEdit:focus {{
                border: none;
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QLineEdit::placeholder {{
                color: palette(mid);
            }}
        """)

    def create_toolbar(self):
        """创建并返回一个工具栏，包含始终显示的搜索框和添加按钮"""
        toolbar = QToolBar("Annotation Tools")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QSize(24, 24))

        # 设置工具栏固定高度
        toolbar.setStyleSheet(f"""
            QToolBar {{
                min-height: {self.TOOLBAR_HEIGHT}px;
                max-height: {self.TOOLBAR_HEIGHT}px;
                padding: 0px;
            }}
            QToolButton {{
                min-height: {self.TOOLBAR_HEIGHT}px;
                max-height: {self.TOOLBAR_HEIGHT}px;
                padding: 0px 10px;
            }}
        """)

        # 创建搜索容器（包含图标和搜索框）
        search_container = QWidget()
        search_layout = QHBoxLayout(search_container)
        search_layout.setContentsMargins(0, 0, 0, 0)
        search_layout.setSpacing(0)  # 移除内部间距

        # 创建搜索框
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索类别...")
        self.search_edit.setFixedWidth(150)
        self.search_edit.setMinimumWidth(120)
        self.search_edit.setMaximumWidth(200)

        # 配置搜索框样式和尺寸
        self._configure_search_edit()

        # 添加到搜索容器
        search_layout.addWidget(self.search_edit)
        search_container.setLayout(search_layout)

        # 添加控件到工具栏
        toolbar.addWidget(search_container)

        # 连接搜索信号
        self.search_edit.textChanged.connect(self._handle_search_text_changed)  # type: ignore

        return toolbar

    def startDrag(self, supportedActions):
        """重写拖拽开始事件"""
        current_index = self.currentIndex()
        if not current_index.isValid():
            return

        source_index = self.proxy_model.mapToSource(current_index)
        if not (0 <= source_index.row() < len(self.project_info.categories)):
            return

        category = self.project_info.categories[source_index.row()]

        drag_data = {
            'class_id': category.class_id,
            'class_name': category.class_name,
            'color': category.color.name(),
            'parent_id': category.parent_id  # 添加父ID信息
        }

        mime_data = QMimeData()
        mime_data.setData('application/x-annotation-category', json.dumps(drag_data).encode('utf-8'))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # 使用自定义的 pixmap 作为拖拽图像
        pixmap = self.delegate.create_drag_pixmap(category)
        drag.setPixmap(pixmap)
        drag.setHotSpot(pixmap.rect().center())  # 设置热点为中心点
        
        # 取消当前选中项的选中状态
        self.selectionModel().clearSelection()
        
        drag.exec_(supportedActions)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.mimeData().hasFormat('application/x-annotation-category'):
            event.acceptProposedAction()
        else:
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        if event.mimeData().hasFormat('application/x-annotation-category'):
            pos = event.pos()
            index = self.indexAt(pos)
            
            # 更新拖拽悬停索引
            self.drag_hover_index = index
            self.delegate.set_hovered_index(index if index.isValid() else None)
            
            # 获取被拖拽的类别ID
            source_data = event.mimeData().data('application/x-annotation-category')
            source_json = json.loads(bytes(source_data).decode('utf-8'))
            dragged_class_id = source_json.get('class_id')
            dragged_parent_id = source_json.get('parent_id')
            
            # 清除当前选中状态
            self.setCurrentIndex(QModelIndex())
            
            if index.isValid():
                # 获取目标类别ID
                source_index = self.proxy_model.mapToSource(index)
                target_class_id = self.source_model.data(source_index, Qt.UserRole + 1)
                
                # 计算放置位置（上方1/4、中间2/4、下方1/4）
                rect = self.visualRect(index)
                y_pos_in_item = pos.y() - rect.top()
                item_height = rect.height()
                
                if y_pos_in_item < item_height / 4:
                    # 上方1/4区域 - 放置在目标项之前
                    self._handle_drop_on_gap(event, pos, dragged_class_id, dragged_parent_id, before_row=source_index.row())
                elif y_pos_in_item > 3 * item_height / 4:
                    # 下方1/4区域 - 放置在目标项之后
                    self._handle_drop_on_gap(event, pos, dragged_class_id, dragged_parent_id, before_row=source_index.row() + 1)
                else:
                    # 中间2/4区域 - 检查是否可以建立父子关系
                    if self._can_drop_category(dragged_class_id, target_class_id):
                        # 保持目标项目高亮显示，表示可以建立父子关系
                        # 不再清除悬停索引
                        # 重置拖拽到间隙的状态
                        self.drag_target_row = -1
                        self.is_dragging_child_to_gap = False
                        event.acceptProposedAction()
                        self.viewport().update()  # 更新视图以重新绘制
                        return
                    else:
                        # 不能建立父子关系，当作放置在目标项之后处理
                        self._handle_drop_on_gap(event, pos, dragged_class_id, dragged_parent_id, before_row=source_index.row() + 1)
            else:
                # 检查是否可以放置在列表开头或结尾的间隙
                self._handle_drop_on_gap(event, pos, dragged_class_id, dragged_parent_id)
                    
        event.ignore()

    def _handle_drop_on_gap(self, event, pos, dragged_class_id, dragged_parent_id, before_row=None):
        """处理拖拽到间隙的情况"""
        if before_row is not None:
            # 使用指定的插入位置
            target_row = before_row
        else:
            # 计算应该放置在哪个位置
            target_row = self._get_drop_target_row(pos)
        
        # 确保target_row在有效范围内
        max_row = len(self.project_info.categories)
        if target_row > max_row:
            target_row = max_row
        elif target_row < 0:
            target_row = 0
        
        # 即使target_row为-1，我们也接受这个放置操作
        self.drag_target_row = target_row
        self.drop_indicator_pos = self._get_drop_indicator_position(target_row)
        
        # 检查是否是子项拖拽到间隙（需要变为一级项）
        self.is_dragging_child_to_gap = dragged_parent_id is not None
        
        event.acceptProposedAction()
        self.viewport().update()  # 更新视图以重新绘制

    def _get_drop_target_row(self, pos):
        """计算拖拽目标行"""
        if self.model().rowCount() == 0:
            return 0  # 空列表时插入到开头
            
        # 查找最近的项目
        for row in range(self.model().rowCount()):
            index = self.model().index(row, 0)
            rect = self.visualRect(index)
            
            # 检查是否在项目上半部分（在该项目之前插入）
            if pos.y() <= rect.top() + rect.height() / 4:
                # 需要将代理模型的行号转换为源模型的行号
                source_index = self.proxy_model.mapToSource(index)
                return source_index.row()
                
            # 检查是否在项目下半部分（在该项目之后插入）
            if pos.y() > rect.top() + 3 * rect.height() / 4 and pos.y() <= rect.bottom():
                # 需要将代理模型的行号转换为源模型的行号
                source_index = self.proxy_model.mapToSource(index)
                return source_index.row() + 1
                
        # 如果在所有项目之后，插入到末尾
        return len(self.project_info.categories)

    def _get_drop_indicator_position(self, target_row):
        """获取拖拽指示器的位置"""
        # 确保target_row在有效范围内
        max_row = len(self.project_info.categories)
        if target_row > max_row:
            target_row = max_row
            
        if target_row == 0 and max_row > 0:
            # 插入到开头
            first_index = self.proxy_model.mapFromSource(self.source_model.index(0, 0))
            if first_index.isValid():
                first_rect = self.visualRect(first_index)
                return QPoint(first_rect.left(), first_rect.top())
        elif target_row >= max_row and max_row > 0:
            # 插入到末尾
            last_index = self.proxy_model.mapFromSource(self.source_model.index(max_row - 1, 0))
            if last_index.isValid():
                last_rect = self.visualRect(last_index)
                return QPoint(last_rect.left(), last_rect.bottom())
        elif 0 < target_row <= max_row:
            # 插入到中间
            prev_source_index = self.source_model.index(target_row - 1, 0)
            next_source_index = self.source_model.index(target_row, 0)
            
            prev_index = self.proxy_model.mapFromSource(prev_source_index)
            next_index = self.proxy_model.mapFromSource(next_source_index)
            
            if prev_index.isValid() and next_index.isValid():
                prev_rect = self.visualRect(prev_index)
                next_rect = self.visualRect(next_index)
                y_pos = (prev_rect.bottom() + next_rect.top()) // 2
                return QPoint(prev_rect.left(), y_pos)
            elif prev_index.isValid():
                # 只有前一个有效
                prev_rect = self.visualRect(prev_index)
                return QPoint(prev_rect.left(), prev_rect.bottom())
            elif next_index.isValid():
                # 只有后一个有效
                next_rect = self.visualRect(next_index)
                return QPoint(next_rect.left(), next_rect.top())
        else:
            # 默认位置
            return QPoint(0, 0)
            
        # 如果无法确定位置，返回默认值
        return QPoint(0, 0)

    def dropEvent(self, event):
        """处理放置事件"""
        if event.mimeData().hasFormat('application/x-annotation-category'):
            # 获取被拖拽的类别
            source_data = event.mimeData().data('application/x-annotation-category')
            source_json = json.loads(bytes(source_data).decode('utf-8'))
            dragged_class_id = source_json.get('class_id')
            dragged_parent_id = source_json.get('parent_id')  # 获取拖拽项的父ID
            
            # 获取放置位置
            pos = event.pos()
            index = self.indexAt(pos)
            
            # 如果放置在项目上，建立父子关系
            if index.isValid() and self.drag_target_row == -1:
                # 获取目标类别
                source_index = self.proxy_model.mapToSource(index)
                target_class_id = self.source_model.data(source_index, Qt.UserRole + 1)
                
                # 检查是否可以建立父子关系
                if self._can_drop_category(dragged_class_id, target_class_id):
                    # 建立父子关系
                    # 检查是否需要在特定子项之后插入
                    insert_after_child_id = None
                    # 这里可以根据需要添加逻辑来确定在哪个子项之后插入
                    self._establish_parent_child_relationship(dragged_class_id, target_class_id, insert_after_child_id)
                    event.acceptProposedAction()
                    # 重置拖拽状态
                    self.drag_target_row = -1
                    self.is_dragging_child_to_gap = False
                    self.drag_hover_index = None
                    self.delegate.set_hovered_index(None)
                    self.viewport().update()
                    return
            elif self.drag_target_row != -1:
                # 放置在间隙，重新排序
                self._reorder_items(dragged_class_id, dragged_parent_id)
                event.acceptProposedAction()
                # 重置拖拽状态
                self.drag_target_row = -1
                self.is_dragging_child_to_gap = False
                self.drag_hover_index = None
                self.delegate.set_hovered_index(None)
                self.viewport().update()
                return
            else:
                # 特殊情况处理：即使drag_target_row为-1，也要处理重新排序
                # 这种情况可能发生在直接拖拽到列表末尾等场景
                self._reorder_items(dragged_class_id, dragged_parent_id)
                event.acceptProposedAction()
                # 重置拖拽状态
                self.drag_target_row = -1
                self.is_dragging_child_to_gap = False
                self.drag_hover_index = None
                self.delegate.set_hovered_index(None)
                self.viewport().update()
                return
                    
        super().dropEvent(event)
        # 重置拖拽状态
        self.drag_target_row = -1
        self.is_dragging_child_to_gap = False
        self.drag_hover_index = None
        self.delegate.set_hovered_index(None)
        self.viewport().update()

    def _reorder_items(self, dragged_class_id, dragged_parent_id=None):
        """重新排序项目"""
            
        # 找到被拖拽的项目在当前列表中的位置
        dragged_row = -1
        for i, cat in enumerate(self.project_info.categories):
            if cat.class_id == dragged_class_id:
                dragged_row = i
                break
                
        if dragged_row == -1:
            return
            
        # 获取被拖拽的类别
        dragged_category = self.project_info.categories[dragged_row]
        
        # 如果是从子项变为一级项，更新其属性
        if self.is_dragging_child_to_gap and dragged_category.parent_id is not None:
            # 从原父项的children列表中移除
            original_parent_id = dragged_category.parent_id
            for cat in self.project_info.categories:
                if cat.class_id == original_parent_id:
                    if dragged_class_id in cat.children:
                        cat.children.remove(dragged_class_id)
                    break
            # 设置为一级项
            dragged_category.parent_id = None
            
            # 更新模型中的数据
            dragged_item = self.source_model.get_item_by_class_id(dragged_class_id)
            if dragged_item:
                dragged_item.setData(None, Qt.UserRole + 2)
        
        # 从原位置移除
        removed_category = self.project_info.categories.pop(dragged_row)
        
        # 计算插入位置（如果原位置在目标位置之前，目标位置需要减1）
        # 如果 drag_target_row 为 -1，则插入到末尾
        if self.drag_target_row == -1:
            insert_row = len(self.project_info.categories)
        else:
            insert_row = self.drag_target_row
            if dragged_row < insert_row:
                insert_row -= 1
            
        # 插入到新位置
        self.project_info.categories.insert(insert_row, removed_category)
        
        # 更新模型
        self.source_model.update_from_categories(self.project_info.categories)
        
        # 保存更改
        self.save_categories()

    def _can_drop_category(self, dragged_class_id: int, target_class_id: int) -> bool:
        """检查是否可以将dragged_class拖放到target_class上"""
        # 不能将类别拖放到自己身上
        if dragged_class_id == target_class_id:
            return False
            
        # 检查是否会形成循环引用（不能将父项拖到自己的子项上）
        current_parent_id = target_class_id
        while current_parent_id is not None:
            # 查找当前parent_id对应的类别
            parent_category = None
            for cat in self.project_info.categories:
                if cat.class_id == current_parent_id:
                    parent_category = cat
                    break
                    
            if parent_category is None:
                break
                
            # 如果发现循环引用，返回False
            if parent_category.parent_id == dragged_class_id:
                return False
                
            current_parent_id = parent_category.parent_id
            
        # 检查目标是否已经是子项（只允许一级嵌套）
        for cat in self.project_info.categories:
            if cat.class_id == target_class_id:
                # 目标已经是子项，不允许再作为父项
                if cat.parent_id is not None:
                    return False
                break
        
        return True

    def _establish_parent_child_relationship(self, child_id: int, parent_id: int, insert_after_child_id: int = None):
        """建立父子关系，可选择在指定子项之后插入"""
        child_category = None
        parent_category = None
        
        # 查找子项和父项
        for cat in self.project_info.categories:
            if cat.class_id == child_id:
                child_category = cat
            elif cat.class_id == parent_id:
                parent_category = cat
                
        if child_category is None or parent_category is None:
            return
            
        # 设置父子关系
        child_category.parent_id = parent_id
        
        # 如果指定了在某个子项之后插入，则调整children列表的顺序
        if insert_after_child_id is not None and insert_after_child_id in parent_category.children:
            # 先确保child_id在children列表中
            if child_id not in parent_category.children:
                parent_category.children.append(child_id)
            
            # 调整顺序，将child_id放在insert_after_child_id之后
            # 先移除child_id
            parent_category.children.remove(child_id)
            
            # 找到insert_after_child_id的位置
            insert_index = parent_category.children.index(insert_after_child_id) + 1
            
            # 在指定位置插入child_id
            parent_category.children.insert(insert_index, child_id)
        else:
            # 默认添加到children列表末尾
            if child_id not in parent_category.children:
                parent_category.children.append(child_id)
            
        # 更新模型中的数据
        child_item = self.source_model.get_item_by_class_id(child_id)
        if child_item:
            child_item.setData(parent_id, Qt.UserRole + 2)
            
        # 重新排序模型以确保正确的显示顺序
        self._reorder_model()
        
        # 保存更改
        self.save_categories()

    def _reorder_model(self):
        """重新排序模型以正确显示父子关系"""
        # 先清空模型
        self.source_model.clear_annotations()
        
        # 按照父子关系重新添加项目
        # 先添加顶级项目
        top_level_categories = [cat for cat in self.project_info.categories if cat.parent_id is None]
        
        # 按照原始顺序添加顶级项目和其子项目
        ordered_categories = []
        added_categories = set()  # 跟踪已添加的类别
        
        # 首先按照project_info.categories中的顺序添加顶级项目及其子项目
        for cat in self.project_info.categories:
            if cat.parent_id is None and cat.class_id not in added_categories:
                ordered_categories.append(cat)
                added_categories.add(cat.class_id)
                # 按照parent_category.children中的顺序添加其子项目
                for child_id in cat.children:
                    for child_cat in self.project_info.categories:
                        if child_cat.class_id == child_id and child_cat.class_id not in added_categories:
                            ordered_categories.append(child_cat)
                            added_categories.add(child_cat.class_id)
                        
        # 添加剩余未处理的项目（处理可能的顺序问题）
        for cat in self.project_info.categories:
            if cat.class_id not in added_categories:
                ordered_categories.append(cat)
                        
        # 更新模型
        self.source_model.update_from_categories(ordered_categories)

    def _handle_item_click(self, clicked_index):
        """处理点击事件 - 保持单选状态"""
        if not clicked_index.isValid():
            return

        if not self.selectionModel().isSelected(clicked_index):
            self.selectionModel().clearSelection()
            self.selectionModel().select(clicked_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def _handle_selection_change(self, selected, deselected):
        if selected.indexes():
            source_index = self.proxy_model.mapToSource(selected.indexes()[0])
            # if 0 <= source_index.row() < len(self.project_info.categories):
            #     self.annotation_selected.emit(self.project_info.categories[source_index.row()])  # type: ignore

    def _handle_model_data_changed(self, top_left, bottom_right, roles=None):
        """处理模型数据变化，同步更新self.project_info.categories"""
        for row_index in range(top_left.row(), bottom_right.row() + 1):
            proxy_index = self.proxy_model.index(row_index, 0)
            source_index = self.proxy_model.mapToSource(proxy_index)
            row = source_index.row()

            if 0 <= row < len(self.project_info.categories):
                if roles is None or Qt.UserRole + 1 in roles:
                    new_id = self.source_model.data(source_index, Qt.UserRole + 1)
                    self.project_info.categories[row].class_id = new_id

                if roles is None or Qt.DisplayRole in roles:
                    new_name = self.source_model.data(source_index, Qt.DisplayRole)
                    self.project_info.categories[row].class_name = new_name
                    # 根据新名称重新生成颜色
                    self.project_info.categories[row].color = self.project_info.categories[row].gen_color()
                    # 更新模型中的颜色数据
                    self.source_model.setData(source_index, self.project_info.categories[row].color, Qt.UserRole)

    def get_selected_category(self):
        """获取当前选中的完整类别对象"""
        selected = self.selectionModel().selectedIndexes()
        if selected:
            source_index = self.proxy_model.mapToSource(selected[0])
            class_id = self.source_model.data(source_index, Qt.UserRole + 1)
            class_name = self.source_model.data(source_index, Qt.DisplayRole)
            return AnnotationCategory(class_id, class_name)
        return None

    def _handle_search_text_changed(self, search_text):
        """处理搜索文本变化，实时过滤列表"""
        # 设置过滤条件，匹配包含搜索内容的行
        self.proxy_model.setFilterFixedString(search_text.strip())
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterRole(Qt.DisplayRole)

    def handle_add_annotation(self, position=None, reference_id=None, default_name=None):
        """处理添加新类别，position为源模型中的位置索引，None表示添加到末尾"""
        # 根据参考ID生成新ID
        if reference_id is not None:
            new_id = reference_id + 1
        else:
            # 如果没有参考ID，使用原逻辑（最大值+1）
            max_id = max((cat.class_id for cat in self.project_info.categories), default=0)
            new_id = max_id + 1

        if default_name is None:
            new_name = f"新类别 {new_id}"
        else:
            new_name = default_name

        new_category = AnnotationCategory(
            class_id=new_id,
            class_name=new_name
        )

        # 根据position决定插入位置
        if position is not None and 0 <= position <= len(self.project_info.categories):
            self.project_info.categories.insert(position, new_category)
            self.source_model.insert_annotation(new_category, position)
        else:
            self.project_info.categories.append(new_category)
            self.source_model.add_annotation(new_category)

        # 获取新添加项的索引
        if position is not None:
            proxy_index = self.proxy_model.mapFromSource(self.source_model.index(position, 0))
        else:
            proxy_index = self.proxy_model.index(self.proxy_model.rowCount() - 1, 0)

        # 滚动到新项位置
        self.scrollTo(proxy_index)

        # 选中新项
        self.selectionModel().select(
            proxy_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
        )

        self.save_categories()

    def _handle_rename(self):
        """处理重命名操作"""
        if self.right_click_index and self.right_click_index.isValid():
            self.delegate.current_edit_type = EditableAnnotationDelegate.EDIT_TYPE_TEXT
            # 获取当前要重命名的项的索引和名称
            source_index = self.proxy_model.mapToSource(self.right_click_index)
            current_name = self.source_model.data(source_index, Qt.DisplayRole)
            
            # 保存当前名称，以便在委托中进行重复性检查
            self.delegate.original_name = current_name
            self.edit(self.right_click_index)

    def _handle_modify_id(self):
        """处理修改ID操作"""
        if self.right_click_index and self.right_click_index.isValid():
            self.delegate.current_edit_type = EditableAnnotationDelegate.EDIT_TYPE_ID
            self.edit(self.right_click_index)

    def _handle_delete(self):
        """处理删除操作"""
        if self.right_click_index and self.right_click_index.isValid():
            source_index = self.proxy_model.mapToSource(self.right_click_index)
            row = source_index.row()

            if 0 <= row < len(self.project_info.categories):
                # 从数据源中删除
                del self.project_info.categories[row]
                # 从模型中删除
                self.source_model.removeRow(row)
                # 保存更改
                self.save_categories()

    def contextMenuEvent(self, event):
        """重写右键菜单事件"""
        # 获取右键点击位置对应的索引
        index = self.indexAt(event.pos())

        # 如果点击位置有item，则选中它
        if index.isValid():
            self.right_click_index = index
            self.selectionModel().clearSelection()
            self.selectionModel().select(index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
        else:
            self.right_click_index = None

        # 创建右键菜单
        menu = QMenu(self)

        # 添加菜单项
        add_action = QAction("新增", self)
        add_action.triggered.connect(self._context_add)  # type:ignore

        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(self._handle_rename) # type: ignore
        rename_action.setEnabled(index.isValid())  # 只有选中项时可用

        modify_id_action = QAction("修改ID", self)
        modify_id_action.triggered.connect(self._handle_modify_id) # type:ignore
        modify_id_action.setEnabled(index.isValid())  # 只有选中项时可用

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._handle_delete)  # type:ignore
        delete_action.setEnabled(index.isValid())  # 只有选中项时可用

        # 添加到菜单
        menu.addAction(add_action)
        menu.addSeparator()
        menu.addAction(rename_action)
        menu.addAction(modify_id_action)
        menu.addAction(delete_action)

        # 显示菜单
        menu.exec_(event.globalPos())

    def _context_add(self):
        """处理右键菜单中的新增操作"""
        reference_id = None
        insert_position = None

        if self.right_click_index and self.right_click_index.isValid():
            # 如果有选中项，获取其ID作为参考
            source_index = self.proxy_model.mapToSource(self.right_click_index)
            row = source_index.row()
            if 0 <= row < len(self.project_info.categories):
                reference_id = self.project_info.categories[row].class_id
                insert_position = row + 1  # 在选中项后插入

        # 调用添加方法，传递参考ID和位置
        self.handle_add_annotation(insert_position, reference_id)

    def save_categories(self):
        """
        使用每个 AnnotationCategory 对象的 to_json 方法保存 categories 列表到指定文件。
        按照列表当前显示顺序保存
        """
        self.project_info.save_categories()

    def load_categories(self):
        """
        从数据库加载类别，与现有类别合并（仅当 class_id 和 class_name 都相同时视为重复）。
        重复项将重新生成颜色，最终列表按 class_id 排序。
        """
        self._merge_and_update_categories(self.project_info.load_categories())

    def load_categories_from_yolo_model(self, model_path):
        """
        从YOLO模型文件(.pt)加载类别信息，并与现有类别合并。
        """
        try:
            model = YOLO(model_path)
            class_dict = model.names  # {0: 'person', 1: 'car', ...}

            new_categories = [
                AnnotationCategory(class_id=i, class_name=name)
                for i, name in class_dict.items()
            ]
        except Exception as e:
            print(f"加载YOLO模型失败: {str(e)}")
            return False

        self._merge_and_update_categories(new_categories)
        return True

    def _merge_and_update_categories(self, new_categories: list[AnnotationCategory]):
        """
        核心合并逻辑：将 new_categories 与 self.project_info.categories 合并。
        - 如果 (class_id, class_name) 相同 → 合并并重新生成颜色
        - 否则添加新类别
        使用字典索引，时间复杂度 O(n + m)
        """
        # 1. 构建现有类别的索引：key -> category
        existing_map: dict[Tuple[int, str], AnnotationCategory] = {
            cat.key(): cat for cat in self.project_info.categories
        }

        # 2. 遍历新类别，进行合并或添加
        updated_categories = []
        for new_cat in new_categories:
            key = new_cat.key()
            if key in existing_map:
                # 已存在：合并（重新生成颜色）
                existing_cat = existing_map[key]
                merged_cat = AnnotationCategory(class_id=new_cat.class_id, class_name=new_cat.class_name)
                merged_cat.color = merged_cat.gen_color()  # 重新生成颜色
                updated_categories.append(merged_cat)
                # 从 existing_map 中移除，表示已处理
                del existing_map[key]
            else:
                # 新类别，直接加入
                updated_categories.append(new_cat)

        # 3. 加入所有未被合并的旧类别
        updated_categories.extend(existing_map.values())

        # 4. 保持加载顺序
        self.project_info.categories = updated_categories

        # 5. 同步到模型（关键修复：确保模型与categories一致）
        self.source_model.update_from_categories(self.project_info.categories)

    def select_category_by_id(self, class_id: int):
        """根据类别ID选中对应的列表项"""
        return self._select_category_by_attr('class_id', class_id)

    def select_category_by_name(self, class_name: str):
        """根据类别名称选中对应的列表项"""
        return self._select_category_by_attr('class_name', class_name)
    
    def _select_category_by_attr(self, attr_name: str, attr_value):
        """根据指定属性名和值选中对应的列表项"""
        for i, category in enumerate(self.project_info.categories):
            if getattr(category, attr_name) == attr_value:
                proxy_index = self.proxy_model.mapFromSource(self.source_model.index(i, 0))
                self.selectionModel().select(
                    proxy_index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                )
                self.scrollTo(proxy_index)
                return True
        return False

    def paintEvent(self, event):
        """重写绘制事件以添加拖拽指示器"""
        # 绘制基础视图
        super().paintEvent(event)
        
        # 绘制拖拽指示器
        if self.drag_target_row != -1:
            painter = QPainter(self.viewport())
            pen = QPen()
            
            # 根据是否是子项拖拽到间隙设置不同的颜色
            if self.is_dragging_child_to_gap:
                pen.setColor(QColor(255, 165, 0))  # 橙色表示子项变为一级项
                pen.setWidth(3)
            else:
                pen.setColor(QColor(0, 191, 255))  # 蓝色表示普通重排
                pen.setWidth(2)
                
            painter.setPen(pen)
            
            # 绘制指示线
            if self.model().rowCount() > 0:
                indicator_width = self.viewport().width() - 20
                painter.drawLine(
                    self.drop_indicator_pos.x() + 10, 
                    self.drop_indicator_pos.y(),
                    self.drop_indicator_pos.x() + indicator_width, 
                    self.drop_indicator_pos.y()
                )
            
                # 添加箭头指示当前拖拽操作类型
                if self.is_dragging_child_to_gap:
                    # 绘制向上箭头表示子项提升为一级项
                    arrow_size = 6
                    painter.drawLine(
                        self.drop_indicator_pos.x() + indicator_width // 2, 
                        self.drop_indicator_pos.y(),
                        self.drop_indicator_pos.x() + indicator_width // 2 - arrow_size, 
                        self.drop_indicator_pos.y() - arrow_size
                    )
                    painter.drawLine(
                        self.drop_indicator_pos.x() + indicator_width // 2, 
                        self.drop_indicator_pos.y(),
                        self.drop_indicator_pos.x() + indicator_width // 2 + arrow_size, 
                        self.drop_indicator_pos.y() - arrow_size
                    )
            elif self.model().rowCount() == 0:
                # 空列表时绘制指示器
                indicator_width = self.viewport().width() - 20
                center_y = self.viewport().height() // 2
                painter.drawLine(
                    10, 
                    center_y,
                    indicator_width, 
                    center_y
                )
            
            painter.end()

    def dragLeaveEvent(self, event):
        """处理拖拽离开事件"""
        super().dragLeaveEvent(event)
        # 重置拖拽状态
        self.drag_target_row = -1
        self.is_dragging_child_to_gap = False
        self.drag_hover_index = None
        self.delegate.set_hovered_index(None)
        self.viewport().update()
        # 清除当前选中状态
        self.setCurrentIndex(QModelIndex())

    def move_item_as_child_after(self, child_id: int, parent_id: int, after_child_id: int = None):
        """
        将指定的子项移动为某个父项的子项，并可选择放置在特定子项之后
        
        Args:
            child_id: 要移动的子项ID
            parent_id: 目标父项ID
            after_child_id: 可选，放置在该子项之后
        """
        # 验证父子关系合法性
        if child_id == parent_id:
            # 不能将项目设置为自己的父项
            return False
            
        # 检查是否会形成循环引用
        current_parent_id = parent_id
        while current_parent_id is not None:
            if current_parent_id == child_id:
                # 会形成循环引用
                return False
            # 查找当前parent_id对应的类别
            parent_category = None
            for cat in self.project_info.categories:
                if cat.class_id == current_parent_id:
                    parent_category = cat
                    break
            if parent_category is None:
                break
            current_parent_id = parent_category.parent_id
            
        # 检查目标是否已经是子项（只允许一级嵌套）
        for cat in self.project_info.categories:
            if cat.class_id == parent_id:
                # 目标已经是子项，不允许再作为父项
                if cat.parent_id is not None:
                    return False
                break
        
        # 查找要移动的子项和目标父项
        child_category = None
        parent_category = None
        after_child_category = None
        
        for cat in self.project_info.categories:
            if cat.class_id == child_id:
                child_category = cat
            elif cat.class_id == parent_id:
                parent_category = cat
            elif after_child_id is not None and cat.class_id == after_child_id:
                after_child_category = cat
                
        if child_category is None or parent_category is None:
            return False
            
        # 如果指定了after_child_id，需要确保它确实是parent_id的子项
        if after_child_id is not None and (after_child_category is None or 
                                          after_child_category.parent_id != parent_id):
            return False
            
        # 如果子项已经是该父项的子项，只需要调整顺序
        if child_category.parent_id == parent_id:
            # 从父项的children列表中移除该子项
            if child_id in parent_category.children:
                parent_category.children.remove(child_id)
        else:
            # 否则，需要更新子项的parent_id
            # 如果子项之前是其他项的子项，需要从原父项的children列表中移除
            if child_category.parent_id is not None:
                for cat in self.project_info.categories:
                    if cat.class_id == child_category.parent_id and child_id in cat.children:
                        cat.children.remove(child_id)
                        break
            # 设置新的父项
            child_category.parent_id = parent_id
            
        # 将子项添加到父项的children列表中
        if after_child_id is not None:
            # 插入到指定子项之后
            insert_index = parent_category.children.index(after_child_id) + 1
            parent_category.children.insert(insert_index, child_id)
        else:
            # 添加到末尾
            parent_category.children.append(child_id)
            
        # 更新模型中的数据
        child_item = self.source_model.get_item_by_class_id(child_id)
        if child_item:
            child_item.setData(parent_id, Qt.UserRole + 2)
            
        # 重新排序模型以确保正确的显示顺序
        self._reorder_model()
        
        # 保存更改
        self.save_categories()
        
        return True
