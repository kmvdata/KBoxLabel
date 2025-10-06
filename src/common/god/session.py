"""
包装werkzeug.local（支持协程和线程）和threading.local（支持线程）下的全局session
兼容flask app上下文，以及普通线程上下文
"""
import threading
import traceback
from pathlib import Path

from sqlalchemy import engine_from_config
from sqlalchemy.orm import scoped_session, sessionmaker

from src.common.god.business_exception import BusinessException
from src.common.god.common_error import CommonError
from src.common.god.logger import logger


class SqliteDB(object):

    def __init__(self, db_path: Path):
        self.db_path = None
        self.db_engine = None
        self.db_session = None
        self.sessions = dict()
        self._load_db(db_path)

    def _load_db(self, db_path: Path):
        try:
            self.db_path = db_path
            if not self.db_path.exists():
                self.db_path.touch()
                logger.info(f'创建数据库文件: {db_path}')

            # SQLAlchemy
            # 多线程网络模型中session生命周期 https://docs.sqlalchemy.org/en/14/orm/contextual.html#thread-local-scope
            # commit后会清空session所有的绑定对象, 如果需要继续使用model, 需要session.refresh(user)或者配置expire_on_commit=False
            db_config = {
                "sqlalchemy.url": f"sqlite:///{str(db_path)}",
                "sqlalchemy.echo": False,
                "sqlalchemy.pool_pre_ping": True,
            }
            self.db_engine = engine_from_config(db_config, prefix="sqlalchemy.")
            # 创建 Session 类
            self.db_session = scoped_session(sessionmaker(bind=self.db_engine, expire_on_commit=False))
        except (NameError, ModuleNotFoundError) as e:
            logger.error(e)
            # 数据库加载失败，继续上抛异常
            raise

    def thread_session(self) -> scoped_session | None:
        # threading.local()每次都会重新生成新的变量
        session = self.sessions.get(threading.get_ident())
        if session is None:
            logger.error('没有合适的线程安全session')
            logger.error(''.join(traceback.format_stack(limit=10)))
            raise BusinessException(CommonError.SESSION_ERROR)
        return session

    @staticmethod
    def close_session(self):
        session = self.sessions.get(threading.get_ident())
        session.close()
        pass
