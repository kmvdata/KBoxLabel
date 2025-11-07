# application_manager.py
from pathlib import Path
from typing import List, Optional

from PyQt5.QtCore import QObject
from PyQt5.QtWidgets import QApplication

from src.ui.project_window import ProjectWindow
from src.ui.welcome_screen import WelcomeScreen


class ApplicationManager(QObject):
    """
    应用管理器类，作为隐藏的主控制器管理多个项目窗口
    实现单例模式，外部可以通过类方法调用其功能
    """
    
    _instance: Optional['ApplicationManager'] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ApplicationManager, cls).__new__(cls)
            # 初始化 QObject 基类
            super(ApplicationManager, cls._instance).__init__()
        return cls._instance
    
    def __init__(self):
        # 防止重复初始化
        if getattr(self, '_initialized', False):
            return

        # 调用父类初始化方法
        super().__init__()

        # 存储打开的项目窗口列表
        self.project_windows: List[ProjectWindow] = []
        
        # 创建并显示欢迎界面
        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.projectOpened.connect(self.open_project)
        self.welcome_screen.destroyed.connect(self.on_welcome_screen_destroyed)
        self.welcome_screen.show()
        
        # 标记已初始化
        self._initialized = True
        
    @classmethod
    def get_instance(cls) -> 'ApplicationManager':
        """
        获取ApplicationManager单例实例
        
        Returns:
            ApplicationManager: 单例实例
        """
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
        
    @classmethod
    def open_project_path(cls, project_path: str):
        """
        类方法：打开项目路径
        
        Args:
            project_path: 项目路径
        """
        instance = cls.get_instance()
        instance.open_project(project_path)
        
    @classmethod
    def get_project_windows(cls) -> List[ProjectWindow]:
        """
        类方法：获取所有打开的项目窗口列表
        
        Returns:
            List[ProjectWindow]: 项目窗口列表
        """
        instance = cls.get_instance()
        return instance.project_windows[:]
        
    @classmethod
    def has_open_projects(cls) -> bool:
        """
        类方法：检查是否有打开的项目
        
        Returns:
            bool: 如果有打开的项目返回True，否则返回False
        """
        instance = cls.get_instance()
        return len(instance.project_windows) > 0
        
    def open_project(self, project_path: str):
        """
        打开新项目窗口
        
        Args:
            project_path: 项目路径
        """
        # 创建新的项目窗口
        project_window = ProjectWindow(Path(project_path))
        
        # 添加到项目窗口列表
        self.project_windows.append(project_window)
        
        # 连接窗口关闭信号，以便在窗口关闭时从列表中移除
        project_window.destroyed.connect(lambda: self.on_project_window_closed(project_window))
        
        # 显示项目窗口
        project_window.show()
        
    def on_welcome_screen_destroyed(self):
        """
        当欢迎界面被销毁时，清理引用
        """
        self.welcome_screen = None
        
    def on_project_window_closed(self, project_window: ProjectWindow):
        """
        当项目窗口关闭时，从列表中移除
        
        Args:
            project_window: 关闭的项目窗口
        """
        if project_window in self.project_windows:
            self.project_windows.remove(project_window)
            
        # 如果没有打开的项目窗口且欢迎界面也关闭了，则退出应用
        if len(self.project_windows) == 0 and (not self.welcome_screen):
            QApplication.quit()
            
    def closeEvent(self, event):
        """
        主窗口关闭事件处理
        """
        print("closeEvent 被调用")
        # 关闭所有项目窗口
        for window in self.project_windows[:]:  # 使用副本避免在迭代时修改列表
            window.close()
            
        # 关闭欢迎界面
        if self.welcome_screen:
            self.welcome_screen.close()
            
        event.accept()