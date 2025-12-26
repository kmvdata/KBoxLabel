import json
import os
from pathlib import Path
from typing import Dict, Optional

from PyQt5.QtCore import QObject, pyqtSignal
from src.core.ksettings import KSettings


# 全局实例
_language_manager_instance = None


class LanguageManager(QObject):
    # 语言变更信号
    language_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        global _language_manager_instance
        # 如果已经有实例存在，抛出异常或返回现有实例（通过工厂函数处理）
        if _language_manager_instance is not None:
            raise RuntimeError("LanguageManager is a singleton. Use LanguageManager.instance() to get the instance.")
        super().__init__(parent)
        self._current_language = "zh"
        self._translations: Dict[str, str] = {}
        self.load_translations()
        
    @classmethod
    def instance(cls):
        global _language_manager_instance
        if _language_manager_instance is None:
            _language_manager_instance = cls()
        return _language_manager_instance
    
    def load_translations(self, language: str = None):
        if language:
            self._current_language = language
            
        # 加载对应语言的翻译文件
        i18n_dir = Path(__file__).parent
        lang_file = i18n_dir / f"{self._current_language}.json"
        
        if lang_file.exists():
            with open(lang_file, 'r', encoding='utf-8') as f:
                self._translations = json.load(f)
        else:
            self._translations = {}
    
    def translate(self, key: str, **kwargs) -> str:
        text = self._translations.get(key, key)
        if kwargs:
            try:
                text = text.format(**kwargs)
            except (KeyError, ValueError):
                pass
        return text

    def set_language(self, language: str):
        """设置语言并重新加载翻译"""
        old_language = self._current_language
        self.load_translations(language)
        # 更新配置中的语言设置
        settings = KSettings()
        settings.set_language(language)
        settings.sync()
        
        # 发送语言变更信号
        if old_language != language:
            self.language_changed.emit(language)


def tr(key: str, **kwargs) -> str:
    """翻译函数"""
    return LanguageManager.instance().translate(key, **kwargs)


def set_language(language: str):
    """设置当前语言"""
    LanguageManager.instance().set_language(language)