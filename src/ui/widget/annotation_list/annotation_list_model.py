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

        for category in self.domain.categories:
            item = AnnotationItem(category)
            self.appendRow(item)

    def append_annotation(self, category: AnnotationCategoryDTO):
        """添加带序号的标注项"""
        self.domain.append(category)
        item = AnnotationItem(category)
        self.appendRow(item)

    def insert_annotation(self, row: int, category: AnnotationCategoryDTO):
        """在指定位置插入标注项"""
        self.domain.insert_category(row, category)
        item = AnnotationItem(category)
        self.insertRow(row, item)

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

    def set_color(self, index: QModelIndex, color: QColor):
        self.setData(index, color, Qt.UserRole)
