import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from src.ui.main_window import MainWindow
from src.ui.welcome_screen import WelcomeScreen


def main():
    app = QApplication(sys.argv)

    # 必须同时设置这两个属性才能在 macOS 正确显示名称
    app.setApplicationName("KBoxLabel")
    app.setApplicationDisplayName("KBoxLabel")  # 关键修复

    # 可选：设置应用程序显示名称（某些系统可能会使用）
    app.setApplicationDisplayName("KBoxLabel Annotation Tool")

    # 其他设置（可选但推荐）
    app.setOrganizationName("kmvdata")

    # 可选：设置域名称（用于设置存储）
    app.setOrganizationDomain("kmvdata.com")

    # 连接项目打开信号到处理函数
    def handle_project_opened(project_path: str):
        print(f"项目已打开: {project_path}")
        # 这里可以创建并显示主窗口
        # main_window = MainWindow(project_path)
        # main_window.show()
        window = MainWindow(Path(project_path))
        window.show()

    # 创建欢迎界面
    welcome = WelcomeScreen()

    welcome.projectOpened.connect(handle_project_opened)

    # 显示欢迎界面
    welcome.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
