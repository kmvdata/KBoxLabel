"""
包装werkzeug.local（支持协程和线程）和threading.local（支持线程）下的全局session
兼容flask app上下文，以及普通线程上下文
"""
import threading
import traceback
import hashlib
import json
import time
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Annotated

from sqlalchemy import engine_from_config, text, func
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

    def get_by_id(self, cls, _id):
        session = self.thread_session()
        if _id is None:
            return None
        if isinstance(_id, tuple):
            _id, = _id
        return session.query(cls).filter_by(id=_id).first()

    def get_by_kid(self, cls, kid):
        """
        :param cls: 继承自KOrmBase的类
        :param kid:
        :return:
        """
        if kid is None:
            return None
        if isinstance(kid, tuple):
            kid, = kid
        session = self.thread_session()
        obj = session.query(cls).filter_by(kid=kid).first()
        return obj

    def get_by_condition(self, cls, with_for_update: bool = False, order_by: str = None, **condition):
        session = self.thread_session()
        if condition is None:
            return None
        if not isinstance(condition, dict):
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter_by(**condition).order_by(_order_by).first() if not with_for_update else \
            session.query(cls).with_for_update().filter_by(**condition).order_by(_order_by).first()

    def gets_by_condition(self, cls, page: int, size: int, order_by: str = None, **condition) -> (list, int):
        session = self.thread_session()
        if condition is None:
            return None
        if not isinstance(condition, dict):
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter_by(**condition).order_by(_order_by).offset((page - 1) * size).limit(
            size).all(), \
            session.query(func.count(cls.id)).filter_by(**condition).scalar()

    def gets_in_ids(self, cls, ids: list, order_by: str = None) -> list | None:
        session = self.thread_session()
        if ids is None:
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter(cls.id.in_(ids)).order_by(_order_by).all()

    def gets_in_kids(self, cls, kids: list, order_by: str = None) -> list | None:
        session = self.thread_session()
        if kids is None:
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter(cls.kid.in_(kids)).order_by(_order_by).all()

    def gets_by_filters(self, cls, filters: tuple, page: int, size: int, order_by: str = None) -> (list, int):
        session = self.thread_session()
        if filters is None:
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter(*filters).order_by(_order_by).offset((page - 1) * size).limit(size).all(), \
            session.query(func.count(cls.id)).filter(*filters).scalar()

    def get_sums(self, cls, fields: list, filters: tuple) -> list | None:
        session = self.thread_session()
        if filters is None:
            return None
        # return db.query(*[func.sum(x) for x in fields if (x.key in cls.__dict__)]).filter(*filters).all()
        return session.query(*[func.sum(x) for x in fields]).filter(*filters).all()

    def delete_by_kid(self, cls, kid: Annotated[str | int, '唯一kid'],
                      with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        if not kid:
            raise BusinessException(error=CommonError.PARAMETER_ERROR)
        instance = self.get_by_kid(cls, kid=kid)
        self.delete(instance, with_commit=with_commit)

    def save(self, obj, with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        session = self.thread_session()
        try:
            obj.remove_kid_if_none()
            session.merge(obj)
            if with_commit:
                # 事务提交
                session.commit()
                # TODO: 这里需要确认cosmos.redis的访问方式
                # if use_cache:
                #     # 节约redis的内存占用
                #     if hasattr(cosmos, 'redis') and obj.kid:
                #         cosmos.redis.hset(name=obj.__tablename__, key=obj.kid,
                #                           value=json.dumps(obj.to_serializable_dict()))
            else:
                # 执行外部事务(外部提交)，需要放弃redis的缓存对应的数据，否则有可能因为外部事务的失败，造成数据库和缓存不一致
                # 部分表kid未使用，永远是null
                # if hasattr(cosmos, 'redis') and obj.kid:
                #     cosmos.redis.hdel(obj.__tablename__, obj.kid)
                pass
        except Exception as e:
            logger.error(e)
            session.rollback()
            raise e

    def add(self, obj, with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        session = self.thread_session()
        try:
            obj.remove_kid_if_none()
            session.add(obj)
            if with_commit:
                session.commit()
                # TODO: 这里需要确认cosmos.redis的访问方式
                # if use_cache and hasattr(cosmos, 'redis'):
                #     if hasattr(obj, 'kid') and obj.kid is not None:
                #         cosmos.redis.hset(name=obj.__tablename__, key=obj.kid,
                #                           value=json.dumps(obj.to_serializable_dict()))
            else:
                # if hasattr(cosmos, 'redis') and obj.kid:
                #     cosmos.redis.hdel(obj.__tablename__, obj.kid)
                pass
        except Exception as e:
            logger.error(e)
            session.rollback()
            raise e

    def delete(self, obj, with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        session = self.thread_session()
        try:
            obj.remove_kid_if_none()
            session.delete(obj)
            if with_commit:
                session.commit()
                # TODO: 这里需要确认cosmos.redis的访问方式
                # if hasattr(cosmos, 'redis') and hasattr(obj, 'kid') and obj.kid:
                #     cosmos.redis.hdel(obj.__tablename__, obj.kid)
            else:
                # if hasattr(cosmos, 'redis') and hasattr(obj, 'kid') and obj.kid:
                #     cosmos.redis.hdel(obj.__tablename__, obj.kid)
                pass
        except Exception as e:
            logger.error(e)
            session.rollback()
            raise e

    @staticmethod
    def generate_kid() -> str:
        """
        more生成kid算法(完全随机)
        """
        return hashlib.md5(time.time().__str__().encode()).hexdigest().lower()[:16]