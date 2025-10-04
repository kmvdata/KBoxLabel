"""
    所有模块全局变量
    全局变量必须是class，不能是简单类型
    重要!!业务系统引用cosmos时，必须确保全局唯一，所以如果业务系统依赖california，必须引用california的cosmos。
"""
from src.common.conf.base_config import BaseConfig


class Cosmos(object):
    sessions: dict = dict()
    config: BaseConfig

    def __init__(self):
        pass


global cosmos
# noinspection PyRedeclaration
cosmos = Cosmos()
