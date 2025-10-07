import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import (Qt, QSize, QThreadPool, QRunnable, pyqtSignal,
                          QAbstractListModel, QModelIndex, QObject, QThread)
from PyQt5.QtGui import (QPixmap, QIcon, QImage, QPainter, QFontMetrics)
from PyQt5.QtWidgets import (QListView, QStyledItemDelegate, QStyle,
                             QMenu, QInputDialog, QMessageBox, QDialog, QVBoxLayout,
                             QLabel, QPushButton, QProgressBar)

from src.models.dto.ref_project_info import RefProjectInfo


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


# ====================== 图片列表模型 ======================
class ImageListModel(QAbstractListModel):
    thumbnailLoaded = pyqtSignal(str, QPixmap)

    def __init__(self, parent=None, row_height=36):  # 默认行高36px
        super().__init__(parent)
        self.row_height = row_height
        self.image_paths = []
        self.thumbnail_cache = {}
        self.placeholder_pixmap = self.create_placeholder()
        self.thread_pool = QThreadPool.globalInstance()
        self.thread_pool.setMaxThreadCount(4)

    @staticmethod
    def create_placeholder():
        """创建占位符图像"""
        pixmap = QPixmap(16, 16)  # 默认缩略图尺寸16x16
        pixmap.fill(Qt.lightGray)
        painter = QPainter(pixmap)
        painter.setPen(Qt.darkGray)
        painter.drawRect(0, 0, 15, 15)
        painter.drawLine(0, 0, 15, 15)
        painter.drawLine(15, 0, 0, 15)
        painter.end()
        return pixmap

    def set_row_height(self, height):
        """统一设置行高并刷新视图"""
        self.row_height = height
        # 清除缓存并重置模型
        self.thumbnail_cache.clear()
        self.beginResetModel()
        self.endResetModel()

    def load_images_from_path(self, project_path: Path):
        """从项目路径加载图片"""
        self.beginResetModel()
        self.image_paths = []
        self.thumbnail_cache = {}

        # 获取所有支持的图片文件
        valid_exts = ['.png', '.jpg', '.jpeg', '.bmp', '.gif', '.tif', '.tiff']
        if project_path.exists():
            self.image_paths = sorted([
                str(project_path / f) for f in os.listdir(project_path)
                if os.path.splitext(f)[1].lower() in valid_exts
            ])

        self.endResetModel()

    def rowCount(self, parent=QModelIndex()):
        return len(self.image_paths)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self.image_paths):
            return None

        file_path = self.image_paths[index.row()]
        file_name = os.path.basename(file_path)

        if role == Qt.DisplayRole:
            return file_name
        elif role == Qt.UserRole:
            return file_path
        elif role == Qt.DecorationRole:
            # 如果缩略图已缓存则返回，否则异步加载
            if file_path in self.thumbnail_cache:
                return QIcon(self.thumbnail_cache[file_path])
            else:
                self.load_thumbnail_async(file_path)
                return QIcon(self.placeholder_pixmap)
        return None

    def load_thumbnail_async(self, file_path):
        """异步加载缩略图"""
        if file_path not in self.thumbnail_cache:
            thumb_height = max(16, self.row_height - 20)
            loader = ThumbnailLoader(file_path, thumb_height)
            # 连接信号载体的信号
            loader.signals.loaded.connect(self.handle_thumbnail_loaded)  # type: ignore
            self.thread_pool.start(loader)

    def handle_thumbnail_loaded(self, file_path, pixmap):
        """处理缩略图加载完成"""
        if file_path in self.image_paths:
            self.thumbnail_cache[file_path] = pixmap
            row = self.image_paths.index(file_path)
            index = self.index(row)
            self.dataChanged.emit(index, index, [Qt.DecorationRole])


