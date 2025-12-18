# YOLO 训练数据使用指南

这份文档将帮助您了解如何在不同操作系统上使用生成的 YOLO 训练数据进行模型训练。

## 目录结构

生成的训练数据具有以下目录结构：

```
train_data/
├── dataset.yaml      # 数据集配置文件
├── train/            # 训练集
│   ├── images/       # 训练图片
│   └── labels/       # 训练标签
└── val/              # 验证集
    ├── images/       # 验证图片
    └── labels/       # 验证标签
```

## 安装依赖

在开始训练之前，您需要安装必要的依赖项。

### 通用依赖安装

无论您使用哪种操作系统，都需要安装 Ultralytics 库：

```bash
pip install ultralytics
```

如果您还需要 GPU 支持，请参考官方文档安装 CUDA 和 cuDNN。

### OSX/macOS

在 macOS 上，您可以使用 pip 安装所需依赖：

```bash
# 安装基础依赖
pip install ultralytics

# 如果您使用 Apple Silicon (M1/M2/M3) 芯片并希望利用 MPS 加速
pip install ultralytics torch torchvision torchaudio
```

### Linux

在 Linux 上，您可以使用 pip 安装所需依赖：

```bash
# 安装基础依赖
pip install ultralytics

# 如果您需要 GPU 支持，请安装 CUDA 驱动和相应的 PyTorch 版本
# 请参考 NVIDIA 官方文档和 PyTorch 官网获取适合您的 CUDA 版本
```

### Windows

在 Windows 上，您可以使用 pip 安装所需依赖：

```cmd
# 安装基础依赖
pip install ultralytics

# 如果您需要 GPU 支持，请安装 CUDA 驱动和相应的 PyTorch 版本
# 请参考 NVIDIA 官方文档和 PyTorch 官网获取适合您的 CUDA 版本
```

## 训练命令

训练命令的基本格式如下：

```bash
yolo detect train model=yolov8s.pt data={数据目录绝对路径}/dataset.yaml epochs=100 imgsz=640 batch=16
```

### 参数说明

- `model`: 预训练模型文件，例如 yolov8s.pt
- `data`: 数据集配置文件路径（即 dataset.yaml）
- `epochs`: 训练轮数，默认为 100
- `imgsz`: 输入图片尺寸，默认为 640
- `batch`: 批次大小，默认为 16

### 示例命令

假设您的训练数据位于 `/home/user/train_data`，可以使用以下命令开始训练：

```bash
yolo detect train model=yolov8s.pt data=/home/user/train_data/dataset.yaml epochs=100 imgsz=640 batch=16
```

在 Windows 上，路径可能类似于：

```cmd
yolo detect train model=yolov8s.pt data=C:\Users\user\train_data\dataset.yaml epochs=100 imgsz=640 batch=16
```

### 其他常用训练选项

您还可以使用以下选项进一步定制训练过程：

```bash
# 指定设备 (0 for GPU 0, cpu for CPU)
yolo detect train model=yolov8s.pt data=dataset.yaml device=0

# 启用混合精度训练
yolo detect train model=yolov8s.pt data=dataset.yaml amp=true

# 指定保存目录
yolo detect train model=yolov8s.pt data=dataset.yaml project=my_project name=my_experiment
```

## 验证模型

训练完成后，您可以使用以下命令验证模型性能：

```bash
yolo detect val model=runs/detect/train/weights/best.pt data=dataset.yaml
```

## 预测

使用训练好的模型进行预测：

```bash
yolo detect predict model=runs/detect/train/weights/best.pt source=image.jpg
```

## 注意事项

1. 确保您的训练数据目录保持完整且未被修改
2. 如果您更改了类别数量，请相应地更新 dataset.yaml 文件
3. 根据您的硬件配置适当调整 batch size 和 imgsz 参数
4. 训练过程中会自动保存最佳模型权重和最新的模型权重
5. 日志和结果将保存在 runs/detect/train/ 目录中