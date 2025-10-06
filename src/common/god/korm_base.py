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
from src.common.god.sqlite_db import DB

metadata = MetaData()


@as_declarative(metadata=metadata)
class KOrmBase(object):
    id = None
    kid = None
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
    def get(cls, _id, with_for_update: bool = False):
        return DB.get_by_id(cls, _id, with_for_update)

    @classmethod
    def get_by_kid(cls, kid, with_for_update: bool = False, use_cache=False):
        return DB.get_by_kid(cls, kid, with_for_update, use_cache)

    @classmethod
    def get_by_condition(cls, with_for_update: bool = False, order_by: str = None, **condition):
        return DB.get_by_condition(cls, with_for_update, order_by, **condition)

    @classmethod
    def gets_by_condition(cls, page: int, size: int, order_by: str = None, **condition) -> (list, int):
        return DB.gets_by_condition(cls, page, size, order_by, **condition)

    @classmethod
    def gets_in_ids(cls, ids: list, order_by: str = None) -> list | None:
        return DB.gets_in_ids(cls, ids, order_by)

    @classmethod
    def gets_in_kids(cls, kids: list, order_by: str = None) -> list | None:
        return DB.gets_in_kids(cls, kids, order_by)

    @classmethod
    def gets_by_filters(cls, filters: tuple, page: int, size: int, order_by: str = None) -> (list, int):
        return DB.gets_by_filters(cls, filters, page, size, order_by)

    @classmethod
    def get_sums(cls, fields: list, filters: tuple) -> list | None:
        return DB.get_sums(cls, fields, filters)

    @classmethod
    def delete_by_kid(cls, kid: Annotated[str | int, '唯一kid'],
                      with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        DB.delete_by_kid(cls, kid, with_commit)

    def save(self, with_commit: Annotated[bool, '是否提交事务'] = True, use_cache: bool = True) -> None:
        DB.save(self, with_commit)

    def add(self, with_commit: Annotated[bool, '是否提交事务'] = True, use_cache: bool = True) -> None:
        DB.add(self, with_commit)

    def delete(self, with_commit: Annotated[bool, '是否提交事务'] = True) -> None:
        DB.delete(self, with_commit)

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