# ====================== 列表项委托 ======================
class ImageListItemDelegate(QStyledItemDelegate):
    def __init__(self, row_height=36, parent=None):  # 默认行高36px
        super().__init__(parent)
        self.thumbnail_size = None
        self.row_height = None
        self.set_row_height(row_height)

    def set_row_height(self, height):
        """统一设置行高"""
        self.row_height = height
        # 计算缩略图大小（行高-20px）
        thumb_size = max(16, height - 20)
        self.thumbnail_size = QSize(thumb_size, thumb_size)

    def sizeHint(self, option, index):
        """设置固定行高"""
        return QSize(option.rect.width(), self.row_height)

    def paint(self, painter, option, index):
        """自定义绘制列表项"""
        # 保存绘制状态
        painter.save()

        # 绘制选中状态背景
        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
            painter.setPen(option.palette.highlightedText().color())
        else:
            painter.fillRect(option.rect, option.palette.base())
            painter.setPen(option.palette.text().color())

        # 设置缩略图位置（居中）
        thumbnail_rect = option.rect.adjusted(2, (self.row_height - self.thumbnail_size.height()) // 2,
                                              -option.rect.width() + self.thumbnail_size.width() + 2,
                                              -(self.row_height - self.thumbnail_size.height()) // 2)

        # 绘制缩略图
        thumbnail = index.data(Qt.DecorationRole)
        thumbnail.paint(painter, thumbnail_rect, Qt.AlignCenter)


        # 设置文本位置（缩略图右侧）
        text_rect = option.rect.adjusted(
            self.thumbnail_size.width() + 6,
            0,
            -4,
            0
        )

        # 绘制文件名（单行显示，省略过长部分）
        file_name = index.data(Qt.DisplayRole)
        font = painter.font()
        font.setPointSize(8)
        painter.setFont(font)

        # 计算文本显示区域
        text_width = text_rect.width() - 4
        metrics = painter.fontMetrics()
        elided_text = metrics.elidedText(file_name, Qt.ElideRight, text_width)

        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_text)

        # 恢复绘制状态
        painter.restore()


class YoloWorker(QThread):
    """复用的YOLO处理工作线程"""
    finished = pyqtSignal(bool, str, Path)  # 成功标志, 消息, 文件路径
    error = pyqtSignal(str, Path)  # 错误消息, 文件路径
    progress_updated = pyqtSignal(int)  # 进度更新信号 (0-100)

    def __init__(self, input_file_path, project_info: RefProjectInfo):
        super().__init__()
        self.file_path = input_file_path
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
            results = self.project_info.exec_yolo(self.file_path)

            if self.is_canceled:
                return

            if results:
                msg = f"Found {len(results)} objects."
            else:
                msg = "No objects found."

            self.finished.emit(True, msg, self.file_path)

        except Exception as e:
            if not self.is_canceled:
                error_msg = f"{str(e)}"
                self.error.emit(error_msg, self.file_path)

    def cancel(self):
        """取消任务"""
        self.is_canceled = True


