from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHeaderView, QLabel, QFrame
)
from PyQt5.QtCore import Qt
from src.core.project_info import ProjectInfo

from src.core.i18n.language_manager import tr

class StatisticsDialog(QDialog):
    def __init__(self, project_info: ProjectInfo, parent=None):
        super().__init__(parent)
        self.project_info = project_info
        self.setWindowTitle(tr("statistics_title"))
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        
        self.init_ui()
        self.populate_statistics()
        
    def init_ui(self):
        """初始化界面"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # 标题
        title_label = QLabel(tr("train_statistics_title"))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # 分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)
        
        # 统计表格
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr("statistics_header_name"), tr("statistics_header_id"), tr("statistics_header_count")])
        self.tree.header().setSectionResizeMode(QHeaderView.Stretch)
        self.tree.setAlternatingRowColors(True)
        self.tree.setStyleSheet("""
            QTreeWidget {
                border: 1px solid #d0d0d0;
                border-radius: 4px;
            }
            QTreeWidget::item {
                padding: 5px;
            }
        """)
        layout.addWidget(self.tree)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_button = QPushButton(tr("menu_close"))
        close_button.clicked.connect(self.accept)
        close_button.setStyleSheet("""
            QPushButton {
                background-color: #0078D7;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #106EBE;
            }
        """)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def populate_statistics(self):
        """填充统计数据"""
        # 获取所有类别，按order字段排序
        categories = self.project_info.domain.query_all_categories()
        
        # 创建类别映射和父子关系
        category_map = {cat.class_name: cat for cat in categories}
        parent_children_map = {}
        
        # 构建父子关系映射
        for category in categories:
            if category.parent_name:
                if category.parent_name not in parent_children_map:
                    parent_children_map[category.parent_name] = []
                parent_children_map[category.parent_name].append(category)
            # 确保所有类别都在映射中，即使它们没有子项
            elif category.class_name not in parent_children_map:
                parent_children_map[category.class_name] = []
        
        # 添加顶级类别及其子类别
        for category in categories:
            # 只处理顶级类别（没有父类别的类别）
            if not category.parent_name:
                # 创建顶级项
                top_level_item = QTreeWidgetItem(self.tree)
                top_level_item.setText(0, category.class_name)
                top_level_item.setText(1, str(category.class_id))
                
                # 获取该类别自身的标注数量
                self_count = self.project_info.domain.count_kilo_items_for_category(category.class_name)
                
                # 统计该类别及其子类别的标注数量
                total_count = self_count
                
                # 添加子类别
                children = parent_children_map.get(category.class_name, [])
                for child in children:
                    child_item = QTreeWidgetItem(top_level_item)
                    child_item.setText(0, "  └─ " + child.class_name)  # 添加缩进来表示层级关系
                    child_item.setText(1, str(child.class_id))
                    
                    # 获取子类别的标注数量
                    child_count = self.project_info.domain.count_kilo_items_for_category(child.class_name)
                    child_item.setText(2, str(child_count))
                    
                    # 累加到总计数中
                    total_count += child_count
                
                # 显示统计数据：如果有子类别则显示"M - N"格式，否则只显示总数
                if children:
                    top_level_item.setText(2, f"{total_count} - {self_count}")
                else:
                    top_level_item.setText(2, str(total_count))
                
        # 展开所有项
        self.tree.expandAll()
