# annotation_list.py
import json
from typing import Tuple

from PyQt5.QtCore import pyqtSignal, Qt, QSize, QRect, QItemSelectionModel, QMimeData, \
    QSortFilterProxyModel
from PyQt5.QtGui import QStandardItemModel, QStandardItem, QPen, QDrag
from PyQt5.QtWidgets import QLineEdit, QSpinBox, QListView, QStyledItemDelegate, QAbstractItemView, \
    QStyle, QToolBar, QWidget, QHBoxLayout, QMenu, QAction

from src.models.dto.annotation_category import AnnotationCategory
from src.models.dto.ref_project_info import RefProjectInfo
from src.models.sql.annotation_category import AnnotationCategory as SQLAnnotationCategory


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

        # 绘制背景（根据选中状态）
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.setPen(option.palette.windowText().color())

        # 计算各区域尺寸
        color_rect = QRect(option.rect.left() + self.MARGIN,
                           option.rect.top() + self.MARGIN,
                           self.row_height - 2 * self.MARGIN,
                           self.row_height - 2 * self.MARGIN)

        name_rect = QRect(color_rect.right() + self.SPACING,
                          option.rect.top(),
                          option.rect.width() - color_rect.width() - self.SPACING - 60 - self.SPACING,
                          option.rect.height())

        id_rect = QRect(name_rect.right() + self.SPACING,
                        option.rect.top(),
                        60,
                        option.rect.height())

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

    def setEditorData(self, editor, index):
        """设置编辑器数据"""
        if isinstance(editor, QLineEdit):
            self.original_name = index.data(Qt.DisplayRole)
            editor.setText(self.original_name)
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
            new_id = editor.value()
            success = model.setData(index, new_id, Qt.UserRole + 1)

        # 重置编辑类型
        self.current_edit_type = None

    def updateEditorGeometry(self, editor, option, index):
        editor.setGeometry(option.rect)


class AnnotationItemModel(QStandardItemModel):
    """优化后的模型类，支持自定义角色数据存储"""
    def __init__(self):
        super().__init__()
        self.setColumnCount(1)

    def add_annotation(self, category: AnnotationCategory):
        """添加标注项"""
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

        # 设置自定义委托和模型
        self.source_model = AnnotationItemModel()
        self.proxy_model = QSortFilterProxyModel(self)
        self.proxy_model.setSourceModel(self.source_model)
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setModel(self.proxy_model)

        # 设置委托
        self.setItemDelegate(EditableAnnotationDelegate(row_height=row_height, parent=self))

        # 设置选择模式
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)  # 禁用默认编辑触发器

        # 启用拖拽
        self.setDragEnabled(True)
        self.setAcceptDrops(False)  # 不接受放置

        # 连接信号
        self.clicked.connect(self._handle_item_click)  # type: ignore
        self.selectionModel().selectionChanged.connect(self._handle_selection_change)  # type: ignore
        self.source_model.dataChanged.connect(self._handle_model_data_changed)  # type: ignore

    def calculate_min_width(self):
        """计算最小宽度以适应所有元素"""
        # 预估最小宽度：颜色方块 + 间距 + 类别名称(预估100px) + 间距 + ID区域(60px) + 边距
        return (self.row_height + 8) * 2 + 100 + 60 + 8

    def create_toolbar(self):
        """创建并返回一个工具栏，包含始终显示的搜索框和添加按钮"""
        toolbar = QToolBar("Annotation Tools")
        toolbar.setToolButtonStyle(Qt.ToolButtonTextUnderIcon)
        toolbar.setIconSize(QSize(24, 24))

        # 设置工具栏样式
        toolbar.setStyleSheet("""
            QToolBar {
                border: none;
                background-color: palette(window);
                spacing: 10px;
            }
            QToolButton {
                border: 1px solid palette(mid);
                border-radius: 4px;
                padding: 4px;
                background: palette(button);
            }
            QToolButton:hover {
                background: palette(light);
            }
        """)

        # 添加按钮
        add_action = QAction("➕", self)
        add_action.setToolTip("添加新类别")
        add_action.triggered.connect(self._handle_add)  # type: ignore
        toolbar.addAction(add_action)

        # 添加弹性空间
        toolbar.addWidget(QWidget())

        # 搜索框
        from PyQt5.QtWidgets import QLineEdit
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("搜索类别...")
        self._configure_search_edit()
        toolbar.addWidget(self.search_edit)

        # 连接搜索信号
        self.search_edit.textChanged.connect(self._handle_search_text_changed)  # type: ignore

        return toolbar

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

    def load_categories_from_db(self):
        """
        从数据库加载类别，与现有类别合并（仅当 class_id 和 class_name 都相同时视为重复）。
        重复项将重新生成颜色，最终列表按 class_id 排序。
        """
        if not self.project_info.sqlite_db:
            return

        try:
            # 从数据库获取所有类别
            session = self.project_info.sqlite_db.db_session()
            try:
                db_categories = session.query(SQLAnnotationCategory).all()
                
                # 转换为DTO对象
                new_categories = []
                for db_cat in db_categories:
                    # 创建DTO对象
                    category = AnnotationCategory(
                        class_id=db_cat.class_id,
                        class_name=db_cat.class_name
                    )
                    # 设置颜色
                    from PyQt5.QtGui import QColor
                    category.color = QColor(db_cat.color_r, db_cat.color_g, db_cat.color_b)
                    new_categories.append(category)
            finally:
                session.close()
                
        except Exception as e:
            raise IOError(f"无法从数据库读取类别: {e}")

        self._merge_and_update_categories(new_categories)

    def load_categories_from_yolo_model(self, model_path):
        """
        从YOLO模型文件(.pt)加载类别信息，并与现有类别合并。
        """
        try:
            from ultralytics import YOLO
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
