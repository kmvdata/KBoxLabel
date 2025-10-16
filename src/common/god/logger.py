import os
import sys
import logging
from functools import wraps
from typing import Annotated

# 设置core日志
logger = logging.getLogger(__package__)
# logger.setLevel(logging.INFO)


def init_logger(debug: Annotated[bool, 'debug模式'],
                package: Annotated[str, '包名'],
                level: Annotated[int, '日志级别'] = logging.INFO,
                logger_path: Annotated[str, '日志文件路径'] = None,
                _format: Annotated[str, '日志格式'] = '%(asctime)s - %(levelname)s - 进程%(process)d:线程%(thread)d - %(filename)s:%(funcName)s:%(lineno)d: %(message)s') -> None:
    # 创建一个logger
    logger.setLevel(level)

    # @20201108增加打印进程ID和线程ID
    # formatter = logging.Formatter('%(asctime)s - %(levelname)s - 进程%(process)d:线程%(thread)d - %(filename)s:%(funcName)s:%(lineno)d: %(message)s')
    # 尝试不打印文件名
    # formatter = logging.Formatter('%(asctime)s - %(levelname)s - 进程%(process)d:线程%(thread)d - %(module)s:%(funcName)s:%(lineno)d: %(message)s')
    # 尝试隐藏更多信息
    # formatter = logging.Formatter('%(asctime)s - %(levelname)s - 进程%(process)d:线程%(thread)d - %(message)s')
    formatter = logging.Formatter(fmt=_format)

    # Debug模式不输出日志文件
    if debug:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    else:
        # 如果logger_path为None或者为空字符串，使用当前目录
        if not logger_path or len(logger_path) == 0:
            logger_path = os.path.join(os.getcwd(), f"{package}.log")
        else:
            logger_path = os.path.join(logger_path, f"{package}.log")

        # 确保日志文件所在的目录存在
        os.makedirs(os.path.dirname(logger_path), exist_ok=True)

        # 创建并设置文件handler
        file_handler = logging.FileHandler(logger_path, encoding='utf-8')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)


def log(func):

    @wraps(func)
    def function_log(*args, **kwargs):

        logger.info("%s(%r | %r)", func.__name__, args[1:].__str__(), kwargs.__str__())
        result = func(*args, **kwargs)

        # 要求这里返回的都是dict
        # try:
        #     logger.info("%s = %s(%r | %r)", result.__str__(), func.__name__, args[1:].__str__(), kwargs.__str__())
        # except Exception as e:
        #     logger.error(e)

        return result
    return function_log


def print_box(message: str):
    return """
=================================================================
%s
=================================================================
    """ % message
