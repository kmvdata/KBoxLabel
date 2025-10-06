import hashlib

from PyQt5.QtGui import QColor


class AnnotationCategory:
    """存储标注类别的数据结构"""
    class_id: int
    class_name: str
    color: QColor

    def __init__(self, class_id: int, class_name: str):
        self.class_id = class_id
        self.class_name = class_name
        self.color = self.gen_color()

    @staticmethod
    def merge_and_regenerate_color(cat1, cat2):
        """
        如果两个AnnotationCategory对象的class_id和class_name相同，则合并它们并重新生成颜色。
        返回合并后的对象。
        """
        if cat1.class_id == cat2.class_id and cat1.class_name == cat2.class_name:
            merged_cat = AnnotationCategory(class_id=cat1.class_id, class_name=cat1.class_name)
            merged_cat.color = merged_cat.gen_color()  # 使用新的颜色生成方法
            return merged_cat
        return None

    def gen_color(self) -> QColor:
        return self._generate_color_from_md5()

    def _generate_color_from_id(self):
        """根据类别ID生成稳定颜色"""
        # 使用类别ID生成颜色，确保同一类别总是相同颜色
        hue = (self.class_id * 137) % 360  # 使用黄金角确保颜色分布均匀
        return QColor.fromHsv(hue, 180, 230)  # 高饱和度，中等亮度

    def _generate_color_from_md5(self):
        """根据类别名称生成稳定颜色（使用MD5后6位），避免接近白色"""
        # 1. 计算class_name的MD5哈希
        md5_hash = hashlib.md5(self.class_name.encode()).hexdigest()

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

    def to_json(self) -> dict:
        """
        将当前对象转换为 JSON 兼容的字典。
        """
        return {
            "class_id": self.class_id,
            "class_name": self.class_name,
            "color": {"r": self.color.red(), "g": self.color.green(), "b": self.color.blue()}
        }

    @classmethod
    def from_json(cls, data: dict):
        """
        从 JSON 兼容的字典创建 AnnotationCategory 实例。
        """
        category = cls(class_id=data["class_id"], class_name=data["class_name"])
        if "color" in data and isinstance(data["color"], dict):
            color_data = data["color"]
            category.color = QColor(color_data.get_by_id("r", 0), color_data.get_by_id("g", 0), color_data.get_by_id("b", 0))
        return category

    def key(self) -> (int, str):
        """返回唯一标识该类别的键"""
        return self.class_id, self.class_name

    def __hash__(self):
        return hash(self.key())

    def __eq__(self, other):
        if not isinstance(other, AnnotationCategory):
            return False
        return self.key() == other.key()