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
    调整项目中所有class_name为'Page-header'的kolo_item项的位置，
    保持当前绝对位置的底部边位置不变，然后扩展其他三个边，让其和image边界对齐
    
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
            # 获取所有class_name为'Page-header'的项目
            page_headers = session.query(KoloItem).filter(
                KoloItem.class_name == 'Page-header'
            ).all()
            
            updated_count = 0
            for item in page_headers:
                try:
                    # 解析当前坐标值
                    x_center = float(item.x_center)
                    y_center = float(item.y_center)
                    width = float(item.width)
                    height = float(item.height)
                    
                    # 计算当前的绝对边界坐标
                    current_left = x_center - width / 2
                    current_top = y_center - height / 2
                    current_right = x_center + width / 2
                    current_bottom = y_center + height / 2
                    
                    # 保持底部边位置不变，调整其他三边与图像边界对齐
                    # 1. 左边与图像左边界对齐 (x=0)
                    # 2. 右边与图像右边界对齐 (x=1)
                    # 3. 顶部与图像顶部对齐 (y=0)
                    # 4. 底部保持不变
                    
                    new_left = 0.0
                    new_right = 1.0
                    new_top = 0.0
                    new_bottom = current_bottom  # 保持底部不变
                    
                    # 重新计算中心点和宽高
                    new_width = new_right - new_left
                    new_height = new_bottom - new_top
                    new_x_center = (new_left + new_right) / 2
                    new_y_center = (new_top + new_bottom) / 2
                    
                    # 确保所有值在[0, 1]范围内
                    new_x_center = max(0.0, min(1.0, new_x_center))
                    new_y_center = max(0.0, min(1.0, new_y_center))
                    new_width = max(0.0, min(1.0, new_width))
                    new_height = max(0.0, min(1.0, new_height))
                    
                    # 更新项目
                    item.x_center = f"{new_x_center:.9f}"
                    item.y_center = f"{new_y_center:.9f}"
                    item.width = f"{new_width:.9f}"
                    item.height = f"{new_height:.9f}"
                    
                    updated_count += 1
                    
                except ValueError as e:
                    print(f"处理项目 {item.kid} 时出现数值转换错误: {e}")
                    continue
            
            print(f"已更新 {updated_count} 个 'Page-header' 项目的位置")
            return updated_count
        
        # 在事务中执行更新
        updated_count = project_domain.execute_in_transaction(transaction_func)
        
        print(f"成功更新了 {updated_count} 个Page-header项目的位置")
        return True
        
    except Exception as e:
        print(f"调整Page-header项目时出错: {str(e)}")
        return False


def adjust_footer(project_path: str):
    """
    调整项目中所有class_name为'Page-footer'的kolo_item项的位置，
    保持当前绝对位置的顶部边位置不变，然后扩展其他三个边，让其和image边界对齐
    
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
            # 获取所有class_name为'Page-footer'的项目
            page_footers = session.query(KoloItem).filter(
                KoloItem.class_name == 'Page-footer'
            ).all()
            
            updated_count = 0
            for item in page_footers:
                try:
                    # 解析当前坐标值
                    x_center = float(item.x_center)
                    y_center = float(item.y_center)
                    width = float(item.width)
                    height = float(item.height)
                    
                    # 计算当前的绝对边界坐标
                    current_left = x_center - width / 2
                    current_top = y_center - height / 2
                    current_right = x_center + width / 2
                    current_bottom = y_center + height / 2
                    
                    # 保持顶部边位置不变，调整其他三边与图像边界对齐
                    # 1. 左边与图像左边界对齐 (x=0)
                    # 2. 右边与图像右边界对齐 (x=1)
                    # 3. 顶部保持不变
                    # 4. 底部与图像底边对齐 (y=1)
                    
                    new_left = 0.0
                    new_right = 1.0
                    new_top = current_top  # 保持顶部不变
                    new_bottom = 1.0
                    
                    # 重新计算中心点和宽高
                    new_width = new_right - new_left
                    new_height = new_bottom - new_top
                    new_x_center = (new_left + new_right) / 2
                    new_y_center = (new_top + new_bottom) / 2
                    
                    # 确保所有值在[0, 1]范围内
                    new_x_center = max(0.0, min(1.0, new_x_center))
                    new_y_center = max(0.0, min(1.0, new_y_center))
                    new_width = max(0.0, min(1.0, new_width))
                    new_height = max(0.0, min(1.0, new_height))
                    
                    # 更新项目
                    item.x_center = f"{new_x_center:.9f}"
                    item.y_center = f"{new_y_center:.9f}"
                    item.width = f"{new_width:.9f}"
                    item.height = f"{new_height:.9f}"
                    
                    updated_count += 1
                    
                except ValueError as e:
                    print(f"处理项目 {item.kid} 时出现数值转换错误: {e}")
                    continue
            
            print(f"已更新 {updated_count} 个 'Page-footer' 项目的位置")
            return updated_count
        
        # 在事务中执行更新
        updated_count = project_domain.execute_in_transaction(transaction_func)
        
        print(f"成功更新了 {updated_count} 个Page-footer项目的位置")
        return True
        
    except Exception as e:
        print(f"调整Page-footer项目时出错: {str(e)}")
        return False


def change_page_number_to_footer(project_path: str):
    """
    将项目中所有class_name为'Page-number'的kolo_item项的class_name改为'Page-footer'
    
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
            # 获取所有class_name为'Page-number'的项目
            page_numbers = session.query(KoloItem).filter(
                KoloItem.class_name == 'Page-number'
            ).all()
            
            updated_count = 0
            for item in page_numbers:
                # 将class_name从'Page-number'改为'Page-footer'
                item.class_name = 'Page-footer'
                updated_count += 1
                    
            print(f"已更新 {updated_count} 个 'Page-number' 项目的类别为 'Page-footer'")
            return updated_count
        
        # 在事务中执行更新
        updated_count = project_domain.execute_in_transaction(transaction_func)
        
        print(f"成功将 {updated_count} 个Page-number项目更改为Page-footer")
        return True
        
    except Exception as e:
        print(f"更改Page-number项目时出错: {str(e)}")
        return False


if __name__ == "__main__":
    _project_path = '/Users/kermit/DataGripProjects/contracts/'
    success = adjust_header(_project_path)
    if success:
        print("Page-header项目调整完成")
    else:
        print("Page-header项目调整失败")
        sys.exit(1)

    success = change_page_number_to_footer(_project_path)
    if success:
        print("Page-number项目转换完成")
    else:
        print("Page-number项目转换失败")
        sys.exit(1)

    success = adjust_footer(_project_path)
    if success:
        print("Page-footer项目调整完成")
    else:
        print("Page-footer项目调整失败")
        sys.exit(1)
        
