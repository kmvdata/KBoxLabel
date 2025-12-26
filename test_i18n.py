#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试国际化功能
"""
from src.core.i18n.language_manager import tr, set_language, LanguageManager
import json
from pathlib import Path


def test_translation():
    print("=== 测试国际化功能 ===")
    
    # 测试中文
    print("当前语言: 中文")
    print(f"欢迎窗口标题: {tr('welcome_window_title')}")
    print(f"新项目: {tr('new_project')}")
    print(f"打开项目: {tr('open_project')}")
    
    # 切换到英文
    print("\n切换到英文...")
    set_language("en")
    print(f"Welcome window title: {tr('welcome_window_title')}")
    print(f"New project: {tr('new_project')}")
    print(f"Open project: {tr('open_project')}")
    
    # 切换回中文
    print("\n切换回中文...")
    set_language("zh")
    print(f"欢迎窗口标题: {tr('welcome_window_title')}")
    print(f"新项目: {tr('new_project')}")
    print(f"打开项目: {tr('open_project')}")
    
    # 测试带参数的翻译
    print(f"\n带参数的翻译测试: {tr('import_result', success_count=10, failed_count=2, failed_details='test')}")
    
    # 检查语言文件是否存在
    i18n_dir = Path(__file__).parent / "src" / "core" / "i18n"
    zh_file = i18n_dir / "zh.json"
    en_file = i18n_dir / "en.json"
    
    print(f"\n中文语言文件存在: {zh_file.exists()}")
    print(f"英文语言文件存在: {en_file.exists()}")
    
    if zh_file.exists():
        with open(zh_file, 'r', encoding='utf-8') as f:
            zh_data = json.load(f)
        print(f"中文语言文件包含 {len(zh_data)} 个条目")
    
    if en_file.exists():
        with open(en_file, 'r', encoding='utf-8') as f:
            en_data = json.load(f)
        print(f"英文语言文件包含 {len(en_data)} 个条目")
    
    print("\n=== 国际化功能测试完成 ===")


if __name__ == "__main__":
    test_translation()