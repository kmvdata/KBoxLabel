# help_dialog.py
import os
from pathlib import Path

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog, QVBoxLayout, QTextBrowser, QPushButton, QHBoxLayout, QApplication
from PyQt5.QtGui import QFont, QDesktopServices
from PyQt5.QtCore import QUrl

from src.core.ksettings import KSettings
from src.core.i18n.language_manager import tr


class HelpDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("help_title"))
        self.setGeometry(200, 100, 800, 600)
        
        # 获取语言设置
        settings = KSettings()
        self.language = settings.language
        
        # 获取README文件路径
        project_root = Path(__file__).parent.parent.parent.parent  # 获取到项目根目录
        if self.language == "zh":
            self.readme_path = project_root / "README.md"
        else:
            self.readme_path = project_root / "README_en.md"
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建文本浏览器来显示markdown内容
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)  # 允许打开外部链接
        self.text_browser.setReadOnly(True)
        
        # 读取并显示README内容
        self.load_readme_content()
        
        layout.addWidget(self.text_browser)
        
        # 创建按钮布局
        button_layout = QHBoxLayout()
        
        # 确定按钮
        ok_button = QPushButton(tr("button_ok"))
        ok_button.clicked.connect(self.accept)
        
        # 在浏览器中打开按钮
        open_external_button = QPushButton(tr("message_open_in_browser"))
        open_external_button.clicked.connect(self.open_in_external_browser)
        
        button_layout.addStretch()
        button_layout.addWidget(open_external_button)
        button_layout.addWidget(ok_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        
    def load_readme_content(self):
        """加载README内容到文本浏览器"""
        if self.readme_path.exists():
            with open(self.readme_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # 简单的markdown到HTML的转换
            html_content = self.markdown_to_html(content)
            self.text_browser.setHtml(html_content)
        else:
            # 如果指定语言的README不存在，尝试另一个语言版本
            project_root = Path(__file__).parent.parent.parent.parent
            fallback_path = project_root / "README.md" if self.readme_path.name == "README_en.md" else project_root / "README_en.md"
            
            if fallback_path.exists():
                with open(fallback_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                html_content = self.markdown_to_html(content)
                self.text_browser.setHtml(html_content)
            else:
                self.text_browser.setHtml(f"<h1>{tr('message_dataset_not_found')}</h1><p>{tr('message_no_help_file')}</p>")
    
    def markdown_to_html(self, markdown_text):
        """简单的markdown到HTML转换"""
        import re
        
        html = markdown_text
        
        # 处理标题
        html = re.sub(r'^# (.*$)', r'<h1>\1</h1>', html, flags=re.MULTILINE)
        html = re.sub(r'^## (.*$)', r'<h2>\1</h2>', html, flags=re.MULTILINE)
        html = re.sub(r'^### (.*$)', r'<h3>\1</h3>', html, flags=re.MULTILINE)
        html = re.sub(r'^#### (.*$)', r'<h4>\1</h4>', html, flags=re.MULTILINE)
        
        # 处理粗体
        html = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', html)
        html = re.sub(r'__(.*?)__', r'<strong>\1</strong>', html)
        
        # 处理斜体
        html = re.sub(r'\*(.*?)\*', r'<em>\1</em>', html)
        html = re.sub(r'_(.*?)_', r'<em>\1</em>', html)
        
        # 处理代码块
        html = re.sub(r'```.*?\n(.*?)```', r'<pre><code>\1</code></pre>', html, flags=re.DOTALL)
        
        # 处理行内代码
        html = re.sub(r'`(.*?)`', r'<code>\1</code>', html)
        
        # 处理链接
        html = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2">\1</a>', html)
        
        # 处理图片
        html = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'<img alt="\1" src="\2" style="max-width:100%;">', html)
        
        # 处理无序列表
        html = re.sub(r'^\* (.*$)', r'<li>\1</li>', html, flags=re.MULTILINE)
        html = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html, flags=re.DOTALL)
        
        # 处理换行
        html = html.replace('\n', '<br>')
        
        # 应用基本样式
        styled_html = f"""
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{ 
                    font-family: Arial, sans-serif; 
                    line-height: 1.6; 
                    padding: 20px;
                    color: #333;
                }}
                h1, h2, h3, h4 {{ 
                    color: #2c3e50; 
                    margin-top: 20px;
                    margin-bottom: 10px;
                }}
                pre {{
                    background-color: #f8f8f8;
                    padding: 10px;
                    border-radius: 5px;
                    overflow-x: auto;
                }}
                code {{
                    background-color: #f0f0f0;
                    padding: 2px 4px;
                    border-radius: 3px;
                }}
                a {{
                    color: #3498db;
                    text-decoration: none;
                }}
                a:hover {{
                    text-decoration: underline;
                }}
                img {{
                    max-width: 100%;
                    height: auto;
                }}
            </style>
        </head>
        <body>
            {html}
        </body>
        </html>
        """
        
        return styled_html
        
    def open_in_external_browser(self):
        """在外部浏览器中打开README文件"""
        if self.readme_path.exists():
            # 使用QDesktopServices打开文件
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.readme_path)))
        else:
            # 如果指定语言的README不存在，尝试另一个语言版本
            project_root = Path(__file__).parent.parent.parent.parent
            fallback_path = project_root / "README.md" if self.readme_path.name == "README_en.md" else project_root / "README_en.md"
            
            if fallback_path.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(fallback_path)))