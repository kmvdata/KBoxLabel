#!/bin/bash
# KBoxLabel Python依赖一键安装脚本
# 针对不同平台进行差异化处理

# 获取系统信息
OS=$(uname -s)
ARCH=$(uname -m)
echo -e "\033[1;34m[INFO] 检测到系统: $OS ($ARCH)\033[0m"

# 定义核心依赖包列表（不含平台特定包）
core_packages=(
    PyQt5
    PyQt5-tools
    Pillow
    ultralytics
    pydantic
    pyqtgraph
    sqlalchemy
    i18n
)

# 定义平台特定包
opencv_package=""
conditional_packages=()

# 根据平台设置opencv版本
case $OS in
    Linux)
        opencv_package="opencv-python-headless"  # Linux使用无头版本
        ;;
    Darwin)
        opencv_package="opencv-python"           # macOS使用标准版本
        # macOS Intel芯片添加numpy版本限制
        if [ "$ARCH" = "x86_64" ]; then
            conditional_packages+=("numpy<2")
            echo -e "\033[1;34m[INFO] 检测到macOS Intel芯片，将安装numpy<2\033[0m"
        fi
        ;;
    *)
        opencv_package="opencv-python"           # 其他系统默认标准版本
        echo -e "\033[1;33m[WARN] 未识别系统，使用默认opencv版本\033[0m"
        ;;
esac

# 合并所有需要安装的包
all_packages=("${core_packages[@]}" "$opencv_package" "${conditional_packages[@]}")

# 使用国内镜像源加速安装
MIRROR_URL="https://pypi.tuna.tsinghua.edu.cn/simple"

echo -e "\033[1;34m[INFO] 开始安装KBoxLabel依赖 (共${#all_packages[@]}个包)\033[0m"
echo -e "\033[1;34m[INFO] 安装列表: ${all_packages[*]}\033[0m"

# 升级pip并安装依赖
python -m pip install --upgrade pip
python -m pip install -i "$MIRROR_URL" --trusted-host pypi.tuna.tsinghua.edu.cn "${all_packages[@]}"

# 验证安装结果（处理可能的版本后缀）
echo -e "\n\033[1;32m[验证] 已安装包列表：\033[0m"
# 构建验证用的正则表达式（处理numpy<2和opencv变体）
verify_packages=("${core_packages[@]}" "opencv-python" "numpy")
python -m pip list --format=columns | grep -E "$(IFS=\|; echo "${verify_packages[*]}")"

echo -e "\n\033[1;32m[SUCCESS] 依赖安装完成！可执行命令: python main.py\033[0m"
