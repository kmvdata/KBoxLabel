from pathlib import Path

from sqlalchemy import engine_from_config, text

from src.common.god.logger import logger
from src.models.sql.annotation_category import AnnotationCategory
from src.models.sql.kolo_item import KoloItem
from src.models.sql.kv_config import KVConfig


def gen_sql_tables(db_path: Path):
    """
    检查db_path对应的sql文件中是否存在，如果不存在，则创建这个表以及对应索引
    :param db_path: SQLite数据库文件路径
    :return: None
    """
    try:
        # 确保数据库文件存在
        if not db_path.exists():
            db_path.parent.mkdir(parents=True, exist_ok=True)
            db_path.touch()
            logger.info(f'创建数据库文件: {db_path}')

        # SQLAlchemy配置
        # 多线程网络模型中session生命周期 https://docs.sqlalchemy.org/en/14/orm/contextual.html#thread-local-scope
        # commit后会清空session所有的绑定对象, 如果需要继续使用model, 需要session.refresh(user)或者配置expire_on_commit=False
        db_config = {
            "sqlalchemy.url": f"sqlite:///{str(db_path)}",
            "sqlalchemy.echo": False,
            "sqlalchemy.pool_pre_ping": True,
        }
        db_engine = engine_from_config(db_config, prefix="sqlalchemy.")

        # 检查并创建表和索引。添加新的类型后，要在这里添加新表
        # 使用checkfirst=False确保每次都重新创建表结构（如果表结构有变化）
        # 但在生产环境中，应该使用数据库迁移工具来处理表结构变更
        AnnotationCategory.metadata.create_all(db_engine, checkfirst=True)  # type: ignore
        KoloItem.metadata.create_all(db_engine, checkfirst=True)  # type: ignore
        KVConfig.metadata.create_all(db_engine, checkfirst=True)  # type: ignore

        # 检查并添加缺失的列（针对已有数据库的升级情况）
        _upgrade_annotation_category_table(db_engine)

    except (NameError, ModuleNotFoundError) as e:
        logger.error(e)
        # 数据库加载失败，继续上抛异常
        raise


def _upgrade_annotation_category_table(db_engine):
    """
    升级annotation_category表结构，添加缺失的列
    """
    # 检查并添加color_r, color_g, color_b列
    with db_engine.connect() as conn:
        # 获取表的当前列信息
        result = conn.execute(text("PRAGMA table_info(annotation_category)"))
        columns = [row[1] for row in result.fetchall()]

        # 检查并添加缺失的列
        if 'color_r' not in columns:
            conn.execute(text("ALTER TABLE annotation_category ADD COLUMN color_r INTEGER NOT NULL DEFAULT 0"))

        if 'color_g' not in columns:
            conn.execute(text("ALTER TABLE annotation_category ADD COLUMN color_g INTEGER NOT NULL DEFAULT 0"))

        if 'color_b' not in columns:
            conn.execute(text("ALTER TABLE annotation_category ADD COLUMN color_b INTEGER NOT NULL DEFAULT 0"))

        conn.commit()
