from PyQt5.QtWidgets import QWidget
from PyQt5.QtCore import QObject, pyqtSlot

from src.core.i18n.language_manager import LanguageManager


class UILanguageHandler:
    """UI组件语言处理器，用于处理语言切换"""
    
    def __init__(self, parent: QWidget):
        self.parent = parent
        # 连接语言变更信号
        LanguageManager.instance().language_changed.connect(self.on_language_changed)
    
    @pyqtSlot(str)
    def on_language_changed(self, language: str):
        """处理语言变更事件"""
        self.update_ui_texts()
    
    def update_ui_texts(self):
        """更新UI文本，子类需要重写此方法"""
        pass