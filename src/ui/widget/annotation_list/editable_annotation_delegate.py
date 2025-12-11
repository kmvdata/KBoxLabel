# annotation_list.py

from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QLineEdit, QWidget, QMessageBox, QProgressDialog
from ultralytics import YOLO

from src.core.project_info import ProjectInfo
from src.ui.widget.annotation_list.annotation_delegate import AnnotationDelegate


# image_canvas.py


class EditableAnnotationDelegate(AnnotationDelegate):
    """支持编辑的委托类，通过右键菜单触发编辑"""
    EDIT_TYPE_TEXT = "text"
    # 删除 EDIT_TYPE_ID = "id"

    def __init__(self, project_info: ProjectInfo, row_height=56, parent=None):
        super().__init__(row_height, parent)
        self.current_edit_type = None
        self.original_name = None
        self.domain = project_info.domain

    def createEditor(self, parent, option, index):
        """创建编辑器"""
        if not self.current_edit_type:
            return None

        if self.current_edit_type == self.EDIT_TYPE_TEXT:
            editor = QLineEdit(parent)
            editor.setFrame(False)
            editor.setPlaceholderText("输入类别名称")
            return editor

        # 删除与EDIT_TYPE_ID相关的代码
        return None

    def get_edit_rects(self, option, index):
        """计算可编辑区域"""
        # 获取数据
        category_color = index.data(Qt.UserRole)
        class_id = index.data(Qt.UserRole + 1)
        category_name = index.data(Qt.DisplayRole)

        if not all([category_color, category_name, class_id is not None]):
            return {"text": QRect()}

        # 计算各区域尺寸
        color_size = self.row_height - 2 * self.MARGIN

        # name区域
        name_min_width = 2 * self.row_height
        available_width = option.rect.width() - (color_size + self.MARGIN + self.SPACING) * 2
        name_width = max(available_width, name_min_width)

        name_rect = QRect(
            option.rect.left() + color_size + self.MARGIN + self.SPACING,
            option.rect.top(),
            name_width,
            self.row_height
        )

        # 删除id_rect相关代码
        return {"text": name_rect}

    def setEditorData(self, editor, index):
        """设置编辑器数据"""
        if isinstance(editor, QLineEdit):
            editor.setText(index.data(Qt.DisplayRole))
        # 删除与QSpinBox相关的代码

    def setModelData(self, editor, model, index):
        """将编辑器数据保存到模型"""
        success = False
        if isinstance(editor, QLineEdit):
            category_name = editor.text().strip()
            if category_name:
                # 检查是否有重复名称（排除自身）
                is_duplicate = False
                if category_name != self.original_name:
                    # 遍历所有项目检查是否有重复名称
                    for row in range(model.rowCount()):
                        if row != index.row():  # 排除自身
                            other_name = model.data(model.index(row, 0), Qt.DisplayRole)
                            if other_name == category_name:
                                is_duplicate = True
                                break

                if not is_duplicate:
                    # 获取视图和原始类别名称
                    view = self.parent()
                    old_class_name = model.data(index, Qt.UserRole + 2)  # 原始class_name
                    
                    # 先更新模型数据
                    success = model.setData(index, category_name, Qt.DisplayRole)
                    
                    # 如果更新成功，继续更新数据库
                    if success:
                        try:
                            # 显示进度对话框
                            progress = QProgressDialog("正在更新类别名称...", "取消", 0, 2, view)
                            progress.setWindowModality(Qt.WindowModal)
                            progress.setWindowTitle("请稍候")
                            progress.show()
                            progress.setValue(0)
                            
                            # 更新数据库中annotation_category表和kolo_item表
                            self.domain.rename_category(old_class_name, category_name)
                            
                            progress.setValue(1)
                            progress.setValue(2)
                            
                            # 显示成功消息
                            QMessageBox.information(view, "成功", f"类别名称已从 '{old_class_name}' 更新为 '{category_name}'")
                            
                        except Exception as e:
                            # 发生异常时显示错误消息
                            QMessageBox.critical(view, "错误", f"更新类别名称失败: {str(e)}")
                            # 回滚模型数据更改
                            model.setData(index, old_class_name, Qt.DisplayRole)
                            success = False
                else:
                    # 名称重复，显示警告对话框
                    view = self.parent()
                    if view is not None:
                        QMessageBox.warning(view, "重命名失败",
                                            f"名称 '{category_name}' 已存在，请使用其他名称。")
                    # 名称重复，不保存更改
                    pass

        # 删除与QSpinBox相关的代码

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何形状"""
        edit_rects = self.get_edit_rects(option, index)

        if self.current_edit_type == self.EDIT_TYPE_TEXT:
            editor.setGeometry(edit_rects["text"])
        # 删除与EDIT_TYPE_ID相关的代码

        editor.setVisible(True)
        editor.setFocus()