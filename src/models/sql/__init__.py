from pathlib import Path
from typing import Type
from sqlalchemy import create_engine, engine_from_config
from sqlalchemy.ext.declarative import DeclarativeMeta

from src.common.god.korm_base import KOrmBase
from src.common.god.logger import logger
from src.models.sql.annotation_category import AnnotationCategory
from src.models.sql.kolo_item import KoloItem


def gen_sql_tables(db_path: Path):
    """
    检查db_path对应的sql文件中是否存在，如果不存在，则创建这个表以及对应索引
    :param db_path: SQLite数据库文件路径
    :return: None
    """
    try:
        db_path = db_path
        if not db_path.exists():
            db_path.touch()
            logger.info(f'创建数据库文件: {db_path}')

        # SQLAlchemy
        # 多线程网络模型中session生命周期 https://docs.sqlalchemy.org/en/14/orm/contextual.html#thread-local-scope
        # commit后会清空session所有的绑定对象, 如果需要继续使用model, 需要session.refresh(user)或者配置expire_on_commit=False
        db_config = {
            "sqlalchemy.url": f"sqlite:///{str(db_path)}",
            "sqlalchemy.echo": False,
            "sqlalchemy.pool_pre_ping": True,
        }
        db_engine = engine_from_config(db_config, prefix="sqlalchemy.")

        # 创建表和索引。添加新的类型后，要在这里添加新表
        AnnotationCategory.metadata.create_all(db_engine)  # type: ignore
        KoloItem.metadata.create_all(db_engine)  # type: ignore

    except (NameError, ModuleNotFoundError) as e:
        logger.error(e)
        # 数据库加载失败，继续上抛异常
        raise


