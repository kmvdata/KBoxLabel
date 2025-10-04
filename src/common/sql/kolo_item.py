from sqlalchemy import Column, INTEGER, String, DateTime, text, Numeric

from src.common.god.korm_base import KOrmBase


class KoloItem(KOrmBase):
    __tablename__ = 'kolo_item'
    __table_args__ = {'comment': 'Kolo项目表'}

    id = Column(INTEGER, primary_key=True, comment='自增id')
    kid = Column(String(40), nullable=False, unique=True, comment='唯一kid')
    
    # 4个浮点类型的Column，精确到小数点后19位
    x_center = Column(Numeric(precision=30, scale=19), comment='中心点X坐标')
    y_center = Column(Numeric(precision=30, scale=19), comment='中心点Y坐标')
    width = Column(Numeric(precision=30, scale=19), comment='宽度')
    height = Column(Numeric(precision=30, scale=19), comment='高度')
    
    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
