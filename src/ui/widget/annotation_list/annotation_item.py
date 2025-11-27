# annotation_item.py
import hashlib

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QColor
from ultralytics import YOLO
from ultralytics import YOLO

from src.common.domain import AnnotationCategory


class AnnotationItem(QStandardItem):
    """自定义项，存储带序号的标注类别数据"""
    def __init__(self, category: AnnotationCategory):
        super().__init__(category.class_name)
        self.set_category(category)

    def set_category(self, category: AnnotationCategory):
        self.setData(self._generate_color_from_class_name(category.class_name), Qt.UserRole)
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

    @staticmethod
    def _generate_color_from_class_id(class_id: int):
        """根据类别ID生成稳定颜色"""
        # 使用类别ID生成颜色，确保同一类别总是相同颜色
        hue = (class_id * 137) % 360  # 使用黄金角确保颜色分布均匀
        return QColor.fromHsv(hue, 180, 230)  # 高饱和度，中等亮度

    @staticmethod
    def _generate_color_from_class_name(class_name: str):
        """根据类别名称生成稳定颜色（使用MD5后6位），避免接近白色"""
        # 1. 计算class_name的MD5哈希
        md5_hash = hashlib.md5(class_name.encode()).hexdigest()

        # 2. 取MD5哈希值的后6位作为颜色代码
        color_hex = md5_hash[-6:]

        # 3. 转换为RGB值
        r = int(color_hex[0:2], 16)
        g = int(color_hex[2:4], 16)
        b = int(color_hex[4:6], 16)

        # 4. 关键优化：避免接近白色
        # 计算当前颜色与白色的欧氏距离
        white_distance = ((255 - r) ** 2 + (255 - g) ** 2 + (255 - b) ** 2) ** 0.5

        # 如果太接近白色（距离<50），应用色相偏移
        if white_distance < 50:
            # 将RGB转换为HSV
            color = QColor(r, g, b)
            h = color.hue()
            s = color.saturation()
            v = color.value()

            # 增加饱和度并降低亮度
            s = min(255, s + 40)  # 提高饱和度
            v = max(60, v - 80)  # 显著降低亮度

            # 转换回RGB
            color = QColor.fromHsv(h, s, v)
            r, g, b, _ = color.getRgb()

        # 5. 确保安全范围（防止过暗或过亮）
        r = max(60, min(r, 220))
        g = max(60, min(g, 220))
        b = max(60, min(b, 220))

        return QColor(r, g, b)



