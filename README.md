# KBoxLabel

KBoxLabel 是一个基于 PyQt5 开发的图像标注工具，专为目标检测任务设计。它提供了直观的图形界面和多种标注格式支持，帮助用户高效完成图像标注工作。

![main_window.png](docs/images/main_window.png)

## 目录
- [核心功能](#核心功能)
- [安装说明](#安装说明)
- [使用指南](#使用指南)
- [贡献](#贡献)
- [许可证](#许可证)
- [联系方式](#联系方式)

## 核心功能

### 图形界面与操作
- 基于 PyQt5 构建的直观易用操作界面
- 支持跨平台运行（Windows、macOS 和 Linux）
- 提供丰富的键盘快捷键提升标注效率

### 标注支持
- 支持矩形框标注，适用于目标检测任务
- 支持 COCO 和 YOLO 格式的导入和导出
- 集成 YOLOv8 模型，支持自动标注功能

### 项目管理
- 完全采用 SQLite3 数据库存储项目配置和标注数据
- 支持同时打开和管理多个项目窗口
- 自动保存标注到 SQLite 数据库中

## 安装说明

### 系统要求
- Python 3.11
- 支持的操作系统：Windows、macOS、Linux

### 安装步骤

1. 克隆项目仓库：
```bash
git clone https://github.com/kmvdata/KBoxLabel.git
cd KBoxLabel
```


2. 创建虚拟环境（推荐）：
```bash
# 使用 conda 创建虚拟环境
conda create -n kboxlabel python=3.11
conda activate kboxlabel
```


3. 安装依赖：
```bash
# Linux/macOS
bash ./app/pip_install.sh

# Windows
pip install -r app/requirements.txt
```


## 使用指南

### 启动应用
```bash
python src/main.py
```


### 基本操作流程
1. 创建或打开项目
2. 导入图像文件
3. 创建所需的标注类别
4. 进行图像标注
5. 保存并导出标注数据

### 快捷键操作
- `Delete` / `Backspace`：删除选中的标注
- `Ctrl+S`：保存标注
- `Ctrl+鼠标滚轮`：图像缩放
- 方向键：微调选中的标注位置
- `Shift+方向键`：调整选中标注的四边位置
- `Ctrl+Shift+方向键`：调整选中标注的大小
- `Shift+Ctrl+鼠标滚轮`：图像缩放

### 自动标注功能
1. 点击工具栏 "Config" 按钮配置模型
2. 选择 YOLOv8 模型文件（.pt 格式）
3. 点击 "Run" 按钮执行自动标注

### 数据存储
所有项目数据（包括标注信息、类别配置等）都存储在项目目录下的 `.kboxlabel` 文件夹中的 SQLite 数据库中，包含：
- 标注信息（`kolo_item` 表）
- 标注类别（`annotation_category` 表）
- 项目配置（`kv_config` 表）

### 支持的图像格式
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- 其他 PyQt5 支持的图像格式

## 贡献

欢迎提交 Issue 和 Pull Request 来帮助改进 KBoxLabel。

## 许可证

本项目采用 [MIT License](LICENSE) 开源许可证。

## 联系方式

如有问题或建议，请通过以下方式联系：
- 提交 Issue
- 发送邮件至：[kermit.mei@gmail.com](mailto:kermit.mei@gmail.com)
