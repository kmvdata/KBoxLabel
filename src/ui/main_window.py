# main_window.py
from typing import List
from PyQt5.QtWidgets import QMainWindow, QApplication
from PyQt5.QtCore import pyqtSignal

from src.ui.project_window import ProjectWindow
from src.ui.welcome_screen import WelcomeScreen


class MainWindow(QMainWindow):
    """
    主窗口类，作为隐藏的主控制器管理多个项目窗口
    """
    
    def __init__(self):
        super().__init__()
        # 隐藏主窗口
        self.hide()
        
        # 存储打开的项目窗口列表
        self.project_windows: List[ProjectWindow] = []
        
        # 创建并显示欢迎界面
        self.welcome_screen = WelcomeScreen()
        self.welcome_screen.projectOpened.connect(self.open_project)
        self.welcome_screen.destroyed.connect(self.on_welcome_screen_destroyed)
        self.welcome_screen.show()
        
    def open_project(self, project_path: str):
        """
        打开新项目窗口
        
        Args:
            project_path: 项目路径
        """
        # 创建新的项目窗口
        project_window = ProjectWindow(project_path)
        
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
        # 关闭所有项目窗口
        for window in self.project_windows[:]:  # 使用副本避免在迭代时修改列表
            window.close()
            
        # 关闭欢迎界面
        if self.welcome_screen:
            self.welcome_screen.close()
            
        event.accept()