from PyQt5.QtCore import QSettings


class KSettings(QSettings):
    def __init__(self):
        # 正确初始化父类，使用固定的组织名和应用名
        super().__init__('kmvdata.com', 'KBoxLabel')

    def get_last_opened_directory(self) -> str:
        """获取最近一次打开的目录路径"""
        return self.value("lastOpenedDirectory", "", type=str)

    def set_last_opened_directory(self, directory: str) -> None:
        """设置最近一次打开的目录路径"""
        self.setValue("lastOpenedDirectory", directory)
        self.sync()
