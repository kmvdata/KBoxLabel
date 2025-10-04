from pathlib import Path
from typing import Type
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import DeclarativeMeta


class DBUtil:
    @classmethod
    def gen_sql(cls, sql_path: Path):
        """
        检查sql_path对应位置的sql文件是否存在，如果不存在，则创建这个文件
        :param sql_path: SQLite数据库文件路径
        :return: None
        """
        if not sql_path.exists():
            # 确保父目录存在
            sql_path.parent.mkdir(parents=True, exist_ok=True)
            # 创建空的SQLite数据库文件
            sql_path.touch()
            
    @classmethod
    def gen_sql_tables(cls, table_class: Type[DeclarativeMeta], sql_path: Path):
        """
        检查table_class在sql_path对应的sql文件中是否存在，如果不存在，则创建这个表以及对应索引
        :param table_class: SQLAlchemy模型类
        :param sql_path: SQLite数据库文件路径
        :return: None
        """
        # 确保数据库文件存在
        cls.gen_sql(sql_path)
        
        # 创建数据库引擎
        engine = create_engine(f'sqlite:///{sql_path}')
        
        # 创建表和索引
        table_class.metadata.create_all(engine)