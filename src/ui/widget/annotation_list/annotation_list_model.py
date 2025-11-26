# annotation_list_model.py
from typing import Optional

from PyQt5.QtCore import Qt, QModelIndex
from PyQt5.QtGui import QStandardItemModel, QColor
from ultralytics import YOLO
from ultralytics import YOLO

from src.core.project_info import ProjectInfo
from src.models.dto.annotation_category_dto import AnnotationCategoryDTO
from src.ui.widget.annotation_list.annotation_item import AnnotationItem


class AnnotationListModel(QStandardItemModel):
    """自定义模型，存储带序号的标注类别数据"""

    def __init__(self, project_info: ProjectInfo, parent=None):
        super().__init__(0, 1, parent)
        self.domain = project_info.domain

    def refresh_model(self):
        """加载项目中的所有类别到列表中"""
        # 清空现有模型数据
        self.clear_annotations()

        # 先确保domain中的categories已按order排序
        sorted_categories = sorted(self.domain.categories, key=lambda cat: cat.order)
        
        for category in sorted_categories:
            item = AnnotationItem(category)
            self.appendRow(item)

    def append_annotation(self, category: AnnotationCategoryDTO):
        """添加带序号的标注项"""
        # 检查是否已存在相同class_name的项
        existing_item = self.get_item_by_class_name(category.class_name)
        if existing_item is None:
            # 不存在则添加
            self.domain.append(category)
            item = AnnotationItem(category)
            self.appendRow(item)
        else:
            # 已存在则更新
            existing_item.set_category(category)

    def insert_annotation(self, row: int, category: AnnotationCategoryDTO):
        """在指定位置插入标注项"""
        # 检查是否已存在相同class_name的项
        existing_item = self.get_item_by_class_name(category.class_name)
        if existing_item is None:
            # 不存在则插入
            self.domain.insert_category(row, category)
            item = AnnotationItem(category)
            self.insertRow(row, item)
        else:
            # 已存在则更新
            existing_item.set_category(category)

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

    def create_new_category_at_index(self, index: QModelIndex, default_name=None):
        """在指定索引位置创建新的类别"""
        # 使用domain方法获取最大ID
        max_id = self.domain.get_max_category_id()
        new_id = max_id + 1

        if default_name is None:
            new_name = f"新类别 {new_id}"
        else:
            new_name = default_name

        new_category = AnnotationCategoryDTO(
            class_id=new_id,
            class_name=new_name
        )

        # 插入新的类别
        self.insert_annotation(index.row(), new_category)
        
        self.domain.refresh_order_entire_list()
        
        return new_category
