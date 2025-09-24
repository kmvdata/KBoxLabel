from PyQt5.QtCore import QSettings


class KSettings(QSettings):
    def __init__(self):
        # 正确初始化父类，使用固定的组织名和应用名
        super().__init__('kmvdata.com', 'KBoxLabel')
