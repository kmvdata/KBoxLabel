from pathlib import Path
from typing import Optional, List

from src.common.domain.project_domain import ProjectDomain
from src.core.yolo_executor import YOLOExecutor
from src.models.dto.annotation_category import AnnotationCategory
from src.common.domain.models.kolo_item import KoloItem


class ProjectInfo:
    """可变容器，用于同步 project_path 的变化，包含YOLO模型配置缓存功能"""

    def __init__(self, path: Path|str):
        self.path: Path = Path(path)  # 可变属性
        self.yolo_executor = YOLOExecutor(self)  # 将自身作为parent传递给YOLOExecutor
        self.categories: list[AnnotationCategory] = []

        # 初始化数据库
        self.domain: ProjectDomain = ProjectDomain(self._db_path)

    def exists(self) -> bool:
        if self.path is None:
            return False
        return self.path.exists()

    @property
    def _db_path(self):
        if self._config_dir is None:
            return None
        return self._config_dir / 'data.db'

    @property
    def _config_dir(self):
        if self.path is None:
            return None
        # 如果存在同名的.kboxlabel文件夹，则使用它，如果不存在，则创建，然后返回路径
        _config_dir = self.path / '.kboxlabel'

        # 检查目录是否存在，如果不存在则创建
        if not _config_dir.exists():
            _config_dir.mkdir(parents=True, exist_ok=True)

        return _config_dir

    @property
    def project_name(self) -> str:
        if self.path is None:
            return ''
        return self.path.name

    @property
    def model_name(self) -> str:
        if not self.yolo_executor.is_model_loaded:
            return ''
        return self.yolo_executor.model_name

    @property
    def _yolo_model_key(self):
        return f"yolo_model_path"

    @property
    def is_model_loaded(self):
        return self.yolo_executor.is_model_loaded()

    def model_path_in_db(self) -> Optional[Path]:
        return self.domain.model_path_in_db()

    def load_yolo_model(self, model_path: Optional[Path] = None):
        """加载YOLO模型并在成功后缓存路径"""
        # 如果没有提供model_path，则从数据库获取
        if model_path is None:
            model_path = self.model_path_in_db()

        if model_path is None:
            return False

        # 尝试加载模型
        self.yolo_executor.load_yolo(model_path)
        is_loaded = self.yolo_executor.is_model_loaded()

        if is_loaded:
            # 加载成功，保存路径到数据库
            self.domain.save_model_path(model_path)
        else:
            # 加载失败，清空数据库中的模型路径
            self.domain.delete_model_path()
            
        return None

    def delete_yolo_model(self):
        """删除YOLO模型并清空数据库中的模型路径"""
        # 创建数据库会话
        self.yolo_executor.clear_model()
        self.domain.delete_model_path()

    def exec_yolo(self, img_path: Path, save_to_db: bool = False)-> list[KoloItem]:
        return self.yolo_executor.exec_yolo(img_path, save_to_db)


    def save_categories(self):
        """
        将当前的 categories 列表保存到数据库中
        """
        self.domain.save_categories(self.categories)

    def load_categories(self) -> List[AnnotationCategory]:
        """
        从数据库加载类别列表
        """
        self.categories = self.domain.load_categories()
        return self.categories


    def find_annotation_by_name(self, name: str) -> Optional[AnnotationCategory]:
        """根据类别名称查找标注类别"""
        for category in self.categories:
            if category.class_name == name:
                return category
        return None  # 未找到时返回None

    def find_annotation_by_id(self, class_id: int) -> Optional[AnnotationCategory]:
        """根据类别ID查找标注类别"""
        # 注意：原方法定义的参数名有误，已更正为class_id（原参数名name不合理）
        for category in self.categories:
            if category.class_id == class_id:
                return category
        return None  # 未找到时返回None

