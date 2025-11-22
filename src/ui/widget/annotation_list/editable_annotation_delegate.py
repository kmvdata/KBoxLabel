# annotation_list.py

from PyQt5.QtCore import Qt, QRect
from PyQt5.QtWidgets import QLineEdit, QSpinBox, QWidget
from ultralytics import YOLO

from src.ui.widget.annotation_list.annotation_delegate import AnnotationDelegate


# image_canvas.py


class EditableAnnotationDelegate(AnnotationDelegate):
    """支持编辑的委托类，通过右键菜单触发编辑"""
    EDIT_TYPE_TEXT = "text"
    EDIT_TYPE_ID = "id"

    def __init__(self, row_height=56, parent=None):
        super().__init__(row_height, parent)
        self.current_edit_type = None
        self.original_name = None

    def createEditor(self, parent, option, index):
        """创建编辑器"""
        if not self.current_edit_type:
            return None

        if self.current_edit_type == self.EDIT_TYPE_TEXT:
            editor = QLineEdit(parent)
            editor.setFrame(False)
            editor.setPlaceholderText("输入类别名称")
            return editor

        elif self.current_edit_type == self.EDIT_TYPE_ID:
            editor = QSpinBox(parent)
            editor.setMinimum(1)
            editor.setButtonSymbols(QSpinBox.NoButtons)
            return editor

        return None

    def get_edit_rects(self, option, index):
        """计算可编辑区域"""
        # 获取数据
        category_color = index.data(Qt.UserRole)
        class_id = index.data(Qt.UserRole + 1)
        category_name = index.data(Qt.DisplayRole)

        if not all([category_color, category_name, class_id is not None]):
            return {"text": QRect(), "id": QRect()}

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

        # id区域
        id_rect = QRect(
            option.rect.right() - color_size - self.MARGIN,
            option.rect.top() + self.MARGIN,
            color_size,
            color_size
        )

        return {"text": name_rect, "id": id_rect}

    def setEditorData(self, editor, index):
        """设置编辑器数据"""
        if isinstance(editor, QLineEdit):
            editor.setText(index.data(Qt.DisplayRole))
        elif isinstance(editor, QSpinBox):
            editor.setValue(index.data(Qt.UserRole + 1))

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
                    success = model.setData(index, category_name, Qt.DisplayRole)
                else:
                    # 名称重复，显示警告对话框
                    from PyQt5.QtWidgets import QMessageBox
                    view = self.parent()
                    if view is not None:
                        QMessageBox.warning(QWidget(view), "重命名失败",
                                            f"名称 '{category_name}' 已存在，请使用其他名称。")
                    # 名称重复，不保存更改
                    pass

        elif isinstance(editor, QSpinBox):
            class_id = editor.value()
            if class_id > 0:
                success = model.setData(index, class_id, Qt.UserRole + 1)
                
                # 如果是修改ID，同时更新project_info.categories中的对应项
                if success:
                    view = self.parent()
                    if view is not None and hasattr(view, 'project_info'):
                        # 获取修改项的class_name
                        class_name = model.data(index, Qt.UserRole + 2)
                        # 在project_info.categories中找到对应的类别并更新class_id
                        for category in view.project_info.categories:
                            if category.class_name == class_name:
                                category.class_id = class_id
                                break

        # 只有在设置数据成功时才保存
        if success:
            view = self.parent()
            if view is not None and hasattr(view, 'save_categories'):
                view.save_categories()  # 调用AnnotationList的save_categories方法

    def updateEditorGeometry(self, editor, option, index):
        """更新编辑器几何形状"""
        edit_rects = self.get_edit_rects(option, index)

        if self.current_edit_type == self.EDIT_TYPE_TEXT:
            editor.setGeometry(edit_rects["text"])
        elif self.current_edit_type == self.EDIT_TYPE_ID:
            editor.setGeometry(edit_rects["id"])

        editor.setVisible(True)
        editor.setFocus()