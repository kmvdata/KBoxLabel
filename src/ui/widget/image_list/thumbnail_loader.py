import os

from PyQt5.QtCore import (Qt, QRunnable, pyqtSignal,
                          QObject)
from PyQt5.QtGui import (QPixmap, QImage)


class ThumbnailLoaderSignals(QObject):
    """信号容器类"""
    loaded = pyqtSignal(str, QPixmap)  # 发送文件路径和缩略图
    error = pyqtSignal(str, str)  # 发送文件路径和错误信息

class ThumbnailLoader(QRunnable):
    """ 图片加载线程 """

    def __init__(self, file_path, height=16):
        super().__init__()
        self.file_path = file_path
        self.height = height
        self.signals = ThumbnailLoaderSignals()
        self.setAutoDelete(True)
        self.is_canceled = False

        # 基本验证
        if not os.path.exists(file_path):
            self.signals.error.emit(file_path, "文件不存在")  # type: ignore
            return

    def run(self):
        try:
            # 检查是否已取消
            if self.is_canceled:
                return

            # 检查文件有效性
            if not os.path.exists(self.file_path):
                self.signals.error.emit(self.file_path, "文件不存在")  # type: ignore
                return

            # 尝试使用QPixmap直接加载
            pixmap = QPixmap(self.file_path)
            if not pixmap.isNull() and not self.is_canceled:
                # 创建缩略图（保持宽高比）
                thumb = pixmap.scaledToHeight(
                    self.height, Qt.SmoothTransformation
                )
                self.signals.loaded.emit(self.file_path, thumb)  # type: ignore
                return

            # 检查是否已取消
            if self.is_canceled:
                return

            # 使用PIL作为后备方案
            from PIL import Image  # 延迟导入PIL避免重复导入
            pil_img = Image.open(self.file_path)
            width = int(self.height * pil_img.width / pil_img.height)
            pil_img = pil_img.resize((width, self.height), Image.Resampling.LANCZOS)

            # 统一转换为RGB模式
            if pil_img.mode != "RGB":
                pil_img = pil_img.convert("RGB")

            # 转换为QImage
            img_data = pil_img.tobytes("raw", "RGB")
            image = QImage(img_data, width, self.height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(image)

            # 检查是否已取消
            if not self.is_canceled:
                self.signals.loaded.emit(self.file_path, pixmap)  # type: ignore

        except Exception as e:
            if not self.is_canceled:
                self.signals.error.emit(self.file_path, str(e))  # type: ignore

    def cancel(self):
        """取消加载任务"""
        self.is_canceled = True
