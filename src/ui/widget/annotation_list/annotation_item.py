# annotation_item.py
import hashlib

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QStandardItem, QColor

from src.common.domain import AnnotationCategory


class AnnotationItem(QStandardItem):
    """自定义项，存储带序号的标注类别数据"""
    def __init__(self, class_name: str, class_id: int, parent_name: str = None):
        super().__init__(class_name)
        self.set_category(class_name, class_id, parent_name)
        # 保存指向模型的引用，以便获取准确的行号
        self._model = None

        # 默认没有order赋值，仅作为排序辅助值使用
        self.order = 0

    def set_category(self, class_name: str, class_id: int, parent_name: str = None):
        self.setData(self._generate_color_from_class_name(class_name), Qt.UserRole)
        self.setData(class_id, Qt.UserRole + 1)
        self.setData(class_name, Qt.UserRole + 2)  # 存储class_name
        self.setData(parent_name, Qt.UserRole + 3)  # 存储父class_name
        self.setEditable(True)


    @property
    def class_id(self) -> int:
        return self.data(Qt.UserRole + 1)

    @class_id.setter
    def class_id(self, class_id: int):
        self.setData(class_id, Qt.UserRole + 1)

    @property
    def class_name(self) -> str:
        return self.data(Qt.UserRole + 2)

    @class_name.setter
    def class_name(self, class_name: str):
        self.setData(class_name, Qt.UserRole + 2)

    @property
    def parent_name(self) -> str:
        return self.data(Qt.UserRole + 3)

    @parent_name.setter  # 这里要使用@property装饰的属性名来关联setter
    def parent_name(self, parent_name: str):  # 补充参数类型注解
        self.setData(parent_name, Qt.UserRole + 3)

    @property
    def order(self) -> int:
        return self.data(Qt.UserRole + 4)

    @order.setter
    def order(self, order: int):
        self.setData(order, Qt.UserRole + 4)

    @property
    def class_color(self) -> QColor:
        return self.data(Qt.UserRole)

    def set_model(self, model):
        """设置模型引用"""
        self._model = model
        
    def actual_row(self):
        """获取item在模型中的实际行号"""
        if self._model is not None:
            # 通过模型查找该item的实际行号
            items = self._model.items
            try:
                return items.index(self)
            except ValueError:
                # 如果item不在模型列表中，返回-1
                return -1
        else:
            # 如果没有设置模型引用，回退到默认行为
            return self.row()

    @staticmethod
    def gen_sql_annotation_category(class_name: str, class_id: int, parent_name: str = None) -> AnnotationCategory:
        category = AnnotationCategory()
        category.class_id = class_id
        category.class_name = class_name
        category.parent_name = parent_name
        return category

    @property
    def annotation_category(self) -> AnnotationCategory:
        return self.gen_sql_annotation_category(self.class_name, self.class_id, self.parent_name)

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