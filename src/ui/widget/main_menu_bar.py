# main_menu_bar.py

import os
import shutil
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, QSettings, Qt
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, QFileDialog, QMessageBox, QProgressDialog


class MainMenuBar(QMenuBar):
    # 定义菜单动作的信号 - 确保使用正确的信号名称
    projectPathChanged: pyqtSignal = pyqtSignal(str)  # 项目路径改变信号
    importImagesRequested: pyqtSignal = pyqtSignal()
    exportToYoloRequested: pyqtSignal = pyqtSignal()
    exportToCocoRequested: pyqtSignal = pyqtSignal()
    closeRequested: pyqtSignal = pyqtSignal()
    editActionRequested: pyqtSignal = pyqtSignal()

    # 最近项目列表的最大长度
    MAX_RECENT_PROJECTS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recent_projects = []  # 存储最近打开的项目路径

        # 初始化应用设置
        self.settings = QSettings("YourCompany", "YourApp")

        # 从设置中加载最近项目列表
        self.load_recent_projects()

        """创建所有菜单动作"""
        # 文件菜单动作
        self.new_action = QAction("新建", self)
        self.recent_projects_menu = QMenu("最近打开的", self)
        self.import_action = QAction("导入图片", self)
        self.close_action = QAction("关闭", self)

        # 导出子菜单动作
        self.yolo_action = QAction("Yolo格式", self)
        self.coco_action = QAction("Coco格式", self)

        self.create_menus()
        self.connect_signals()

        # 初始更新最近项目菜单
        self.update_recent_projects_menu()

    def create_menus(self):
        """创建菜单结构"""
        # 文件菜单
        file_menu = self.addMenu("文件")
        file_menu.addAction(self.new_action)
        file_menu.addMenu(self.recent_projects_menu)  # 添加最近项目子菜单
        file_menu.addAction(self.import_action)

        # 导出子菜单
        export_menu = QMenu("导出", self)
        export_menu.setStyleSheet("QMenu::item { padding: 5px 20px; }")
        export_menu.addAction(self.yolo_action)
        export_menu.addAction(self.coco_action)
        file_menu.addMenu(export_menu)

        file_menu.addSeparator()
        file_menu.addAction(self.close_action)

    def connect_signals(self):
        """连接动作的信号到槽函数"""
        self.new_action.triggered.connect(self.handle_new_project)
        self.import_action.triggered.connect(self.import_images)  # 连接导入图片动作

        self.yolo_action.triggered.connect(self.exportToYoloRequested.emit)  # type: ignore
        self.coco_action.triggered.connect(self.exportToCocoRequested.emit)  # type: ignore
        self.close_action.triggered.connect(self.closeRequested.emit)  # type: ignore

    def handle_new_project(self):
        """处理新建项目的目录选择"""
        # 获取上次打开的目录
        from src.core.ksettings import KSettings
        settings = KSettings()
        last_directory = settings.get_last_opened_directory()
        
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "选择或创建项目目录",
            last_directory,  # 使用上次打开的目录作为默认路径
            options=QFileDialog.ShowDirsOnly | QFileDialog.DontUseNativeDialog
        )

        if selected_dir:
            self.create_new_project(selected_dir)
            # 保存当前选择的目录
            settings.set_last_opened_directory(selected_dir)

    def create_new_project(self, project_path: str):
        """创建或打开项目目录"""
        try:
            path = Path(project_path)

            # 确保目标目录存在
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)

            # 添加到最近项目列表
            self.add_to_recent_projects(str(path))

            # 发出项目路径更改信号
            self.projectPathChanged.emit(str(path))  # ig

        except Exception as e:
            QMessageBox.critical(
                self,
                "项目创建失败",
                f"无法访问目录: {str(e)}"
            )
            # 确保发送信号清除项目路径
            self.projectPathChanged.emit("")  # type: ignore

    def load_recent_projects(self):
        """从设置文件加载最近打开的项目"""
        size = self.settings.beginReadArray("recentProjects")
        for i in range(size):
            self.settings.setArrayIndex(i)
            project_path = self.settings.value("path")
            if project_path:
                self.recent_projects.append(project_path)
        self.settings.endArray()
        # 确保不超过最大数量
        self.recent_projects = self.recent_projects[:self.MAX_RECENT_PROJECTS]

    def save_recent_projects(self):
        """将最近项目保存到设置文件"""
        self.settings.beginWriteArray("recentProjects")
        for i, path in enumerate(self.recent_projects):
            self.settings.setArrayIndex(i)
            self.settings.setValue("path", path)
        self.settings.endArray()
        self.settings.sync()

    def add_to_recent_projects(self, path):
        """添加新项目到最近项目列表"""
        # 将路径标准化
        normalized_path = os.path.normpath(path)

        # 如果已经在列表中，先移除
        if normalized_path in self.recent_projects:
            self.recent_projects.remove(normalized_path)

        # 添加到列表开头
        self.recent_projects.insert(0, normalized_path)

        # 确保不超过最大数量
        if len(self.recent_projects) > self.MAX_RECENT_PROJECTS:
            self.recent_projects = self.recent_projects[:self.MAX_RECENT_PROJECTS]

        # 更新菜单
        self.update_recent_projects_menu()

        # 保存到设置
        self.save_recent_projects()

    def update_recent_projects_menu(self):
        """更新最近项目菜单内容"""
        # 先清除现有菜单项
        self.recent_projects_menu.clear()

        if not self.recent_projects:
            # 如果没有最近项目，显示禁用菜单项
            no_project = QAction("无最近项目", self)
            no_project.setEnabled(False)
            self.recent_projects_menu.addAction(no_project)
            return

        # 添加最近项目
        for path in self.recent_projects:
            # 创建带路径的动作
            action = QAction(self.truncate_path(path), self)
            action.setData(path)  # 存储完整路径
            action.triggered.connect(self.handle_open_recent_project)
            self.recent_projects_menu.addAction(action)

        # 添加清除历史选项
        self.recent_projects_menu.addSeparator()
        clear_action = QAction("清除历史记录", self)
        clear_action.triggered.connect(self.clear_recent_projects)
        self.recent_projects_menu.addAction(clear_action)

    @staticmethod
    def truncate_path(path):
        """截断过长的路径，保留开头和结尾"""
        if len(path) < 50:
            return path
        return f"{path[:15]}...{path[-30:]}"

    def handle_open_recent_project(self):
        """处理用户选择最近项目"""
        # 获取发送信号的QAction对象
        action = self.sender()
        if isinstance(action, QAction):
            # 从动作中获取完整路径
            path = action.data()
            if path:
                # 添加到最近项目列表顶部
                if path in self.recent_projects:
                    self.recent_projects.remove(path)
                self.recent_projects.insert(0, path)
                self.save_recent_projects()

                # 打开项目
                self.create_new_project(path)

    def clear_recent_projects(self):
        """清除所有最近项目"""
        self.recent_projects = []
        self.save_recent_projects()
        self.update_recent_projects_menu()

    def import_images(self):
        """处理图片导入功能"""
        main_window = self.parent()
        # 使用getattr安全获取project_path属性，如果不存在则返回None
        project_path_ref = getattr(main_window, 'project_path', None)
        project_path = project_path_ref.path
        # 检查project_path是否存在且是Path类型
        if project_path is None or not isinstance(project_path, Path):
            QMessageBox.warning(self, "错误", "获取工程路径异常")
            return

        # 2. 验证项目路径
        if not project_path or not project_path.exists():
            QMessageBox.warning(self, "项目未打开", "请先创建或打开有效的项目目录")
            return

        # 3. 选择导入方式
        import_type = self.select_import_type()
        if not import_type:
            return  # 用户取消操作

        # 4. 获取图片文件列表
        image_files = self.get_image_files(import_type)
        if not image_files:
            return  # 用户未选择文件

        # 5. 复制文件到项目目录
        success_count, failed_files = self.copy_images_to_project(image_files, project_path)

        # 6. 显示操作结果
        self.show_import_result(success_count, failed_files)

        # 7. 刷新父窗口的图片列表
        if hasattr(main_window, 'image_list') and callable(getattr(main_window.image_list, 'load_images_from_path', None)):
            main_window.image_list.load_images_from_path(project_path)

    def select_import_type(self):
        """选择导入方式（文件或文件夹）"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("选择导入方式")
        msg_box.setText("请选择导入方式：")
        file_btn = msg_box.addButton("导入文件", QMessageBox.ActionRole)
        folder_btn = msg_box.addButton("导入文件夹", QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton("取消", QMessageBox.RejectRole)
        msg_box.exec_()

        if msg_box.clickedButton() == file_btn:
            return "files"
        elif msg_box.clickedButton() == folder_btn:
            return "folder"
        return None

    def get_image_files(self, import_type):
        """根据选择的类型获取图片文件列表"""
        if import_type == "files":
            # 选择多个图片文件 [3](@ref)
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                "选择图片文件",
                "",
                "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff);;所有文件 (*.*)"
            )
            return file_paths
        else:
            # 选择文件夹并获取所有图片文件
            folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
            if not folder_path:
                return []

            # 递归获取文件夹下所有支持的图片文件
            supported_formats = ['.jpg', '.jpeg', '.png', '.bmp', '.gif', '.tif', '.tiff']
            image_files = []

            for root, _, files in os.walk(folder_path):
                for file in files:
                    file_ext = os.path.splitext(file)[1].lower()
                    if file_ext in supported_formats:
                        image_files.append(os.path.join(root, file))

            return image_files

    def copy_images_to_project(self, image_files, project_path):
        """复制图片到项目目录，处理重名文件"""
        # 创建进度对话框 [7](@ref)
        progress = QProgressDialog("导入图片...", "取消", 0, len(image_files), self)
        progress.setWindowTitle("导入进度")
        progress.setWindowModality(Qt.WindowModal)
        progress.setValue(0)

        # 用于记录文件名的计数（用于处理重名）
        name_counter = {}
        success_count = 0
        failed_files = []

        for i, src_path in enumerate(image_files):
            if progress.wasCanceled():
                break

            try:
                # 获取源文件名
                src_filename = os.path.basename(src_path)
                base, ext = os.path.splitext(src_filename)

                # 处理重名文件
                if src_filename in name_counter:
                    name_counter[src_filename] += 1
                    counter = name_counter[src_filename]

                    # 检查是否超过9999个重复
                    if counter > 9999:
                        raise Exception(f"文件重复次数超过9999: {src_filename}")

                    # 生成新文件名：test_0001.png
                    new_filename = f"{base}_{counter:04d}{ext}"
                    dest_path = project_path / new_filename
                else:
                    # 检查是否已有同名文件
                    dest_path = project_path / src_filename
                    if dest_path.exists():
                        # 第一次遇到重名，设置计数器为1
                        name_counter[src_filename] = 1
                        new_filename = f"{base}_0001{ext}"
                        dest_path = project_path / new_filename
                    else:
                        # 无重名
                        name_counter[src_filename] = 0

                # 复制文件 [3](@ref)
                shutil.copy2(src_path, str(dest_path))
                success_count += 1

            except Exception as e:
                failed_files.append((src_path, str(e)))

            progress.setValue(i + 1)

        progress.close()
        return success_count, failed_files

    def show_import_result(self, success_count, failed_files):
        """显示导入结果"""
        msg = f"成功导入 {success_count} 张图片"

        if failed_files:
            msg += f"\n\n失败 {len(failed_files)} 张图片："
            for file, error in failed_files:
                msg += f"\n- {os.path.basename(file)}: {error}"

        QMessageBox.information(self, "导入结果", msg)
