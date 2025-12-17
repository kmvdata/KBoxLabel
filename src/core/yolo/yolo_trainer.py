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

    def organize_training_data(self, source_dir: Path, data_dir: Path, project_domain, split_ratio: float = 0.8):
        """
        整理训练数据，从数据库中获取映射关系，按照图片名分组获取kolo_item，
        并根据映射表创建yolo格式的txt文本
        
        Args:
            source_dir: 源数据目录（项目路径）
            data_dir: 目标数据目录
            project_domain: 项目数据库域对象
            split_ratio: 训练集占比
        """
        # 支持的图片格式
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.tiff'}
        
        # 获取类别映射关系
        category_map = project_domain.gen_category_map()
        class_name_to_id = {category.class_name: category.class_id for category in category_map.values()}
        
        # 获取所有不重复的图片名称并排序
        all_image_names = []
        page = 1
        page_size = 1000
        while True:
            image_names = project_domain.load_image_names_from_kilo_item(page=page, page_size=page_size)
            if not image_names:
                break
            all_image_names.extend(image_names)
            page += 1
        
        # 分割训练集和验证集
        split_index = int(len(all_image_names) * split_ratio)
        train_image_names = all_image_names[:split_index]
        val_image_names = all_image_names[split_index:]
        
        # 处理训练集
        self._process_image_set(train_image_names, source_dir, data_dir / "train", 
                               image_extensions, category_map, class_name_to_id, project_domain)
        
        # 处理验证集
        self._process_image_set(val_image_names, source_dir, data_dir / "val", 
                               image_extensions, category_map, class_name_to_id, project_domain)
        
        # 生成README.md文件
        self._generate_readmes(data_dir)

    def _process_image_set(self, image_names: List[str], source_dir: Path, target_dir: Path,
                          image_extensions: set, category_map: Dict, class_name_to_id: Dict, 
                          project_domain):
        """
        处理图片集，生成对应的YOLO标签文件和复制图片
        
        Args:
            image_names: 图片名称列表
            source_dir: 源目录（项目路径）
            target_dir: 目标目录
            image_extensions: 支持的图片扩展名集合
            category_map: 类别映射
            class_name_to_id: 类别名称到ID的映射
            project_domain: 项目数据库域对象
        """
        # 确保目标目录存在
        (target_dir / "images").mkdir(parents=True, exist_ok=True)
        (target_dir / "labels").mkdir(parents=True, exist_ok=True)
        
        for image_name in image_names:
            # 查找对应的图片文件
            image_file = None
            for ext in image_extensions:
                candidate = source_dir / image_name
                if candidate.exists() and candidate.suffix.lower() == ext:
                    image_file = candidate
                    break
                    
            # 如果找不到图片文件，跳过
            if image_file is None:
                logging.warning(f"未找到图片文件 {image_name}")
                continue
                
            # 从数据库获取该图片的标注信息
            kolo_items = project_domain.load_kolo_items_for_image(image_name)
            
            # 如果没有标注数据，跳过
            if not kolo_items:
                logging.info(f"图片 {image_name} 没有标注数据，跳过")
                continue
                
            # 生成YOLO格式的标签文件
            label_filename = Path(image_name).with_suffix('.txt')
            label_file_path = target_dir / "labels" / label_filename
            
            valid_labels = []
            for item in kolo_items:
                # 处理类别层级映射
                class_name = item.class_name
                mapped_category = category_map.get(class_name)
                if mapped_category:
                    class_name = mapped_category.class_name
                    
                # 获取类别ID
                class_id = class_name_to_id.get(class_name, -1)
                if class_id == -1:
                    logging.warning(f"未找到类别 '{class_name}' 的ID，跳过该标注")
                    continue
                    
                # YOLO格式: class_id x_center y_center width height
                yolo_line = f"{class_id} {item.x_center} {item.y_center} {item.width} {item.height}\n"
                valid_labels.append(yolo_line)
            
            # 只有当有有效的标签时才创建标签文件和复制图片
            if valid_labels:
                # 写入标签文件
                with open(label_file_path, 'w', encoding='utf-8') as f:
                    f.writelines(valid_labels)
                    
                # 复制图片文件
                import shutil
                shutil.copy2(image_file, target_dir / "images" / image_file.name)
            else:
                logging.info(f"图片 {image_name} 没有有效的标签，跳过")

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

    def _generate_readmes(self, data_dir: Path):
        """
        在训练数据目录中生成README.md和README_en.md文件
        
        Args:
            data_dir: 训练数据目录路径
        """
        # 生成中文README
        readme_cn_path = Path(__file__).parent / "README.md"
        destination_cn_path = data_dir / "README.md"
        
        # 生成英文README
        readme_en_path = Path(__file__).parent / "README_en.md"
        destination_en_path = data_dir / "README_en.md"
        
        # 复制中文README文件
        if readme_cn_path.exists():
            import shutil
            shutil.copy2(readme_cn_path, destination_cn_path)
            logging.info(f"已生成 README.md 文件: {destination_cn_path}")
        else:
            logging.warning(f"README.md 模板文件不存在: {readme_cn_path}")
            
        # 复制英文README文件
        if readme_en_path.exists():
            import shutil
            shutil.copy2(readme_en_path, destination_en_path)
            logging.info(f"已生成 README_en.md 文件: {destination_en_path}")
        else:
            logging.warning(f"README_en.md 模板文件不存在: {readme_en_path}")