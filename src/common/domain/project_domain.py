from pathlib import Path
from typing import Optional, List

from PyQt5.QtGui import QColor

from src.common.god.ksnowflake import KSnowflake
from src.common.domain.abs_sqlite_domain import AbsSqliteDomain
from src.models.dto.annotation_category_dto import AnnotationCategoryDTO
from src.common.domain.models.annotation_category import AnnotationCategory as SQLAnnotationCategory, AnnotationCategory
from src.common.domain.models.kolo_item import KoloItem
from src.common.domain.models.kv_config import KVConfig


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
            
    def save_categories(self, categories: List[AnnotationCategoryDTO]):
        """
        将类别列表保存到数据库中
        """
        # 开始事务
        session = self.db_session()
        try:
            # 清除现有的所有类别
            session.query(SQLAnnotationCategory).delete()

            # 添加所有当前类别
            for category in categories:
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
            
    def load_categories(self) -> List[AnnotationCategoryDTO]:
        """
        从数据库加载类别列表
        """
        # 开始会话
        session = self.db_session()
        # 转换为AnnotationCategory对象列表
        categories: list = []
        try:
            # 查询所有类别
            sql_categories = session.query(SQLAnnotationCategory).all()
            for sql_cat in sql_categories:
                category = AnnotationCategoryDTO(
                    class_id=sql_cat.class_id,
                    class_name=sql_cat.class_name
                )
                category.color = QColor(sql_cat.color_r, sql_cat.color_g, sql_cat.color_b)
                category.parent_name = sql_cat.parent_name  # 添加加载parent_name字段
                categories.append(category)
        except Exception as e:
            print(f"加载类别列表失败: {str(e)}")
        finally:
            session.close()
            return categories
            
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

    @staticmethod
    def _prepare_kolo_items_for_save(kolo_items: list[KoloItem]) -> list[KoloItem]:
        """
        准备KoloItem对象以供保存到数据库
        为每个新对象生成新的 kid，避免主键冲突
        同时创建新的对象实例，避免会话绑定问题
        
        :param kolo_items: 原始KoloItem对象列表
        :return: 准备好的新KoloItem对象列表
        """
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
        return new_kolo_items

    def save_kolo_item_to_db(self, kolo_items: list[KoloItem]):
        """
        保存kolo项到数据库
        :param kolo_items: KoloItem对象列表
        """
        def transaction_func(session):
            # 准备要保存的KoloItem对象
            new_kolo_items = self._prepare_kolo_items_for_save(kolo_items)
            
            # 批量插入新对象
            session.add_all(new_kolo_items)
            session.flush()  # 强制检查约束违规
        
        try:
            self.execute_in_transaction(transaction_func)
            print(f"保存了 {len(kolo_items)} 个Kolo项目到数据库")
        except Exception as e:
            print(f"保存Kolo项目到数据库时出错: {str(e)}")

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
            new_kolo_items = self._prepare_kolo_items_for_save(kolo_items)

            # 批量插入新对象
            session.add_all(new_kolo_items)
            session.flush()  # 强制检查约束违规
            print(f"删除: {deleted_count}, 保存:  {len(new_kolo_items)} 个Kolo项目到数据库")

        try:
            self.execute_in_transaction(transaction_func)
            print(f"保存了 {len(kolo_items)} 个Kolo项目到数据库")
        except Exception as e:
            print(f"保存Kolo项目到数据库时出错: {str(e)}")


    def load_images(self, page: int = 1, page_size: int = 1000) -> list[str]:
        pass

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




