from sqlalchemy import Column, INTEGER, String, DateTime, text, func, Index

from src.common.god.korm_base import KOrmBase


class KoloItem(KOrmBase):
    __tablename__ = 'kolo_item'
    __table_args__ = (
        Index('kolo_item_idx_image_name', 'image_name'),
        Index('kolo_item_idx_class_name', 'class_name'),
        {'comment': 'Kolo项目表'}
    )

    id = Column(INTEGER, primary_key=True, comment='自增id')
    kid = Column(INTEGER, nullable=False, unique=True, comment='唯一kid')

    image_name = Column(String(255), nullable=False, comment='名称')
    class_name = Column(String(64), nullable=False, comment='名称')

    # 4个字符串类型的Column，用于存储高精度坐标值
    x_center = Column(String(64), nullable=False, comment='中心点X坐标')
    y_center = Column(String(64), nullable=False, comment='中心点Y坐标')
    width = Column(String(64), nullable=False, comment='宽度')
    height = Column(String(64), nullable=False, comment='高度')

    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(DateTime,
                         default=func.current_timestamp(),  # 插入时默认当前时间
                         onupdate=func.current_timestamp(),  # 更新时自动更新为当前时间
                         comment='更新时间')
