# KBoxLabel

KBoxLabel 是一个基于 PyQt5 开发的图像标注工具，支持目标检测任务的标注工作。它提供了直观的图形界面，支持多种标注格式的导入导出，包括 COCO 和 YOLO 格式。

## 功能特性

- **图形化界面**：基于 PyQt5 构建，提供直观易用的操作界面
- **多种标注类型**：支持矩形框标注，适用于目标检测任务
- **多格式支持**：支持 COCO 和 YOLO 格式的导入和导出
- **自动标注**：集成 YOLOv8 模型，支持自动标注功能
- **跨平台**：支持 Windows、macOS 和 Linux 系统
- **快捷键操作**：提供丰富的键盘快捷键，提高标注效率
- **手势支持**：支持触摸板手势操作，如捏合缩放

## 界面预览

![界面预览](docs/images/interface.png)

## 安装指南

### 系统要求

- Python 3.10 或更高版本
- 支持的系统：Windows、macOS、Linux

### 安装步骤

1. 克隆项目仓库：
```bash
git clone https://github.com/your-username/KBoxLabel.git
cd KBoxLabel
```

2. 创建虚拟环境（推荐）：
```bash
# 使用conda创建虚拟环境
conda create -n kboxlabel python=3.10
conda activate kboxlabel
```

3. 安装依赖：
```bash
# Linux/macOS
./app/pip_install.sh

# Windows
pip install -r app/requirements.txt
```

## 使用说明

### 启动应用

```bash
python src/main.py
```

### 基本操作

1. **创建或打开项目**：应用启动后，选择新建项目或打开现有项目
2. **导入图像**：将图像文件放入项目目录，或使用导入功能
3. **创建标注类别**：在右侧标注列表中添加需要的类别
4. **进行标注**：
   - 选择要标注的类别
   - 在图像上按住鼠标左键拖拽创建矩形框
   - 可以通过拖拽边框或角落调整矩形框位置和大小
5. **保存标注**：标注会自动保存为 .kolo 格式文件

### 快捷键

- `Delete` / `Backspace`：删除选中的标注
- `Ctrl+S`：保存标注
- `Ctrl+鼠标滚轮`：图像缩放
- `方向键`：微调选中的标注位置
- `Shift+方向键`：调整选中标注的大小

### 标注管理

- **选择标注**：单击标注框选择
- **移动标注**：选中标注后拖拽
- **调整大小**：选中标注后拖拽边缘或角落的控制点
- **类别切换**：通过右侧类别列表选择当前标注类别

### 导入导出

#### COCO 格式

1. 在菜单栏选择 "导出" -> "导出为 COCO"
2. 选择导出目录
3. 系统将自动转换所有 .kolo 文件为 COCO 格式

#### YOLO 格式

1. 在菜单栏选择 "导出" -> "导出为 YOLO"
2. 系统将自动转换所有 .kolo 文件为 YOLO 格式

## 自动标注

KBoxLabel 集成了 YOLOv8 模型，支持自动标注功能：

1. 在工具栏点击 "Config" 按钮配置模型
2. 选择你的 YOLOv8 模型文件（.pt 格式）
3. 点击 "Run" 按钮执行自动标注

## 文件格式

### .kolo 格式

.kolo 是 KBoxLabel 的原生标注格式，每行代表一个标注对象：

```
[类别名称Base64编码] [中心点x] [中心点y] [宽度] [高度]
```

其中坐标和尺寸均为相对于图像尺寸的归一化值（0-1之间）。

### 支持的图像格式

- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- 其他 PyQt5 支持的图像格式

## 开发指南

### 项目结构

```
KBoxLabel/
├── app/                 # 应用配置和依赖
├── src/                 # 源代码
│   ├── core/            # 核心功能模块
│   ├── models/          # 数据模型
│   ├── ui/              # 用户界面
│   └── main.py          # 应用入口
└── README.md            # 说明文档
```

### 构建项目

如需从头开始构建项目结构，可以运行：

```bash
./init_proj.sh
```

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进 KBoxLabel。

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：

- 提交 Issue
- 发送邮件至：[kermit.mei@gmail.com]