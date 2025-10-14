import json
from pathlib import Path
from typing import Optional, List

from PyQt5.QtGui import QColor

from src.common.god.sqlite_db import SqliteDB
from src.core.ksettings import KSettings
from src.core.yolo_executor import YOLOExecutor
from src.models.dto.annotation_category import AnnotationCategory
from src.models.sql import gen_sql_tables
from src.models.sql.annotation_category import AnnotationCategory as SQLAnnotationCategory


class RefProjectInfo:
    """可变容器，用于同步 project_path 的变化，包含YOLO模型配置缓存功能"""

    def __init__(self, path: Path):
        self.path = path  # 可变属性
        self.yolo_executor = YOLOExecutor()
        self.categories: list[AnnotationCategory] = []

        # 初始化数据库
        gen_sql_tables(self.db_path)
        self.sqlite_db: Optional[SqliteDB] = SqliteDB(self.db_path)

    def exists(self) -> bool:
        if self.path is None:
            return False
        return self.path.exists()

    @property
    def db_path(self):
        if self._config_dir is None:
            return None
        return self._config_dir / 'data.db'

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
            return self.yolo_executor.is_model_loaded()
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

    def save_categories(self):
        """
        将当前的 categories 列表保存到数据库中
        """
        if not self.sqlite_db:
            raise Exception("数据库未初始化")

        # 开始事务
        session = self.sqlite_db.db_session()
        try:
            # 清除现有的所有类别
            session.query(SQLAnnotationCategory).delete()
            
            # 添加所有当前类别
            for category in self.categories:
                sql_category = SQLAnnotationCategory()
                sql_category.class_id = category.class_id
                sql_category.class_name = category.class_name
                sql_category.color_r = category.color.red()
                sql_category.color_g = category.color.green()
                sql_category.color_b = category.color.blue()
                session.add(sql_category)
            
            # 提交事务
            session.commit()
        except Exception as e:
            # 回滚事务
            session.rollback()
            raise e
        finally:
            session.close()

    def load_categories(self) -> List[AnnotationCategory]:
        """
        从数据库加载类别列表
        """
        if not self.sqlite_db:
            return []
            
        # 开始会话
        session = self.sqlite_db.db_session()
        try:
            # 查询所有类别
            sql_categories = session.query(SQLAnnotationCategory).all()
            
            # 转换为AnnotationCategory对象列表
            categories = []
            for sql_cat in sql_categories:
                category = AnnotationCategory(
                    class_id=sql_cat.class_id,
                    class_name=sql_cat.class_name
                )
                category.color = QColor(sql_cat.color_r, sql_cat.color_g, sql_cat.color_b)
                categories.append(category)
                
            return categories
        finally:
            session.close()

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