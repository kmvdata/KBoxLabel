import hashlib
import json
import time
from datetime import datetime, date
from decimal import Decimal
from typing import Annotated

from sqlalchemy import text, func, MetaData
from sqlalchemy.orm import as_declarative

from src.common.god import cosmos
from src.common.god.business_exception import BusinessException
from src.common.god.common_error import CommonError
from src.common.god.logger import logger
from src.common.god.session import DB

metadata = MetaData()


@as_declarative(metadata=metadata)
class KOrmBase(object):
    __tablename__ = None

    def __init__(self):
        self.kid = None
        self.__table__ = None

    def to_serializable_dict(self):
        rst_dict = {}
        # for public_key in self.__table__.columns
        for column in self.__table__.columns:
            key = column.name
            value = getattr(self, key)
            if isinstance(value, datetime):
                rst_dict[key] = {"__type__": "datetime", "value": value.strftime("%Y-%m-%d %H:%M:%S")}
            elif isinstance(value, date):
                rst_dict[key] = {"__type__": "date", "value": '{0.year:4d}-{0.month:02d}-{0.day:02d}'.format(value)}
            elif isinstance(value, Decimal):
                rst_dict[key] = {"__type__": "Decimal", "value": str(value)}
            else:
                rst_dict[key] = value
        return rst_dict

    @classmethod
    def unserializable_from_dict(cls, obj_dict):
        args = {}
        for key, value in obj_dict.items():
            if isinstance(value, dict):
                if value["__type__"] == "datetime":
                    args[key] = datetime.strptime(value["value"], "%Y-%m-%d %H:%M:%S")
                elif value["__type__"] == "date":
                    args[key] = datetime.strptime(value["value"], "%Y-%m-%d").date()
                elif value["__type__"] == "Decimal":
                    args[key] = Decimal(value["value"])
            else:
                args[key] = value

        return cls(**args)

    @classmethod
    def get(cls, id, with_for_update: bool = False):
        session = DB.thread_session()
        if id is None:
            return None
        if isinstance(id, tuple):
            id, = id
        return session.query(cls).filter_by(id=id).first() if not with_for_update else session.query(
            cls).with_for_update().filter_by(id=id).first()

    @classmethod
    def get_by_kid(cls, kid, with_for_update: bool = False, use_cache=False):
        """
        :param kid:
        :param with_for_update: 加互斥锁，并发读并修改后解除锁
        :param use_cache:
        :return:
        """
        if kid is None:
            return None
        if isinstance(kid, tuple):
            kid, = kid
        session = DB.thread_session()
        if use_cache and hasattr(cosmos, 'redis'):
            _obj = cosmos.redis.hget(name=cls.__tablename__, key=kid)
            obj = cls.unserializable_from_dict(json.loads(_obj)) if _obj else None
            # 缓存未命中, 从数据库中获取
            if obj is None:
                obj = session.query(cls).filter_by(kid=kid).first() if not with_for_update else \
                    session.query(cls).with_for_update().filter_by(kid=kid).first()
                # 补充到缓存中
                if obj:
                    cosmos.redis.hset(name=cls.__tablename__, key=kid, value=json.dumps(obj.to_serializable_dict()))
        else:
            obj = session.query(cls).filter_by(kid=kid).first() if not with_for_update else session.query(
                cls).with_for_update().filter_by(kid=kid).first()
            # 补充到缓存中
            if obj and hasattr(cosmos, 'redis'):
                cosmos.redis.hset(name=cls.__tablename__, key=kid, value=json.dumps(obj.to_serializable_dict()))
        return obj

    @classmethod
    def get_by_condition(cls, with_for_update: bool = False, order_by: str = None, **condition):
        session = DB.thread_session()
        if condition is None:
            return None
        if not isinstance(condition, dict):
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter_by(**condition).order_by(_order_by).first() if not with_for_update else \
            session.query(cls).with_for_update().filter_by(**condition).order_by(_order_by).first()

    @classmethod
    def gets_by_condition(cls, page: int, size: int, order_by: str = None, **condition) -> (list, int):
        session = DB.thread_session()
        if condition is None:
            return None
        if not isinstance(condition, dict):
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter_by(**condition).order_by(_order_by).offset((page - 1) * size).limit(
            size).all(), \
            session.query(func.count(cls.id)).filter_by(**condition).scalar()

    @classmethod
    def gets_in_ids(cls, ids: list, order_by: str = None) -> list | None:
        session = DB.thread_session()
        if ids is None:
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter(cls.id.in_(ids)).order_by(_order_by).all()

    @classmethod
    def gets_in_kids(cls, kids: list, order_by: str = None) -> list | None:
        session = DB.thread_session()
        if kids is None:
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter(cls.kid.in_(kids)).order_by(_order_by).all()

    # 使用方法见 https://www.jianshu.com/p/a4de47d668e3 和 https://stackoverflow.com/questions/29885879/sqlalchemy-dynamic-filter-by
    @classmethod
    def gets_by_filters(cls, filters: tuple, page: int, size: int, order_by: str = None) -> (list, int):
        session = DB.thread_session()
        if filters is None:
            return None
        _order_by = text(order_by) if order_by else text('id desc')
        return session.query(cls).filter(*filters).order_by(_order_by).offset((page - 1) * size).limit(size).all(), \
            session.query(func.count(cls.id)).filter(*filters).scalar()

    @classmethod
    def get_sums(cls, fields: list, filters: tuple) -> list | None:
        session = DB.thread_session()
        if filters is None:
            return None
        # return db.query(*[func.sum(x) for x in fields if (x.key in cls.__dict__)]).filter(*filters).all()
        return session.query(*[func.sum(x) for x in fields]).filter(*filters).all()

    @classmethod
    def delete_by_kid(cls, kid: Annotated[str, '唯一kid'], with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        if not kid:
            raise BusinessException(error=CommonError.PARAMETER_ERROR)
        instance = cls.get_by_kid(kid=kid)
        instance.delete(with_commit=with_commit)

    def save(self, with_commit: Annotated[bool, '是否提交事务'] = True, use_cache: bool = True) -> None:
        session = DB.thread_session()
        try:
            self.remove_kid_if_none()
            session.merge(self)
            if with_commit:
                # 事务提交
                session.commit()
                if use_cache:
                    # 节约redis的内存占用
                    if hasattr(cosmos, 'redis') and self.kid:
                        cosmos.redis.hset(name=self.__tablename__, key=self.kid,
                                          value=json.dumps(self.to_serializable_dict()))
            else:
                # 执行外部事务(外部提交)，需要放弃redis的缓存对应的数据，否则有可能因为外部事务的失败，造成数据库和缓存不一致
                # 部分表kid未使用，永远是null
                if hasattr(cosmos, 'redis') and self.kid:
                    cosmos.redis.hdel(self.__tablename__, self.kid)
        except Exception as e:
            logger.error(e)
            session.rollback()
            raise e

    def add(self, with_commit: Annotated[bool, '是否提交事务'] = True, use_cache: bool = True) -> None:
        session = DB.thread_session()
        try:
            self.remove_kid_if_none()
            session.add(self)
            if with_commit:
                session.commit()
                if use_cache and hasattr(cosmos, 'redis'):
                    if hasattr(self, 'kid') and self.kid is not None:
                        cosmos.redis.hset(name=self.__tablename__, key=self.kid,
                                          value=json.dumps(self.to_serializable_dict()))
            else:
                if hasattr(cosmos, 'redis') and self.kid:
                    cosmos.redis.hdel(self.__tablename__, self.kid)
        except Exception as e:
            logger.error(e)
            session.rollback()
            raise e

    def delete(self, with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        session = DB.thread_session()
        try:
            self.remove_kid_if_none()
            session.delete(self)
            if with_commit:
                session.commit()
                if hasattr(cosmos, 'redis') and hasattr(self, 'kid') and self.kid:
                    cosmos.redis.hdel(self.__tablename__, self.kid)
            else:
                if hasattr(cosmos, 'redis') and hasattr(self, 'kid') and self.kid:
                    cosmos.redis.hdel(self.__tablename__, self.kid)
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

    def remove_kid_if_none(self):
        """
        为了兼容没有kid的库
        :return:
        """
        try:
            if self.kid is None:
                del self.kid
        except AttributeError:
            pass
        return self
