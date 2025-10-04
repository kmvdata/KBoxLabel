import logging
import os
import sys
from typing import TypeVar, Optional, Union

import i18n
import redis
import yaml
from fastapi import FastAPI
from fastapi_socketio import SocketManager
from pydantic import BaseModel, Field, computed_field

from kanata.common.common.tool.logger import logger

try:
    from sqlalchemy.orm.scoping import scoped_session as ScopedSession

    SQLAlchemySessionType = ScopedSession
except ImportError:
    SQLAlchemySessionType = any  # 如果 SQLAlchemy 未安装，回退到 Any

# 根据 Python 版本选择日志级别映射方式
if sys.version_info >= (3, 11):
    # Python 3.11+ 使用内置方法
    def get_level_value(level_text: str) -> int:
        return logging.getLevelNamesMapping().get(level_text.upper(), 0)
else:
    # Python 3.10 及以下使用手动定义的字典
    LEVEL_MAPPING = {
        'NOTSET': 0,
        'DEBUG': 10,
        'INFO': 20,
        'WARNING': 30,
        'ERROR': 40,
        'CRITICAL': 50,
    }


    def get_level_value(level_text: str) -> int:
        return LEVEL_MAPPING.get(level_text.upper(), 0)


# ---------------------------
# 嵌套配置模型
# ---------------------------

class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = Field(ge=1)
    max_overflow: int = Field(ge=0)
    pool_recycle: int = Field(ge=60)
    echo: bool = False


class RedisConfig(BaseModel):
    host: str
    port: int = Field(ge=1, le=65535)
    db: int = Field(ge=0)
    password: str
    decode_responses: bool = True


class GeneralConfig(BaseModel):
    debug: bool = False
    env: str = 'test'


class LoggingConfig(BaseModel):
    level_text: str = Field(alias="level")  # 改为字符串更符合日志级别惯例，如 "INFO"
    path: str = "logs/app.log"  # 日志文件路径

    @computed_field  # Pydantic v2 新特性
    @property
    def level(self) -> int:
        """通过属性直接访问数值级别"""
        return get_level_value(self.level_text)


class SocketioConfig(BaseModel):
    mount_location: str = "/ws"
    socketio_path: str = "/socket.io"
    cors_allowed_origins: Union[str, list] = '*'


class ServiceConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(ge=1, le=65535, default=8000)
    workers: int = Field(ge=1, default=4)
    reload: bool = False
    socketio_config: Optional[SocketioConfig] = None

    def gen_socket_manager(self, app: FastAPI) -> Optional[SocketManager]:
        """
        初始化并返回 Socket.IO 管理器
        Args:
            app: FastAPI 应用实例
        Returns:
            Optional[SocketManager]:
                - 如果配置了 socketio_config，返回 SocketManager 实例
                - 如果没有配置，返回 None
        """
        if not self.socketio_config:
            return None

        return SocketManager(
            app=app,
            socketio_path=self.socketio_config.socketio_path,
            cors_allowed_origins=self.socketio_config.cors_allowed_origins
        )


class I18nConfig(BaseModel):
    path: str = "locales"
    locale: str = "en"


class ProxiesConfig(BaseModel):
    http: str
    https: str


# ---------------------------
# 顶层配置模型
# ---------------------------
T = TypeVar('T', bound='BaseConfig')


class BaseConfig(BaseModel):
    general: GeneralConfig
    logging: LoggingConfig
    service: Optional[ServiceConfig] = None
    i18n: Optional[I18nConfig] = None
    database: Optional[DatabaseConfig] = None
    redis: Optional[RedisConfig] = None
    proxies: Optional[ProxiesConfig] = None

    @classmethod
    def load_config(cls, file_path: str) -> T:
        """
        从YAML文件加载配置
        自动返回调用类的实例，子类无需重新实现
        """
        with open(file_path, "r", encoding="utf-8") as f:
            # 添加对空文件的处理
            try:
                yaml_data = yaml.safe_load(f) or {}
            except yaml.YAMLError as e:
                raise ValueError(f"YAML解析错误: {e}")

            return cls(**yaml_data)

    def init_logger(self,
                    package: str,
                    _format: str = '%(asctime)s - %(levelname)s - 进程%(process)d:线程%(thread)d - %(filename)s:%('
                                   'funcName)s:%(lineno)d: %(message)s') -> None:
        # 创建一个logger
        logger.setLevel(self.logging.level)

        # 日志格式
        formatter = logging.Formatter(fmt=_format)

        # Debug模式不输出日志文件
        if self.general.debug:
            console_handler = logging.StreamHandler(sys.stdout)
            console_handler.setFormatter(formatter)
            logger.addHandler(console_handler)
        else:
            # 如果logger_path为None或者为空字符串，使用当前目录
            if not self.logging.path or len(self.logging.path) == 0:
                logger_path = os.path.join(os.getcwd(), f"{package}.log")
            else:
                logger_path = os.path.join(self.logging.path, f"{package}.log")

            # 确保日志文件所在的目录存在
            os.makedirs(os.path.dirname(logger_path), exist_ok=True)

            # 创建并设置文件handler
            file_handler = logging.FileHandler(logger_path, encoding='utf-8')
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)

    def load_i18n(self):
        """
        国际化i18n
        """
        if self.i18n is None:
            return
        i18n.load_path.append(self.i18n.path)
        i18n.set('file_format', 'json')
        i18n.set('enable_memoization', True)
        # i18n.set('filename_format', '{locale}.{format}')
        i18n.set('skip_locale_root_data', True)
        i18n.set('locale', self.i18n.locale)

    @classmethod
    def gen_db_session(cls, db_config: DatabaseConfig) -> SQLAlchemySessionType:
        try:
            from sqlalchemy import engine_from_config
            from sqlalchemy.orm import scoped_session, sessionmaker
            # SQLAlchemy
            # 多线程网络模型中session生命周期 https://docs.sqlalchemy.org/en/14/orm/contextual.html#thread-local-scope
            # commit后会清空session所有的绑定对象, 如果需要继续使用model, 需要session.refresh(user)或者配置expire_on_commit=False
            db_engine = engine_from_config(db_config.model_dump(), prefix="")
            # 创建 Session 类
            db_session = scoped_session(sessionmaker(bind=db_engine, expire_on_commit=False))
            return db_session
        except (NameError, ModuleNotFoundError) as e:
            logger.error(e)
            raise RuntimeError("SQLAlchemy is not installed") from e

    @classmethod
    def gen_redis_client(cls, redis_config: RedisConfig):
        try:
            return redis.StrictRedis(**redis_config.model_dump())
        except (ImportError, NameError) as e:
            logger.error(e)


# ---------------------------
# 使用示例
# ---------------------------
if __name__ == "__main__":
    config = BaseConfig.load_config("config-debug.yaml")
    print("Debug模式:", config.general.debug)
    print("数据库URL:", config.database.url)  # 字段名调整
    print("Redis端口:", config.redis.port)  # 字段名调整
    print(f"日志级别: {config.logging.level_text} - {config.logging.level}")
    print(f"服务端口: {config.service}")
