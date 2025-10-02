#!/bin/bash
# KBoxLabel Python依赖一键安装脚本
# 默认已配置好conda环境，仅安装Python包

# 定义核心依赖包列表
core_packages=(
    PyQt5
    PyQt5-tools
    opencv-python
    Pillow
    ultralytics
    pyqtgraph
    pyqt5
    "numpy<2"
)

# 使用国内镜像源加速安装
MIRROR_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

echo -e "\033[1;34m[INFO] 开始安装KBoxLabel核心依赖 (共${#core_packages[@]}个包)\033[0m"

# 批量安装核心包
python -m pip install --upgrade pip
python -m pip install -i $MIRROR_URL --trusted-host pypi.tuna.tsinghua.edu.cn "${core_packages[@]}"

# 验证安装结果
echo -e "\n\033[1;32m[验证] 已安装包列表：\033[0m"
python -m pip list --format=columns | grep -E "$(IFS=\|; echo "${core_packages[*]}")"

echo -e "\n\033[1;32m[SUCCESS] 依赖安装完成！可执行命令: python main.py\033[0m"