# ====================== 图片列表视图 ======================
class ImageListView(QListView):
    sig_image_clicked = pyqtSignal(str)
    sig_canvas_needs_reload = pyqtSignal()  # 发送canvas需要reload的信号
    sig_selection_changed = pyqtSignal(int, int)  # 发送图片总数和当前选中索引信号

    def __init__(self, project_info: RefProjectInfo):
        super().__init__()
        self.project_info = project_info
        self.setSelectionMode(QListView.SingleSelection)
        self.setVerticalScrollMode(QListView.ScrollPerPixel)
        self.setResizeMode(QListView.Adjust)
        self.setUniformItemSizes(True)  # 优化性能

        # 创建模型和委托（使用默认行高56px）
        self.model = ImageListModel(self, row_height=56)
        self.setModel(self.model)
        self.delegate = ImageListItemDelegate(row_height=56)
        self.setItemDelegate(self.delegate)

        # 连接信号
        self.doubleClicked.connect(self.handle_item_clicked)  # type: ignore
        self.selectionModel().selectionChanged.connect(self.on_selection_changed)  # type: ignore

    def set_row_height(self, height):
        """统一设置行高（更新模型和委托）"""
        self.model.set_row_height(height)
        self.delegate.set_row_height(height)
        # 强制视图更新布局
        self.setUniformItemSizes(True)
        self.updateGeometry()
        self.viewport().update()

    def load_images_from_path(self, project_path: Path):
        """从项目路径加载图片"""
        self.model.load_images_from_path(project_path)

    def on_selection_changed(self, selected, deselected):
        """处理选择变化事件"""
        # 获取当前选中索引
        indexes = selected.indexes()
        current_index = indexes[0].row() + 1 if indexes else 0
        
        # 获取总图片数
        total_count = self.model.rowCount()
        
        # 发送信号
        self.sig_selection_changed.emit(total_count, current_index)

    def handle_item_clicked(self, index):
        """处理项点击事件"""
        if index.isValid():
            file_path = self.model.data(index, Qt.UserRole)
            if file_path:
                self.sig_image_clicked.emit(file_path)  # type: ignore

    def contextMenuEvent(self, event):
        """处理右键菜单事件"""
        # 获取当前点击位置的索引（判断是否点击在item上）
        index = self.indexAt(event.pos())
        is_item_clicked = index.isValid()

        # 创建右键菜单
        menu = QMenu(self)
        # 添加原有菜单项
        rename_action = menu.addAction("重命名")
        delete_action = menu.addAction("删除")

        # 添加打开文件夹选项（根据操作系统）
        if sys.platform == 'darwin':  # macOS
            open_action = menu.addAction("在Finder中打开")
        else:  # Windows, Linux
            open_action = menu.addAction("在文件夹中打开")

        # 添加新增的Run和Run All菜单项
        run_action = menu.addAction("Run")
        run_all_action = menu.addAction("Run All")
        
        # 添加新的菜单项
        jump_to_action = menu.addAction("跳转至...")
        smart_jump_action = menu.addAction("智能跳转")

        # 检查模型是否已加载，控制Run相关菜单项的可用性
        model_loaded = self.project_info.is_model_loaded
        run_action.setEnabled(is_item_clicked and model_loaded)
        run_all_action.setEnabled(model_loaded)

        # 根据点击位置设置其他菜单项可用性
        rename_action.setEnabled(is_item_clicked)
        delete_action.setEnabled(is_item_clicked)
        open_action.setEnabled(is_item_clicked)
        
        # 设置新菜单项的可用性
        jump_to_action.setEnabled(True)
        smart_jump_action.setEnabled(self.model.rowCount() > 0)

        # 连接菜单项信号
        rename_action.triggered.connect(lambda: self.rename_selected(index))  # type: ignore
        delete_action.triggered.connect(lambda: self.delete_selected(index))  # type: ignore
        open_action.triggered.connect(lambda: self.open_in_explorer(index))  # type: ignore
        run_action.triggered.connect(lambda: self.on_run_clicked(index))  # type: ignore
        run_all_action.triggered.connect(self.on_run_all_clicked)  # type: ignore
        
        # 连接新菜单项的信号
        jump_to_action.triggered.connect(self.on_jump_to_clicked)  # type: ignore
        smart_jump_action.triggered.connect(self.on_smart_jump_clicked)  # type: ignore

        # 显示菜单
        menu.exec_(self.mapToGlobal(event.pos()))

    def rename_selected(self, index):
        """重命名单个文件"""
        if not index.isValid():
            return

        # 获取当前文件路径
        old_path = self.model.image_paths[index.row()]
        old_name = os.path.basename(old_path)
        name, ext = os.path.splitext(old_name)

        # 弹出输入对话框
        new_name, ok = QInputDialog.getText(
            self,
            "重命名文件",
            "请输入新文件名:",
            text=name
        )

        if ok and new_name:
            # 验证新文件名
            if new_name == name:
                return

            # 检查文件名是否包含非法字符
            invalid_chars = set(r'<>:"/\|?*')
            if any(c in invalid_chars for c in new_name):
                QMessageBox.warning(self, "错误", "文件名包含非法字符！")
                return

            # 构建新路径
            dir_path = os.path.dirname(old_path)
            new_path = os.path.join(dir_path, new_name + ext)

            # 检查新文件是否已存在
            if os.path.exists(new_path):
                QMessageBox.warning(self, "错误", "文件已存在！")
                return

            try:
                # 重命名文件
                os.rename(old_path, new_path)

                # 查找并重命名关联的.txt和.kolo文件
                associated_extensions = ['.txt', '.kolo']
                for assoc_ext in associated_extensions:
                    old_assoc_path = os.path.join(dir_path, name + assoc_ext)
                    new_assoc_path = os.path.join(dir_path, new_name + assoc_ext)

                    # 如果关联文件存在，则重命名
                    if os.path.exists(old_assoc_path):
                        try:
                            os.rename(old_assoc_path, new_assoc_path)
                        except Exception as assoc_e:
                            # 记录错误但继续处理其他文件
                            print(f"重命名关联文件失败 {old_assoc_path}: {str(assoc_e)}")

                # 更新模型数据
                self.model.image_paths[index.row()] = new_path
                self.model.dataChanged.emit(index, index)

                # 更新缩略图缓存
                if old_path in self.model.thumbnail_cache:
                    self.model.thumbnail_cache[new_path] = self.model.thumbnail_cache.pop(old_path)

                # 重命名成功后手动触发选中项变化
                # 获取当前选择模型
                selection_model = self.selectionModel()
                if selection_model:
                    # 清除当前选择
                    selection_model.clearSelection()
                    # 重新选择同一行（因为只是重命名，行位置不变）
                    new_index = self.model.index(index.row(), 0)
                    selection_model.select(new_index, selection_model.Select)

                    # 手动发射selectionChanged信号
                    selection_model.selectionChanged.emit(  # type: ignore
                        selection_model.selection(),
                        selection_model.selection()  # 通常这里传递新旧选择，但这里都传递相同值
                    )

            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")

    def delete_selected(self, index):
        """删除单个文件"""
        if not index.isValid():
            return

        # 获取文件信息
        file_path = self.model.image_paths[index.row()]
        file_name = os.path.basename(file_path)

        # 确认删除
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除 '{file_name}' 吗？\n此操作不可恢复！",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            try:
                # 删除文件
                os.remove(file_path)

                # 从模型中移除
                self.model.beginRemoveRows(QModelIndex(), index.row(), index.row())
                del self.model.image_paths[index.row()]
                self.model.endRemoveRows()

                # 清理缩略图缓存
                if file_path in self.model.thumbnail_cache:
                    del self.model.thumbnail_cache[file_path]

            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def open_in_explorer(self, index):
        """在系统文件管理器中打开文件所在目录并选中文件"""
        if not index.isValid():
            return

        file_path = self.model.data(index, Qt.UserRole)

        try:
            if sys.platform == 'darwin':  # macOS
                # 使用open -R命令在Finder中显示并选中文件
                subprocess.Popen(['open', '-R', file_path])
            elif sys.platform == 'win32':  # Windows
                # Windows中使用explorer /select,可以高亮显示文件
                subprocess.Popen(['explorer', '/select,', file_path])
            else:  # Linux和其他Unix-like系统
                # 尝试使用xdg-open打开目录
                # 注意：大多数Linux桌面环境的xdg-open不支持直接选中文件
                # 但有些环境可以尝试特定命令
                desktop_env = os.environ.get('XDG_CURRENT_DESKTOP', '').lower()

                if 'gnome' in desktop_env or 'ubuntu' in desktop_env:
                    # GNOME桌面环境可以使用nautilus --select
                    try:
                        subprocess.Popen(['nautilus', '--select', file_path])
                        return
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass

                elif 'kde' in desktop_env:
                    # KDE桌面环境可以使用dolphin --select
                    try:
                        subprocess.Popen(['dolphin', '--select', file_path])
                        return
                    except FileNotFoundError:
                        pass
                    except OSError:
                        pass

                # 默认情况下，只打开目录
                subprocess.Popen(['xdg-open', os.path.dirname(file_path)])
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开文件夹失败: {str(e)}")

    def on_run_clicked(self, index):
        """Run菜单项点击事件：处理单个文件"""
        if index.isValid() and self.project_info.is_model_loaded:
            file_path_str = self.model.data(index, Qt.UserRole)
            file_path = Path(file_path_str)
            if file_path:
                print(f"Running single file: {file_path.name}")

                # 创建处理中对话框
                progress_dialog = QDialog(self)
                progress_dialog.setWindowTitle("Processing")
                progress_dialog.setFixedSize(300, 100)
                layout = QVBoxLayout(progress_dialog)

                label = QLabel(f"Processing {file_path.name}...")
                cancel_btn = QPushButton("Cancel")

                layout.addWidget(label)
                layout.addWidget(cancel_btn)
                progress_dialog.setLayout(layout)

                # 创建工作线程，传入project_info
                worker = YoloWorker(file_path, self.project_info)

                # 处理完成回调
                def on_finished(success, msg, file_path):
                    progress_dialog.accept()
                    if success:
                        QMessageBox.information(
                            self, "Success",
                            f"Completed processing {file_path.name}.\n{msg}"
                        )
                        # 刷新canvas
                        self.sig_canvas_needs_reload.emit()

                # 错误处理回调
                def on_error(msg, _file_path):
                    progress_dialog.accept()
                    QMessageBox.critical(
                        self, "Error",
                        f"Error processing {_file_path.name}:\n{msg}"
                    )

                # 取消按钮回调 - 修复核心
                def on_canceled():
                    # 标记worker为取消状态
                    worker.cancel()
                    # 关闭对话框
                    progress_dialog.accept()
                    # 等待worker结束
                    worker.wait()
                    # 显示取消消息
                    QMessageBox.information(self, "Cancelled", "Processing has been cancelled.")

                # 连接信号与槽 - 只连接到on_canceled，避免冲突
                worker.finished.connect(on_finished)
                worker.error.connect(on_error)
                cancel_btn.clicked.connect(on_canceled)

                # 启动工作线程
                worker.start()
                # 显示对话框
                progress_dialog.exec_()

    def on_run_all_clicked(self):
        """Run All菜单项点击事件：处理所有文件"""
        if self.project_info.is_model_loading:
            QMessageBox.warning(self, "Warning", "YOLO model is still loading. Please wait until loading is complete.")
            return
            
        if not self.project_info.is_model_loaded:
            QMessageBox.warning(self, "Warning", "YOLO model not loaded. Please load a model first.")
            return

        all_file_paths = self.model.image_paths
        total_files = len(all_file_paths)

        if total_files == 0:
            QMessageBox.information(self, "Info", "No files to process.")
            return

        print(f"Running all files, total count: {total_files}")

        # 创建总进度对话框
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Processing All")
        progress_dialog.setWindowModality(Qt.WindowModal)
        progress_dialog.setFixedSize(500, 200)

        # 创建主布局
        main_layout = QVBoxLayout(progress_dialog)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)

        # 创建文本显示区域布局
        text_layout = QVBoxLayout()
        text_layout.setSpacing(8)

        # 第一行：正在处理的文件名
        filename_label = QLabel()
        filename_label.setWordWrap(True)
        filename_label.setMinimumHeight(60)
        filename_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        text_layout.addWidget(filename_label)

        # 第二行：处理进度
        progress_text_label = QLabel()
        progress_text_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        text_layout.addWidget(progress_text_label)

        main_layout.addLayout(text_layout)

        # 进度条
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        main_layout.addWidget(progress_bar)
        main_layout.setSpacing(4)

        # 取消按钮
        cancel_btn = QPushButton("Cancel")
        main_layout.addWidget(cancel_btn)

        # 统计信息
        success_count = 0
        error_count = 0
        canceled = False
        current_worker = None  # 跟踪当前正在执行的worker

        # 创建总控线程管理所有文件处理
        class AllFilesController(QThread):
            # 更新信号：当前文件索引, 文件名, 进度文本, 完成百分比
            update_progress = pyqtSignal(int, str, str, int)
            # 完成信号：成功数, 错误数, 是否取消, 已处理数
            processing_complete = pyqtSignal(int, int, bool, int)

            def __init__(self, files, project_info: RefProjectInfo):
                super().__init__()
                self.files = files
                self.project_info = project_info
                self.is_canceled = False

            def run(self):
                success = 0
                error = 0
                total = len(self.files)
                nonlocal current_worker

                for i, file_path_str in enumerate(self.files, 1):
                    if self.is_canceled:
                        break

                    file_path = Path(file_path_str)
                    file_name = file_path.name

                    percentage = int((i / total) * 100) if total > 0 else 0
                    progress_text = f"{i}/{total} files ({percentage}%)"
                    self.update_progress.emit(i, file_name, progress_text, percentage)

                    # 创建并启动工作线程
                    current_worker = YoloWorker(file_path, self.project_info)
                    current_worker.start()

                    # 等待当前文件处理完成或取消
                    while current_worker.isRunning() and not self.is_canceled:
                        current_worker.msleep(100)

                    if self.is_canceled:
                        if current_worker and current_worker.isRunning():
                            current_worker.cancel()
                            current_worker.wait()
                        break

                    # 检查处理结果
                    if current_worker.is_canceled:
                        error += 1
                    else:
                        success += 1

                # 发送最终进度
                final_text = "Finishing up..." if not self.is_canceled else "Canceling..."
                final_percentage = 100 if not self.is_canceled else progress_bar.value()
                self.update_progress.emit(i, "", final_text, final_percentage)
                self.processing_complete.emit(success, error, self.is_canceled, i)

            def cancel(self):
                self.is_canceled = True

        # 创建总控线程
        controller = AllFilesController(all_file_paths, self.project_info)

        # 更新进度条和标签
        def update_progress_bar(index, file_name, text, percentage):
            if file_name:
                metrics = QFontMetrics(filename_label.font())
                max_width = filename_label.width()
                elided_text = metrics.elidedText(file_name, Qt.ElideLeft, max_width)
                filename_label.setText(elided_text)

            progress_text_label.setText(text)
            progress_bar.setValue(percentage)

        # 处理完成
        def on_complete(success, error, is_canceled, processed):
            nonlocal success_count, error_count, canceled
            success_count = success
            error_count = error
            canceled = is_canceled
            progress_bar.setValue(100)
            filename_label.setText("Processing complete!")
            progress_text_label.setText("")
            # 关闭对话框
            progress_dialog.accept()
            # 刷新canvas
            self.sig_canvas_needs_reload.emit()

            # 显示结果统计
            if canceled:
                QMessageBox.information(
                    self, "Cancelled",
                    f"Processing cancelled.\nCompleted {success_count}/{total_files} files."
                )
            else:
                result_msg = (f"Processing complete.\n"
                              f"Total: {total_files}\n"
                              f"Success: {success_count}\n"
                              f"Errors: {error_count}")
                QMessageBox.information(self, "Complete", result_msg)

        # 取消处理 - 修复核心
        def on_cancel():
            if controller.isRunning():
                controller.cancel()
                # 立即取消当前正在执行的任务
                if current_worker and current_worker.isRunning():
                    current_worker.cancel()
                filename_label.setText("Canceling... Please wait.")
                progress_text_label.setText("")

                # 启动一个短延迟来确保线程有时间停止
                QThread.msleep(200)
                # 关闭对话框
                progress_dialog.accept()
                # 等待控制器结束
                controller.wait()
                # 显示取消消息
                QMessageBox.information(self, "Cancelled", "Processing has been cancelled.")

        # 连接信号与槽
        controller.update_progress.connect(update_progress_bar)
        controller.processing_complete.connect(on_complete)
        cancel_btn.clicked.connect(on_cancel)

        # 启动总控线程
        controller.start()
        # 刷新canvas
        self.sig_canvas_needs_reload.emit()
        # 显示进度对话框
        progress_dialog.exec_()

    def on_jump_to_clicked(self):
        """跳转至...菜单项点击事件"""
        if self.model.rowCount() == 0:
            return
            
        # 弹出输入对话框让用户输入要跳转到的图片序号
        max_index = self.model.rowCount()
        jump_to, ok = QInputDialog.getInt(
            self,
            "跳转至...",
            f"请输入图片序号 (1-{max_index}):",
            1, 1, max_index, 1
        )
        
        if ok:
            # 跳转到指定图片（索引从0开始，所以需要减1）
            index = self.model.index(jump_to - 1, 0)
            if index.isValid():
                self.setCurrentIndex(index)
                # 模拟点击事件以加载图片
                self.handle_item_clicked(index)

    def on_smart_jump_clicked(self):
        """智能跳转菜单项点击事件：跳转到第一个没有对应.kolo文件的图片"""
        if self.model.rowCount() == 0:
            return
            
        # 遍历所有图片，查找第一个没有对应.kolo文件的图片
        for i in range(self.model.rowCount()):
            file_path = self.model.image_paths[i]
            # 获取图片文件名（不含扩展名）
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            # 构造对应的.kolo文件路径
            kolo_file_path = os.path.join(os.path.dirname(file_path), file_name + '.kolo')
            
            # 如果.kolo文件不存在，则跳转到该图片
            if not os.path.exists(kolo_file_path):
                index = self.model.index(i, 0)
                if index.isValid():
                    self.setCurrentIndex(index)
                    # 模拟点击事件以加载图片
                    self.handle_item_clicked(index)
                return
                
        # 如果所有图片都有对应的.kolo文件，显示提示信息
        QMessageBox.information(self, "智能跳转", "所有图片都已标注完成，没有找到未标注的图片。")
