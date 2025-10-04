from sqlalchemy import Column, INTEGER, String, DateTime, text, func  # 导入func

from src.common.god.korm_base import KOrmBase


class AnnotationCategory(KOrmBase):
    __tablename__ = 'annotation_category'
    __table_args__ = {'comment': '标注类别表'}

    id = Column(INTEGER, primary_key=True, comment='自增id')
    class_id = Column(INTEGER, nullable=False, unique=False, comment='类别ID')
    class_name = Column(String(64), nullable=False, comment='类别名称')
    
    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(DateTime,
                         default=func.current_timestamp(),  # 插入时默认当前时间
                         onupdate=func.current_timestamp(),  # 更新时自动更新为当前时间
                         comment='更新时间')