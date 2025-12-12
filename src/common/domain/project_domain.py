from pathlib import Path
from typing import Optional

from src.common.domain import AnnotationCategory
from src.common.domain.abs_sqlite_domain import AbsSqliteDomain
from src.common.domain.models.kolo_item import KoloItem
from src.common.domain.models.kv_config import KVConfig
from src.common.god.ksnowflake import KSnowflake


class ProjectDomain(AbsSqliteDomain):
    """数据库领域类"""
    def __init__(self, db_path: Path):
        super().__init__(db_path)

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
            print(f"第一次事务：因 class_name 匹配更新 {updated_count_class} 条AnnotationCategory 记录")

            # 第二次事务：更新 parent_name（独立事务，避免自引用冲突）
            updated_count_parent = session.query(AnnotationCategory).filter(
                AnnotationCategory.parent_name == old_class_name
            ).update({AnnotationCategory.parent_name: new_class_name})
            print(f"第二次事务：因 parent_name 匹配更新 {updated_count_parent} 条AnnotationCategory 记录")

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

    def change_category_class_id(self, category_name: str, new_class_id: int):
        """
        在数据库中，把annotation_category表中class_name=category_name的项目，全部改成class_id=new_class_id
        :param category_name: 类别名称
        :param new_class_id: 新类别ID
        """
        # 获取数据库会话
        session = self.db_session()
        try:
            # 更新annotation_category表中class_name等于category_name的记录的class_id
            updated_count = session.query(AnnotationCategory).filter(
                AnnotationCategory.class_name == category_name
            ).update({AnnotationCategory.class_id: new_class_id})
            
            print(f"更新了 {updated_count} 条AnnotationCategory记录的class_id为{new_class_id}")
            
            # 同时也要更新kolo_item表中class_name等于category_name的记录的class_id
            # 但实际上kolo_item表没有class_id字段，只有class_name字段，所以不需要更新kolo_item表
            
            session.commit()
            print('事务执行完成')
        except Exception as e:
            # 回滚事务
            session.rollback()
            print(f"更新类别class_id失败: {str(e)}")
            raise e
        finally:
            # 关闭会话
            session.close()

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

    def get_max_category_id(self):
        """
        获取annotation_category表中最大的class_id值
        :return: 最大的class_id值，如果没有记录则返回0
        """
        session = self.db_session()
        try:
            # 查询annotation_category表中最大的class_id值
            max_id = session.query(AnnotationCategory.class_id).order_by(AnnotationCategory.class_id.desc()).first()
            return max_id[0] if max_id else 0
        finally:
            session.close()

    def query_all_categories(self) -> list[AnnotationCategory]:
        """
        查询annotation_category表中的所有数据
        :return: 所有数据列表
        """
        with self.db_session() as session:
            return session.query(AnnotationCategory).order_by(AnnotationCategory.order).all()

    def resave_all_categories(self, sql_annotation_category_list: list[AnnotationCategory]):
        """
        重新保存所有类别
        首先删除SQLAnnotationCategory表中全部的数据，然后保存传入的所有对象。
        """
        try:
            with self.db_session() as session:
                # 删除所有现有类别
                session.query(AnnotationCategory).delete()

                # 批量添加（高效）
                if sql_annotation_category_list:
                    session.add_all(sql_annotation_category_list)

                # 提交事务（上下文块内完成）
                session.commit()
        except Exception as e:
            # 上下文管理器的__exit__会自动处理rollback（取决于db_session的实现）
            # 若自定义上下文管理器未处理，可手动捕获并抛出
            print(f"重新保存类别时出错: {str(e)}")
            raise e

    def gen_category_map(self) -> dict[str, AnnotationCategory]:
        """
        从项目信息中加载所有标注类别，并构建一个映射字典。

        返回:
            dict[str, AnnotationCategory]: 以类别名称为键，AnnotationCategory 对象为值的字典。
            如果某个类别有父类别（parent_name），则其值会被替换为其父类别的 AnnotationCategory 对象。

        注意事项:
            - 此方法假定 self.project_info.categories 包含所有可用的类别信息
            - 父类别引用必须形成有效的树状结构，不支持循环引用
            - 若父类别不存在，则保留原始类别对象
        """
        # 初始化类别映射字典
        category_map = {}

        # 第一步：建立基础映射（类别名称 -> AnnotationCategory 对象）
        all_categories = self.query_all_categories()
        for category in all_categories:
            category_map[category.class_name] = category
        # 第二步：遍历category_map，并更新父类别引用
        for category in all_categories:
            if category.parent_name:
                parent_category = category_map.get(category.parent_name)
                if parent_category:
                    category_map[category.class_name] = parent_category
        print(f'category_map -> {category_map}')
        return category_map
