# annotation_list_model.py
from enum import Enum
from typing import Optional

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QColor
from PyQt5.QtGui import QStandardItemModel
from ultralytics import YOLO
from ultralytics import YOLO

from src.common.domain import AnnotationCategory
from src.core.project_info import ProjectInfo
from src.ui.widget.annotation_list.annotation_item import AnnotationItem


class AnnotationDropArea(Enum):
    TOP = "top"
    CENTER = "center"
    BOTTOM = "bottom"

class AnnotationListModel(QStandardItemModel):
    """自定义模型，存储带序号的标注类别数据"""

    def __init__(self, project_info: ProjectInfo, parent=None):
        super().__init__(0, 1, parent)
        self.domain = project_info.domain

    def refresh_model(self):
        """加载项目中的所有类别到列表中"""
        # 清空现有模型数据
        self.clear_annotations()

        self.load_categories()

    def insert_annotation_item(self, row: int, class_name: str, class_id: int, parent_name: str = None):
        """在指定位置插入标注项"""
        # 检查是否已存在相同class_name的项
        existing_item = self.get_item_by_class_name(class_name)
        # 已存在就直接返回
        if existing_item:
            return existing_item
        # 不存在就执行插入
        item = AnnotationItem(class_name, class_id, parent_name)
        self.insertRow(row, item)
        return item

    def clear_annotations(self):
        """清除所有标注"""
        self.clear()
        self.setColumnCount(1)

    def get_item_by_class_name(self, class_name: str) -> Optional[AnnotationItem]:
        """根据class_name获取对应的item"""
        # 遍历模型中的所有行，查找匹配的class_name
        for row in range(self.rowCount()):
            item = self.item(row)
            if isinstance(item, AnnotationItem):
                stored_class_name = item.data(Qt.UserRole + 2)
                if stored_class_name == class_name:
                    return item
        return None

    def get_category_name_by_index(self, index: QModelIndex) -> Optional[str]:
        """根据索引获取对应的类别名称"""
        if not index.isValid():
            return None
            
        # 从模型中获取item
        item = self.itemFromIndex(index)
        if item is not None:
            # 返回类别名称（存储在UserRole+2中）
            return item.data(Qt.UserRole + 2)
        return None

    def set_color(self, index: QModelIndex, color: QColor):
        self.setData(index, color, Qt.UserRole)

    def delete_category(self, category_name: str):
        """删除指定名称的类别"""
        self.domain.delete_category(category_name)
        self.refresh_model()

    def delete_category_by_index(self, index: QModelIndex):
        """删除指定索引的类别"""
        # 找出index对应的category名称
        category_name = self.get_category_name_by_index(index)
        self.domain.delete_category(category_name)
        self.refresh_model()

    def count_kilo_items_for_category(self, category_name: str):
        return self.domain.count_kilo_items_for_category(category_name)

    def append_new_category(self, class_name: Optional[str]=None, class_id: Optional[int]= None) -> AnnotationItem:
        """创建新的类别"""
        # 调用create_new_category_at_index实现，需要获取列表最后的index作为参数传入
        return self.create_new_category_at_index(self.index(self.rowCount() - 1, 0), class_name, class_id)

    def create_new_category_at_index(self,
                                     index: QModelIndex,
                                     class_name:Optional[str]=None,
                                     class_id: Optional[int]= None) -> AnnotationItem:
        """在指定索引位置创建新的类别"""
        # 如果已存在，则直接返回
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

        # 1. 创建AnnotationItem实例（根据AnnotationItem的构造参数调整）
        # 若AnnotationItem需要parent_name，可从index关联的父项获取，示例中默认None
        new_item = AnnotationItem(
            class_name=class_name,
            class_id=class_id
        )

        # 2. 插入AnnotationItem到模型指定位置（处理父索引，适配树形/列表结构）
        # parent_index = index.parent()  # 获取父节点索引（树形结构）
        insert_row = index.row()  # 插入位置的行号

        # 模型插入行并设置Item（QStandardItemModel的标准操作）
        self.insertRow(insert_row, new_item)
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
            self.domain.move_category_as_children(target_category_name, dragged_category_name)
        elif drop_area == AnnotationDropArea.TOP:
            # 将dragged_category_name移动到target_category_name之前
            self.domain.move_category_by_name_before(dragged_category_name, target_category_name)
        elif drop_area == AnnotationDropArea.BOTTOM:
            # 将dragged_category_name移动到target_category_name之后
            self.domain.move_category_by_name_after(dragged_category_name, target_category_name)
        
        # 重新刷新模型以反映更改
        self.refresh_model()

    def save_categories(self):
        """保存类别列表到数据库"""
        # 按顺序遍历所有的annotation_item，由items生成对应的annotation_category orm对象（class AnnotationCategory(KOrmBase)），
        # 然后按照当前顺序，给这些对象的order赋值，从1000开始，每个平级的item的order间隔为1000，如果是二级item，则间隔为1，同一个父item下的二级item，第一个二级item以其父item.order+1起始，依次类推。
        # 最后，调用数据库方法resave_all_categories，保存生成的annotation_category。

        # 收集所有item并构建类别列表
        categories: list[AnnotationCategory] = []
        last_order = 1000
        for row in range(self.rowCount()):
            item = self.item(row)
            if isinstance(item, AnnotationItem):
                sql_category = AnnotationCategory()
                sql_category.class_id = item.class_id
                sql_category.class_name = item.class_name
                color = item.class_color
                sql_category.color_r = color.red()
                sql_category.color_g = color.green()
                sql_category.color_b = color.blue()
                sql_category.parent_name = item.parent_name
                if item.parent_name is None:
                    sql_category.order = (row+1) * 1000
                else:
                    sql_category.order = last_order + 1

                last_order = sql_category.order
                categories.append(sql_category)
        
        # 保存到数据库
        self.domain.resave_all_categories(categories)

    def load_categories(self):
        categories = self.domain.query_all_categories()
        # 根据categories内容创建AnnotationItem
        for category in categories:
            item = AnnotationItem(category.class_name, category.class_id, category.parent_name)
            self.appendRow(item)
