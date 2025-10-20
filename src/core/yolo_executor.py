import logging
from pathlib import Path
from typing import Optional

from PIL import Image  # 用于获取图像尺寸

from src.models.sql.kolo_item import KoloItem


class YOLOExecutor:
    """YOLO模型执行器，负责加载模型和执行目标检测"""
    
    yolo_model_path_key = "yolo_model_path"  # 类属性，固定值为"yolo_model_path"

    def __init__(self):
        self.yolo_model = None  # 存储加载好的YOLO模型
        self.model_name = None  # 存储模型名称
        self.yolo_model_path: Optional[Path] = None  # 实例属性，存储加载的模型路径

    def is_model_loaded(self) -> bool:
        """
        判断模型是否已经加载

        返回:
            如果模型已加载则返回True，否则返回False
        """
        return self.yolo_model is not None and self.yolo_model_path is not None and self.yolo_model_path.exists()

    def load_yolo(self, model_path: Path):
        """
        加载YOLO模型

        参数:
            model_path: YOLO模型文件的路径

        异常:
            当模型加载失败时抛出异常
        """
        try:
            # 延迟导入，只有在需要时才导入ultralytics
            from ultralytics import YOLO

            # 检查模型文件是否存在
            if not model_path.exists():
                error_msg = f"YOLO model file not found: {str(model_path)}"
                logging.error(error_msg)
                raise FileNotFoundError(error_msg)

            # 加载模型
            self.yolo_model = YOLO(str(model_path))
            self.model_name = model_path.name
            self.yolo_model_path = model_path  # 保存模型路径
            logging.info(f"Loaded YOLO model: {self.model_name}")
            return True

        except ImportError:
            error_msg = "Please install ultralytics library first: pip install ultralytics"
            logging.error(error_msg)
            self.clear_model()
            raise Exception(error_msg)
        except Exception as e:
            error_msg = f"Error loading YOLO model: {str(e)}"
            logging.error(error_msg)
            self.clear_model()
            raise Exception(error_msg) from e

    def clear_model(self):
        self.yolo_model = None  # 存储加载好的YOLO模型
        self.model_name = None  # 存储模型名称
        self.yolo_model_path = None  # 实例属性，存储加载的模型路径

    def process_detection_results(self, results, img_width, img_height, image_name=None) -> list[KoloItem]:
        """
        新增方法：处理检测结果并格式化为指定格式
        参数:
            results: YOLO模型返回的检测结果
            img_width: 图像宽度
            img_height: 图像高度
            image_name: 图像名称（可选），用于创建KoloItem对象
        返回:
            格式化的检测结果列表，类型为list[KoloItem]
        """
        detection_results = []
        for result in results:
            for box in result.boxes:
                # 获取类别ID和置信度
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # 获取类别名称并进行base64编码
                class_name = self.yolo_model.names[class_id]
                
                # 获取边界框坐标并转换为归一化坐标
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                x_center = (x1 + x2) / 2 / img_width
                y_center = (y1 + y2) / 2 / img_height
                width = (x2 - x1) / img_width
                height = (y2 - y1) / img_height
                
                # 创建KoloItem对象
                kolo_item = KoloItem()
                kolo_item.kid = KoloItem.gen_kid()
                kolo_item.image_name = image_name if image_name else ''
                kolo_item.class_name = class_name
                kolo_item.x_center = f"{x_center:.9f}"
                kolo_item.y_center = f"{y_center:.9f}"
                kolo_item.width = f"{width:.9f}"
                kolo_item.height = f"{height:.9f}"
                
                # 添加到结果列表
                detection_results.append(kolo_item)
        return detection_results

    def exec_yolo(self, img_path: Path):
        """使用yolo识别目标，从.kolo文件读取现有数据，合并结果"""
        # 保留原有参数检查逻辑
        if not self.is_model_loaded():
            error_msg = "No YOLO model loaded! Please load a model first."
            raise Exception(error_msg)

        if not img_path.exists():
            error_msg = f"Image file not found: {str(img_path)}"
            raise FileNotFoundError(error_msg)

        # 自动获取图像尺寸
        try:
            with Image.open(img_path) as img:
                img_width, img_height = img.size
            logging.debug(f"获取图像尺寸: {img_width}x{img_height}")
        except Exception as e:
            logging.error(f"获取图像尺寸失败: {str(e)}")
            raise

        # 执行检测并处理结果
        detection_results = self.process_detection_results(
            self.yolo_model(str(img_path)),
            img_width,
            img_height,
            img_path.name
        )
        logging.debug(f"YOLO检测到 {len(detection_results)} 个目标")

        # 读取同名.kolo文件并合并符合格式的内容
        kolo_path = img_path.with_suffix('.kolo')
        logging.debug(f"尝试读取.kolo文件: {kolo_path}")

        if kolo_path.exists():
            try:
                with open(kolo_path, 'r', encoding='utf-8') as f:  # 支持带BOM的UTF-8文件
                    kolo_lines = f.readlines()

                logging.debug(f"成功读取.kolo文件，共 {len(kolo_lines)} 行")
                added_count = 0  # 统计成功添加的行数

                # 验证每行格式并合并
                for line_num, line in enumerate(kolo_lines, 1):
                    original_line = line
                    line = line.strip()

                    if not line:  # 跳过空行
                        continue

                    # 检查格式是否匹配（5个部分）
                    parts = line.split()
                    if len(parts) != 5:
                        logging.warning(f".kolo文件第{line_num}行格式错误（部分数量不对）: {original_line[:50]}...")
                        continue

                    # 验证坐标部分是否为浮点数
                    try:
                        # 只验证后四个坐标部分
                        float(parts[1])  # x_center
                        float(parts[2])  # y_center
                        float(parts[3])  # width
                        float(parts[4])  # height
                        
                        # 解码类别名称
                        import base64
                        class_name = base64.b64decode(parts[0]).decode('utf-8')
                        
                        # 创建对应的KoloItem对象
                        from src.models.sql.kolo_item import KoloItem
                        kolo_item = KoloItem()
                        kolo_item.kid = KoloItem.gen_kid()
                        kolo_item.image_name = img_path.name
                        kolo_item.class_name = class_name
                        kolo_item.x_center = parts[1]
                        kolo_item.y_center = parts[2]
                        kolo_item.width = parts[3]
                        kolo_item.height = parts[4]

                        # 格式验证通过，添加到结果中
                        detection_results.append(kolo_item)
                        added_count += 1
                    except (ValueError, base64.binascii.Error, UnicodeDecodeError):
                        logging.warning(f".kolo文件第{line_num}行坐标格式错误: {original_line[:50]}...")
                        continue

                logging.debug(f"从.kolo文件成功添加 {added_count} 个标注")

            except Exception as e:
                # 记录错误并提示用户
                error_msg = f"读取或处理.kolo文件时出错: {str(e)}"
                logging.error(error_msg)
                # 这里可以根据需要决定是否抛出异常中断执行
                # raise Exception(error_msg)
        else:
            logging.debug(f".kolo文件不存在: {kolo_path}")

        # 合并相似结果并返回
        merged_results = self.merge_similar_detections(detection_results)
        logging.debug(f"合并后最终结果数量: {len(merged_results)}")
        return merged_results

    @staticmethod
    def merge_similar_detections(detection_results: list[KoloItem], threshold=0.05):
        """
        合并类别相同且位置相近的检测结果，保留第一个出现的条目

        参数:
            detection_results: 原始检测结果列表，每个元素为KoloItem对象
            threshold: 位置相近的阈值，坐标差异小于此值视为相近，默认0.01（归一化坐标下）

        返回:
            合并后的检测结果列表，每个元素为KoloItem对象
        """
        from collections import defaultdict
        
        print(f'传入：{len(detection_results)}')

        # 解析检测结果并按类别分组
        grouped_results = defaultdict(list)  # key: 类别名称, value: [(x_center, y_center, width, height, KoloItem对象), ...]

        for item in detection_results:
            if not isinstance(item, KoloItem):
                # 格式不正确的条目直接保留
                grouped_results["__invalid__"].append((None, None, None, None, item))
                continue

            try:
                # 获取类别名称
                class_name = item.class_name
                # 转换坐标为浮点数
                x_center = float(item.x_center)
                y_center = float(item.y_center)
                width = float(item.width)
                height = float(item.height)

                grouped_results[class_name].append((x_center, y_center, width, height, item))
            except ValueError:
                # 坐标格式错误
                grouped_results["__invalid__"].append((None, None, None, None, item))

        # 对每个类别组进行相似合并
        merged = []
        for class_name, items in grouped_results.items():
            if class_name == "__invalid__":
                # 直接保留无效条目
                merged.extend([item[4] for item in items])
                continue

            # 用于记录已保留的条目
            kept = []
            for item in items:
                xc, yc, w, h, original_item = item
                is_similar = False

                # 与已保留的条目比较
                for kept_item in kept:
                    kept_xc, kept_yc, kept_w, kept_h, _ = kept_item
                    # 检查四个坐标是否都在阈值范围内
                    if (abs(xc - kept_xc) < threshold and
                            abs(yc - kept_yc) < threshold and
                            abs(w - kept_w) < threshold and
                            abs(h - kept_h) < threshold):
                        is_similar = True
                        break

                # 如果相似，打印日志
                if is_similar:
                    print(f'相似：{item}')
                else:
                    kept.append(item)

            # 将保留的条目按原始顺序添加到结果（取原始KoloItem对象）
            merged.extend([item[4] for item in kept])
        print(f'传出：{len(merged)}')
        return merged
