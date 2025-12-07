# annotation_list_model.py
import time
from enum import Enum
from typing import Optional, List, Any

from PyQt5.QtCore import Qt, QModelIndex, QAbstractListModel, QVariant
from ultralytics import YOLO

from src.common.domain import AnnotationCategory
from src.core.project_info import ProjectInfo
from src.ui.widget.annotation_list.annotation_item import AnnotationItem


class AnnotationDropArea(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"


class AnnotationListModel(QAbstractListModel):
    """自定义模型，存储带序号的标注类别数据"""

    def __init__(self, project_info: ProjectInfo, parent=None):
        super().__init__(parent)
        self.domain = project_info.domain
        self.items: List[AnnotationItem] = []

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        """返回模型中的项目数量"""
        if parent.isValid():
            return 0
        return len(self.items)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        """返回指定索引和角色的数据"""
        if not index.isValid() or index.row() >= len(self.items):
            return QVariant()

        item = self.items[index.row()]

        if role == Qt.DisplayRole:
            return item.class_name
        elif role == Qt.UserRole:
            return item.class_color
        elif role == Qt.UserRole + 1:
            return item.class_id
        elif role == Qt.UserRole + 2:
            return item.class_name
        elif role == Qt.UserRole + 3:
            return item.parent_name

        return QVariant()

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        """设置指定索引和角色的数据"""
        if not index.isValid() or index.row() >= len(self.items):
            return False

        item = self.items[index.row()]
        if role == Qt.DisplayRole:
            item.class_name = value
        elif role == Qt.UserRole + 1:
            item.class_id = value
        elif role == Qt.UserRole + 3:
            item.parent_name = value
        else:
            return False

        self.dataChanged.emit(index, index, [role])
        return True

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        """返回项目的标志"""
        if not index.isValid():
            return  Qt.ItemFlags(Qt.ItemFlag.ItemIsEnabled)

        return Qt.ItemFlags(super().flags(index) | Qt.ItemFlag.ItemIsEditable | Qt.ItemFlag.ItemIsDragEnabled | Qt.ItemFlag.ItemIsDropEnabled)


    def item_from_index(self, index: QModelIndex) -> Optional[AnnotationItem]:
        """根据索引返回对应的AnnotationItem"""
        if not index.isValid() or index.row() < 0 or index.row() >= len(self.items):
            return None
        return self.items[index.row()]

    def refresh_model(self):
        """加载项目中的所有类别到列表中"""
        self.beginResetModel()
        # 清空现有模型数据
        self.items.clear()
        # 重新从数据库中加载AnnotationItem
        categories = self.domain.query_all_categories()
        # 根据categories内容创建AnnotationItem
        for category in categories:
            item = AnnotationItem(category.class_name, category.class_id, category.parent_name)
            self.items.append(item)
        self.endResetModel()

    def save_categories(self):
        """保存类别列表到数据库"""
        # 按顺序遍历所有的annotation_item，由items生成对应的annotation_category orm对象
        # 然后按照当前顺序，给这些对象的order赋值，从1000开始，每个平级的item的order间隔为1000
        # 如果是二级item，则间隔为1，同一个父item下的二级item，第一个二级item以其父item.order+1起始，依次类推。
        # 最后，调用数据库方法resave_all_categories，保存生成的annotation_category。

        # 收集所有item并构建类别列表
        categories: list[AnnotationCategory] = []
        last_order = 1000
        parent_orders = {}  # 记录每个父类别的order值

        for item in self.items:
            sql_category = AnnotationCategory()
            sql_category.class_id = item.class_id
            sql_category.class_name = item.class_name
            color = item.class_color
            sql_category.color_r = color.red()
            sql_category.color_g = color.green()
            sql_category.color_b = color.blue()
            sql_category.parent_name = item.parent_name

            if item.parent_name is None:
                # 顶级类别，order间隔为1000
                sql_category.order = (self.items.index(item) + 1) * 1000
                parent_orders[item.class_name] = sql_category.order
            else:
                # 子类别，需要找到父类别的order值
                if item.parent_name in parent_orders:
                    # 父类别已处理，基于父类别的order继续编号
                    sql_category.order = parent_orders[item.parent_name] + len(
                        [c for c in categories if c.parent_name == item.parent_name]) + 1
                else:
                    # 父类别尚未处理（理论上不应该发生），使用默认方案
                    sql_category.order = last_order + 1

            last_order = sql_category.order
            categories.append(sql_category)

        # 保存到数据库
        self.domain.resave_all_categories(categories)

    def get_item_by_class_name(self, class_name: str) -> Optional[AnnotationItem]:
        """根据class_name获取对应的item"""
        for item in self.items:
            if item.class_name == class_name:
                return item
        return None

    def get_category_name_by_index(self, index: QModelIndex) -> Optional[str]:
        """根据索引获取对应的类别名称"""
        if not index.isValid() or index.row() >= len(self.items):
            return None

        return self.items[index.row()].class_name

    def delete_category_by_index(self, index: QModelIndex):
        """删除指定索引的类别"""
        if not index.isValid() or index.row() >= len(self.items):
            return

        # 找出index对应的category名称
        category_name = self.get_category_name_by_index(index)
        self.domain.delete_category(category_name)
        self.refresh_model()

    def count_kilo_items_for_category(self, category_name: str):
        return self.domain.count_kilo_items_for_category(category_name)

    def append_new_category(self, class_name: Optional[str] = None, class_id: Optional[int] = None) -> AnnotationItem:
        """创建新的类别"""
        # 调用create_new_category_at_index实现，需要获取列表最后的index作为参数传入
        return self.create_new_category_at_index(self.index(len(self.items) - 1, 0), class_name, class_id)

    def create_new_category_at_index(self,
                                     index: QModelIndex,
                                     class_name: Optional[str] = None,
                                     class_id: Optional[int] = None) -> AnnotationItem:
        """在指定索引位置创建新的类别"""
        # 如果已存在，则直接返回
        if class_name:
            exist_item = self.get_item_by_class_name(class_name)
            if exist_item:
                return exist_item

        # 使用domain方法获取最大ID
        if class_id is None:
            class_id = self.domain.get_max_category_id() + 1

        if class_name is None:
            class_name = f"新类别 {class_id}"

        # 如果class_name已存在，则生成新的class_name
        while self.get_item_by_class_name(class_name):
            class_id += 1
            class_name = f"新类别 {class_id}"

        # 创建AnnotationItem实例
        new_item = AnnotationItem(
            class_name=class_name,
            class_id=class_id
        )

        # 插入AnnotationItem到模型指定位置
        insert_row = index.row() + 1 if index.isValid() else 0
        self.beginInsertRows(QModelIndex(), insert_row, insert_row)
        self.items.insert(insert_row, new_item)
        self.endInsertRows()

        self.save_categories()
        return new_item

    def move_category(self, dragged_category_name: str, target_category_name: str, drop_area: AnnotationDropArea):
        """
        移动类别到目标类别

        Args:
            dragged_category_name (str): 被拖拽的类别名称
            target_category_name (str): 目标类别名称
            drop_area (AnnotationDropArea): 放置区域 (TOP, CENTER, BOTTOM)
        """
        if drop_area == AnnotationDropArea.CENTER:
            # 将dragged_category_name作为target_category_name的子类别
            self.move_category_as_children(target_category_name, dragged_category_name)
        elif drop_area == AnnotationDropArea.TOP:
            # 将dragged_category_name移动到target_category_name之前
            self.move_category_by_name_before(dragged_category_name, target_category_name)
        elif drop_area == AnnotationDropArea.BOTTOM:
            # 将dragged_category_name移动到target_category_name之后
            self.move_category_by_name_after(dragged_category_name, target_category_name)

        self.refresh_model()

    def move_category_as_children(self, parent_category_name: str, child_category_name: str,
                                  before_category_name: Optional[str] = None):
        """
        将一个类别移动为另一个类别的子类别，并可选择性地调整其在子类别列表中的位置。
        """
        # 检查是否试图将类别设置为自己的子类别
        if parent_category_name == child_category_name:
            raise ValueError("不能将类别设置为自己的子类别")

        # 查找父类别和子类别
        parent_item = self.get_item_by_class_name(parent_category_name)
        child_item = self.get_item_by_class_name(child_category_name)

        # 检查类别是否存在
        if not parent_item:
            raise ValueError(f"父类别 '{parent_category_name}' 不存在")
        if not child_item:
            raise ValueError(f"子类别 '{child_category_name}' 不存在")

        # 更新子类别 parent_name
        child_index = self.index(self.items.index(child_item))
        child_item.parent_name = parent_category_name
        self.dataChanged.emit(child_index, child_index, [Qt.UserRole + 3])

        # 如果指定了要放在某个子类别之前
        if before_category_name:
            before_item = self.get_item_by_class_name(before_category_name)
            if before_item and before_item.parent_name == parent_category_name:
                # 先移除再插入到指定位置
                self._move_item(child_item, self.items.index(before_item))

        self.save_categories()

    def move_category_by_name_before(self, dragged_name: str, target_name: str):
        """将拖拽的类别移动到目标类别之前"""
        dragged_item = self.get_item_by_class_name(dragged_name)
        target_item = self.get_item_by_class_name(target_name)

        if dragged_item and target_item and dragged_item != target_item:
            # 确保移动后成为顶级类别
            if dragged_item.parent_name is not None:
                dragged_index = self.index(self.items.index(dragged_item))
                dragged_item.parent_name = None
                self.dataChanged.emit(dragged_index, dragged_index, [Qt.UserRole + 3])

            self._move_item(dragged_item, self.items.index(target_item))
            self.save_categories()

    def move_category_by_name_after(self, dragged_name: str, target_name: str):
        """将拖拽的类别移动到目标类别之后"""
        dragged_item = self.get_item_by_class_name(dragged_name)
        target_item = self.get_item_by_class_name(target_name)

        if dragged_item and target_item and dragged_item != target_item:
            # 确保移动后成为顶级类别
            if dragged_item.parent_name is not None:
                dragged_index = self.index(self.items.index(dragged_item))
                dragged_item.parent_name = None
                self.dataChanged.emit(dragged_index, dragged_index, [Qt.UserRole + 3])

            target_index = self.items.index(target_item)
            self._move_item(dragged_item, target_index + 1)
            self.save_categories()

    def _move_item(self, item: AnnotationItem, new_position: int):
        """将项目移动到新位置"""
        old_position = self.items.index(item)
        if old_position == new_position:
            return

        # 调整新位置以适应列表边界
        new_position = max(0, min(new_position, len(self.items) - 1))

        # 开始移动操作
        self.beginMoveRows(QModelIndex(), old_position, old_position, QModelIndex(), new_position)
        # 从列表中移除并插入到新位置
        self.items.insert(new_position, self.items.pop(old_position))
        self.endMoveRows()
