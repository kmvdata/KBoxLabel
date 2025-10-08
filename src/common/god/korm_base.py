from datetime import datetime, date
from decimal import Decimal

from sqlalchemy import MetaData
from sqlalchemy.orm import as_declarative

from src.common.god.ksnowflake import KSnowflake

metadata = MetaData()


@as_declarative(metadata=metadata)
class KOrmBase(object):
    __tablename__ = None

    snowflake = KSnowflake()

    def __init__(self):
        self.id = None
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
    def gen_kid(cls) -> int:
        return cls.snowflake.gen_kid()
