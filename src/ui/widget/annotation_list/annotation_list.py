# annotation_list.py

import json
from typing import Optional, Union

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSize, QItemSelectionModel, QMimeData, \
    QSortFilterProxyModel, QPoint, QModelIndex
from PyQt5.QtGui import QPen, QDrag, QColor, QPainter
from PyQt5.QtWidgets import QLineEdit, QListView, QAbstractItemView, \
    QToolBar, QWidget, QHBoxLayout, QMenu, QAction, QMessageBox
from ultralytics import YOLO

from src.core.project_info import ProjectInfo
from src.models.dto.annotation_category_dto import AnnotationCategoryDTO
from src.ui.widget.annotation_list.annotation_delegate import AnnotationDelegate
from src.ui.widget.annotation_list.annotation_list_model import AnnotationListModel
from src.ui.widget.annotation_list.editable_annotation_delegate import EditableAnnotationDelegate


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

    def startDrag(self, supported_actions: Union[QtCore.Qt.DropActions, QtCore.Qt.DropAction]):
        """重写拖拽开始事件"""
        current_index = self.currentIndex()
        print(f"[Drag] Start dragging, current index: {current_index}")
        if not current_index.isValid():
            print("[Drag] Current index is invalid, aborting drag")
            return

        source_index = self.proxy_model.mapToSource(current_index)
        print(f"[Drag] Source index row: {source_index.row()}, categories count: {len(self.project_info.categories)}")
        if not (0 <= source_index.row() < len(self.project_info.categories)):
            print("[Drag] Source index out of range, aborting drag")
            return

        category = self.project_info.categories[source_index.row()]
        print(f"[Drag] Dragging category: id={category.class_id}, name={category.class_name}, parent={category.parent_name}")

        drag_data = {
            'class_id': category.class_id,
            'class_name': category.class_name,
            'color': category.color.name(),
            'parent_name': category.parent_name  # 添加父ID信息
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
        print("[Drag] Cleared selection, starting drag operation")
        
        result = drag.exec_(supported_actions)
        print(f"[Drag] Drag operation finished with result: {result}")

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        print(f"[Drag] Drag enter event, mime data formats: {event.mimeData().formats()}")
        if event.mimeData().hasFormat('application/x-annotation-category'):
            print("[Drag] Accepting drag enter event for annotation category")
            event.acceptProposedAction()
        else:
            print("[Drag] Ignoring drag enter event, unsupported format")
            super().dragEnterEvent(event)

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        print(f"[Drag] Drag move event at position: {event.pos()}")
        if event.mimeData().hasFormat('application/x-annotation-category'):
            pos = event.pos()
            index = self.indexAt(pos)
            print(f"[Drag] Item index at position: {index}")
            
            # 更新拖拽悬停索引
            self.drag_hover_index = index
            self.delegate.set_hovered_index(index if index.isValid() else None)
            
            # 获取被拖拽的类别ID
            source_data = event.mimeData().data('application/x-annotation-category')
            source_json = json.loads(bytes(source_data).decode('utf-8'))
            dragged_class_name = source_json.get('class_name')
            dragged_parent_name = source_json.get('parent_name')
            print(f"[Drag] Dragged item: name={dragged_class_name}, parent={dragged_parent_name}")
            
            # 清除当前选中状态
            self.setCurrentIndex(QModelIndex())
            
            if index.isValid():
                print("[Drag] Index is valid, processing drop targets")
                # 获取目标类别ID
                source_index = self.proxy_model.mapToSource(index)
                target_class_name = self.source_model.data(source_index, Qt.UserRole + 2)
                target_parent_name = self.source_model.data(source_index, Qt.UserRole + 3)  # 获取目标的父级
                print(f"[Drag] Target item name: {target_class_name}, parent: {target_parent_name}")
                
                # 计算放置位置（上方1/4、中间2/4、下方1/4）
                rect = self.visualRect(index)
                y_pos_in_item = pos.y() - rect.top()
                item_height = rect.height()
                print(f"[Drag] Position in item: y={y_pos_in_item}, item height: {item_height}")
                
                if y_pos_in_item < item_height / 4:
                    # 上方1/4区域 - 放置在目标项之前
                    print("[Drag] Drop position: top quarter, placing before target")
                    # 清除拖拽目标高亮
                    self.delegate.set_drag_target_index(None)
                    self._handle_drop_on_gap(event, pos, dragged_class_name, dragged_parent_name, before_row=source_index.row())
                elif y_pos_in_item > 3 * item_height / 4:
                    # 下方1/4区域 - 放置在目标项之后
                    print("[Drag] Drop position: bottom quarter, placing after target")
                    # 清除拖拽目标高亮
                    self.delegate.set_drag_target_index(None)
                    self._handle_drop_on_gap(event, pos, dragged_class_name, dragged_parent_name, before_row=source_index.row() + 1)
                else:
                    # 中间2/4区域 - 检查是否可以建立父子关系
                    print("[Drag] Drop position: middle half, checking parent-child relationship")
                    # 如果目标已经是子项，则将拖拽项设置为与目标相同的父级
                    if target_parent_name is not None:
                        print(f"[Drag] Target is already a child, setting dragged item to same parent: {target_parent_name}")
                        # 高亮整个目标项目，表示可以建立父子关系
                        self.delegate.set_drag_target_index(index)
                        # 重置拖拽到间隙的状态
                        self.drag_target_row = -1
                        self.is_dragging_child_to_gap = False
                        event.acceptProposedAction()
                        self.viewport().update()  # 更新视图以重新绘制
                        return
                    elif self._can_drop_category(dragged_class_name, target_class_name):
                        print("[Drag] Parent-child relationship allowed")
                        # 高亮整个目标项目，表示可以建立父子关系
                        self.delegate.set_drag_target_index(index)
                        # 重置拖拽到间隙的状态
                        self.drag_target_row = -1
                        self.is_dragging_child_to_gap = False
                        event.acceptProposedAction()
                        self.viewport().update()  # 更新视图以重新绘制
                        return
                    else:
                        print("[Drag] Parent-child relationship not allowed, placing after target")
                        # 不能建立父子关系，当作放置在目标项之后处理
                        # 清除拖拽目标高亮
                        self.delegate.set_drag_target_index(None)
                        self._handle_drop_on_gap(event, pos, dragged_class_name, dragged_parent_name, before_row=source_index.row() + 1)
            else:
                print("[Drag] Index is not valid, handling gap drop at list edges")
                # 检查是否可以放置在列表开头或结尾的间隙
                # 清除拖拽目标高亮
                self.delegate.set_drag_target_index(None)
                self._handle_drop_on_gap(event, pos, dragged_class_name, dragged_parent_name)
                    
        else:
            print("[Drag] Event ignored, wrong mime type")
            event.ignore()

    def _handle_drop_on_gap(self, event, pos, dragged_class_name: str, dragged_parent_name: Optional[str], before_row=None):
        """处理拖拽到间隙的情况"""
        print(f"[Drag] Handling drop on gap, dragged item: {dragged_class_name}, parent: {dragged_parent_name}")
        if before_row is not None:
            # 使用指定的插入位置
            target_row = before_row
            print(f"[Drag] Using specified row: {before_row}")
        else:
            # 计算应该放置在哪个位置
            target_row = self._get_drop_target_row(pos)
            print(f"[Drag] Calculated target row: {target_row}")
        
        # 确保target_row在有效范围内
        max_row = len(self.project_info.categories)
        print(f"[Drag] Max row: {max_row}")
        if target_row > max_row:
            target_row = max_row
        elif target_row < 0:
            target_row = 0
        
        print(f"[Drag] Final target row: {target_row}")
        # 即使target_row为-1，我们也接受这个放置操作
        self.drag_target_row = target_row
        self.drop_indicator_pos = self._get_drop_indicator_position(target_row)
        print(f"[Drag] Drop indicator position: {self.drop_indicator_pos}")
        
        # 检查是否是子项拖拽到间隙（需要变为一级项）
        self.is_dragging_child_to_gap = dragged_parent_name is not None
        print(f"[Drag] Is dragging child to gap: {self.is_dragging_child_to_gap}")
        
        event.acceptProposedAction()
        self.viewport().update()  # 更新视图以重新绘制
        print("[Drag] Accepted proposed action and updated viewport")

    def _get_drop_target_row(self, pos):
        """计算拖拽目标行"""
        print(f"[Drag] Calculating drop target row for position: {pos}")
        if self.model().rowCount() == 0:
            print("[Drag] Model is empty, target row is 0")
            return 0  # 空列表时插入到开头
            
        # 查找最近的项目
        for row in range(self.model().rowCount()):
            index = self.model().index(row, 0)
            rect = self.visualRect(index)
            
            # 检查是否在项目上半部分（在该项目之前插入）
            if pos.y() <= rect.top() + rect.height() / 4:
                # 需要将代理模型的行号转换为源模型的行号
                source_index = self.proxy_model.mapToSource(index)
                print(f"[Drag] Position in top quarter of row {row}, inserting before. Source row: {source_index.row()}")
                return source_index.row()
                
            # 检查是否在项目下半部分（在该项目之后插入）
            if rect.top() + 3 * rect.height() / 4 < pos.y() <= rect.bottom():
                # 需要将代理模型的行号转换为源模型的行号
                source_index = self.proxy_model.mapToSource(index)
                print(f"[Drag] Position in bottom quarter of row {row}, inserting after. Source row: {source_index.row() + 1}")
                return source_index.row() + 1
                
        # 如果在所有项目之后，插入到末尾
        print("[Drag] Position after all items, inserting at end")
        return len(self.project_info.categories)

    def _get_drop_indicator_position(self, target_row):
        """获取拖拽指示器的位置"""
        print(f"[Drag] Getting drop indicator position for target row: {target_row}")
        # 确保target_row在有效范围内
        max_row = len(self.project_info.categories)
        if target_row > max_row:
            target_row = max_row
            
        if target_row == 0 and max_row > 0:
            # 插入到开头
            first_index = self.proxy_model.mapFromSource(self.source_model.index(0, 0))
            if first_index.isValid():
                first_rect = self.visualRect(first_index)
                pos = QPoint(first_rect.left(), first_rect.top())
                print(f"[Drag] Indicator position for start of list: {pos}")
                return pos
        elif target_row >= max_row > 0:
            # 插入到末尾
            last_index = self.proxy_model.mapFromSource(self.source_model.index(max_row - 1, 0))
            if last_index.isValid():
                last_rect = self.visualRect(last_index)
                pos = QPoint(last_rect.left(), last_rect.bottom())
                print(f"[Drag] Indicator position for end of list: {pos}")
                return pos
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
                pos = QPoint(prev_rect.left(), y_pos)
                print(f"[Drag] Indicator position between items: {pos}")
                return pos
            elif prev_index.isValid():
                # 只有前一个有效
                prev_rect = self.visualRect(prev_index)
                pos = QPoint(prev_rect.left(), prev_rect.bottom())
                print(f"[Drag] Indicator position after previous item: {pos}")
                return pos
            elif next_index.isValid():
                # 只有后一个有效
                next_rect = self.visualRect(next_index)
                pos = QPoint(next_rect.left(), next_rect.top())
                print(f"[Drag] Indicator position before next item: {pos}")
                return pos
        else:
            # 默认位置
            print("[Drag] Using default position (0, 0)")
            return QPoint(0, 0)
            
        # 如果无法确定位置，返回默认值
        print("[Drag] Unable to determine position, using default (0, 0)")
        return QPoint(0, 0)

    def dropEvent(self, event):
        """处理放置事件"""
        print(f"[Drag] Drop event at position: {event.pos()}")
        if event.mimeData().hasFormat('application/x-annotation-category'):
            # 获取被拖拽的类别
            source_data = event.mimeData().data('application/x-annotation-category')
            source_json = json.loads(bytes(source_data).decode('utf-8'))
            dragged_class_name = source_json.get('class_name')
            dragged_parent_name = source_json.get('parent_name')  # 获取拖拽项的父ID
            print(f"[Drag] Dropped item: name={dragged_class_name}, parent={dragged_parent_name}")
            
            # 获取放置位置
            pos = event.pos()
            index = self.indexAt(pos)
            print(f"[Drag] Drop index: valid={index.isValid()}")
            
            # 如果放置在项目上，建立父子关系
            if index.isValid() and self.drag_target_row == -1:
                print("[Drag] Drop on item, attempting to establish parent-child relationship")
                # 获取目标类别
                source_index = self.proxy_model.mapToSource(index)
                target_class_name = self.source_model.data(source_index, Qt.UserRole + 2)
                target_parent_name = self.source_model.data(source_index, Qt.UserRole + 3)  # 获取目标的父级
                print(f"[Drag] Target item name: {target_class_name}, parent: {target_parent_name}")
                
                # 如果目标已经是子项，则将拖拽项设置为与目标相同的父级
                if target_parent_name is not None:
                    print(f"[Drag] Target is already a child, setting dragged item to same parent: {target_parent_name}")
                    # 计算放置位置（上方1/4、中间2/4、下方1/4）
                    rect = self.visualRect(index)
                    y_pos_in_item = pos.y() - rect.top()
                    item_height = rect.height()
                    print(f"[Drag] Position in item: y={y_pos_in_item}, item height: {item_height}")
                    
                    # 根据释放位置决定放置在目标项的上方还是下方
                    if y_pos_in_item < item_height / 2:
                        # 上半部分 - 放置在目标项之前
                        print("[Drag] Drop position: upper half, placing before target")
                        self._move_item_with_same_parent_before(dragged_class_name, target_class_name)
                    else:
                        # 下半部分 - 放置在目标项之后
                        print("[Drag] Drop position: lower half, placing after target")
                        self._move_item_with_same_parent_after(dragged_class_name, target_class_name)
                        
                    event.acceptProposedAction()
                    # 重置拖拽状态
                    self.drag_target_row = -1
                    self.is_dragging_child_to_gap = False
                    self.drag_hover_index = None
                    self.delegate.set_hovered_index(None)
                    self.delegate.set_hovered_index(None)
                    self.viewport().update()
                    print("[Drag] Item moved with same parent")
                    # 确保保存到数据库
                    self.project_info.domain.save_categories()
                    return
                # 检查是否可以建立父子关系
                elif self._can_drop_category(dragged_class_name, target_class_name):
                    print(f"[Drag] Parent-child relationship allowed, establishing relationship: {dragged_class_name} - {target_class_name}")
                    # 建立父子关系
                    # 检查是否需要在特定子项之后插入
                    insert_after_child_name: Optional[str] = None
                    # 这里可以根据需要添加逻辑来确定在哪个子项之后插入
                    self._establish_parent_child_relationship(dragged_class_name, target_class_name, insert_after_child_name)
                    event.acceptProposedAction()
                    # 重置拖拽状态
                    self.drag_target_row = -1
                    self.is_dragging_child_to_gap = False
                    self.drag_hover_index = None
                    self.delegate.set_hovered_index(None)
                    self.delegate.set_hovered_index(None)
                    self.viewport().update()
                    print("[Drag] Parent-child relationship established")
                    # 确保保存到数据库
                    self.project_info.domain.save_categories()
                    # 不再重新加载数据，避免覆盖内存中的更改
                    # self.load_categories()
                    return
                else:
                    print("[Drag] Parent-child relationship not allowed")
            elif self.drag_target_row != -1:
                print(f"[Drag] Drop on gap, reordering items. Target row: {self.drag_target_row}")
                # 放置在间隙，重新排序
                self._reorder_items(dragged_class_name, dragged_parent_name)
                event.acceptProposedAction()
                # 重置拖拽状态
                self.drag_target_row = -1
                self.is_dragging_child_to_gap = False
                self.drag_hover_index = None
                self.delegate.set_hovered_index(None)
                self.viewport().update()
                print("[Drag] Items reordered")
                # 不再重新加载数据，避免覆盖内存中的更改
                # self.load_categories()
                return
            else:
                # 特殊情况处理：即使drag_target_row为-1，也要处理重新排序
                # 这种情况可能发生在直接拖拽到列表末尾等场景
                print("[Drag] Special case: reordering items with target row -1")
                self._reorder_items(dragged_class_name, dragged_parent_name)
                event.acceptProposedAction()
                # 重置拖拽状态
                self.drag_target_row = -1
                self.is_dragging_child_to_gap = False
                self.drag_hover_index = None
                self.delegate.set_hovered_index(None)
                self.viewport().update()
                print("[Drag] Items reordered (special case)")
                # 不再重新加载数据，避免覆盖内存中的更改
                # self.load_categories()
                return
                    
        print("[Drag] Calling super().dropEvent()")
        super().dropEvent(event)
        # 重置拖拽状态
        self.drag_target_row = -1
        self.is_dragging_child_to_gap = False
        self.drag_hover_index = None
        self.delegate.set_hovered_index(None)
        self.delegate.set_drag_target_index(None)
        self.viewport().update()
        print("[Drag] Drop event finished, state reset")
        # 确保保存到数据库
        self.project_info.domain.save_categories()
        # 不再重新加载数据，避免覆盖内存中的更改
        # self.load_categories()

    def _reorder_items(self, dragged_class_name, dragged_parent_name=None):
        """重新排序项目"""
        print(f"[Drag] Reordering items, dragged class name: {dragged_class_name}, parent name: {dragged_parent_name}")
            
        # 找到被拖拽的项目在当前列表中的位置
        dragged_row = -1
        for i, cat in enumerate(self.project_info.categories):
            if cat.class_name == dragged_class_name:
                dragged_row = i
                break
                
        if dragged_row == -1:
            print(f"[Drag] Dragged item not found in categories, aborting reorder")
            return
            
        print(f"[Drag] Dragged item found at row: {dragged_row}")
        # 获取被拖拽的类别
        dragged_category = self.project_info.categories[dragged_row]
        print(f"[Drag] Dragged category details: name={dragged_category.class_name}, parent={dragged_category.parent_name}")
        
        # 如果是从子项变为一级项，更新其属性
        if self.is_dragging_child_to_gap and dragged_category.parent_name is not None:
            print("[Drag] Converting child item to top-level item")
            # 设置为一级项
            dragged_category.parent_name = None
            print("[Drag] Set item as top-level (parent=None)")
            
            # 更新模型中的数据
            dragged_item = self.source_model.get_item_by_class_name(dragged_class_name)
            if dragged_item:
                dragged_item.set_parent_name(None)
        
        # 从原位置移除
        removed_category = self.project_info.categories.pop(dragged_row)
        print(f"[Drag] Removed category from row {dragged_row}")
        
        # 计算插入位置（如果原位置在目标位置之前，目标位置需要减1）
        # 如果 drag_target_row 为 -1，则插入到末尾
        if self.drag_target_row == -1:
            insert_row = len(self.project_info.categories)
        else:
            insert_row = self.drag_target_row
            if dragged_row < insert_row:
                insert_row -= 1
            
        print(f"[Drag] Inserting category at row: {insert_row}")
        # 插入到新位置
        self.project_info.categories.insert(insert_row, removed_category)
        print(f"[Drag] Category inserted")
        
        # 更新所有项的order属性
        self._update_category_orders()
        
        # 重新排序整个列表以确保正确的显示顺序
        self._reorder_entire_list()
        
        # 保存更改
        self.project_info.domain.save_categories()
        print("[Drag] Categories saved")

    def _can_drop_category(self, dragged_class_name: str, target_class_name: str) -> bool:
        """检查是否可以将dragged_class拖放到target_class上"""
        # 不能将类别拖放到自己身上
        if dragged_class_name == target_class_name:
            return False
            
        # 检查是否会形成循环引用（不能将父项拖到自己的子项上）
        current_parent_name = target_class_name
        while current_parent_name is not None:
            # 查找当前parent_name对应的类别
            parent_category = None
            for cat in self.project_info.categories:
                if cat.class_name == current_parent_name:
                    parent_category = cat
                    break
                    
            if parent_category is None:
                break
                
            # 如果发现循环引用，返回False
            if parent_category.parent_name == dragged_class_name:
                return False
                
            current_parent_name = parent_category.parent_name
            
        # 检查目标是否已经是子项（只允许一级嵌套）
        for cat in self.project_info.categories:
            if cat.class_name == target_class_name:
                # 目标已经是子项，不允许再作为父项
                if cat.parent_name is not None:
                    return False
                break
        
        return True

    def _establish_parent_child_relationship(self, child_name: str, parent_name: str, insert_after_child_name: Optional[str] = None):
        """建立父子关系，可选择在指定子项之后插入"""
        print(f"[Drag] Establishing parent-child relationship: child={child_name}, parent={parent_name}, insert_after={insert_after_child_name}")
        child_category = None
        parent_category = None
        
        # 查找子项和父项
        for cat in self.project_info.categories:
            if cat.class_name == child_name:
                child_category = cat
            elif cat.class_name == parent_name:
                parent_category = cat
                
        if child_category is None or parent_category is None:
            print(f"[Drag] Child or parent category not found, aborting. Child: {child_category}, Parent: {parent_category}")
            return
            
        print(f"[Drag] Found child category: id={child_category.class_id}, parent={child_category.parent_name}")
        print(f"[Drag] Found parent category: id={parent_category.class_id}, parent={parent_category.parent_name}")
            
        # 保存原始的父级信息，用于后续处理子项
        original_child_parent = child_category.parent_name
            
        # 设置父子关系
        child_category.parent_name = parent_name
        print(f"[Drag] Set child's parent to: {parent_name}")
        
        # 同时更新模型中的数据
        child_item = self.source_model.get_item_by_class_name(child_name)
        if child_item:
            child_item.set_parent_name(parent_name)
        
        # 查找并移动所有child的子项也作为parent的子项
        child_items_to_move = []
        for cat in self.project_info.categories:
            if cat.parent_name == child_name:
                child_items_to_move.append(cat)
        
        # 将child的所有子项也设置为parent的子项
        for child_item in child_items_to_move:
            child_item.parent_name = parent_name
            item_in_model = self.source_model.get_item_by_class_name(child_item.class_name)
            if item_in_model:
                item_in_model.set_parent_name(parent_name)
            print(f"[Drag] Moved grandchild '{child_item.class_name}' to be child of '{parent_name}'")
        
        # 重新排序整个列表以确保正确的显示顺序
        self._reorder_entire_list()
        print("[Drag] Reordered entire list")
        
        # 保存更改
        self.project_info.domain.save_categories()
        print("[Drag] Categories saved")

    def _reorder_entire_list(self):
        """根据parent_name和order属性重新排序整个列表"""
        # 先按照order排序
        sorted_categories = sorted(self.project_info.categories, key=lambda cat: cat.order)
        
        # 分离顶级项目和子项目
        top_level_categories = [cat for cat in sorted_categories if cat.parent_name is None]
        child_categories = [cat for cat in sorted_categories if cat.parent_name is not None]
        
        # 创建父项到子项的映射
        parent_to_children = {}
        for child in child_categories:
            if child.parent_name not in parent_to_children:
                parent_to_children[child.parent_name] = []
            parent_to_children[child.parent_name].append(child)
        
        # 按照正确顺序重新排列
        ordered_categories = []
        for cat in top_level_categories:  # 只处理顶级项目
            ordered_categories.append(cat)
            # 添加其子项目
            if cat.class_name in parent_to_children:
                # 按order排序子项目
                sorted_children = sorted(parent_to_children[cat.class_name], key=lambda c: c.order)
                ordered_categories.extend(sorted_children)
        
        # 更新project_info.categories
        self.project_info.categories = ordered_categories
        
        # 更新模型
        self.source_model.update_from_categories(ordered_categories)
        
        # 更新order值，一级项目使用100的间隔，二级项目使用1的间隔
        self._update_category_orders()

    def _update_category_orders(self):
        """更新类别顺序，一级项目间隔100，二级项目间隔1"""
        # 先处理一级项目
        top_level_categories = [cat for cat in self.project_info.categories if cat.parent_name is None]
        for index, category in enumerate(top_level_categories):
            category.order = (index + 1) * 100
            
        # 再处理二级项目
        # 首先为每个父级项目创建子项目列表
        parent_to_children = {}
        for category in self.project_info.categories:
            if category.parent_name is not None:
                if category.parent_name not in parent_to_children:
                    parent_to_children[category.parent_name] = []
                parent_to_children[category.parent_name].append(category)
        
        # 为每个父级的子项目设置顺序
        for parent_name, children in parent_to_children.items():
            # 找到父级项目的order值
            parent_order = 0
            for cat in self.project_info.categories:
                if cat.class_name == parent_name:
                    parent_order = cat.order
                    break
            
            # 为子项目设置顺序，从父级order开始，间隔为1
            # 首先对子项目进行排序
            sorted_children = sorted(children, key=lambda c: c.order)
            
            # 然后更新它们的order值
            for index, child in enumerate(sorted_children):
                child.order = parent_order + index + 1

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
                    self.source_model.set_color(source_index, self.project_info.categories[row].color)

    def get_selected_category(self):
        """获取当前选中的完整类别对象"""
        selected = self.selectionModel().selectedIndexes()
        if selected:
            source_index = self.proxy_model.mapToSource(selected[0])
            class_id = self.source_model.data(source_index, Qt.UserRole + 1)
            class_name = self.source_model.data(source_index, Qt.DisplayRole)
            return AnnotationCategoryDTO(class_id, class_name)
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

        new_category = AnnotationCategoryDTO(
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

        # 更新所有项的order属性
        self._update_category_orders()

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

        self.project_info.domain.save_categories()

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
                # 获取要删除的类别
                category_to_delete = self.project_info.categories[row]
                category_name = category_to_delete.class_name
                
                # 检查有多少个kilo_item引用了这个类型
                count = self.project_info.domain.count_kilo_items_for_category(category_name)
                
                # 如果有引用，则弹出确认对话框
                if count > 0:
                    reply = QMessageBox.question(
                        self, 
                        "确认删除", 
                        f"有{count}个标记数据使用了类别'{category_name}'，是否确认删除？",
                        QMessageBox.Yes | QMessageBox.No, 
                        QMessageBox.No
                    )
                    
                    # 如果用户不确认删除，则返回
                    if reply != QMessageBox.Yes:
                        return
                
                # 调用ProjectDomain的delete_category方法进行删除
                try:
                    self.project_info.domain.delete_category(category_name)
                except Exception as e:
                    QMessageBox.critical(self, "删除失败", f"删除类别时出错: {str(e)}")
                    return
                
                # 删除成功后，立即更新project_info中的categories，防止旧数据被保存
                self.source_model.removeRow(row)
                self.source_model.update_from_categories(self.project_info.categories)
                
                # 保存更改
                self.project_info.domain.save_categories()

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


    def load_categories_from_yolo_model(self, model_path):
        """
        从YOLO模型文件(.pt)加载类别信息，并与现有类别合并。
        """
        try:
            model = YOLO(model_path)
            class_dict = model.names  # {0: 'person', 1: 'car', ...}

            new_categories = [
                AnnotationCategoryDTO(class_id=i, class_name=name)
                for i, name in class_dict.items()
            ]
            self.project_info.domain.add_categories(new_categories)
            return True
        except Exception as e:
            print(f"加载YOLO模型失败: {str(e)}")
            return False


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
                pen.setColor(QColor(255, 165, 0))  # 橙色表示重新排序
                pen.setWidth(2)
                
            painter.setPen(pen)
            
            # 绘制指示线
            if self.model().rowCount() > 0:
                indicator_width = self.viewport().width() - 20
                # 只在重新排序时绘制指示线
                if not (hasattr(self.delegate, 'drag_target_index') and self.delegate.drag_target_index):
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
        print("[Drag] Drag leave event")
        super().dragLeaveEvent(event)
        # 重置拖拽状态
        self.drag_target_row = -1
        self.is_dragging_child_to_gap = False
        self.drag_hover_index = None
        self.delegate.set_hovered_index(None)
        self.delegate.set_drag_target_index(None)
        self.viewport().update()
        # 清除当前选中状态
        self.setCurrentIndex(QModelIndex())
        print("[Drag] Drag leave event handled, state reset")

    def move_item_as_child_after(self, child_name: str, parent_name: str, after_child_name: Optional[str] = None):
        """
        将指定的子项移动为某个父项的子项，并可选择放置在特定子项之后
        
        Args:
            child_name: 要移动的子项ID
            parent_name: 目标父项ID
            after_child_name: 可选，放置在该子项之后
        """
        # 验证父子关系合法性
        if child_name == parent_name:
            # 不能将项目设置为自己的父项
            return False
            
        # 检查是否会形成循环引用
        current_parent_name = parent_name
        while current_parent_name is not None:
            if current_parent_name == child_name:
                # 会形成循环引用
                return False
            # 查找当前parent_name对应的类别
            parent_category = None
            for cat in self.project_info.categories:
                if cat.class_name == current_parent_name:
                    parent_category = cat
                    break
            if parent_category is None:
                break
            current_parent_name = parent_category.parent_name
            
        # 检查目标是否已经是子项（只允许一级嵌套）
        for cat in self.project_info.categories:
            if cat.class_name == parent_name:
                # 目标已经是子项，不允许再作为父项
                if cat.parent_name is not None:
                    return False
                break
        
        # 查找要移动的子项和目标父项
        child_category = None
        parent_category = None
        after_child_category = None
        
        for cat in self.project_info.categories:
            if cat.class_name == child_name:
                child_category = cat
            elif cat.class_name == parent_name:
                parent_category = cat
            elif after_child_name is not None and cat.class_name == after_child_name:
                after_child_category = cat
                
        if child_category is None or parent_category is None:
            return False
            
        # 如果指定了after_child_name，需要确保它确实是parent_name的子项
        if after_child_name is not None and (after_child_category is None or
                                             after_child_category.parent_name != parent_name):
            return False
            
        # 更新子项的parent_name
        child_category.parent_name = parent_name
            
        # 重新排序整个列表
        self._reorder_entire_list()
        
        # 保存更改
        self.project_info.domain.save_categories()
        
        return True
        
    def _move_item_with_same_parent_before(self, moved_class_name: str, target_class_name: str):
        """将拖拽项设置为与目标项相同的父级，并放置在目标项之前"""
        print(f"[Drag] Moving item '{moved_class_name}' to same parent as '{target_class_name}', placing before target")
        
        # 查找目标项以获取其父级
        target_category = None
        moved_category = None
        
        for cat in self.project_info.categories:
            if cat.class_name == target_class_name:
                target_category = cat
            elif cat.class_name == moved_class_name:
                moved_category = cat
                
        if target_category is None or moved_category is None:
            print("[Drag] Target or moved category not found")
            return
            
        # 获取目标的父级
        target_parent_name = target_category.parent_name
        print(f"[Drag] Target parent name: {target_parent_name}")
        
        # 设置拖拽项的父级与目标项相同
        moved_category.parent_name = target_parent_name
        
        # 更新模型中的数据
        moved_item = self.source_model.get_item_by_class_name(moved_class_name)
        if moved_item:
            moved_item.set_parent_name(target_parent_name)
            
        # 查找moved_category的所有子项
        moved_children = []
        for cat in self.project_info.categories:
            if cat.parent_name == moved_class_name:
                moved_children.append(cat)
                
        # 更新所有子项的父级为target_parent_name
        for child in moved_children:
            child.parent_name = target_parent_name
            child_item = self.source_model.get_item_by_class_name(child.class_name)
            if child_item:
                child_item.set_parent_name(target_parent_name)
            print(f"[Drag] Updated child '{child.class_name}' parent to '{target_parent_name}'")
            
        # 重新排序整个列表
        self._reorder_with_moved_item_before_target_and_children(moved_class_name, target_class_name, moved_children)
        
        # 保存更改
        self.project_info.domain.save_categories()
        
    def _reorder_with_moved_item_before_target_and_children(self, moved_class_name: str, target_class_name: str, moved_children: list):
        """重新排序列表，确保移动的项及其子项在目标项之前"""
        # 先按照order排序
        sorted_categories = sorted(self.project_info.categories, key=lambda cat: cat.order)
        
        # 分离顶级项目和子项目
        top_level_categories = [cat for cat in sorted_categories if cat.parent_name is None]
        child_categories = [cat for cat in sorted_categories if cat.parent_name is not None]
        
        # 创建父项到子项的映射
        parent_to_children = {}
        for child in child_categories:
            if child.parent_name not in parent_to_children:
                parent_to_children[child.parent_name] = []
            parent_to_children[child.parent_name].append(child)
        
        # 按照正确顺序重新排列
        ordered_categories = []
        for cat in top_level_categories:  # 只处理顶级项目
            ordered_categories.append(cat)
            # 添加其子项目
            if cat.class_name in parent_to_children:
                # 按order排序子项目
                sorted_children = sorted(parent_to_children[cat.class_name], key=lambda c: c.order)
                # 确保moved_class_name在target_class_name之前，并且其子项紧跟在后面
                self._ensure_order_before_with_children(sorted_children, target_class_name, moved_class_name, moved_children)
                ordered_categories.extend(sorted_children)
        
        # 更新project_info.categories
        self.project_info.categories = ordered_categories
        
        # 更新模型
        self.source_model.update_from_categories(ordered_categories)
        
        # 更新order值
        self._update_category_orders()
            
    def _ensure_order_before_with_children(self, children_list, target_name, moved_name, moved_children):
        """确保在children_list中moved_name及其子项在target_name之前"""
        target_index = -1
        moved_index = -1
        
        # 找到target_name和moved_name的索引
        for i, child in enumerate(children_list):
            if child.class_name == target_name:
                target_index = i
            elif child.class_name == moved_name:
                moved_index = i
                
        # 如果都找到了且moved_index在target_index之后，则调整顺序
        if target_index != -1 and moved_index != -1 and moved_index > target_index:
            # 先移动所有子项
            moved_child_items = []
            for child in moved_children:
                # 查找子项在列表中的位置
                child_index = -1
                for i, c in enumerate(children_list):
                    if c.class_name == child.class_name:
                        child_index = i
                        break
                        
                if child_index != -1:
                    # 移除子项
                    child_item = children_list.pop(child_index)
                    moved_child_items.append(child_item)
                    # 如果子项在moved_item之前被移除，需要调整moved_index和target_index
                    if child_index < moved_index:
                        moved_index -= 1
                    if child_index < target_index:
                        target_index -= 1
            
            # 移除moved_item
            moved_item = children_list.pop(moved_index)
            # 在target_item之前插入moved_item
            children_list.insert(target_index, moved_item)
            
            # 将子项插入到moved_item之后
            for i, child_item in enumerate(moved_child_items):
                children_list.insert(target_index + 1 + i, child_item)
                
    def _move_item_with_same_parent_after(self, moved_class_name: str, target_class_name: str):
        """将拖拽项设置为与目标项相同的父级，并放置在目标项之后"""
        print(f"[Drag] Moving item '{moved_class_name}' to same parent as '{target_class_name}', placing after target")
        
        # 查找目标项以获取其父级
        target_category = None
        moved_category = None
        
        for cat in self.project_info.categories:
            if cat.class_name == target_class_name:
                target_category = cat
            elif cat.class_name == moved_class_name:
                moved_category = cat
                
        if target_category is None or moved_category is None:
            print("[Drag] Target or moved category not found")
            return
            
        # 获取目标的父级
        target_parent_name = target_category.parent_name
        print(f"[Drag] Target parent name: {target_parent_name}")
        
        # 设置拖拽项的父级与目标项相同
        moved_category.parent_name = target_parent_name
        
        # 更新模型中的数据
        moved_item = self.source_model.get_item_by_class_name(moved_class_name)
        if moved_item:
            moved_item.set_parent_name(target_parent_name)
            
        # 查找moved_category的所有子项
        moved_children = []
        for cat in self.project_info.categories:
            if cat.parent_name == moved_class_name:
                moved_children.append(cat)
                
        # 更新所有子项的父级为target_parent_name
        for child in moved_children:
            child.parent_name = target_parent_name
            child_item = self.source_model.get_item_by_class_name(child.class_name)
            if child_item:
                child_item.set_parent_name(target_parent_name)
            print(f"[Drag] Updated child '{child.class_name}' parent to '{target_parent_name}'")
            
        # 重新排序整个列表，确保拖拽项在目标项之后
        self._reorder_with_moved_item_after_target_and_children(moved_class_name, target_class_name, moved_children)
        
        # 保存更改
        self.project_info.domain.save_categories()
        
    def _reorder_with_moved_item_after_target_and_children(self, moved_class_name: str, target_class_name: str, moved_children: list):
        """重新排序列表，确保移动的项及其子项在目标项之后"""
        # 先按照order排序
        sorted_categories = sorted(self.project_info.categories, key=lambda cat: cat.order)
        
        # 分离顶级项目和子项目
        top_level_categories = [cat for cat in sorted_categories if cat.parent_name is None]
        child_categories = [cat for cat in sorted_categories if cat.parent_name is not None]
        
        # 创建父项到子项的映射
        parent_to_children = {}
        for child in child_categories:
            if child.parent_name not in parent_to_children:
                parent_to_children[child.parent_name] = []
            parent_to_children[child.parent_name].append(child)
        
        # 按照正确顺序重新排列
        ordered_categories = []
        for cat in top_level_categories:  # 只处理顶级项目
            ordered_categories.append(cat)
            # 添加其子项目
            if cat.class_name in parent_to_children:
                # 按order排序子项目
                sorted_children = sorted(parent_to_children[cat.class_name], key=lambda c: c.order)
                # 确保moved_class_name在target_class_name之后，并且其子项紧跟在后面
                self._ensure_order_with_children(sorted_children, target_class_name, moved_class_name, moved_children)
                ordered_categories.extend(sorted_children)
        
        # 更新project_info.categories
        self.project_info.categories = ordered_categories
        
        # 更新模型
        self.source_model.update_from_categories(ordered_categories)
        
        # 更新order值
        self._update_category_orders()
            
    def _ensure_order_with_children(self, children_list, target_name, moved_name, moved_children):
        """确保在children_list中moved_name及其子项在target_name之后"""
        target_index = -1
        moved_index = -1
        
        # 找到target_name和moved_name的索引
        for i, child in enumerate(children_list):
            if child.class_name == target_name:
                target_index = i
            elif child.class_name == moved_name:
                moved_index = i
                
        # 如果都找到了且moved_index在target_index之前，则调整顺序
        if target_index != -1 and moved_index != -1 and moved_index < target_index:
            # 移除moved_item
            moved_item = children_list.pop(moved_index)
            # 在target_item之后插入
            children_list.insert(target_index, moved_item)
            
            # 同时移动所有子项到moved_item之后
            inserted_count = 0
            for child in moved_children:
                # 查找子项在列表中的位置
                child_index = -1
                for i, c in enumerate(children_list):
                    if c.class_name == child.class_name:
                        child_index = i
                        break
                        
                if child_index != -1:
                    # 移除子项
                    child_item = children_list.pop(child_index)
                    # 如果子项在moved_item之前被移除，需要调整target_index
                    if child_index < target_index:
                        target_index -= 1
                    # 在moved_item之后插入子项
                    target_index += 1
                    children_list.insert(target_index, child_item)
                    inserted_count += 1
