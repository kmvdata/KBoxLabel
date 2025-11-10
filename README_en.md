# KBoxLabel

KBoxLabel is a PyQt5-based image annotation tool designed for object detection tasks. It provides an intuitive graphical interface and supports importing and exporting annotations in multiple formats, including COCO and YOLO.

![main_window.png](docs/images/main_window.png)

## Table of Contents
- [Key Features](#key-features)
- [Installation Guide](#installation-guide)
- [Usage Guide](#usage-guide)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Key Features

### Graphical Interface and Operations
- Intuitive and easy-to-use interface built with PyQt5
- Cross-platform support (Windows, macOS, and Linux)
- Rich keyboard shortcuts to improve annotation efficiency

### Annotation Support
- Rectangle annotation support suitable for object detection tasks
- Import and export support for COCO and YOLO formats
- Integrated YOLOv8 model for automatic annotation capabilities

### Project Management
- Fully adopts SQLite3 database for storing project configurations and annotation data
- Supports simultaneously opening and managing multiple project windows
- Automatically saves annotations to SQLite database

## Installation Guide

### System Requirements
- Python 3.11
- Supported operating systems: Windows, macOS, Linux

### Installation Steps

1. Clone the repository:
```bash
git clone https://github.com/kmvdata/KBoxLabel.git
cd KBoxLabel
```

2. Create a virtual environment (recommended):
```bash
# Using conda to create virtual environment
conda create -n kboxlabel python=3.11
conda activate kboxlabel
```

3. Install dependencies:
```bash
# Linux/macOS
bash ./app/pip_install.sh

# Windows
pip install -r app/requirements.txt
```

## Usage Guide

### Launch the Application
```bash
python src/main.py
```

### Basic Operation Flow
1. Create or open a project
2. Import image files
3. Create required annotation categories
4. Perform image annotation
5. Save and export annotation data

### Keyboard Shortcuts
- `Delete` / `Backspace`: Delete selected annotations
- `Ctrl+S`: Save annotations
- `Ctrl+Mouse Wheel`: Zoom image
- Arrow keys: Fine-tune selected annotation positions
- `Shift+Arrow Keys`: Adjust the four sides of selected annotations
- `Ctrl+Shift+Arrow Keys`: Adjust the size of selected annotations
- `Shift+Ctrl+Mouse Wheel`: Zoom image

### Auto Annotation Feature
1. Click the "Config" button on the toolbar to configure the model
2. Select the YOLOv8 model file (.pt format)
3. Click the "Run" button to execute automatic annotation

### Data Storage
All project data (including annotation information, category configurations, etc.) is stored in the SQLite database in the `.kboxlabel` folder under the project directory, containing:
- Annotation information (`kolo_item` table)
- Annotation categories (`annotation_category` table)
- Project configurations (`kv_config` table)

### Supported Image Formats
- JPEG (.jpg, .jpeg)
- PNG (.png)
- BMP (.bmp)
- Other image formats supported by PyQt5

## Contributing

Issues and Pull Requests are welcome to help improve KBoxLabel.

## License

This project is licensed under the [MIT License](LICENSE).

## Contact

If you have any questions or suggestions, please contact us through:
- Submit an Issue
- Email: [kermit.mei@gmail.com](mailto:kermit.mei@gmail.com)
