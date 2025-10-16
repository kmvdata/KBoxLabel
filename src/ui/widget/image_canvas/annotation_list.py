# annotation_list.py
import json
from typing import Tuple

from PyQt5.QtCore import pyqtSignal, Qt, QSize, QRect, QItemSelectionModel, QMimeData, \
    QSortFilterProxyModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPen, QDrag
from PyQt5.QtWidgets import QLineEdit, QSpinBox, QListView, QStyledItemDelegate, QAbstractItemView, \
    QStyle, QToolBar, QWidget, QHBoxLayout, QMenu, QAction
from ultralytics import YOLO

from src.models.dto.annotation_category import AnnotationCategory
from src.models.dto.ref_project_info import RefProjectInfo


class AnnotationDelegate(QStyledItemDelegate):
    """优化后的委托类，实现垂直居中对齐和布局调整"""
    MARGIN = 4  # 整体边距
    SPACING = 8  # 区域间间距

    def __init__(self, row_height=56, parent=None):
        super().__init__(parent)
        self.row_height = row_height

    def set_row_height(self, height: int):
        self.row_height = height

    def sizeHint(self, option, index):
        # 计算最小宽度：color区域 + name最小区域 + id区域 + 间距和边距
        min_width = (self.row_height + self.SPACING) * 2 + 2 * self.row_height + 2 * self.MARGIN
        return QSize(min_width, self.row_height)

    def paint(self, painter, option, index):
        # 获取数据
        category_color = index.data(Qt.UserRole)
        class_id = index.data(Qt.UserRole + 1)
        category_name = index.data(Qt.DisplayRole)

        if not all([category_color, category_name, class_id is not None]):
            return

        # 处理选中状态
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.fillRect(option.rect, option.palette.window())
            painter.setPen(option.palette.windowText().color())

        # 计算各区域尺寸
        # color区域：正方形，宽度和高度等于item高度
        color_size = self.row_height - 2 * self.MARGIN
        color_rect = QRect(
            option.rect.left() + self.MARGIN,
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
        available_width = option.rect.width() - (color_size + self.MARGIN + self.SPACING) * 2
        name_width = max(available_width, name_min_width)

        name_rect = QRect(
            color_rect.right() + self.SPACING,
            option.rect.top(),
            name_width,
            self.row_height
        )

        # 绘制元素
        painter.fillRect(color_rect, category_color)  # 颜色方块
        painter.drawText(name_rect, Qt.AlignLeft | Qt.AlignVCenter, category_name)  # 文本
        painter.drawText(id_rect, Qt.AlignCenter, str(class_id))  # 序号

        # 添加颜色方块边框增强可读性
        border_pen = QPen(option.palette.windowText().color(), 1)
        painter.setPen(border_pen)
        painter.drawRect(color_rect)


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
                        QMessageBox.warning(view, "重命名失败", f"名称 '{category_name}' 已存在，请使用其他名称。")
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

    def add_annotation(self, category: AnnotationCategory):
        """添加带序号的标注项"""
        item = QStandardItem(category.class_name)
        item.setData(category.color, Qt.UserRole)
        item.setData(category.class_id, Qt.UserRole + 1)
        item.setEditable(True)
        self.appendRow(item)

    def insert_annotation(self, category: AnnotationCategory, row: int):
        """在指定位置插入标注项"""
        item = QStandardItem(category.class_name)
        item.setData(category.color, Qt.UserRole)
        item.setData(category.class_id, Qt.UserRole + 1)
        item.setEditable(True)
        self.insertRow(row, item)

    def clear_annotations(self):
        """清除所有标注"""
        self.clear()
        self.setColumnCount(1)

    def update_from_categories(self, categories: list[AnnotationCategory]):
        """从类别列表更新模型"""
        self.clear_annotations()
        for category in categories:
            self.add_annotation(category)


class AnnotationList(QListView):
    """带序号的YOLO标注类别列表组件"""
    annotation_selected = pyqtSignal(AnnotationCategory)

    # 可配置的工具栏高度变量（默认56px）
    TOOLBAR_HEIGHT = 56

    def __init__(self, project_info: RefProjectInfo, row_height=56):
        super().__init__()
        self.search_edit = None
        self.project_info = project_info
        self.row_height = row_height
        self.setObjectName("YOLOAnnotationList")
        self.right_click_index = None  # 记录右键点击的索引位置

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
        self.setEditTriggers(QAbstractItemView.EditKeyPressed)
        self.setSelectionBehavior(QAbstractItemView.SelectItems)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragOnly)
        self.setDefaultDropAction(Qt.CopyAction)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setAttribute(Qt.WA_AlwaysShowToolTips)

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
            'color': category.color.name()
        }

        mime_data = QMimeData()
        mime_data.setData('application/x-annotation-category', json.dumps(drag_data).encode('utf-8'))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(supportedActions)

    def _handle_item_click(self, clicked_index):
        """处理点击事件 - 保持单选状态"""
        if not clicked_index.isValid():
            return

        if not self.selectionModel().isSelected(clicked_index):
            self.selectionModel().clearSelection()
            self.selectionModel().select(clicked_index, QItemSelectionModel.ClearAndSelect)

    def _handle_selection_change(self, selected, deselected):
        if selected.indexes():
            source_index = self.proxy_model.mapToSource(selected.indexes()[0])
            if 0 <= source_index.row() < len(self.project_info.categories):
                self.annotation_selected.emit(self.project_info.categories[source_index.row()])  # type: ignore

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
            QItemSelectionModel.ClearAndSelect
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

    def _sort_by_name(self):
        """按名称排序类别"""
        if not self.project_info.categories:
            return
        # 按名称升序排序
        self.project_info.categories.sort(key=lambda x: x.class_name)
        # 更新模型
        self.source_model.update_from_categories(self.project_info.categories)
        # 保存排序结果
        self.save_categories()

    def _sort_by_id(self):
        """按ID排序类别"""
        if not self.project_info.categories:
            return
        # 按ID升序排序
        self.project_info.categories.sort(key=lambda x: x.class_id)
        # 更新模型
        self.source_model.update_from_categories(self.project_info.categories)
        # 保存排序结果
        self.save_categories()

    def contextMenuEvent(self, event):
        """重写右键菜单事件"""
        # 获取右键点击位置对应的索引
        index = self.indexAt(event.pos())

        # 如果点击位置有item，则选中它
        if index.isValid():
            self.right_click_index = index
            self.selectionModel().clearSelection()
            self.selectionModel().select(index, QItemSelectionModel.ClearAndSelect)
        else:
            self.right_click_index = None

        # 创建右键菜单
        menu = QMenu(self)

        # 添加菜单项
        add_action = QAction("新增", self)
        add_action.triggered.connect(self._context_add)

        rename_action = QAction("重命名", self)
        rename_action.triggered.connect(self._handle_rename)
        rename_action.setEnabled(index.isValid())  # 只有选中项时可用

        modify_id_action = QAction("修改ID", self)
        modify_id_action.triggered.connect(self._handle_modify_id)
        modify_id_action.setEnabled(index.isValid())  # 只有选中项时可用

        delete_action = QAction("删除", self)
        delete_action.triggered.connect(self._handle_delete)
        delete_action.setEnabled(index.isValid())  # 只有选中项时可用

        # 添加排序相关菜单项
        menu.addSeparator()
        sort_name_action = QAction("按名称排序", self)
        sort_name_action.triggered.connect(self._sort_by_name)
        sort_id_action = QAction("按ID排序", self)
        sort_id_action.triggered.connect(self._sort_by_id)

        menu.addAction(sort_name_action)
        menu.addAction(sort_id_action)

        # 添加到菜单
        menu.insertAction(None, add_action)
        menu.insertSeparator(rename_action)
        menu.insertAction(None, rename_action)
        menu.insertAction(None, modify_id_action)
        menu.insertAction(None, delete_action)

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

    def load_categories_from_json(self):
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
        for i, category in enumerate(self.project_info.categories):
            if category.class_id == class_id:
                proxy_index = self.proxy_model.mapFromSource(self.source_model.index(i, 0))
                self.selectionModel().select(
                    proxy_index,
                    QItemSelectionModel.ClearAndSelect
                )
                self.scrollTo(proxy_index)
                return True
        return False

    def select_category_by_name(self, class_name: str):
        """根据类别名称选中对应的列表项"""
        for i, category in enumerate(self.project_info.categories):
            if category.class_name == class_name:
                proxy_index = self.proxy_model.mapFromSource(self.source_model.index(i, 0))
                self.selectionModel().select(
                    proxy_index,
                    QItemSelectionModel.ClearAndSelect
                )
                self.scrollTo(proxy_index)
                return True
        return False
