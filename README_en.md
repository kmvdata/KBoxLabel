# KBoxLabel

KBoxLabel is a professional image annotation tool developed based on PyQt5, specially designed for object detection tasks in computer vision. It provides an intuitive graphical interface and supports multiple annotation formats to help users efficiently complete image annotation work. KBoxLabel is particularly suitable for machine learning engineers, researchers, and data scientists preparing training datasets.

![main_window.png](docs/images/main_window.png)

## Table of Contents
- [Core Features](#core-features)
- [Unique Advantages](#unique-advantages)
- [Installation Guide](#installation-guide)
- [Quick Start](#quick-start)
- [Usage Guide](#usage-guide)
- [Automatic Annotation](#automatic-annotation)
- [Data Export](#data-export)
- [Contributing](#contributing)
- [License](#license)
- [Contact](#contact)

## Core Features

### Graphical Interface and Operations
- Intuitive and easy-to-use interface built with PyQt5
- Cross-platform support (Windows, macOS, and Linux)
- Rich keyboard shortcuts to improve annotation efficiency
- Support for managing multiple project windows simultaneously
- Real-time saving of annotation data to SQLite database

### Annotation Support
- Rectangle annotation support suitable for object detection tasks
- Integrated YOLOv8 model for automatic annotation capabilities
- Support for hierarchical category management (parent-child category relationships)
- Visual editing and adjustment of annotations
- Support for drag-and-drop sorting and renaming of annotations

### Project Management
- Fully adopts SQLite3 database for storing project configurations and annotation data
- Supports simultaneously opening and managing multiple project windows
- Automatically saves annotations to SQLite database
- Support for project data backup and migration

## Unique Advantages

### Intelligent Automatic Annotation
KBoxLabel integrates the advanced YOLOv8 object detection model, which can automatically identify objects in images and generate annotation boxes, greatly improving annotation efficiency. Users can enjoy one-click automatic annotation by simply loading a pre-trained model.

### Hierarchical Category Management
Supports parent-child category structures, allowing users to create complex category systems. For example, "Vehicle" can be created as a parent category with "Car", "Truck", and "Motorcycle" as child categories. This hierarchical structure facilitates organization and management of complex annotation categories.

### Efficient Operation Experience
Provides rich keyboard shortcuts and mouse operation support:
- Ctrl+Mouse Wheel: Image zoom
- Arrow keys: Fine-tune annotation box position
- Shift+Arrow keys: Adjust annotation box edges
- Ctrl+Shift+Arrow keys: Adjust annotation box size
- Box selection supports simultaneous operation of multiple annotation boxes
- Supports drag-and-drop sorting of annotation lists
- Right-click menu for quick operations

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

## Quick Start

### Launch the Application
```bash
python src/main.py
```

### Basic Operation Flow
1. Create or open a project
2. Import image files
3. Create required annotation categories
4. Perform image annotation
5. Save annotation data

## Usage Guide

### Project Management
- Click "New Project" to create a new project and select the project save directory
- Click "Open Project" to open an existing project
- Quickly access historical projects from the "Recently Opened Projects" list

### Image Management
- Use the "Import Images" function to add images to the project
- Browse all images in the left image list
- Right-click on images for operations such as renaming and deleting
- Support jumping to specified images or the last annotated image

### Annotation Category Management
- Manage annotation categories in the right category list
- Support adding, deleting, and renaming categories
- Adjust category order through drag and drop
- Support setting parent-child category relationships
- Support modifying category colors

### Image Annotation Operations
1. Select the category to annotate in the category list
2. Hold down the left mouse button in the image area to drag and create an annotation box
3. Adjust the position and size of the annotation box via mouse or keyboard
4. Right-click on the annotation box for operations such as deletion and sending to back
5. Support batch operations on multiple annotation boxes

### Keyboard Shortcuts
- `Delete` / `Backspace`: Delete selected annotations
- `Ctrl+S`: Save annotations
- `Ctrl+Mouse Wheel`: Image zoom
- `Shift+Ctrl+Mouse Wheel`: Image zoom (more precise)
- Arrow keys: Fine-tune selected annotation positions
- `Shift+Arrow Keys`: Adjust the four sides of selected annotations
- `Ctrl+Shift+Arrow Keys`: Adjust the size of selected annotations

## Automatic Annotation

KBoxLabel integrates powerful automatic annotation functionality, utilizing the YOLOv8 model to quickly generate high-quality initial annotations:

### Configure Automatic Annotation
1. Click the "Config" button in the toolbar
2. Select the YOLOv8 model file (.pt format)
3. Configure parameters such as confidence threshold and IOU threshold

### Execute Automatic Annotation
1. Right-click on images in the image list
2. Select "Run" to perform automatic annotation on a single image
3. Select "Run All" to perform automatic annotation on all images

### Automatic Annotation Parameter Descriptions
- **Confidence Threshold**: Filter low-confidence detection results. Higher values make results more reliable but may miss detections
- **IOU Threshold**: Intersection-over-Union threshold for non-maximum suppression to remove duplicate detections
- **Batch Size**: Number of images processed at once, affecting processing speed and memory usage
- **Input Size**: Model input image dimensions, affecting detection accuracy and speed

## Data Export

KBoxLabel supports exporting annotation data as YOLO format training datasets:

### YOLO Dataset Export
1. Click menu bar "File" -> "Train" -> "YOLO Dataset"
2. Select the training data save directory
3. The system will automatically organize data according to training/validation set ratio (default 8:2)
4. Generate standard YOLO dataset structure with images and labels subdirectories
5. Automatically generate dataset.yaml configuration file

### Data Storage Structure
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