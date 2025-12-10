import logging
from pathlib import Path
from typing import Optional, Union, List, Dict
from ultralytics import YOLO
import yaml


class YOLOTrainer:
    """
    YOLO模型训练器，用于训练YOLO模型
    支持训练目录下的txt文件及其对应的同名图片文件
    """

    def __init__(self, project_path: Optional[Path] = None):
        """
        初始化YOLO训练器
        
        Args:
            project_path: 项目路径
        """
        self.project_path = project_path
        self.model = None
        self.train_config = {}

    @staticmethod
    def prepare_dataset_yaml( data_dir: Path, class_names: list) -> Path:
        """
        准备数据集yaml配置文件
        
        Args:
            data_dir: 数据目录路径
            class_names: 类别名称列表
            
        Returns:
            yaml配置文件路径
        """
        # 创建训练集和验证集目录结构
        train_dir = data_dir / "train"
        val_dir = data_dir / "val"
        train_dir.mkdir(exist_ok=True)
        val_dir.mkdir(exist_ok=True)
        
        # 创建images和labels子目录
        (train_dir / "images").mkdir(exist_ok=True)
        (train_dir / "labels").mkdir(exist_ok=True)
        (val_dir / "images").mkdir(exist_ok=True)
        (val_dir / "labels").mkdir(exist_ok=True)
        
        # 构建yaml配置
        dataset_config = {
            'path': str(data_dir.absolute()),
            'train': 'train',
            'val': 'val',
            'nc': len(class_names),
            'names': class_names
        }
        
        # 写入yaml文件
        yaml_path = data_dir / "dataset.yaml"
        with open(yaml_path, 'w', encoding='utf-8') as f:
            yaml.dump(dataset_config, f, allow_unicode=True)
            
        return yaml_path

    def organize_training_data(self, source_dir: Path, data_dir: Path, split_ratio: float = 0.8, 
                              categories: Optional[List] = None):
        """
        整理训练数据，将图片和标签文件组织到指定目录结构中
        
        Args:
            source_dir: 源数据目录（包含txt和图片文件）
            data_dir: 目标数据目录
            split_ratio: 训练集占比
            categories: 类别列表，用于处理父子类别映射
        """
        # 支持的图片格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        
        # 获取所有txt文件
        txt_files = list(source_dir.glob("*.txt"))
        
        # 创建类别映射（如果提供了categories）
        class_mapping = {}
        top_level_classes = []
        if categories:
            # 创建从子类到父类的映射
            class_mapping = self._build_class_hierarchy_mapping(categories)
            # 获取顶层类别（没有父类的类别）
            top_level_classes = [cat.class_name for cat in categories if cat.parent_name is None]
        else:
            top_level_classes = None
        
        # 分割训练集和验证集
        split_index = int(len(txt_files) * split_ratio)
        train_txt_files = txt_files[:split_index]
        val_txt_files = txt_files[split_index:]
        
        # 处理训练集
        self._copy_files_to_split_dir(train_txt_files, source_dir, data_dir / "train", image_extensions, 
                                     class_mapping, top_level_classes)
        
        # 处理验证集
        self._copy_files_to_split_dir(val_txt_files, source_dir, data_dir / "val", image_extensions,
                                     class_mapping, top_level_classes)
        
    @staticmethod
    def _build_class_hierarchy_mapping(categories) -> Dict[str, str]:
        """
        构建类别层级映射，将子类别映射到其父类别
        
        Args:
            categories: 类别列表
            
        Returns:
            类别名称到父类别名称的映射字典
        """
        # 创建类别名称到父类别名称的映射
        class_mapping = {}
        for cat in categories:
            if cat.parent_name is not None:
                class_mapping[cat.class_name] = cat.parent_name
                
        return class_mapping

    @staticmethod
    def _copy_files_to_split_dir(txt_files: list, source_dir: Path, target_dir: Path, 
                                image_extensions: set, class_mapping: Optional[Dict] = None,
                                top_level_classes: Optional[List[str]] = None):
        """
        将文件复制到指定的分割目录中
        
        Args:
            txt_files: txt文件列表
            source_dir: 源目录
            target_dir: 目标目录
            image_extensions: 支持的图片扩展名集合
            class_mapping: 类别映射字典（可选）
            top_level_classes: 顶层类别列表（可选）
        """
        # 确保目标目录存在
        (target_dir / "images").mkdir(parents=True, exist_ok=True)
        (target_dir / "labels").mkdir(parents=True, exist_ok=True)
        
        for txt_file in txt_files:
            # 检查是否有对应图片文件
            stem = txt_file.stem
            image_file = None
            
            for ext in image_extensions:
                candidate = source_dir / f"{stem}{ext}"
                if candidate.exists():
                    image_file = candidate
                    break
                    
            if image_file is None:
                logging.warning(f"未找到与标签文件 {txt_file.name} 对应的图片文件")
                continue
                
            # 复制图片文件
            import shutil
            shutil.copy2(image_file, target_dir / "images" / image_file.name)
            
            # 处理并复制标签文件
            if class_mapping is not None and top_level_classes is not None:
                YOLOTrainer._process_label_file(txt_file, target_dir / "labels" / txt_file.name, 
                                               class_mapping, top_level_classes)
            else:
                # 直接复制标签文件
                shutil.copy2(txt_file, target_dir / "labels" / txt_file.name)

    @staticmethod
    def _process_label_file(src_label_path: Path, dst_label_path: Path, 
                           class_mapping: Dict, top_level_classes: List[str]):
        """
        处理标签文件，将子类别映射到父类别
        
        Args:
            src_label_path: 源标签文件路径
            dst_label_path: 目标标签文件路径
            class_mapping: 类别名称映射
            top_level_classes: 顶层类别列表
        """
        try:
            with open(src_label_path, 'r') as src_file:
                lines = src_file.readlines()
                
            processed_lines = []
            for line in lines:
                parts = line.strip().split()
                if not parts:
                    continue
                    
                # 第一个是类别名称（在源文件中存储的是类别名称而不是ID）
                class_name = parts[0]
                # 如果这个类别有父类别，则替换为父类别名称
                if class_name in class_mapping:
                    new_class_name = class_mapping[class_name]
                    # 更新行中的类别名称
                    parts[0] = new_class_name
                
                # 检查是否是顶层类别
                if parts[0] in top_level_classes:
                    processed_lines.append(' '.join(parts) + '\n')
                # 如果不是顶层类别，跳过该行（相当于过滤掉非顶层类别）
                
            # 写入处理后的标签文件
            # 只有当有处理后的行时才写入，否则复制原文件
            if processed_lines:
                with open(dst_label_path, 'w') as dst_file:
                    dst_file.writelines(processed_lines)
            else:
                # 如果没有有效的标签行，复制原文件
                import shutil
                shutil.copy2(src_label_path, dst_label_path)
                logging.warning(f"标签文件 {src_label_path} 中没有有效的顶层类别标签，已复制原始文件")
                
        except Exception as e:
            logging.warning(f"处理标签文件 {src_label_path} 时出错: {e}")
            # 出错时直接复制原文件
            import shutil
            shutil.copy2(src_label_path, dst_label_path)
