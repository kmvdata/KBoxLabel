# project_window.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import cast

from PyQt5.QtCore import QThreadPool, QTimer, QItemSelectionModel
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog, QProgressBar
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QSplitter, QLabel, QDialog,
                             QPushButton, QInputDialog, QDialogButtonBox,
                             )  # 新增导入
from PyQt5.QtWidgets import QMessageBox

from src.core.project_info import ProjectInfo
# 在文件顶部导入新创建的对话框
from src.ui.dialog.train_yolo_dialog import TrainYoloDialog
from src.ui.widget.image_canvas.image_canvas import ImageCanvas
from src.ui.widget.image_list.image_list import ImageListView
from src.ui.widget.main_menu_bar import MainMenuBar
from src.core.i18n.language_manager import tr, LanguageManager
from PyQt5.QtCore import pyqtSlot


class ProjectWindow(QMainWindow):

    def __init__(self, project_path: Path):
        super().__init__(parent=None)
        self.left_status = None
        self.image_cache = None
        self.visible_range = (0, 0)
        self.project_info = ProjectInfo(path=project_path)
        self.setGeometry(300, 200, 1000, 600)

        # 将 self (MainWindow) 明确转换为 QWidget 类型
        self.menu_bar = MainMenuBar(cast(QWidget, self))

        # 使用自定义的菜单栏
        self.create_custom_menubar()

        # 创建中央部件和主布局
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(10)

        # ===== 左侧图片列表区 =====
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # 添加图片列表组件
        self.thread_pool = QThreadPool(self)
        self.image_list = ImageListView(self.project_info)
        left_layout.addWidget(self.image_list)


        # ===== 中间图片编辑区域 =====
        # 创建ImageCanvas
        self.image_canvas = ImageCanvas(self.project_info)  # 保存为实例变量，方便后续访问

        # 创建包含工具栏的容器
        canvas_container = QWidget(self)  # 重命名避免与后面变量冲突
        center_layout = QVBoxLayout(canvas_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(0)

        # 添加工具栏
        toolbar = self.image_canvas.create_toolbar()
        center_layout.addWidget(toolbar)

        # 添加图像画布
        center_layout.addWidget(self.image_canvas)
        center_layout.setStretchFactor(self.image_canvas, 1)  # 使画布占满剩余空间

        # ===== 右侧标注列表 =====
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.addWidget(self.image_canvas.annotation_list.toolbar)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # 创建自定义标注列表组件
        right_layout.addWidget(self.image_canvas.annotation_list)

        # ===== 核心修改：使用QSplitter实现可拖拽分隔 =====
        # 创建水平分割器（左右方向），替代原来的QHBoxLayout
        splitter = QSplitter(Qt.Horizontal)
        splitter.setContentsMargins(0, 0, 0, 0)

        # 修正：使用样式表设置分隔器间距，替代setSpacing()
        splitter.setStyleSheet("""
            QSplitter::handle {
                margin: 0 5px;  /* 左右各5px间距，总共10px */
                background-color: #cccccc;
                width: 4px;     /* 分隔器宽度 */
            }
        """)

        # 向分割器添加三个核心区域
        splitter.addWidget(left_widget)  # 左侧图片列表
        splitter.addWidget(canvas_container)  # 中间图片编辑区
        splitter.addWidget(right_widget)  # 右侧标注列表

        # 设置初始大小比例（约1:3:1）
        splitter.setSizes([200, 600, 200])

        # 设置拉伸策略：中间区域优先拉伸
        splitter.setStretchFactor(1, 1)

        # 将分割器添加到主布局
        main_layout.addWidget(splitter)

        # 底部状态栏
        self.create_statusbar()

        # 初始设置窗口标题
        self.setWindowTitle(self.window_title)
        
        # 连接语言变更信号
        LanguageManager.instance().language_changed.connect(self.on_language_changed)
    
    @pyqtSlot(str)
    def on_language_changed(self, language: str):
        """处理语言变更事件"""
        # 更新窗口标题
        self.setWindowTitle(self.window_title)
        
        # 更新状态栏文本
        if hasattr(self, 'left_status') and self.left_status:
            self.left_status.setText(tr("status_ready"))
        
        # 更新菜单栏语言
        if hasattr(self, 'menu_bar'):
            self.menu_bar.update_menu_texts()

        self.set_project_path(self.project_info.path)
        # 确保项目路径有效（强制用户设置）
        self.ensure_project_path()
        self.image_list.sig_canvas_needs_reload.connect(
            self.image_canvas.reload_image
        )

        # 连接选中项变化信号
        self.image_list.sig_selection_changed.connect(self.on_image_list_selection_changed)  # type: ignore
        # self.image_list.selectionModel().selectionChanged.connect(self.on_image_selection_changed)  # type: ignore
        self.image_list.sig_image_clicked.connect(self.image_canvas.load_image)

        # 窗口加载完成后自动选中第一个元素
        QTimer.singleShot(0, self.select_first_image)

    def select_first_image(self):
        """选中图片列表中的第一个元素"""
        model = self.image_list.model
        if model and model.rowCount() > 0:
            # 创建第一个元素的索引
            index = model.index(0, 0)
            if index.isValid():
                # 选中第一个元素 - 使用QItemSelectionModel而非Qt
                self.image_list.selectionModel().select(
                    index,
                    QItemSelectionModel.SelectionFlag.ClearAndSelect
                )

    def on_image_selected(self, file_path: str):
        """实际处理选中图片的逻辑"""
        print(f"图片选中: {file_path}")
        try:
            self.image_canvas.load_image(Path(file_path))
        except (OSError, FileNotFoundError) as e:
            print(f'加载图片异常：{e}')
            self.image_list.load_images_from_path(self.project_info.path)

    class ProjectRequiredDialog(QDialog):
        def __init__(self, main_window: 'ProjectWindow'):
            super().__init__(main_window)
            self.main_window = main_window
            self.setWindowTitle(tr("dialog_title_project_required"))
            self.setModal(True)

            # 创建布局和控件
            layout = QVBoxLayout()
            label = QLabel(tr("dialog_project_required_label"))
            layout.addWidget(label)

            # 操作按钮
            btn_open = QPushButton(tr("dialog_button_open_project"))
            btn_new = QPushButton(tr("menu_new"))
            layout.addWidget(btn_open)
            layout.addWidget(btn_new)

            # 取消按钮
            button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
            layout.addWidget(button_box)

            self.setLayout(layout)

            # 连接信号
            btn_open.clicked.connect(self.open_project)  # type: ignore
            btn_new.clicked.connect(self.new_project)    # type: ignore
            button_box.rejected.connect(self.reject)     # type: ignore

        def open_project(self):
            """处理打开现有工程"""
            path = QFileDialog.getExistingDirectory(
                self, "Select Project Directory"
            )
            if not path:
                return  # 用户取消选择

            try:
                p = Path(path)
                # 验证路径存在且为目录
                if not p.exists() or not p.is_dir():
                    raise FileNotFoundError("Directory does not exist")

                # 通过主窗口方法设置路径（包含验证逻辑）
                self.main_window.set_project_path(p)
                self.accept()  # 关闭对话框
            except (OSError, FileNotFoundError) as e:
                QMessageBox.critical(
                    self, tr("error_invalid_path"),
                    tr("error_invalid_directory")
                )

        def new_project(self):
            """处理创建新工程"""
            path, ok = QInputDialog.getText(
                self, "New Project", "Enter new project directory path:"
            )
            if not ok or not path:
                return  # 用户取消或输入为空

            try:
                p = Path(path).resolve()
                # 尝试创建目录（自动创建父目录）
                p.mkdir(parents=True, exist_ok=True)

                # 二次验证是否为目录
                if not p.is_dir():
                    raise OSError("Path is not a directory")

                # 通过主窗口方法设置路径
                self.main_window.set_project_path(p)
                self.accept()  # 关闭对话框
            except OSError as e:
                QMessageBox.critical(
                    self, tr("error_invalid_path"),
                    tr("error_invalid_path")
                )
            except (ValueError, TypeError) as e:
                QMessageBox.critical(
                    self, tr("error_invalid_path"),
                    tr("error_invalid_path")
                )

    def ensure_project_path(self):
        """强制用户设置有效工程路径，否则保持主窗口禁用状态"""
        # 如果路径已设置，直接返回
        if self.project_info is not None and self.project_info.path.exists():
            return

        # 禁用主窗口所有控件
        self.setDisabled(True)

        # 循环直到获得有效路径
        while not (self.project_info and self.project_info.path.exists()):
            dialog = self.ProjectRequiredDialog(self)
            # 模态对话框阻塞执行，直到用户操作完成
            dialog.exec_()

        # 路径设置成功，启用主窗口
        self.setDisabled(False)

    def create_custom_menubar(self):
        """使用自定义菜单栏"""
        self.setMenuBar(self.menu_bar)

        # 连接菜单栏的信号到本地处理函数
        self.menu_bar.importImagesRequested.connect(self.handle_import_images)  # type line: ignore
        self.menu_bar.closeRequested.connect(self.handle_close_request)  # type: ignore
        self.menu_bar.editActionRequested.connect(self.handle_edit_action)  # type: ignore
        # 连接训练YOLO信号
        self.menu_bar.trainYoloRequested.connect(self.handle_train_yolo)  # type: ignore

    def set_project_path(self, project_path: Path):
        """设置项目路径（包含验证逻辑）"""
        try:
            # 处理字符串路径输入（兼容对话框返回的字符串路径）
            if isinstance(project_path, str):
                project_path = Path(project_path)

            self.project_info.path = project_path

            # 验证路径是否存在
            if not self.project_info.path.exists():
                raise FileNotFoundError(tr("project_invalid"))

            # 更新UI
            self.setWindowTitle(self.window_title)
            self.set_left_status(tr("status_ready"))

            # 加载项目图片
            self.handle_import_images()
            print(f"项目加载成功: {project_path}")
        except (OSError, FileNotFoundError) as e:
            QMessageBox.warning(
                self,
                tr("error_load_project"),
                tr("error_project_path", error=str(e))
            )
            # 确保项目路径为无效状态
            self.project_info = None
            self.setWindowTitle(self.window_title)

    @property
    def window_title(self) -> str:
        """获取窗口标题"""
        if not (self.project_info and self.project_info.path.exists()):
            return tr("project_required_message")

        try:
            if self.project_info.path == self.project_info.path.parent:
                if os.name == 'nt' and len(self.project_info.path.drive) > 0:
                    return f"{self.project_info.path.drive} " + tr("project_root_directory")
                return "/ " + tr("project_root_directory")

            return self.project_info.project_name

        except OSError as e:
            print(f"路径访问错误: {str(e)}")
            return tr("project_loading_failed")

    def on_image_selection_changed(self, selected, deselected):
        """处理图片列表选中项变化"""
        indexes = selected.indexes()
        if indexes:
            # 获取第一个选中的项（单选模式下只有一个）
            index = indexes[0]
            file_path = self.image_list.model.data(index, Qt.UserRole)  # 使用 UserRole 获取路径
            if file_path:
                self.on_image_selected(file_path)

    def handle_close_request(self):
        self.close()

    def handle_edit_action(self):
        print(f"hello world: 菜单点击 {self.project_info.path}")

    def handle_image_click(self, image_path):
        """处理图片点击事件，打印图片路径并更新界面状态"""
        print(f"选中的图片路径: {image_path}")
        self.set_left_status(f"已选择图片: {image_path}")

    def create_statusbar(self):
        """创建底部状态栏"""
        status = self.statusBar()
        status.setStyleSheet("background-color: #f0f0f0; padding: 5px;")

        # 左侧状态
        self.left_status = QLabel(tr("status_ready"))
        self.left_status.setStyleSheet("font-size: 12px;")

        status.addWidget(self.left_status, 1)

    def set_left_status(self, text: str):
        if self.left_status:
            self.left_status.setText(text)

    def on_image_list_selection_changed(self, total_count, selected_count):
        """处理图片列表选择变化，更新状态栏"""
        # 获取当前选中的索引
        current_index = self.image_list.currentIndex()
        
        if selected_count == 1:
            # 只选中一张图片时，显示具体是第几张
            current_row = current_index.row() + 1  # 行号从0开始，所以加1
            status_text = tr("status_selected_image", total=total_count, current=current_row)
        elif selected_count > 1:
            # 选中多张图片时，显示选中数量
            status_text = tr("status_selected_multiple", total=total_count, selected=selected_count)
        else:
            # 未选中任何图片
            status_text = tr("status_no_selection", total=total_count)
        self.set_left_status(status_text)

    def handle_import_images(self):
        """处理图片导入功能"""
        if self.project_info and self.project_info.path.exists():
            # 加载图片到列表
            self.image_list.load_images_from_path(self.project_info.path)

            # 更新状态栏
            count = self.image_list.model.rowCount()
            self.set_left_status(tr("status_loading_images", count=count))
            
            # 自动跳转到最后一个有标注的图片
            QTimer.singleShot(100, self.image_list.jump_to_last_annotated_image)
            
    def closeEvent(self, event):
        """
        重写窗口关闭事件
        """
        # 从父类调用closeEvent确保正常关闭
        super().closeEvent(event)

    def _export_with_progress(self, total_images, process_func, finish_callback=None):
        """
        通用的带进度条的导出函数
        
        Args:
            total_images: 图片总数
            process_func: 处理单个图片的函数，接收(image_path, progress_dialog, i)参数
            finish_callback: 导出完成后的回调函数（可选）
        """
        if not self.project_info.path.exists():
            QMessageBox.warning(self, tr("error_export_failed"), tr("error_get_project_path"))
            return

        try:
            if total_images == 0:
                QMessageBox.information(self, tr("dialog_title_export_progress"), tr("message_no_images_found"))
                return

            # 创建自定义进度对话框
            progress_dialog = QDialog(self)
            progress_dialog.setWindowTitle(tr("dialog_title_export_progress"))
            progress_dialog.setModal(True)
            progress_dialog.resize(400, 150)

            layout = QVBoxLayout()

            # 标签显示正在处理的文件
            file_label = QLabel(tr("dialog_export_label"))
            file_label.setWordWrap(True)
            layout.addWidget(file_label)

            # 进度条
            progress_bar = QProgressBar()
            progress_bar.setRange(0, total_images)
            progress_bar.setValue(0)
            layout.addWidget(progress_bar)

            # 添加进度标签（显示在取消按钮上方，格式如：2/100）
            progress_label = QLabel("0/0")
            progress_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addWidget(progress_label)

            # 取消按钮
            cancel_button = QPushButton(tr("button_cancel"))
            layout.addWidget(cancel_button)

            progress_dialog.setLayout(layout)

            # 变量用于跟踪处理状态
            canceled = False

            # 连接取消按钮
            def cancel_processing():
                nonlocal canceled
                canceled = True
                progress_dialog.close()

            cancel_button.clicked.connect(cancel_processing)  # type: ignore

            # 显示对话框
            progress_dialog.show()

            # 处理每个图片
            for i, image_path in enumerate(self.image_list.model.image_paths):
                image_name = os.path.basename(image_path)

                # 检查是否取消
                if canceled:
                    QMessageBox.information(self, tr("message_import_cancelled"), tr("message_export_cancelled"))
                    return

                # 更新进度对话框
                progress_bar.setValue(i)
                file_label.setText(f"正在导出: {image_name}")
                
                # 更新进度标签
                progress_label.setText(f"{i+1}/{total_images}")

                # 处理事件队列，确保UI更新
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                # 处理单个图片
                try:
                    process_func(image_path, progress_dialog, i)
                except Exception as e:
                    print(f"导出图片 {image_name} 的标注时出错: {str(e)}")
                    # 继续处理其他图片而不是中断整个过程

            # 完成进度
            progress_bar.setValue(total_images)
            progress_label.setText(f"{total_images}/{total_images}")
            
            # 处理事件队列，确保UI更新
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
            
            # 短暂延迟让用户看到完成状态
            from PyQt5.QtCore import QTimer
            loop = QApplication.processEvents
            for _ in range(50):  # 约500ms延迟
                QTimer.singleShot(10, lambda: None)
                loop()
            
            # 关闭进度对话框
            progress_dialog.close()

            # 调用完成回调
            if finish_callback:
                finish_callback(progress_dialog)

        except Exception as e:
            QMessageBox.warning(self, tr("error_export_failed"), tr("error_export_process", error=str(e)))

    def handle_train_yolo(self):
        """处理训练YOLO模型请求"""
        try:
            dialog = TrainYoloDialog(self)
            dialog.exec_()
        except Exception as e:
            QMessageBox.critical(self, tr("error_open_train_dialog"), tr("error_open_train_dialog", error=str(e)))
