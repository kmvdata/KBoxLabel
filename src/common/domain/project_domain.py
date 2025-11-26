from pathlib import Path
from typing import Optional

from PyQt5.QtGui import QColor

from src.common.domain.abs_sqlite_domain import AbsSqliteDomain
from src.common.domain.models.annotation_category import AnnotationCategory as SQLAnnotationCategory, AnnotationCategory
from src.common.domain.models.kolo_item import KoloItem
from src.common.domain.models.kv_config import KVConfig
from src.common.god.ksnowflake import KSnowflake
from src.models.dto.annotation_category_dto import AnnotationCategoryDTO


class ProjectDomain(AbsSqliteDomain):
    """数据库领域类"""
    def __init__(self, db_path: Path):
        super().__init__(db_path)
        self._categories: list[AnnotationCategoryDTO] = []
        self.load_categories()
    
    @property
    def categories(self) -> list[AnnotationCategoryDTO]:
        """获取类别列表"""
        return self._categories
    
    @categories.setter
    def categories(self, value: list[AnnotationCategoryDTO]):
        """设置类别列表"""
        self._categories = value
        self.refresh_order_entire_list()

    def model_path_in_db(self) -> Optional[Path]:
        """从数据库查询模型路径"""
        # 创建数据库会话
        session = self.db_session()
        try:
            # 查询数据库中的模型路径
            kv_record = session.query(KVConfig).filter(KVConfig.key == "yolo_model_path").first()
            if kv_record and kv_record.value:
                return Path(kv_record.value)
            else:
                return None
        finally:
            session.close()
            
    def save_model_path(self, model_path: Path):
        """保存模型路径到数据库"""
        session = self.db_session()
        try:
            # 查询是否已有记录
            kv_record = session.query(KVConfig).filter(KVConfig.key == "yolo_model_path").first()

            # 保存或更新路径
            if kv_record:
                kv_record.value = str(model_path)
            else:
                # 创建新记录
                kv_record = KVConfig()
                kv_record.kid = KSnowflake().gen_kid()
                kv_record.key = "yolo_model_path"
                kv_record.value = str(model_path)
                kv_record.comment = "YOLO模型路径"
                session.add(kv_record)

            session.commit()
        except Exception as e:
            session.rollback()
            print(f"更新数据库中的YOLO模型路径失败: {str(e)}")
        finally:
            session.close()
            
    def delete_model_path(self):
        """从数据库中删除模型路径"""
        # 创建数据库会话
        session = self.db_session()
        try:
            # 删除模型路径记录
            session.query(KVConfig).filter(KVConfig.key == "yolo_model_path").delete()
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"删除数据库中的YOLO模型路径失败: {str(e)}")
        finally:
            session.close()
            
    def save_categories(self):
        """
        将类别列表保存到数据库中
        """
        # 开始事务
        session = self.db_session()
        try:
            # 清除现有的所有类别
            session.query(SQLAnnotationCategory).delete()

            # 添加所有当前类别
            for category in self.categories:
                sql_category = SQLAnnotationCategory()
                sql_category.class_id = category.class_id
                sql_category.class_name = category.class_name
                sql_category.color_r = category.color.red()
                sql_category.color_g = category.color.green()
                sql_category.color_b = category.color.blue()
                sql_category.parent_name = category.parent_name
                sql_category.order = category.order
                session.add(sql_category)

            # 提交事务
            session.commit()
        except Exception as e:
            # 回滚事务
            session.rollback()
            raise e
        finally:
            session.close()
            
    def load_categories(self):
        """
        从数据库加载类别列表
        """
        # 开始会话
        session = self.db_session()
        # 转换为AnnotationCategory对象列表
        categories: list = []
        try:
            # 查询所有类别，按order字段排序
            sql_categories = session.query(SQLAnnotationCategory).order_by(SQLAnnotationCategory.order).all()
            for sql_cat in sql_categories:
                category = AnnotationCategoryDTO(
                    class_id=sql_cat.class_id,
                    class_name=sql_cat.class_name
                )
                category.color = QColor(sql_cat.color_r, sql_cat.color_g, sql_cat.color_b)
                category.parent_name = sql_cat.parent_name  # 添加加载parent_name字段
                categories.append(category)

            self.categories = categories
            self.refresh_order_entire_list()
            return self.categories
        except Exception as e:
            print(f"加载类别列表失败: {str(e)}")
        finally:
            session.close()

    def add_categories(self, new_categories: list[AnnotationCategoryDTO]):
        # 把new_categories添加到self.categories中
        # 获取当前已存在的类别名称集合
        existing_names = {category.class_name for category in self.categories}
        
        # 添加不重复的新类别
        for category in new_categories:
            if category.class_name not in existing_names:
                self.categories.append(category)
                existing_names.add(category.class_name)
        
        # 重新排序
        self.refresh_order_entire_list()

    def rename_image_for_kolo_item(self, old_img_name: str, new_img_name: str):
        """
        在数据库中，把kolo_item表中image_name=old_img_name的项目，全部改成image_name=new_img_name
        :param old_img_name: 旧图片名称
        :param new_img_name: 新图片名称
        """
        # 获取数据库会话
        session = self.db_session()
        try:
            # 更新kolo_item表中所有image_name等于old_img_name的记录为new_img_name
            session.query(KoloItem).filter(KoloItem.image_name == old_img_name).update(
                {KoloItem.image_name: new_img_name}
            )
            # 提交事务
            session.commit()
        except Exception as e:
            # 回滚事务
            session.rollback()
            print(f"重命名图片关联的kolo_item记录失败: {str(e)}")
            raise e
        finally:
            # 关闭会话
            session.close()
            
    def rename_category(self, old_class_name: str, new_class_name: str):
        """
        在数据库中，把kolo_item表中class_name=old_class_name的项目，全部改成class_name=new_class_name。
        注意：执行完这个方法后，应该立即更新project_info中的categories，防止旧数据被保存。
        :param old_class_name: 旧类别名称
        :param new_class_name: 新类别名称
        """
        # 获取数据库会话
        session = self.db_session()
        try:
            # 第一次事务：更新 class_name（独立事务）
            updated_count_class = session.query(AnnotationCategory).filter(
                AnnotationCategory.class_name == old_class_name
            ).update({AnnotationCategory.class_name: new_class_name})
            print(f"第一次事务：因 class_name 匹配更新 {updated_count_class} 条 AnnotationCategory 记录")

            # 第二次事务：更新 parent_name（独立事务，避免自引用冲突）
            updated_count_parent = session.query(AnnotationCategory).filter(
                AnnotationCategory.parent_name == old_class_name
            ).update({AnnotationCategory.parent_name: new_class_name})
            print(f"第二次事务：因 parent_name 匹配更新 {updated_count_parent} 条 AnnotationCategory 记录")

            # 第三次事务：更新 KoloItem（如果需要，也可独立，但通常无冲突）
            kolo_updated = session.query(KoloItem).filter(
                KoloItem.class_name == old_class_name
            ).update({KoloItem.class_name: new_class_name})
            print(f"第三次事务：因 class_name 匹配更新 {kolo_updated} 条 KoloItem 记录")
            session.commit()
            print('事务执行完成')
        except Exception as e:
            # 回滚事务
            session.rollback()
            print(f"重命名类别关联的kolo_item记录失败: {str(e)}")
            raise e
        finally:
            # 关闭会话
            session.close()

        # rename执行完成后重新加载categories
        self.load_categories()
            
    def load_kolo_items_for_image(self, img_name: str) -> list[KoloItem]:
        """
        从数据库加载指定图片的kolo项
        :param img_name: 图片名称
        :return: KoloItem列表
        """
        try:
            # 创建数据库会话
            with self.db_session() as session:
                # 从数据库读取image_name为img_name的行
                kolo_items = session.query(KoloItem).filter(KoloItem.image_name == img_name).all()
                return kolo_items
        except Exception as e:
            print(f"从数据库加载Kolo项目时出错: {str(e)}")
            return []
            
    def delete_kolo_items_for_image(self, img_name: str):
        """
        从数据库删除指定图片的kolo项
        :param img_name: 图片名称
        """
        try:
            # 创建数据库会话
            with self.db_session() as session:
                # 删除image_name为img_name的所有行
                deleted_count = session.query(KoloItem).filter(KoloItem.image_name == img_name).delete()
                session.commit()  # 确保提交事务
                print(f"从数据库删除了 {deleted_count} 个Kolo项目")
        except Exception as e:
            print(f"从数据库删除Kolo项目时出错: {str(e)}")

    def restore_kolo_item_for_image(self, kolo_items: list[KoloItem], img_name: str):
        """
        从数据库删除指定图片的kolo项, 然后在同一个事务中保存kolo项到数据库
        :param kolo_items: KoloItem对象列表
        :param img_name: 图片名称
        """

        def transaction_func(session):
            # 删除现有记录
            deleted_count = session.query(KoloItem).filter(KoloItem.image_name == img_name).delete()

            # 准备要保存的KoloItem对象
            new_kolo_items = []
            for item in kolo_items:
                new_item = KoloItem()
                new_item.kid = KSnowflake().gen_kid()
                new_item.image_name = item.image_name
                new_item.class_name = item.class_name
                new_item.x_center = item.x_center
                new_item.y_center = item.y_center
                new_item.width = item.width
                new_item.height = item.height
                new_kolo_items.append(new_item)

            # 批量插入新对象
            session.add_all(new_kolo_items)
            session.flush()  # 强制检查约束违规
            print(f"删除: {deleted_count}, 保存:  {len(new_kolo_items)} 个Kolo项目到数据库")

        try:
            self.execute_in_transaction(transaction_func)
            print(f"保存了 {len(kolo_items)} 个Kolo项目到数据库")
        except Exception as e:
            print(f"保存Kolo项目到数据库时出错: {str(e)}")

    def load_image_names_from_kilo_item(self, page: int = 1, page_size: int = 1000) -> list[str]:
        """
        从kolo_item表中检索出所有不重复的image_name，并按image_name排序
        
        :param page: 页码，从1开始
        :param page_size: 每页大小
        :return: image_name列表
        """
        try:
            # 创建数据库会话
            with self.db_session() as session:
                # 查询所有不重复的image_name，并按image_name排序
                image_names = session.query(KoloItem.image_name) \
                    .distinct() \
                    .order_by(KoloItem.image_name) \
                    .offset((page - 1) * page_size) \
                    .limit(page_size) \
                    .all()
                
                # 提取image_name字符串
                return [item[0] for item in image_names]
        except Exception as e:
            print(f"从数据库加载image_name列表时出错: {str(e)}")
            return []

    def count_image_names_from_kilo_item(self) -> int:
        """
        统计kolo_item表中不重复的image_name数量
        
        :return: 不重复的image_name数量
        """
        try:
            # 创建数据库会话
            with self.db_session() as session:
                # 查询所有不重复的image_name数量
                count = session.query(KoloItem.image_name).distinct().count()
                return count
        except Exception as e:
            print(f"统计数据库中image_name数量时出错: {str(e)}")
            return 0

    def count_kilo_items_for_category(self, category_name: str) -> int:
        """
        统计kolo_item表中的class_name=category_name的记录数量
        :return: 记录数量
        """
        try:
            # 创建数据库会话
            with self.db_session() as session:
                count = session.query(KoloItem).filter(KoloItem.class_name == category_name).count()
                return count
        except Exception as e:
            print(f"统计数据库中kolo_item数量时出错: {str(e)}")
            return 0

    def refresh_order_entire_list(self):
        """根据parent_name指向的父子关系以及整个self.categories列表当前顺序，重新设置每个category的order值"""
        # 创建类别名称到类别对象的映射
        category_map = {cat.class_name: cat for cat in self.categories}
        
        # 分离一级和二级类别
        top_level_categories = []
        second_level_categories = []
        
        for cat in self.categories:
            if cat.parent_name is None:
                top_level_categories.append(cat)
            else:
                second_level_categories.append(cat)
        
        # 为一级类别分配order值 (1000, 2000, 3000...)
        order_value = 1000
        for cat in top_level_categories:
            cat.order = order_value
            order_value += 1000
        
        # 处理二级类别
        # 构建父类别到其子类别的映射
        parent_to_children = {}
        invalid_second_level = []  # 存储无效的二级类别
        
        for cat in second_level_categories:
            parent_name = cat.parent_name
            if parent_name in category_map:
                # 有效的二级类别
                if parent_name not in parent_to_children:
                    parent_to_children[parent_name] = []
                parent_to_children[parent_name].append(cat)
            else:
                # 无效的二级类别，清除parent_name
                cat.parent_name = None
                invalid_second_level.append(cat)
        
        # 为有效的二级类别分配order值
        for parent_name, children in parent_to_children.items():
            parent_category = category_map[parent_name]
            # 从父类order+1开始，每个子类间隔为1
            child_order = parent_category.order + 1
            for child in children:
                child.order = child_order
                child_order += 1
        
        # 为无效的二级类别（现在是一级类别）分配order值
        if invalid_second_level:
            # 找到最后一个一级类别的order值，继续递增
            last_order = 0
            if top_level_categories:
                last_order = top_level_categories[-1].order
            else:
                # 如果还没有一级类别，从1000开始
                last_order = 0
            
            order_value = last_order + 1000
            for cat in invalid_second_level:
                cat.order = order_value
                order_value += 1000
                # 同时添加到一级类别列表中，保证顺序正确
                top_level_categories.append(cat)

        self.save_categories()

    def insert_category(self, index: int, category: AnnotationCategoryDTO):
        self.categories.insert(index, category)
        self.refresh_order_entire_list()

    def append(self, category: AnnotationCategoryDTO):
        self.categories.append(category)
        self.refresh_order_entire_list()

    def delete_category(self, category_name: str):
        """
        删除指定类别的kolo项
        :param category_name: 类别名称
        """
        try:
            # 创建数据库会话
            with self.db_session() as session:
                # 删除kolo_item表中所有class_name等于category_name的数据
                session.query(KoloItem).filter(KoloItem.class_name == category_name).delete()

                # 删除annotation_category表中class_name为category_name的数据
                session.query(AnnotationCategory).filter(AnnotationCategory.class_name == category_name).delete()

                # 把annotation_category表中parent_name为category_name的数据的parent_name字段都设置成None
                session.query(AnnotationCategory).filter(AnnotationCategory.parent_name == category_name).update({
                    AnnotationCategory.parent_name: None
                })

                session.commit()  # 确保提交事务
                print(f"已删除类别 '{category_name}' 相关的所有数据")
        except Exception as e:
            print(f"删除类别 '{category_name}' 时出错: {str(e)}")
            raise
        # 删除完成后重新加载categories
        self.load_categories()

    def move_category_as_children(self, parent_category_name: str, child_category_name: str, before_category_name: Optional[str] = None):
        """
        将一个类别移动为另一个类别的子类别，并可选择性地调整其在子类别列表中的位置。
        
        此方法会将[child_category_name](file:///Users/kermit/Projects/KBoxLabel/src/common/domain/project_domain.py#L445-L445)设置为[parent_category_name](file:///Users/kermit/Projects/KBoxLabel/src/common/domain/project_domain.py#L445-L445)的子类别，
        并根据[before_category_name](file:///Users/kermit/Projects/KBoxLabel/src/common/domain/project_domain.py#L445-L445)参数决定其在子类别列表中的位置。
        
        Args:
            parent_category_name (str): 父类别的名称，将成为[child_category_name](file:///Users/kermit/Projects/KBoxLabel/src/common/domain/project_domain.py#L445-L445)的父类别
            child_category_name (str): 要移动的子类别的名称
            before_category_name (Optional[str]): 可选参数，指定[child_category_name](file:///Users/kermit/Projects/KBoxLabel/src/common/domain/project_domain.py#L445-L445)应该放置在其后的类别名称。
                                             如果为None，则[child_category_name](file:///Users/kermit/Projects/KBoxLabel/src/common/domain/project_domain.py#L445-L445)会被放置在父类别的最后位置。
                                             
        Raises:
            ValueError: 当任何指定的类别名称在当前类别列表中找不到时抛出此异常
            
        Example:
            # 将"狗"类别设置为"动物"类别的子类别，并放置在"猫"类别之后
            project_domain.move_category_as_children("动物", "狗", "猫")
            
            # 将"鸟"类别设置为"动物"类别的子类别，并放置在最后
            project_domain.move_category_as_children("动物", "鸟")
        """
        # 检查参数合法性，确保所有涉及的类别都存在于当前类别列表中
        category_names = {cat.class_name for cat in self.categories}
        if parent_category_name not in category_names:
            raise ValueError(f"Parent category '{parent_category_name}' not found")
        if child_category_name not in category_names:
            raise ValueError(f"Child category '{child_category_name}' not found")
        if before_category_name is not None and before_category_name not in category_names:
            raise ValueError(f"Before category '{before_category_name}' not found")
        
        # 查找要移动的子类别对象
        child_category = None
        for cat in self.categories:
            if cat.class_name == child_category_name:
                child_category = cat
                break
        
        # 设置为父类的子项
        child_category.parent_name = parent_category_name
        
        # 如果指定了before_category_name，则调整顺序
        if before_category_name is not None:
            # 找到目标位置并重新排列
            self.refresh_order_entire_list()
            
            # 查找before_category和child_category在列表中的位置
            before_index = None
            child_index = None
            for i, cat in enumerate(self.categories):
                if cat.class_name == before_category_name:
                    before_index = i
                elif cat.class_name == child_category_name:
                    child_index = i
            
            # 如果before_category在child_category之前，需要将child_category移到before_category之后
            if before_index is not None and child_index is not None and before_index < child_index:
                # 重新排列列表，将子类别移动到指定位置之后
                self.categories.remove(child_category)
                self.categories.insert(before_index + 1, child_category)
        else:
            # 没有指定before_category_name，只需设置parent_name即可
            pass
            
        # 重新计算并更新所有类别的顺序值
        self.refresh_order_entire_list()

    def move_category_by_name_before(self, moved_category_name: str, target_category_name: str):
        """
        将一个类别移动到另一个类别之前，并保持相同的父级关系
        
        Args:
            moved_category_name (str): 要移动的类别名称
            target_category_name (str): 目标类别名称（将移动到此类别之前）
        """
        # 查找要移动的类别和目标类别
        moved_category, target_category = self._find_categories_by_name(moved_category_name, target_category_name)
        
        if moved_category == target_category:
            return  # 位置相同，无需移动
            
        # 获取目标的父级
        target_parent_name = target_category.parent_name
        
        # 设置移动项的父级与目标项相同
        moved_category.parent_name = target_parent_name
        
        # 更新所有子项的父级为target_parent_name
        moved_children = []
        for cat in self.categories:
            if cat.parent_name == moved_category_name:
                cat.parent_name = target_parent_name
                moved_children.append(cat)
        
        # 重新排序整个列表
        self.refresh_order_entire_list()

    def move_category_by_name_after(self, moved_category_name: str, target_category_name: str):
        """
        将一个类别移动到另一个类别之后，并保持相同的父级关系
        
        Args:
            moved_category_name (str): 要移动的类别名称
            target_category_name (str): 目标类别名称（将移动到此类别之后）
        """
        # 查找要移动的类别和目标类别
        moved_category, target_category = self._find_categories_by_name(moved_category_name, target_category_name)
            
        # 获取目标的父级
        target_parent_name = target_category.parent_name
        
        # 设置移动项的父级与目标项相同
        moved_category.parent_name = target_parent_name
        
        # 更新所有子项的父级为target_parent_name
        moved_children = []
        for cat in self.categories:
            if cat.parent_name == moved_category_name:
                cat.parent_name = target_parent_name
                moved_children.append(cat)
        
        # 调整位置 - 将移动项放在目标项之后
        target_index = self.categories.index(target_category)
        moved_index = self.categories.index(moved_category)
        
        if target_index < moved_index:
            # 如果目标在移动项之前，移动项的新位置是目标项位置
            self.categories.remove(moved_category)
            self.categories.insert(target_index, moved_category)
            
            # 同时移动所有子项
            for child in moved_children:
                self.categories.remove(child)
                self.categories.insert(target_index + 1, child)
        else:
            # 如果目标在移动项之后，移动项的新位置是目标项位置+1
            self.categories.remove(moved_category)
            self.categories.insert(target_index, moved_category)
            
            # 同时移动所有子项
            for child in moved_children:
                self.categories.remove(child)
                self.categories.insert(target_index + 1, child)
        
        # 重新排序整个列表
        self.refresh_order_entire_list()

    def move_category_to_position(self, moved_category_name: str, target_position: int):
        """
        将一个类别移动到指定的位置
        
        Args:
            moved_category_name (str): 要移动的类别名称
            target_position (int): 目标位置索引
        """
        # 查找要移动的类别
        moved_category = None
        moved_index = -1
        for i, cat in enumerate(self.categories):
            if cat.class_name == moved_category_name:
                moved_category = cat
                moved_index = i
                break
        
        if moved_category is None:
            raise ValueError(f"Category {moved_category_name} not found")
        
        # 如果目标位置超出范围，则放在末尾
        if target_position >= len(self.categories):
            target_position = len(self.categories) - 1
        elif target_position < 0:
            target_position = 0
            
        # 如果位置相同，则无需移动
        if moved_index == target_position:
            return
            
        # 移动类别到新位置
        self.categories.remove(moved_category)
        self.categories.insert(target_position, moved_category)
        
        # 重新排序整个列表
        self.refresh_order_entire_list()

    def convert_child_to_top_level(self, category_name: str):
        """
        将子类别转换为顶级类别（设置parent_name为None）
        
        Args:
            category_name (str): 要转换的类别名称
        """
        # 查找类别
        category = None
        for cat in self.categories:
            if cat.class_name == category_name:
                category = cat
                break
        
        if category is None:
            raise ValueError(f"Category {category_name} not found")
        
        # 设置为顶级类别
        category.parent_name = None
        
        # 重新排序整个列表
        self.refresh_order_entire_list()

    def _find_categories_by_name(self, first_category_name: str, second_category_name: str) -> tuple[AnnotationCategoryDTO, AnnotationCategoryDTO]:
        """
        根据两个类别名称查找对应的类别对象

        Args:
            first_category_name (str): 第一个类别名称
            second_category_name (str): 第二个类别名称

        Returns:
            tuple[AnnotationCategoryDTO, AnnotationCategoryDTO]: 两个类别对象

        Raises:
            ValueError: 当任何一个类别名称找不到时抛出此异常
        """
        first_category = None
        second_category = None

        for cat in self.categories:
            if cat.class_name == first_category_name:
                first_category = cat
            elif cat.class_name == second_category_name:
                second_category = cat

        if first_category is None:
            raise ValueError(f"Category {first_category_name} not found")

        if second_category is None:
            print(f"Category {second_category_name} not found")

        return first_category, second_category

    def get_max_category_id(self):
        """
        获取annotation_category表中最大的class_id值
        :return: 最大的class_id值，如果没有记录则返回0
        """
        session = self.db_session()
        try:
            # 查询annotation_category表中最大的class_id值
            max_id = session.query(SQLAnnotationCategory.class_id).order_by(SQLAnnotationCategory.class_id.desc()).first()
            return max_id[0] if max_id else 0
        finally:
            session.close()







