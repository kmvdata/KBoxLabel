from sqlalchemy import Column, INTEGER, String, DateTime, text, Numeric, func

from src.common.god.korm_base import KOrmBase


class KoloItem(KOrmBase):
    __tablename__ = 'kolo_item'
    __table_args__ = {'comment': 'Kolo项目表'}

    id = Column(INTEGER, primary_key=True, comment='自增id')
    kid = Column(INTEGER, nullable=False, unique=True, comment='唯一kid')

    image_name = Column(String(255), nullable=False, comment='名称')
    class_name = Column(String(64), nullable=False, comment='名称')

    # 4个浮点类型的Column，精确到小数点后19位
    x_center = Column(Numeric(precision=30, scale=19), comment='中心点X坐标')
    y_center = Column(Numeric(precision=30, scale=19), comment='中心点Y坐标')
    width = Column(Numeric(precision=30, scale=19), comment='宽度')
    height = Column(Numeric(precision=30, scale=19), comment='高度')

    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(DateTime,
                         default=func.current_timestamp(),  # 插入时默认当前时间
                         onupdate=func.current_timestamp(),  # 更新时自动更新为当前时间
                         comment='更新时间')
