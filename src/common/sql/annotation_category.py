from sqlalchemy import Column, INTEGER, String, DateTime, text, Numeric
from src.common.sql.base import KOrmBase
from PyQt5.QtGui import QColor


class AnnotationCategory(KOrmBase):
    """存储标注类别的数据结构"""
    __tablename__ = 'annotation_category'
    __table_args__ = {'comment': '标注类别表'}

    id = Column(INTEGER, primary_key=True, comment='自增id')
    class_id = Column(INTEGER, nullable=False, comment='类别ID')
    class_name = Column(String(100), nullable=False, comment='类别名称')
    color_r = Column(INTEGER, nullable=False, comment='颜色R值')
    color_g = Column(INTEGER, nullable=False, comment='颜色G值')
    color_b = Column(INTEGER, nullable=False, comment='颜色B值')
    
    # 4个浮点类型的Column，精确到小数点后19位
    x_center = Column(Numeric(precision=30, scale=19), comment='中心点X坐标')
    y_center = Column(Numeric(precision=30, scale=19), comment='中心点Y坐标')
    width = Column(Numeric(precision=30, scale=19), comment='宽度')
    height = Column(Numeric(precision=30, scale=19), comment='高度')
    
    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')