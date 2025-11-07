import sys
from pathlib import Path

from PyQt5.QtWidgets import QApplication

from src.ui.main_window import MainWindow


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

    # 创建主窗口（会自动创建并显示欢迎界面）
    main_window = MainWindow()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
