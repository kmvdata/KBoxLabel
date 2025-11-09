# project_window.py
import json
import os
from datetime import datetime
from pathlib import Path
from typing import cast

from PyQt5.QtCore import QThreadPool, QTimer, QItemSelectionModel
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QFileDialog
from PyQt5.QtWidgets import (QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
                             QSplitter, QLabel, QDialog,
                             QPushButton, QInputDialog, QDialogButtonBox,
                             )  # 新增导入
from PyQt5.QtWidgets import QProgressDialog, QMessageBox

from src.models.dto.ref_project_info import RefProjectInfo
from src.models.sql.kolo_item import KoloItem
from src.ui.widget.image_canvas.image_canvas import ImageCanvas
from src.ui.widget.image_list import ImageListView
from src.ui.widget.main_menu_bar import MainMenuBar


class ProjectWindow(QMainWindow):

    def __init__(self, project_path: Path):
        super().__init__(parent=None)
        self.left_status = None
        self.image_cache = None
        self.visible_range = (0, 0)
        self.project_info = RefProjectInfo(path=project_path)
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
        # 连接选中项变化信号
        self.image_list.sig_selection_changed.connect(self.on_image_list_selection_changed)  # type: ignore
        self.image_list.selectionModel().selectionChanged.connect(self.on_image_selection_changed)  # type: ignore

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

        self.set_project_path(project_path)
        # 确保项目路径有效（强制用户设置）
        self.ensure_project_path()
        self.image_list.sig_canvas_needs_reload.connect(
            self.image_canvas.reload_image
        )

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
        print(f"✅ 图片选中: {file_path}")
        try:
            self.image_canvas.load_image(Path(file_path))
        except (OSError, FileNotFoundError) as e:
            print(f'加载图片异常：{e}')
            self.image_list.load_images_from_path(self.project_info.path)

    class ProjectRequiredDialog(QDialog):
        def __init__(self, main_window: 'ProjectWindow'):
            super().__init__(main_window)
            self.main_window = main_window
            self.setWindowTitle("Project Required")
            self.setModal(True)

            # 创建布局和控件
            layout = QVBoxLayout()
            label = QLabel("Please open or create a project:")
            layout.addWidget(label)

            # 操作按钮
            btn_open = QPushButton("Open Project")
            btn_new = QPushButton("New Project")
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
                    self, "Error",
                    "Invalid path: Directory does not exist."
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
                self.main_window.set_project_path(str(p))
                self.accept()  # 关闭对话框
            except OSError as e:
                QMessageBox.critical(
                    self, "Error",
                    "Invalid path: Check directory name or permissions."
                )
            except (ValueError, TypeError) as e:
                QMessageBox.critical(
                    self, "Error",
                    "Invalid path: Check directory name or permissions."
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
        self.menu_bar.importImagesRequested.connect(self.handle_import_images)  # type: ignore
        self.menu_bar.exportToYoloRequested.connect(self.export_project_to_yolo)  # type: ignore
        self.menu_bar.exportToCocoRequested.connect(self.export_project_to_coco)  # type: ignore
        self.menu_bar.closeRequested.connect(self.handle_close_request)  # type: ignore
        self.menu_bar.editActionRequested.connect(self.handle_edit_action)  # type: ignore

    def set_project_path(self, project_path: Path):
        """设置项目路径（包含验证逻辑）"""
        try:
            # 处理字符串路径输入（兼容对话框返回的字符串路径）
            if isinstance(project_path, str):
                project_path = Path(project_path)

            self.project_info.path = project_path

            # 验证路径是否存在
            if not self.project_info.path.exists():
                raise FileNotFoundError(f"项目目录不存在: {project_path}")

            # 更新UI
            self.setWindowTitle(self.window_title)
            self.statusBar().showMessage(f"已打开项目: {project_path}", 5000)

            # 加载项目图片
            self.handle_import_images()
            print(f"项目加载成功: {project_path}")
        except (OSError, FileNotFoundError) as e:
            QMessageBox.warning(
                self,
                "打开项目失败",
                f"无法打开项目: {str(e)}"
            )
            # 确保项目路径为无效状态
            self.project_info = None
            self.setWindowTitle(self.window_title)

    @property
    def window_title(self) -> str:
        """获取窗口标题"""
        if not (self.project_info and self.project_info.path.exists()):
            return "请先打开或新建工程"

        try:
            if self.project_info.path == self.project_info.path.parent:
                if os.name == 'nt' and len(self.project_info.path.drive) > 0:
                    return f"{self.project_info.path.drive} 根目录"
                return "/ 根目录"

            return self.project_info.project_name

        except OSError as e:
            print(f"路径访问错误: {str(e)}")
            return "工程加载失败"

    def on_image_selection_changed(self, selected, deselected):
        """处理图片列表选中项变化"""
        indexes = selected.indexes()
        if indexes:
            # 获取第一个选中的项（单选模式下只有一个）
            index = indexes[0]
            file_path = self.image_list.model.data(index, Qt.UserRole)  # 使用 UserRole 获取路径
            if file_path:
                self.on_image_selected(file_path)

    def export_project_to_yolo(self):
        """
        从数据库读取所有kolo_item对象，转换为YOLO格式，显示进度条和取消按钮
        """
        # 检查项目路径是否存在
        if not self.project_info.path.exists():
            QMessageBox.warning(self, "导出失败", "项目路径不存在")
            return

        # 创建数据库会话
        session = self.project_info.sqlite_db.db_session()
        
        try:
            # 获取总记录数用于进度条
            total_items = session.query(KoloItem).count()
            
            if total_items == 0:
                QMessageBox.information(self, "导出完成", "未找到任何标注数据")
                return

            # 创建进度对话框
            progress_dialog = QProgressDialog("正在导出标注数据...", "取消", 0, total_items, self)
            progress_dialog.setWindowTitle("导出进度")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setAutoClose(True)

            # 创建类别名称到ID的映射
            class_name_to_id = {category.class_name: category.class_id for category in self.project_info.categories}
            
            # 按image_name分组查询，避免一次性加载所有数据到内存
            image_names = session.query(KoloItem.image_name).distinct().all()
            image_names = [name[0] for name in image_names]
            
            # 处理每个图片的标注数据
            processed_count = 0
            for i, image_name in enumerate(image_names):
                # 检查是否取消
                if progress_dialog.wasCanceled():
                    QMessageBox.information(self, "导出中止", "用户取消了导出操作")
                    return

                # 更新进度对话框
                progress_dialog.setValue(processed_count)
                progress_dialog.setLabelText(f"正在导出: {image_name}")

                # 处理事件队列，确保UI更新
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                # 构造输出文件路径（同名的txt文件）
                txt_path = self.project_info.path / f"{Path(image_name).stem}.txt"
                
                try:
                    # 查询该图片的所有标注
                    kolo_items = session.query(KoloItem).filter(KoloItem.image_name == image_name).all()
                    
                    # 写入YOLO格式的txt文件
                    with open(txt_path, 'w', encoding='utf-8') as txt_file:
                        for item in kolo_items:
                            # 获取类别ID
                            class_id = class_name_to_id.get(item.class_name, -1)
                            if class_id == -1:
                                print(f"警告: 未找到类别 '{item.class_name}' 的ID，跳过该标注")
                                continue

                            # 写入YOLO格式: class_id x_center y_center width height
                            yolo_line = f"{class_id} {item.x_center} {item.y_center} {item.width} {item.height}\n"
                            txt_file.write(yolo_line)
                            
                    processed_count += len(kolo_items)
                    
                except Exception as e:
                    print(f"导出图片 {image_name} 的标注时出错: {str(e)}")
                    # 继续处理其他图片而不是中断整个过程

            # 完成进度
            progress_dialog.setValue(total_items)
            QMessageBox.information(self, "导出完成", f"成功导出 {len(image_names)} 个文件，共 {processed_count} 条标注")

        finally:
            session.close()

    def export_project_to_coco(self):
        """
        从数据库读取所有kolo_item对象，转换为COCO格式，显示进度条和取消按钮
        """


        # 检查项目路径是否存在
        if not self.project_info.path.exists():
            QMessageBox.warning(self, "导出失败", "项目路径不存在")
            return

        # 创建数据库会话
        session = self.project_info.sqlite_db.db_session()
        
        try:
            # 获取总记录数用于进度条
            total_items = session.query(KoloItem).count()
            
            if total_items == 0:
                QMessageBox.information(self, "导出完成", "未找到任何标注数据")
                return

            # 选择输出目录
            output_dir = QFileDialog.getExistingDirectory(self, "选择COCO数据导出目录", str(self.project_info.path))
            if not output_dir:
                return

            output_path = Path(output_dir)

            # 创建进度对话框
            progress_dialog = QProgressDialog("正在导出标注数据...", "取消", 0, total_items + 1, self)
            progress_dialog.setWindowTitle("导出进度")
            progress_dialog.setWindowModality(Qt.WindowModal)
            progress_dialog.setMinimumDuration(0)
            progress_dialog.setAutoClose(True)

            # 准备COCO数据结构
            coco_data = {
                "info": {
                    "year": datetime.now().year,
                    "version": "1.0",
                    "description": "KBoxLabel COCO format dataset",
                    "contributor": "KBoxLabel",
                    "url": "",
                    "date_created": datetime.now().strftime("%Y/%m/%d")
                },
                "licenses": [{
                    "id": 1,
                    "name": "Unknown",
                    "url": ""
                }],
                "images": [],
                "annotations": [],
                "categories": []
            }

            # 添加类别信息
            for category in self.project_info.categories:
                coco_data["categories"].append({
                    "id": category.class_id,
                    "name": category.class_name,
                    "supercategory": ""
                })

            # 创建类别名称到ID的映射
            class_name_to_id = {category.class_name: category.class_id for category in self.project_info.categories}

            # 按image_name分组查询，避免一次性加载所有数据到内存
            image_names = session.query(KoloItem.image_name).distinct().all()
            image_names = [name[0] for name in image_names]
            
            # 创建image_name到id的映射
            image_name_to_id = {}
            for i, image_name in enumerate(image_names):
                image_name_to_id[image_name] = i + 1
                # 添加图像信息到COCO数据
                coco_data["images"].append({
                    "id": i + 1,
                    "width": 0,  # 需要实际图像尺寸
                    "height": 0,  # 需要实际图像尺寸
                    "file_name": image_name,
                    "license": 1,
                    "flickr_url": "",
                    "coco_url": "",
                    "date_captured": ""
                })

            annotation_id = 1
            processed_count = 0

            # 分批处理每个图片的标注数据，提高大数据量时的处理效率
            for i, image_name in enumerate(image_names):
                # 检查是否取消
                if progress_dialog.wasCanceled():
                    QMessageBox.information(self, "导出中止", "用户取消了导出操作")
                    return

                # 更新进度对话框
                progress_dialog.setValue(processed_count)
                progress_dialog.setLabelText(f"正在导出: {image_name}")

                # 处理事件队列，确保UI更新
                from PyQt5.QtWidgets import QApplication
                QApplication.processEvents()

                try:
                    # 分批查询该图片的所有标注，避免一次性加载过多数据
                    batch_size = 1000
                    offset = 0
                    while True:
                        kolo_items = session.query(KoloItem).filter(
                            KoloItem.image_name == image_name
                        ).offset(offset).limit(batch_size).all()
                        
                        if not kolo_items:
                            break
                        
                        # 处理每批数据
                        for item in kolo_items:
                            # 获取类别ID
                            class_id = class_name_to_id.get(item.class_name, -1)
                            if class_id == -1:
                                print(f"警告: 未找到类别 '{item.class_name}' 的ID，跳过该标注")
                                continue

                            # 转换为COCO格式的边界框 [x, y, width, height]
                            # x, y 是边界框左上角坐标
                            x = float(item.x_center) - float(item.width) / 2
                            y = float(item.y_center) - float(item.height) / 2

                            # 添加注解信息
                            coco_data["annotations"].append({
                                "id": annotation_id,
                                "image_id": image_name_to_id[image_name],
                                "category_id": class_id,
                                "bbox": [x, y, float(item.width), float(item.height)],
                                "area": float(item.width) * float(item.height),
                                "segmentation": [],
                                "iscrowd": 0
                            })

                            annotation_id += 1
                            processed_count += 1
                            
                        offset += batch_size
                        
                except Exception as e:
                    print(f"导出图片 {image_name} 的标注时出错: {str(e)}")
                    # 继续处理其他图片而不是中断整个过程

            # 完成进度
            progress_dialog.setValue(total_items)
            progress_dialog.setLabelText("正在保存COCO文件...")

            # 写入COCO格式的JSON文件
            coco_json_path = output_path / "annotations.json"
            try:
                with open(coco_json_path, 'w', encoding='utf-8') as f:
                    json.dump(coco_data, f, indent=2, ensure_ascii=False)
            except (OSError, FileNotFoundError) as e:
                QMessageBox.warning(self, "导出失败", f"保存COCO文件时出错: {str(e)}")
                return

            progress_dialog.setValue(total_items + 1)
            QMessageBox.information(self, "导出完成", f"成功导出COCO格式数据到: {output_path}，共处理 {processed_count} 条标注")

        finally:
            session.close()

    def export_to_coco(self, kolo_path: Path):
        """
        将单个kolo文件转换为COCO格式（用于单个文件处理）
        """
        # 检查kolo文件是否存在
        if not kolo_path.exists():
            print(f"Kolo文件不存在: {kolo_path}")
            return

        # 构造输出文件路径（同目录下同名的json文件）
        json_path = kolo_path.with_suffix('.json')

        # 创建类别名称到ID的映射
        class_name_to_id = {category.class_name: category.class_id for category in self.project_info.categories}

        # 准备COCO数据结构
        coco_data = {
            "images": [],
            "annotations": [],
            "categories": []
        }

        # 添加类别信息
        for category in self.project_info.categories:
            coco_data["categories"].append({
                "id": category.class_id,
                "name": category.class_name,
                "supercategory": ""
            })

        # 获取图像文件名（假设与kolo文件同名）
        image_file = kolo_path.with_suffix('.jpg')
        if not image_file.exists():
            image_file = kolo_path.with_suffix('.png')
        if not image_file.exists():
            image_file = kolo_path.with_suffix('.jpeg')

        # 添加图像信息
        coco_data["images"].append({
            "id": 1,
            "width": 0,  # 需要实际图像尺寸
            "height": 0,  # 需要实际图像尺寸
            "file_name": image_file.name,
            "license": 1,
            "flickr_url": "",
            "coco_url": "",
            "date_captured": ""
        })

        annotation_id = 1

        try:
            # 读取kolo文件
            with open(kolo_path, 'r', encoding='utf-8') as kolo_file:
                lines = kolo_file.readlines()

            # 处理每一行
            for line in lines:
                parts = line.strip().split()
                if len(parts) < 5:
                    continue

                # 解析kolo格式的各个部分
                base64_class_name = parts[0]
                x_center = float(parts[1])
                y_center = float(parts[2])
                width = float(parts[3])
                height = float(parts[4])

                # 将Base64编码的类别名称解码为原始名称
                from src.core.utils.string_util import StringUtil
                class_name = StringUtil.base64_to_string(base64_class_name)

                # 获取类别ID
                class_id = class_name_to_id.get(class_name, -1)
                if class_id == -1:
                    print(f"警告: 未找到类别 '{class_name}' 的ID，跳过该标注")
                    continue

                # 转换为COCO格式的边界框 [x, y, width, height]
                # x, y 是边界框左上角坐标
                x = x_center - width / 2
                y = y_center - height / 2

                # 添加注解信息
                coco_data["annotations"].append({
                    "id": annotation_id,
                    "image_id": 1,
                    "category_id": class_id,
                    "bbox": [x, y, width, height],
                    "area": width * height,
                    "segmentation": [],
                    "iscrowd": 0
                })

                annotation_id += 1

            # 写入COCO格式的JSON文件
            with open(json_path, 'w', encoding='utf-8') as json_file:
                json.dump(coco_data, json_file, indent=2, ensure_ascii=False)

            print(f"成功导出COCO格式文件: {json_path}")

        except (OSError, FileNotFoundError, ValueError, TypeError) as e:
            print(f"导出COCO格式时出错: {str(e)}")
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "导出失败", f"导出COCO格式时出错: {str(e)}")

    def handle_close_request(self):
        self.close()

    def handle_edit_action(self):
        print(f"hello world: 菜单点击 {self.project_info.path}")

    def handle_image_click(self, image_path):
        """处理图片点击事件，打印图片路径并更新界面状态"""
        print(f"选中的图片路径: {image_path}")
        self.statusBar().showMessage(f"已选择图片: {image_path}")

    def create_statusbar(self):
        """创建底部状态栏"""
        status = self.statusBar()
        status.setStyleSheet("background-color: #f0f0f0; padding: 5px;")

        # 左侧状态
        self.left_status = QLabel("状态1: 准备就绪")
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
            status_text = f"共加载 {total_count} 张图片，当前选中第 {current_row} 张"
        elif selected_count > 1:
            # 选中多张图片时，显示选中数量
            status_text = f"共加载 {total_count} 张图片，当前选中 {selected_count} 张"
        else:
            # 未选中任何图片
            status_text = f"共加载 {total_count} 张图片，未选中任何图片"
        self.statusBar().showMessage(status_text)

    def handle_import_images(self):
        """处理图片导入功能"""
        if self.project_info and self.project_info.path.exists():
            # 加载图片到列表
            self.image_list.load_images_from_path(self.project_info.path)

            # 更新状态栏
            count = self.image_list.model.rowCount()
            self.statusBar().showMessage(f"已加载 {count} 张图片", 3000)
            self.set_left_status(f"已加载 {count} 张图片")
            
            # 自动跳转到最后一个有标注的图片
            QTimer.singleShot(100, self.image_list.auto_jump_to_last_annotated_image)
            
    def closeEvent(self, event):
        """
        重写窗口关闭事件
        """
        # 从父类调用closeEvent确保正常关闭
        super().closeEvent(event)