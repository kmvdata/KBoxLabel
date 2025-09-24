#!/bin/bash

# KBoxLabel 发布脚本

echo "开始构建 KBoxLabel 包..."

# 清理之前的构建文件
echo "清理之前的构建文件..."
rm -rf build/
rm -rf dist/
rm -rf *.egg-info/

# 构建源码分发包
echo "构建源码分发包..."
python setup.py sdist

# 构建 wheel 包
echo "构建 wheel 包..."
python setup.py bdist_wheel

echo "构建完成！"
echo "生成的包位于 dist/ 目录中"

# 检查是否安装了 twine
if ! command -v twine &> /dev/null
then
    echo "未找到 twine，正在安装..."
    pip install twine
fi

echo "你可以使用以下命令发布包到 PyPI:"
echo "twine upload dist/*"

echo "或者发布到 TestPyPI:"
echo "twine upload --repository testpypi dist/*"