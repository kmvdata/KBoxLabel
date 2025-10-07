import json
from pathlib import Path
from typing import Optional
from PyQt5.QtCore import QThread, pyqtSignal

from src.common.god.sqlite_db import SqliteDB
from src.core.ksettings import KSettings
from src.core.yolo_executor import YOLOExecutor
from src.models.dto.annotation_category import AnnotationCategory


class ModelLoadThread(QThread):
    """用于在后台线程中加载模型的线程类"""
    # 定义信号，用于在加载完成时通知主线程
    model_loaded = pyqtSignal(bool, str)  # (success, error_message)
    
    def __init__(self, yolo_executor: YOLOExecutor, model_path: Path):
        super().__init__()
        self.yolo_executor = yolo_executor
        self.model_path = model_path
        self._success = False
        self._error_message = ""
    
    def run(self):
        """在后台线程中执行模型加载"""
        try:
            # 尝试加载模型
            self.yolo_executor.load_yolo(self.model_path)
            self._success = True
            self._error_message = ""
        except Exception as e:
            # 捕获加载异常
            self._success = False
            self._error_message = str(e)
        finally:
            # 发出信号通知主线程加载完成
            self.model_loaded.emit(self._success, self._error_message)


class RefProjectInfo:
    """可变容器，用于同步 project_path 的变化，包含YOLO模型配置缓存功能"""

    def __init__(self, path: Optional[Path] = None):
        self.path = path  # 可变属性
        self.yolo_executor = YOLOExecutor()
        self.yolo_model_path: Optional[str] = None  # 添加模型路径属性
        self.categories: list[AnnotationCategory] = []
        self.sqlite_db: Optional[SqliteDB] = None
        self._model_loading = False  # 标记是否正在加载模型

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
        if not self.yolo_executor.is_model_loaded():
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

    @property
    def is_model_loading(self):
        """返回模型是否正在加载中"""
        return self._model_loading

    @property
    def sqlite_path(self) -> Optional[Path]:
        if self.path is None:
            return None
        return self.path / '__sql_config__.sql'

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

    def load_yolo_async(self, model_path: Path):
        """异步加载YOLO模型"""
        # 如果已经在加载模型，则不重复加载
        if self._model_loading:
            return None
            
        # 标记正在加载模型
        self._model_loading = True
        
        # 创建并启动模型加载线程
        self._model_load_thread = ModelLoadThread(self.yolo_executor, model_path)
        self._model_load_thread.model_loaded.connect(self._on_model_loaded)
        self._model_load_thread.start()
        return self._model_load_thread

    def _on_model_loaded(self, success: bool, error_message: str):
        """模型加载完成后的回调函数"""
        # 标记加载完成
        self._model_loading = False
        
        if success:
            # 加载成功，保存模型路径到缓存
            model_path = Path(self._model_load_thread.model_path)
            self._save_yolo_model_to_cache(model_path)
        else:
            # 加载失败，打印错误信息
            print(f"异步加载YOLO模型失败: {error_message}")

    def exec_yolo(self, img_path: Path):
        # 检查模型是否正在加载
        if self._model_loading:
            raise Exception("Model is still loading, please wait.")
            
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
                self.load_yolo_async(model_path)

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