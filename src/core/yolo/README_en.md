# YOLO Training Data Usage Guide

This document will help you understand how to use the generated YOLO training data for model training on different operating systems.

## Directory Structure

The generated training data has the following directory structure:

```
train_data/
├── dataset.yaml      # Dataset configuration file
├── train/            # Training set
│   ├── images/       # Training images
│   └── labels/       # Training labels
└── val/              # Validation set
    ├── images/       # Validation images
    └── labels/       # Validation labels
```

## Installing Dependencies

Before starting training, you need to install the necessary dependencies.

### Generic Dependency Installation

Regardless of which operating system you use, you need to install the Ultralytics library:

```bash
pip install ultralytics
```

If you also need GPU support, please refer to the official documentation to install CUDA and cuDNN.

### OSX/macOS

On macOS, you can use pip to install the required dependencies:

```bash
# Install basic dependencies
pip install ultralytics

# If you are using Apple Silicon (M1/M2/M3) chips and want to leverage MPS acceleration
pip install ultralytics torch torchvision torchaudio
```

### Linux

On Linux, you can use pip to install the required dependencies:

```bash
# Install basic dependencies
pip install ultralytics

# If you need GPU support, please install CUDA drivers and the corresponding PyTorch version
# Please refer to the NVIDIA official documentation and PyTorch website for the CUDA version suitable for you
```

### Windows

On Windows, you can use pip to install the required dependencies:

```cmd
# Install basic dependencies
pip install ultralytics

# If you need GPU support, please install CUDA drivers and the corresponding PyTorch version
# Please refer to the NVIDIA official documentation and PyTorch website for the CUDA version suitable for you
```

## Training Commands

The basic format of the training command is as follows:

```bash
yolo detect train model=yolov8s.pt data={absolute path to data directory}/dataset.yaml epochs=100 imgsz=640 batch=16
```

### Parameter Description

- `model`: Pre-trained model file, e.g. yolov8s.pt
- `data`: Dataset configuration file path (i.e. dataset.yaml)
- `epochs`: Number of training epochs, default is 100
- `imgsz`: Input image size, default is 640
- `batch`: Batch size, default is 16

### Example Commands

Assuming your training data is located at `/home/user/train_data`, you can use the following command to start training:

```bash
yolo detect train model=yolov8s.pt data=/home/user/train_data/dataset.yaml epochs=100 imgsz=640 batch=16
```

On Windows, the path might look like:

```cmd
yolo detect train model=yolov8s.pt data=C:\Users\user\train_data\dataset.yaml epochs=100 imgsz=640 batch=16
```

### Other Common Training Options

You can also use the following options to further customize the training process:

```bash
# Specify device (0 for GPU 0, cpu for CPU)
yolo detect train model=yolov8s.pt data=dataset.yaml device=0

# Enable mixed precision training
yolo detect train model=yolov8s.pt data=dataset.yaml amp=true

# Specify save directory
yolo detect train model=yolov8s.pt data=dataset.yaml project=my_project name=my_experiment
```

## Validating the Model

After training is complete, you can use the following command to validate model performance:

```bash
yolo detect val model=runs/detect/train/weights/best.pt data=dataset.yaml
```

## Prediction

Using the trained model for prediction:

```bash
yolo detect predict model=runs/detect/train/weights/best.pt source=image.jpg
```

## Notes

1. Make sure your training data directory remains intact and unmodified
2. If you change the number of categories, update the dataset.yaml file accordingly
3. Adjust batch size and imgsz parameters appropriately according to your hardware configuration
4. During training, the best model weights and latest model weights will be automatically saved
5. Logs and results will be saved in the runs/detect/train/ directory