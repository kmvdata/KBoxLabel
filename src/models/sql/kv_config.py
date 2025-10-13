from sqlalchemy import Column, INTEGER, String, DateTime, text, Numeric, func, Index

from src.common.god.korm_base import KOrmBase


class KVConfig(KOrmBase):
    __tablename__ = 'kv_config'
    __table_args__ = (
        Index('idx_key', 'key'),
        {'comment': 'kv配置项目'}
    )

    id = Column(INTEGER, primary_key=True, comment='自增id')
    kid = Column(INTEGER, nullable=False, unique=True, comment='唯一kid')

    key = Column(String(64), nullable=False, comment='key')
    value = Column(String(64), nullable=False, comment='value')
    comment = Column(String(64), nullable=False, comment='备注')

    create_time = Column(DateTime, nullable=False, server_default=text("CURRENT_TIMESTAMP"), comment='创建时间')
    update_time = Column(DateTime,
                         default=func.current_timestamp(),  # 插入时默认当前时间
                         onupdate=func.current_timestamp(),  # 更新时自动更新为当前时间
                         comment='更新时间')
