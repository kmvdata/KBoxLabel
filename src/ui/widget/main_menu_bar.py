# main_menu_bar.py

import os
import shutil
import sys
from pathlib import Path

from PyQt5.QtCore import pyqtSignal, Qt, pyqtSlot
from PyQt5.QtWidgets import QMenuBar, QAction, QMenu, QFileDialog, QMessageBox, QProgressDialog

from src.core.i18n.language_manager import tr, LanguageManager

# 解决循环导入问题：延迟导入 ApplicationManager
# from src.ui.application_manager import ApplicationManager


class MainMenuBar(QMenuBar):
    # 定义菜单动作的信号 - 确保使用正确的信号名称
    importImagesRequested: pyqtSignal = pyqtSignal()
    closeRequested: pyqtSignal = pyqtSignal()
    editActionRequested: pyqtSignal = pyqtSignal()
    # 新增训练相关的信号
    trainYoloRequested: pyqtSignal = pyqtSignal()

    # 最近项目列表的最大长度
    MAX_RECENT_PROJECTS = 5

    def __init__(self, parent=None):
        super().__init__(parent)
        self.recent_projects = []  # 存储最近打开的项目路径

        # 初始化应用设置
        from src.core.ksettings import KSettings
        self.settings = KSettings()

        # 从设置中加载最近项目列表
        self.load_recent_projects()

        """创建所有菜单动作"""
        # 文件菜单动作
        self.new_action = QAction("", self)  # 初始文本为空，稍后设置
        self.recent_projects_menu = QMenu("", self)  # 初始文本为空，稍后设置
        self.import_action = QAction("", self)  # 初始文本为空，稍后设置
        self.close_action = QAction("", self)  # 初始文本为空，稍后设置

        # 训练子菜单动作
        self.train_yolo_action = QAction("", self)  # 初始文本为空，稍后设置
        
        # 帮助菜单动作
        self.help_doc_action = QAction("", self)  # 初始文本为空，稍后设置
        self.chinese_action = QAction("", self)  # 初始文本为空，稍后设置
        self.english_action = QAction("", self)  # 初始文本为空，稍后设置
        self.about_action = QAction("", self)  # 初始文本为空，稍后设置

        # 设置菜单文本
        self.update_menu_texts()
        
        self.create_menus()
        self.connect_signals()

        # 初始更新最近项目菜单
        self.update_recent_projects_menu()
        
        # 连接语言变更信号
        LanguageManager.instance().language_changed.connect(self.on_language_changed)

    def update_menu_texts(self):
        """更新菜单文本"""
        self.new_action.setText(tr("menu_new"))
        self.recent_projects_menu.setTitle(tr("menu_recent"))
        self.import_action.setText(tr("menu_import_images"))
        self.close_action.setText(tr("menu_close"))
        self.train_yolo_action.setText(tr("menu_train_yolo"))
        self.help_doc_action.setText(tr("menu_help_documentation"))
        self.chinese_action.setText(tr("menu_chinese"))
        self.english_action.setText(tr("menu_english"))
        self.about_action.setText(tr("menu_about"))
        
        # 更新菜单标题
        # 注意：QMenuBar的菜单标题需要重新创建菜单项来更新
        self.recreate_menus()
    
    def recreate_menus(self):
        """重新创建菜单以更新语言"""
        # 清除现有菜单
        self.clear()
        
        # 重新创建菜单
        self.create_menus()
    
    @pyqtSlot(str)
    def on_language_changed(self, language: str):
        """处理语言变更事件"""
        self.update_menu_texts()

    def create_menus(self):
        """创建菜单结构"""
        # 文件菜单
        file_menu = self.addMenu(tr("menu_file"))
        file_menu.addAction(self.new_action)
        file_menu.addMenu(self.recent_projects_menu)  # 添加最近项目子菜单
        file_menu.addAction(self.import_action)
        
        # 训练子菜单
        train_menu = QMenu(tr("menu_train"), self)
        train_menu.setStyleSheet("QMenu::item { padding: 5px 20px; }")
        train_menu.addAction(self.train_yolo_action)
        file_menu.addMenu(train_menu)

        file_menu.addSeparator()
        file_menu.addAction(self.close_action)
        
        # 帮助菜单
        help_menu = self.addMenu(tr("menu_help"))
        help_menu.addAction(self.help_doc_action)
        
        # 语言子菜单
        language_menu = QMenu(tr("menu_language"), self)
        language_menu.addAction(self.chinese_action)
        language_menu.addAction(self.english_action)
        help_menu.addMenu(language_menu)
        
        # 添加分隔线和关于菜单
        help_menu.addSeparator()
        help_menu.addAction(self.about_action)

    def connect_signals(self):
        """连接动作的信号到槽函数"""
        self.new_action.triggered.connect(self.handle_new_project)
        self.import_action.triggered.connect(self.import_images)  # 连接导入图片动作
        self.close_action.triggered.connect(self.closeRequested.emit)  # type: ignore
        
        # 连接训练相关的信号
        self.train_yolo_action.triggered.connect(self.trainYoloRequested.emit)  # type: ignore
        
        # 连接帮助菜单相关的信号
        self.help_doc_action.triggered.connect(self.open_help_documentation)  # type: ignore
        self.chinese_action.triggered.connect(self.switch_to_chinese)  # type: ignore
        self.english_action.triggered.connect(self.switch_to_english)  # type: ignore
        self.about_action.triggered.connect(self.show_about_dialog)  # type: ignore

    def handle_new_project(self):
        """处理新建项目的目录选择"""
        # 获取上次打开的目录
        from src.core.ksettings import KSettings
        settings = KSettings()
        last_directory = settings.get_last_opened_directory()
        
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            tr("select_or_create_project_dir"),
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
            # 解决循环导入问题：延迟导入 ApplicationManager
            from src.ui.application_manager import ApplicationManager
            ApplicationManager.open_project(str(path))

        except Exception as e:
            QMessageBox.critical(
                self,
                tr("error_create_project"),
                tr("error_invalid_path", error=str(e))
            )

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
            no_project = QAction(tr("no_recent_project"), self)
            no_project.setEnabled(False)
            self.recent_projects_menu.addAction(no_project)
            return

        # 添加最近项目
        for path in self.recent_projects:
            # 创建带路径的动作
            action = QAction(self.truncate_path(path), self)
            action.setData(path)  # 存储完整路径
            action.triggered.connect(self.handle_open_recent_project) # type: ignore
            self.recent_projects_menu.addAction(action)

        # 添加清除历史选项
        self.recent_projects_menu.addSeparator()
        clear_action = QAction(tr("message_clear_history"), self)
        clear_action.triggered.connect(self.clear_recent_projects)  # type: ignore
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
        project_info = getattr(main_window, 'project_info', None)
        project_path = project_info.path
        # 检查project_path是否存在且是Path类型
        if project_path is None or not isinstance(project_path, Path):
            QMessageBox.warning(self, tr("error_get_project_path"), tr("error_get_project_path"))
            return

        # 2. 验证项目路径
        if not project_path or not project_path.exists():
            QMessageBox.warning(self, tr("error_project_not_opened"), tr("error_project_not_opened"))
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
        msg_box.setWindowTitle(tr("dialog_title_import"))
        msg_box.setText(tr("import_type_selection"))
        file_btn = msg_box.addButton(tr("import_files"), QMessageBox.ActionRole)
        folder_btn = msg_box.addButton(tr("import_folder"), QMessageBox.ActionRole)
        cancel_btn = msg_box.addButton(tr("button_cancel"), QMessageBox.RejectRole)
        msg_box.exec_()

        if msg_box.clickedButton() == file_btn:
            return "files"
        elif msg_box.clickedButton() == folder_btn:
            return "folder"
        return None

    def get_image_files(self, import_type):
        """根据选择的类型获取图片文件列表"""
        # 获取上次打开的目录
        from src.core.ksettings import KSettings
        settings = KSettings()
        last_directory = settings.get_last_opened_directory()
        
        if import_type == "files":
            # 选择多个图片文件 [3](@ref)
            file_paths, _ = QFileDialog.getOpenFileNames(
                self,
                tr("dialog_title_import"),
                last_directory,
                "图片文件 (*.jpg *.jpeg *.png *.bmp *.gif *.tif *.tiff);;所有文件 (*.*)"
            )
            
            # 保存当前选择的目录
            if file_paths:
                settings.set_last_opened_directory(str(Path(file_paths[0]).parent))
                
            return file_paths
        else:
            # 选择文件夹并获取所有图片文件
            folder_path = QFileDialog.getExistingDirectory(self, tr("dialog_title_import"), last_directory)
            
            # 保存当前选择的目录
            if folder_path:
                settings.set_last_opened_directory(folder_path)
                
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
        progress = QProgressDialog(tr("import_progress"), tr("button_cancel"), 0, len(image_files), self)
        progress.setWindowTitle(tr("import_progress"))
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
        msg = tr("import_success", count=success_count)

        if failed_files:
            msg += tr("import_result", success_count=success_count, failed_count=len(failed_files), failed_details='\n'.join([f'- {os.path.basename(file)}: {error}' for file, error in failed_files]))

        QMessageBox.information(self, tr("dialog_title_import"), msg)

    def open_help_documentation(self):
        """打开帮助文档"""
        # 导入帮助对话框
        from src.ui.dialog.help_dialog import HelpDialog
        
        # 创建并显示帮助对话框
        help_dialog = HelpDialog(self)
        help_dialog.exec_()

    def switch_to_chinese(self):
        """切换到中文语言"""
        from src.core.i18n.language_manager import set_language
        set_language("zh")
        QMessageBox.information(self, tr("menu_language"), tr("message_language_switched_to_chinese"))

    def switch_to_english(self):
        """切换到英文语言"""
        from src.core.i18n.language_manager import set_language
        set_language("en")
        QMessageBox.information(self, tr("menu_language"), tr("message_language_switched_to_english"))

    def show_about_dialog(self):
        """显示关于对话框"""
        from src.ui.dialog.about_dialog import AboutDialog
        
        about_dialog = AboutDialog(self)
        about_dialog.exec_()
