# annotation_item.py

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QColor
from ultralytics import YOLO
from ultralytics import YOLO

from src.models.dto.annotation_category_dto import AnnotationCategoryDTO


class AnnotationItem(QStandardItem):
    """自定义项，存储带序号的标注类别数据"""
    def __init__(self, category: AnnotationCategoryDTO):
        super().__init__(category.class_name)
        self.set_category(category)

    def set_category(self, category: AnnotationCategoryDTO):
        self.setData(category.color, Qt.UserRole)
        self.setData(category.class_id, Qt.UserRole + 1)
        self.setData(category.class_name, Qt.UserRole + 2)  # 存储class_name
        self.setData(category.parent_name, Qt.UserRole + 3)  # 存储父class_name
        self.setEditable(True)

    def set_parent_name(self, parent_name):
        self.setData(parent_name, Qt.UserRole + 3)

    def get_class_id(self) -> int:
        return self.data(Qt.UserRole + 1)

    def get_class_name(self) -> str:
        return self.data(Qt.UserRole + 2)

    def get_parent_name(self) -> str:
        return self.data(Qt.UserRole + 3)

    def get_color(self) -> QColor:
        return self.data(Qt.UserRole)


