# annotation_list.py

import json
import typing
from typing import Optional, Union

from PyQt5 import QtCore
from PyQt5.QtCore import Qt, QSize, QItemSelectionModel, QMimeData, \
    QSortFilterProxyModel, QPoint, QModelIndex
from PyQt5.QtGui import QPen, QDrag, QColor, QPainter
from PyQt5.QtWidgets import QLineEdit, QListView, QAbstractItemView, \
    QToolBar, QWidget, QHBoxLayout, QMenu, QAction, QMessageBox, QColorDialog
from ultralytics import YOLO

from src.core.project_info import ProjectInfo
from src.ui.widget.annotation_list.annotation_delegate import AnnotationDelegate
from src.ui.widget.annotation_list.annotation_item import AnnotationItem
from src.ui.widget.annotation_list.annotation_list_model import AnnotationListModel, AnnotationDropArea
from src.ui.widget.annotation_list.editable_annotation_delegate import EditableAnnotationDelegate
from src.core.i18n.language_manager import tr  # 添加国际化翻译导入


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
        
        # 添加对image_canvas的引用
        self.image_canvas = None

        # 设置最小宽度，确保能显示所有区域
        self.setMinimumWidth(self.calculate_min_width())

        # 创建工具栏
        self.toolbar = self.create_toolbar()

        # 创建模型
        self.source_model = AnnotationListModel(project_info=self.project_info, parent=self)

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
        self.delegate = EditableAnnotationDelegate(self.project_info, row_height, self)
        self.setItemDelegate(self.delegate)

        # 连接信号
        self.clicked.connect(self._handle_item_click)  # type: ignore
        # self.selectionModel().selectionChanged.connect(self._handle_selection_change)  # type: ignore
        # self.source_model.dataChanged.connect(self._handle_model_data_changed)
        
        # 加载类别数据
        self.source_model.refresh_model()

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
        self.search_edit.setPlaceholderText(tr("class_manager_label") + "...")
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
        annotation_item = self.get_annotation_item_by_index(self.currentIndex())
        print(f"[Drag] Dragging category: id={annotation_item.class_id}, name={annotation_item.class_name}, parent={annotation_item.parent_name}")

        drag_data = {
            'class_id': annotation_item.class_id,
            'class_name': annotation_item.class_name,
            'color': annotation_item.class_color.name(),
            'parent_name': annotation_item.parent_name  # 添加父ID信息
        }

        mime_data = QMimeData()
        mime_data.setData('application/x-annotation-category', json.dumps(drag_data).encode('utf-8'))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        
        # 使用自定义的 pixmap 作为拖拽图像
        pixmap = self.delegate.create_drag_pixmap(annotation_item)
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

    def get_annotation_item_by_index(self, index: QModelIndex) -> Optional[AnnotationItem]:
        """根据索引获取对应的item"""
        if not index.isValid():
            return None
        source_index = self.proxy_model.mapToSource(index)
        if not (0 <= source_index.row() < self.source_model.rowCount()):
            print("[Drag] Source index out of range, aborting drag")
            return None
        item = typing.cast(AnnotationItem, self.source_model.item_from_index(source_index))
        # 确保item具有正确的模型引用
        item.set_model(self.source_model)
        return item

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
        max_row = self.source_model.rowCount()
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
        return self.source_model.rowCount()

    def _get_drop_indicator_position(self, target_row):
        """获取拖拽指示器的位置"""
        print(f"[Drag] Getting drop indicator position for target row: {target_row}")
        # 确保target_row在有效范围内
        max_row = self.source_model.rowCount()
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
            
            # 分析拖拽情况并确定drop区域
            drop_area = None
            target_class_name = None
            
            if index.isValid():
                # 获取目标类别
                source_index = self.proxy_model.mapToSource(index)
                target_class_name = self.source_model.data(source_index, Qt.UserRole + 2)
                target_parent_name = self.source_model.data(source_index, Qt.UserRole + 3)  # 获取目标的父级
                print(f"[Drag] Target item name: {target_class_name}, parent: {target_parent_name}")
                
                # 计算放置位置（上方1/4、中间2/4、下方1/4）
                rect = self.visualRect(index)
                y_pos_in_item = pos.y() - rect.top()
                item_height = rect.height()
                print(f"[Drag] Position in item: y={y_pos_in_item}, item height: {item_height}")
                
                # 根据释放位置决定放置在目标项的上方、中间还是下方
                if y_pos_in_item < item_height / 4:
                    # 上方1/4区域 - 放置在目标项之前
                    drop_area = AnnotationDropArea.TOP
                    print("[Drag] Drop position: top quarter, placing before target")
                elif y_pos_in_item > 3 * item_height / 4:
                    # 下方1/4区域 - 放置在目标项之后
                    drop_area = AnnotationDropArea.BOTTOM
                    print("[Drag] Drop position: bottom quarter, placing after target")
                else:
                    # 中间2/4区域 - 检查是否可以建立父子关系
                    print("[Drag] Drop position: middle half")
                    # 如果目标已经是子项，则将拖拽项设置为与目标相同的父级
                    if target_parent_name is not None:
                        print(f"[Drag] Target is already a child, setting dragged item to same parent: {target_parent_name}")
                        drop_area = AnnotationDropArea.TOP  # 作为同级项处理
                    elif self._can_drop_category(dragged_class_name, target_class_name):
                        print("[Drag] Parent-child relationship allowed")
                        drop_area = AnnotationDropArea.CENTER
                    else:
                        print("[Drag] Parent-child relationship not allowed, placing after target")
                        drop_area = AnnotationDropArea.BOTTOM
                        
                # 调用模型的移动方法
                if drop_area and target_class_name:
                    self.source_model.move_category(dragged_class_name, target_class_name, drop_area)
                    event.acceptProposedAction()
            elif self.drag_target_row != -1 or True:  # 总是处理这种情况
                print(f"[Drag] Drop on gap, reordering items. Target row: {self.drag_target_row}")
                # 放置在间隙，重新排序
                event.acceptProposedAction()
                    
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


    @staticmethod
    def _can_drop_category(dragged_class_name: str, target_class_name: str) -> bool:
        """检查是否可以将dragged_class拖放到target_class上"""
        # 不能将类别拖放到自己身上
        if dragged_class_name == target_class_name:
            return False
        return True

    def _handle_item_click(self, clicked_index):
        """处理点击事件 - 保持单选状态"""
        if not clicked_index.isValid():
            return

        if not self.selectionModel().isSelected(clicked_index):
            self.selectionModel().clearSelection()
            self.selectionModel().select(clicked_index, QItemSelectionModel.SelectionFlag.ClearAndSelect)

    def get_selected_annotation_item(self) -> Optional[AnnotationItem]:
        """获取当前选中的完整类别对象"""
        selected = self.selectionModel().selectedIndexes()
        if selected:
            source_index = self.proxy_model.mapToSource(selected[0])
            # 从source_model中获取对应的AnnotationItem实例（关键修复）
            selected_item = self.source_model.item_from_index(source_index)
            # 确保获取的是AnnotationItem类型（可选类型校验）
            if isinstance(selected_item, AnnotationItem):
                return selected_item
        return None

    def _handle_search_text_changed(self, search_text):
        """处理搜索文本变化，实时过滤列表"""
        # 设置过滤条件，匹配包含搜索内容的行
        self.proxy_model.setFilterFixedString(search_text.strip())
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setFilterRole(Qt.DisplayRole)

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


    def _handle_delete(self):
        """处理删除操作"""
        if not(self.right_click_index and self.right_click_index.isValid()):
            return

        source_index = self.proxy_model.mapToSource(self.right_click_index)
        category_name = self.source_model.get_category_name_by_index(source_index)
        # 检查有多少个kilo_item引用了这个类型
        count = self.source_model.count_kilo_items_for_category(category_name)
        # 如果有引用，则弹出确认对话框
        if count > 0:
            reply = QMessageBox.question(
                self,
                tr("context_menu_confirm_delete"),
                tr("context_menu_delete_confirm_message", count=count, category_name=category_name),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No
            )

            # 如果用户不确认删除，则返回
            if reply != QMessageBox.Yes:
                return

        try:
            self.source_model.delete_category_by_index(source_index)
        except Exception as e:
            QMessageBox.critical(self, tr("context_menu_delete_error"), tr("context_menu_delete_error_message", error=str(e)))
            return

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
        add_action = QAction(tr("context_menu_add"), self)
        add_action.triggered.connect(self._handle_add_annotation)  # type:ignore

        rename_action = QAction(tr("context_menu_rename"), self)
        rename_action.triggered.connect(self._handle_rename) # type: ignore
        rename_action.setEnabled(index.isValid())  # 只有选中项时可用


        delete_action = QAction(tr("context_menu_delete"), self)
        delete_action.triggered.connect(self._handle_delete)  # type:ignore
        delete_action.setEnabled(index.isValid())  # 只有选中项时可用

        # 添加到菜单
        menu.addAction(add_action)
        menu.addSeparator()
        menu.addAction(rename_action)
        
        # 添加修改颜色菜单项
        color_action = QAction(tr("context_menu_edit_color"), self)
        color_action.triggered.connect(self._handle_set_color)  # type:ignore
        color_action.setEnabled(index.isValid())  # 只有选中项时可用
        menu.addAction(color_action)
        
        menu.addAction(delete_action)
        
        # 添加分隔线
        menu.addSeparator()
        
        # 添加统计菜单项
        statistics_action = QAction(tr("context_menu_statistics"), self)
        statistics_action.triggered.connect(self._handle_statistics)  # type:ignore
        menu.addAction(statistics_action)

        # 显示菜单
        menu.exec_(event.globalPos())

    def _handle_add_annotation(self):
        """处理新增标注操作"""
        # 添加到末尾
        row_count = self.source_model.rowCount()
        new_category = self.source_model.append_new_category()
        proxy_index = self.proxy_model.mapFromSource(self.source_model.index(row_count, 0))

        print(f"新类别添加成功: {new_category.class_name}")

        # 滚动到新项位置
        self.scrollTo(proxy_index)

        # 选中新项
        self.selectionModel().select(
            proxy_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
        )

    def _handle_statistics(self):
        """处理统计操作"""
        # 导入统计对话框
        from src.ui.dialog.statistics_dialog import StatisticsDialog
        
        # 创建并显示统计对话框
        dialog = StatisticsDialog(self.project_info, self)
        dialog.exec_()

    def _handle_set_color(self):
        """处理修改颜色操作"""
        if not (self.right_click_index and self.right_click_index.isValid()):
            return

        # 获取当前选中的类别信息
        source_index = self.proxy_model.mapToSource(self.right_click_index)
        annotation_item = self.source_model.item_from_index(source_index)
        
        if not annotation_item:
            return
            
        # 获取当前颜色作为初始颜色
        current_color = annotation_item.class_color
        
        # 显示颜色选择对话框
        color = QColorDialog.getColor(current_color, self, tr("context_menu_edit_color"))
        
        if color.isValid():  # 如果用户选择了颜色并确认
            try:
                # 获取类别名称
                class_name = annotation_item.class_name
                color_name = color.name()  # 获取颜色的十六进制表示
                
                # 调用domain的recolor_category方法更新数据库
                success = self.project_info.domain.recolor_category(class_name, color_name)
                
                if success:
                    # 更新模型中的颜色
                    annotation_item.setData(color, Qt.UserRole)
                    # 同时更新color_name字段
                    annotation_item.setData(color_name, Qt.UserRole + 5)

                    # 刷新视图
                    self.source_model.dataChanged.emit(source_index, source_index, [Qt.UserRole])

                    # 通知image canvas更新所有对应类别的annotation view颜色
                    if self.image_canvas:
                        self.image_canvas.update_annotation_colors(class_name, color)

                    print(f"类别 '{class_name}' 的颜色已更新为 {color_name}")
                else:
                    QMessageBox.warning(self, tr("dialog_title_error"), f"无法更新类别 '{class_name}' 的颜色")
            except Exception as e:
                QMessageBox.critical(self, tr("dialog_title_error"), f"修改颜色时出错: {str(e)}")

    def load_categories_from_yolo_model(self, model_path):
        """
        从YOLO模型文件(.pt)加载类别信息，并与现有类别合并。
        """
        try:
            model = YOLO(model_path)
            class_dict = model.names  # {0: 'person', 1: 'car', ...}
            for i, name in class_dict.items():
                self.source_model.append_new_category(class_name=name, class_id=i)
            return True
        except Exception as e:
            print(f"加载YOLO模型失败: {str(e)}")
            return False


    def select_category_by_name(self, class_name: str):
        """根据类别名称选中对应的列表项"""
        annotation_item = self.source_model.get_item_by_class_name(class_name)
        if not annotation_item:
            return False

        # 使用actual_row()方法获取准确的行号
        proxy_index = self.proxy_model.mapFromSource(self.source_model.index(annotation_item.actual_row(), 0))
        self.selectionModel().select(
            proxy_index,
            QItemSelectionModel.SelectionFlag.ClearAndSelect
        )
        self.scrollTo(proxy_index)
        return True

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
