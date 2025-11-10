from pathlib import Path

from PyQt5.QtCore import (pyqtSignal,
                          QThread)

from src.models.dto.ref_project_info import RefProjectInfo


class YoloWorker(QThread):
    """复用的YOLO处理工作线程"""
    finished = pyqtSignal(bool, str, Path)  # 成功标志, 消息, 文件路径
    error = pyqtSignal(str, Path)  # 错误消息, 文件路径
    progress_updated = pyqtSignal(int)  # 进度更新信号 (0-100)

    def __init__(self, input_file_path: str|Path, project_info: RefProjectInfo):
        super().__init__()
        self.file_path: Path = Path(input_file_path)
        self.project_info = project_info  # 保存RefProjectInfo实例
        self.is_canceled = False

    def run(self):
        try:
            if self.is_canceled:
                return

            # 检查模型是否已加载
            if not self.project_info.is_model_loaded:
                raise Exception("YOLO model not loaded")

            # 使用project_info中的exec_yolo方法进行推理
            results = self.project_info.exec_yolo(self.file_path, save_to_db=True)

            if self.is_canceled:
                return

            if results:
                msg = f"Found {len(results)} objects."
            else:
                msg = "No objects found."

            self.finished.emit(True, msg, self.file_path) # type: ignore

        except Exception as e:
            if not self.is_canceled:
                error_msg = f"{str(e)}"
                self.error.emit(error_msg, str(self.file_path))  # type: ignore

    def cancel(self):
        """取消任务"""
        self.is_canceled = True

