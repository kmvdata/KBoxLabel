# annotation_list_model.py

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
        self._category_items = {}  # class_name -> QStandardItem 映射
        self.domain = project_info.domain

    def refresh_model(self):
        """加载项目中的所有类别到列表中"""
        # 清空现有模型数据
        self.clear_annotations()

        # 从project_info获取类别并添加到模型
        for category in self.domain.categories:
            item = AnnotationItem(category)
            self.appendRow(item)
            self._category_items[category.class_name] = item

    def append_annotation(self, category: AnnotationCategoryDTO):
        """添加带序号的标注项"""
        self.domain.append(category)
        item = AnnotationItem(category)
        self.appendRow(item)
        self._category_items[category.class_name] = item

    def insert_annotation(self, row: int, category: AnnotationCategoryDTO):
        """在指定位置插入标注项"""
        item = AnnotationItem(category)
        self.insertRow(row, item)
        self._category_items[category.class_name] = item

    def clear_annotations(self):
        """清除所有标注"""
        self.clear()
        self.setColumnCount(1)
        self._category_items.clear()

    def get_item_by_class_name(self, class_name: str) -> AnnotationItem:
        """根据class_id获取对应的item"""
        return self._category_items.get(class_name)

    def get_class_name_by_row(self, row: int) -> int:
        """根据行号获取class_name"""
        index = self.index(row, 0)
        return self.data(index, Qt.UserRole + 2)

    def set_color(self, index: QModelIndex, color: QColor):
        self.setData(index, color, Qt.UserRole)