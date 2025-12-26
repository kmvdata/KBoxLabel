from PyQt5.QtCore import QObject, pyqtSignal
from typing import Callable, List

from src.core.i18n.language_manager import set_language as set_current_language


class I18nManager(QObject):
    """国际化管理器，用于处理语言切换和UI更新通知"""
    
    # 语言切换信号
    language_changed = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        self._current_language = "zh"
        self._ui_components = []
        
    def register_component(self, component):
        """注册需要语言更新的UI组件"""
        if component not in self._ui_components:
            self._ui_components.append(component)
    
    def unregister_component(self, component):
        """注销UI组件"""
        if component in self._ui_components:
            self._ui_components.remove(component)
    
    def set_language(self, language: str):
        """设置语言并通知所有注册的组件"""
        if self._current_language != language:
            self._current_language = language
            # 更新语言管理器
            set_current_language(language)
            # 发送信号通知所有组件
            self.language_changed.emit(language)
    
    def get_current_language(self) -> str:
        """获取当前语言"""
        return self._current_language


# 全局国际化管理器实例
_i18n_manager = I18nManager()


def get_i18n_manager() -> I18nManager:
    """获取国际化管理器实例"""
    return _i18n_manager