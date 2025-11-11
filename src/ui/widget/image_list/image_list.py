import os
import subprocess
import sys
from pathlib import Path

from PyQt5.QtCore import (Qt, QSize, QThreadPool, pyqtSignal,
                          QAbstractListModel, QModelIndex, QItemSelection, QItemSelectionModel)
from PyQt5.QtGui import (QPixmap, QIcon, QPainter)
from PyQt5.QtWidgets import (QListView, QStyledItemDelegate, QStyle,
                             QMenu, QInputDialog, QMessageBox, QDialog, QVBoxLayout,
                             QLabel, QPushButton, QProgressBar, QApplication)

from src.core.project_info import ProjectInfo
from src.ui.widget.image_list.thumbnail_loader import ThumbnailLoader
from src.ui.widget.image_list.yolo_workder import YoloWorker


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
        elided_text = metrics.elidedText(file_name, Qt.TextElideMode.ElideRight, text_width)

        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, elided_text)

        # 恢复绘制状态
        painter.restore()


# ====================== 图片列表视图 ======================
class ImageListView(QListView):
    sig_image_clicked = pyqtSignal(Path)
    sig_canvas_needs_reload = pyqtSignal()  # 发送canvas需要reload的信号
    sig_selection_changed = pyqtSignal(int, int)  # 发送图片总数和当前选中索引信号

    def __init__(self, project_info: ProjectInfo):
        super().__init__()
        self.project_info = project_info
        self.setSelectionMode(QListView.SelectionMode.ExtendedSelection)  # 改为扩展选择模式
        self.setVerticalScrollMode(QListView.ScrollMode.ScrollPerPixel)
        self.setResizeMode(QListView.ResizeMode.Adjust)
        self.setUniformItemSizes(True)  # 优化性能
        self.last_selected_row = -1  # 记录上次选中的行
        self.current_selection_anchor = -1  # 记录当前选择的锚点

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

    def mousePressEvent(self, event):
        """重写鼠标按下事件以处理Shift键多选"""
        if event.button() == Qt.LeftButton:
            index = self.indexAt(event.pos())
            if index.isValid():
                modifiers = QApplication.keyboardModifiers()
                if modifiers == Qt.ShiftModifier and self.current_selection_anchor != -1:
                    current_row = index.row()
                    selection_model = self.selectionModel()
                    
                    # 使用Toggle模式扩展选择，而不是替换选择
                    selection_model.select(
                        QItemSelection(self.model.index(min(self.current_selection_anchor, current_row), 0),
                                      self.model.index(max(self.current_selection_anchor, current_row), 0)),
                        QItemSelectionModel.SelectionFlag.SelectCurrent | QItemSelectionModel.SelectionFlag.Rows
                    )
                    
                    # 加载最新选中的图片
                    file_path = self.model.data(index, Qt.UserRole)
                    if file_path:
                        self.sig_image_clicked.emit(Path(file_path))  # type: ignore
                    
                    return
                else:
                    # 更新选择锚点
                    self.current_selection_anchor = index.row()
        
        super().mousePressEvent(event)

    def on_selection_changed(self, selected, deselected):
        """处理选择变化事件"""
        # 获取当前选中索引
        indexes = self.selectionModel().selectedIndexes()
        selected_count = len(indexes)
        
        # 获取总图片数
        total_count = self.model.rowCount()
        
        # 发送信号
        self.sig_selection_changed.emit(total_count, selected_count)  # type: ignore
        
        # 如果有选中项，更新最后选中的行和选择锚点
        if indexes:
            self.last_selected_row = indexes[-1].row()
            # 只有在没有按住Shift键时才更新锚点
            modifiers = QApplication.keyboardModifiers()
            if modifiers != Qt.ShiftModifier:
                self.current_selection_anchor = self.last_selected_row
            
            # 加载最新选中的图片
            latest_selected_index = indexes[-1]
            file_path = self.model.data(latest_selected_index, Qt.UserRole)
            if file_path:
                # 运行yolo后会执行此处，保留！
                self.sig_image_clicked.emit(Path(file_path))  # type: ignore

    def handle_item_clicked(self, index):
        """处理项点击事件"""
        if index.isValid():
            # 更新最后选中的行
            self.last_selected_row = index.row()
            
            file_path = self.model.data(index, Qt.UserRole)
            if file_path:
                self.sig_image_clicked.emit(Path(file_path))  # type: ignore

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
        smart_jump_action = menu.addAction("跳转到最后标注")

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
        rename_action.triggered.connect(lambda: self.rename_image_with_index(index))  # type: ignore
        delete_action.triggered.connect(lambda: self.delete_selected())  # type: ignore
        open_action.triggered.connect(lambda: self.open_in_explorer(index))  # type: ignore
        run_action.triggered.connect(lambda: self.on_run_clicked(index))  # type: ignore
        run_all_action.triggered.connect(self.on_run_all_clicked)  # type: ignore
        
        # 连接新菜单项的信号
        jump_to_action.triggered.connect(self.on_jump_to_clicked)  # type: ignore
        smart_jump_action.triggered.connect(self.jump_to_last_annotated_image)  # type: ignore

        # 显示菜单
        menu.exec_(self.mapToGlobal(event.pos()))

    def rename_image_with_index(self, index):
        """重命名单个文件"""
        if not index.isValid():
            return

        # 获取当前文件路径
        old_path = Path(self.model.image_paths[index.row()])
        old_name = old_path.name
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
            new_path = old_path.parent / (new_name + ext)

            # 检查新文件是否已存在
            if new_path.exists():
                QMessageBox.warning(self, "错误", "文件已存在！")
                return

            try:
                # 重命名文件
                os.rename(str(old_path), str(new_path))

                # 更新模型数据
                self.model.image_paths[index.row()] = str(new_path)
                self.model.dataChanged.emit(index, index)

                # 更新缩略图缓存
                if str(old_path) in self.model.thumbnail_cache:
                    self.model.thumbnail_cache[str(new_path)] = self.model.thumbnail_cache.pop(str(old_path))

                # 重命名成功后手动触发选中项变化
                # 获取当前选择模型
                selection_model = self.selectionModel()
                if selection_model:
                    # 清除当前选择
                    selection_model.clearSelection()
                    # 重新选择同一行（因为只是重命名，行位置不变）
                    new_index = self.model.index(index.row(), 0)
                    selection_model.select(new_index, QItemSelectionModel.SelectionFlag.Select)

                    # 手动发射selectionChanged信号
                    selection_model.selectionChanged.emit(  # type: ignore
                        selection_model.selection(),
                        selection_model.selection()  # 通常这里传递新旧选择，但这里都传递相同值
                    )
                self.project_info.domain.rename_image_for_kolo_item(old_path, new_path)

            except Exception as e:
                QMessageBox.critical(self, "错误", f"重命名失败: {str(e)}")

    def delete_selected(self):
        """删除文件（支持多选删除）"""
        # 获取所有选中的索引
        selected_indexes = self.selectionModel().selectedIndexes()
        
        # 如果没有选中项，直接返回
        if not selected_indexes:
            return
            
        # 获取要删除的文件信息
        files_to_delete = []
        for idx in selected_indexes:
            if idx.isValid():
                file_path = self.model.image_paths[idx.row()]
                file_name = os.path.basename(file_path)
                files_to_delete.append((idx.row(), file_path, file_name))
                
        # 如果没有有效文件，直接返回
        if not files_to_delete:
            return
            
        # 确认删除
        if len(files_to_delete) == 1:
            # 单个文件删除确认
            file_name = files_to_delete[0][2]
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除 '{file_name}' 吗？\n此操作不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
        else:
            # 多个文件删除确认
            reply = QMessageBox.question(
                self,
                "确认删除",
                f"确定要删除选中的 {len(files_to_delete)} 个文件吗？\n此操作不可恢复！",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
        if reply == QMessageBox.Yes:
            try:
                # 对选中项按行号排序
                files_to_delete.sort(key=lambda x: x[0])
                
                # 计算要选中的项
                next_index = None
                prev_index = None
                
                # 优先选择最下面一项的下一项
                last_row = files_to_delete[-1][0]  # 最下面一项的行号
                if last_row + 1 < self.model.rowCount():
                    next_index = self.model.index(last_row + 1, 0)
                
                # 如果下一项不存在，则选择最上面一项的前一项
                if next_index is None:
                    first_row = files_to_delete[0][0]  # 最上面一项的行号
                    if first_row > 0:
                        prev_index = self.model.index(first_row - 1, 0)
                
                # 执行选择操作
                if next_index is not None:
                    # 选择下一项
                    self.setCurrentIndex(next_index)
                    self.handle_item_clicked(next_index)
                elif prev_index is not None:
                    # 选择前一项
                    self.setCurrentIndex(prev_index)
                    self.handle_item_clicked(prev_index)
                else:
                    # 没有可选项，清空画布
                    self.sig_canvas_needs_reload.emit() # type: ignore
                
                # 按行号降序排列，从后往前删除，避免索引变化问题
                files_to_delete.sort(key=lambda x: x[0], reverse=True)
                
                # 记录删除成功的文件和失败的文件
                success_count = 0
                failed_files = []
                
                for row, file_path, file_name in files_to_delete:
                    try:
                        # 删除文件
                        os.remove(file_path)
                        success_count += 1
                    except Exception as e:
                        failed_files.append((file_name, str(e)))
                        
                # 从模型中批量移除（需要处理索引变化）
                for row, file_path, file_name in files_to_delete:
                    # 从数据库中删除相关的kolo item项
                    self.project_info.domain.delete_kolo_item_for_image(file_name)
                    
                    # 从模型中移除
                    self.model.beginRemoveRows(QModelIndex(), row, row)
                    del self.model.image_paths[row]
                    self.model.endRemoveRows()
                    
                    # 清理缩略图缓存
                    if file_path in self.model.thumbnail_cache:
                        del self.model.thumbnail_cache[file_path]
                        
                # 显示结果信息
                if failed_files:
                    error_msg = f"成功删除 {success_count} 个文件。\n\n以下文件删除失败：\n"
                    for file_name, error in failed_files[:5]:  # 只显示前5个错误
                        error_msg += f"{file_name}: {error}\n"
                    if len(failed_files) > 5:
                        error_msg += f"... 还有 {len(failed_files) - 5} 个文件删除失败\n"
                    QMessageBox.warning(self, "删除完成", error_msg)
                elif len(files_to_delete) > 1:
                    QMessageBox.information(self, "删除完成", f"成功删除 {success_count} 个文件。")

            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除过程中发生错误: {str(e)}")

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

    def jump_to_last_annotated_image(self):
        """跳转到最后一个有标注的图片的通用方法
        """
        if self.model.rowCount() == 0:
            return

        try:
            # 定义查询函数，获取按ID排序的最后一个KoloItem
            def query_func(session):
                from src.common.domain.models.kolo_item import KoloItem
                return session.query(KoloItem).order_by(KoloItem.id.desc()).first()

            # 执行查询
            last_kolo_item = self.project_info.domain.execute_in_transaction(query_func)

            # 如果没有找到任何KoloItem，根据参数决定是否显示提示信息
            if not last_kolo_item:
                QMessageBox.information(self, "智能跳转", "数据库中没有找到任何标注记录。")
                return

            # 获取最后一个KoloItem对应的图片名称
            target_image_name = last_kolo_item.image_name

            # 遍历所有图片，查找对应的图片文件
            for i in range(self.model.rowCount()):
                file_path = self.model.image_paths[i]
                # 获取图片文件名
                image_file_name = os.path.basename(file_path)

                # 如果图片文件名匹配，则跳转到该图片
                if image_file_name == target_image_name:
                    index = self.model.index(i, 0)
                    if index.isValid():
                        self.setCurrentIndex(index)
                        # 模拟点击事件以加载图片
                        self.handle_item_clicked(index)
                    return

            # 如果没有找到对应的图片文件，根据参数决定是否显示提示信息
            QMessageBox.information(self, "智能跳转", f"未找到与最后一条标注记录关联的图片文件: {target_image_name}")

        except Exception as e:
            print(f"跳转到最后标注图片时出错: {e}")
            # 根据参数决定是否显示错误提示
            QMessageBox.warning(self, "错误", f"跳转时发生错误: {str(e)}")

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

    def on_run_clicked(self, index):
        """处理用户选中的一个或多个文件，使用YOLO模型对这些文件进行处理"""
        # 检查模型是否已加载
        if not self.project_info.is_model_loaded:
            QMessageBox.warning(self, "警告", "模型未加载，请先加载YOLO模型。")
            return

        # 获取当前选中的所有文件索引
        selected_indexes = self.selectionModel().selectedIndexes()
        
        # 如果没有选中项则直接返回
        if not selected_indexes:
            return

        # 确定要处理的文件列表
        # 如果只选中一项且传入的index有效，则只处理该index对应的文件
        # 如果选中多项，则处理所有选中的文件
        indexes_to_process = []
        if len(selected_indexes) == 1 and index.isValid():
            indexes_to_process = [index]
        else:
            indexes_to_process = selected_indexes

        # 创建进度对话框显示处理状态
        progress_dialog = QDialog(self)
        progress_dialog.setWindowTitle("Processing")
        progress_dialog.setModal(True)
        progress_dialog.resize(400, 150)

        layout = QVBoxLayout()

        file_label = QLabel("正在处理: ")
        file_label.setWordWrap(True)
        layout.addWidget(file_label)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, len(indexes_to_process))
        progress_bar.setValue(0)
        layout.addWidget(progress_bar)

        # 添加进度标签（显示在取消按钮上方）
        progress_label = QLabel("")
        progress_label.setAlignment(Qt.AlignRight)
        layout.addWidget(progress_label)

        cancel_button = QPushButton("Cancel")
        layout.addWidget(cancel_button)

        progress_dialog.setLayout(layout)

        # 变量用于跟踪处理状态
        processed_count = 0
        success_count = 0
        error_count = 0
        total_count = len(indexes_to_process)
        errors = []
        canceled = False

        # 连接取消按钮
        def cancel_processing():
            nonlocal canceled
            canceled = True
            progress_dialog.close()

        cancel_button.clicked.connect(cancel_processing)

        # 显示对话框
        progress_dialog.show()

        # 处理每个文件
        for i, idx in enumerate(indexes_to_process):
            if canceled:
                break

            # 获取文件路径
            file_path = self.model.data(idx, Qt.UserRole)
            if not file_path:
                continue

            # 更新UI显示当前处理的文件
            file_label.setText(f"正在处理: {os.path.basename(file_path)}")
            progress_bar.setValue(i)
            
            # 更新进度标签（格式：当前处理项/总数量）
            progress_label.setText(f"{i+1}/{total_count}")
            
            QApplication.processEvents()  # 保持UI响应

            # 创建YoloWorker工作线程进行处理
            worker = YoloWorker(file_path, self.project_info)

            # 标记是否已完成处理
            worker_finished = False
            worker_error = False
            worker_result_msg = ""
            
            # 连接信号
            def on_worker_finished(success, msg, path):
                nonlocal worker_finished, worker_error, success_count, error_count, worker_result_msg
                worker_finished = True
                if success:
                    success_count += 1
                    worker_result_msg = msg
                else:
                    error_count += 1
                    worker_result_msg = msg
                    errors.append(f"{os.path.basename(path)}: {msg}")

            def on_worker_error(error_msg, path):
                nonlocal worker_finished, worker_error, error_count, worker_result_msg
                worker_finished = True
                worker_error = True
                error_count += 1
                worker_result_msg = error_msg
                errors.append(f"{os.path.basename(path)}: {error_msg}")

            worker.finished.connect(on_worker_finished)
            worker.error.connect(on_worker_error)

            # 启动工作线程
            worker.start()

            # 等待当前工作线程完成
            while not worker_finished and not canceled:
                QApplication.processEvents()

        # 更新进度条到最后
        progress_bar.setValue(len(indexes_to_process) if not canceled else processed_count)
        # 更新进度标签为最终状态
        if not canceled:
            progress_label.setText(f"{total_count}/{total_count}")
        QApplication.processEvents()

        # 隐藏并销毁进度对话框
        progress_dialog.close()

        # 处理完成后发送信号刷新canvas
        self.sig_canvas_needs_reload.emit() # type: ignore

        # 显示统计信息对话框
        if not canceled:
            msg = f"处理完成\n\n总数: {total_count}\n成功: {success_count}\n错误: {error_count}"
            if errors:
                msg += "\n\n错误详情:\n" + "\n".join(errors[:5])  # 只显示前5个错误
                if len(errors) > 5:
                    msg += f"\n... 还有 {len(errors) - 5} 个错误"
            QMessageBox.information(self, "处理结果", msg)
        else:
            msg = f"处理被用户取消\n\n已处理: {processed_count}\n成功: {success_count}\n错误: {error_count}"
            QMessageBox.information(self, "处理结果", msg)

    def on_run_all_clicked(self):
        """处理项目中的所有文件，使用YOLO模型对所有文件进行批量处理"""
        # 检查模型是否已加载
        if not self.project_info.is_model_loaded:
            QMessageBox.warning(self, "警告", "模型未加载，请先加载YOLO模型。")
            return

        # 检查是否存在可处理的文件
        if self.model.rowCount() == 0:
            QMessageBox.information(self, "提示", "没有可处理的文件。")
            return

        # 清除当前选择并选中所有文件索引
        self.selectAll()
        
        # 直接调用on_run_clicked处理所有选中文件
        # 创建一个无效的QModelIndex作为参数
        self.on_run_clicked(QModelIndex())