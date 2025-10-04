import logging
import os
import sys
from typing import TypeVar, Optional, Union

import yaml

from pydantic import BaseModel, Field, computed_field

from src.common.god.logger import logger

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


# ---------------------------
# 顶层配置模型
# ---------------------------
T = TypeVar('T', bound='BaseConfig')


class BaseConfig(BaseModel):
    general: GeneralConfig
    logging: LoggingConfig

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
