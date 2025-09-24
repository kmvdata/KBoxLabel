import json
from pathlib import Path
from typing import Optional

from src.core.ksettings import KSettings
from src.core.yolo_executor import YOLOExecutor
from src.models.annotation_category import AnnotationCategory


class RefProjectInfo:
    """可变容器，用于同步 project_path 的变化，包含YOLO模型配置缓存功能"""

    def __init__(self, path: Optional[Path] = None):
        self.path = path  # 可变属性
        self.yolo_executor = YOLOExecutor()
        self.categories: list[AnnotationCategory] = []

        # 初始化时检查是否有缓存的模型路径并尝试加载
        self._load_cached_yolo_model()

    def set_path(self, new_path: Path):
        old_path = self.path
        self.path = new_path
        # 当路径改变时，重新检查缓存的模型
        if old_path != new_path:
            self._load_cached_yolo_model()

    def exists(self) -> bool:
        if self.path is None:
            return False
        return self.path.exists()

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
        if self.path is None:
            return None
        return f"yolo_model_{str(self.path)}"

    @property
    def is_model_loaded(self):
        return self.yolo_executor.is_model_loaded()

    def load_yolo(self, model_path: Path) -> bool:
        """加载YOLO模型并在成功后缓存路径"""
        try:
            # 尝试加载模型
            self.yolo_executor.load_yolo(model_path)
            # 加载成功，缓存模型路径
            self._save_yolo_model_to_cache(model_path)
            return True
        except Exception as e:
            # 可以根据实际需求修改异常处理方式
            print(f"加载YOLO模型失败: {str(e)}")
            return False

    def exec_yolo(self, img_path: Path):
        results = self.yolo_executor.exec_yolo(img_path)
        # 生成与图片同名的.kolo文件路径
        kolo_path = img_path.with_suffix('.kolo')

        try:
            # 写入检测结果到.kolo文件
            with open(kolo_path, 'w', encoding='utf-8') as f:
                for result in results:
                    # 确保结果是字符串格式（根据实际结果类型调整）
                    line = str(result) if isinstance(result, (list, tuple)) else result
                    f.write(f"{line}\n")

            # 记录成功日志
            print(f"检测结果已成功保存到.kolo文件: {kolo_path}")

        except Exception as e:
            # 记录错误日志并抛出异常
            error_msg = f"保存.kolo文件失败: {str(e)}"
            print(error_msg)
            raise Exception(error_msg)

        return results

    def _load_cached_yolo_model(self):
        """从配置中加载缓存的YOLO模型路径"""
        if self.path is None:
            return

        # 使用自定义的KSettings确保配置一致性
        settings = KSettings()

        # 从配置中获取保存的模型路径
        cached_model_path = settings.value(self._yolo_model_key)
        if cached_model_path:
            model_path = Path(cached_model_path)
            # 检查模型文件是否存在
            if model_path.exists():
                self.load_yolo(model_path)

    def _save_yolo_model_to_cache(self, model_path: Path):
        """将模型路径保存到配置中"""
        if self.path is None:
            return

        # 使用自定义的KSettings确保配置一致性
        settings = KSettings()
        # 使用项目路径作为key

        # 保存模型路径
        settings.setValue(self._yolo_model_key, str(model_path))
        # 确保配置被写入
        settings.sync()

    @property
    def categories_path(self) -> Path:
        if not self.path.exists():
            raise FileNotFoundError(f"项目路径不存在: {self.path}")
        return self.path / '__categories__.json'

    def save_categories(self):
        """
        使用每个 AnnotationCategory 对象的 to_json 方法保存 categories 列表到指定文件。
        按照列表当前显示顺序保存
        """
        data = [cat.to_json() for cat in self.categories]
        self.categories_path.parent.mkdir(parents=True, exist_ok=True)
        with self.categories_path.open('w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

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
