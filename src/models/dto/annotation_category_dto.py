import hashlib
from typing import Optional

from PyQt5.QtGui import QColor


class AnnotationCategoryDTO:
    """存储标注类别的数据结构"""

    def __init__(self, class_id: int, class_name: str, parent_name: Optional[str] = None):
        pass
