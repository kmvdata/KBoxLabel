#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
调整页眉页脚的工具模块
"""

import sys
from pathlib import Path

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from src.common.domain.project_domain import ProjectDomain
from src.common.domain.models.kolo_item import KoloItem


def adjust_header(project_path: str):
    """
    调整项目中所有class_name为'Page-header'的kolo_item项的width为"1.0"
    
    :param project_path: 项目路径
    """
    # 构造数据库路径
    db_path = Path(project_path) / ".kboxlabel" / "data.db"
    
    # 检查数据库文件是否存在
    if not db_path.exists():
        print(f"错误: 在路径 {db_path} 找不到数据库文件")
        return False
    
    try:
        # 创建ProjectDomain实例
        project_domain = ProjectDomain(db_path)
        
        # 定义事务函数来更新数据
        def transaction_func(session):
            # 更新所有class_name为'Page-header'的项目的width为"1.0"
            updated_count = session.query(KoloItem).filter(
                KoloItem.class_name == 'Page-header'
            ).update({KoloItem.width: "1.0"})
            
            print(f"已更新 {updated_count} 个 'Page-header' 项目的width为 '1.0'")
            return updated_count
        
        # 在事务中执行更新
        updated_count = project_domain.execute_in_transaction(transaction_func)
        
        print(f"成功更新了 {updated_count} 个Page-header项目的width值")
        return True
        
    except Exception as e:
        print(f"调整Page-header项目时出错: {str(e)}")
        return False


if __name__ == "__main__":
    _project_path = '/Users/kermit/DataGripProjects/contracts'
    success = adjust_header(_project_path)
    if success:
        print("Page-header项目调整完成")
        sys.exit(0)
    else:
        print("Page-header项目调整失败")
        sys.exit(1)