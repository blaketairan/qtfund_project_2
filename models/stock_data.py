from sqlalchemy import Column, String, DECIMAL, BigInteger, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, timezone, timedelta
from database.connection import Base
import uuid

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))

def get_china_time() -> datetime:
    """获取中国时区当前时间"""
    return datetime.now(CHINA_TZ)


class StockDailyData(Base):
    """股票日行情数据表
    
    使用 TimescaleDB 时序数据库存储股票的日级别行情数据。
    主键采用 市场代码+股票代码 的组合形式（如：SH.000001, SZ.159998）
    """
    
    __tablename__ = 'stock_daily_data'
    
    # 主键：时间戳
    trade_date = Column(DateTime, primary_key=True, nullable=False, comment='交易日期')
    
    # 主键：股票标识
    symbol = Column(String(20), primary_key=True, nullable=False, comment='股票代码（含市场前缀，如：SH.000001）')
    
    # 基础信息
    stock_name = Column(String(100), nullable=False, comment='股票名称')
    
    # 价格相关数据（使用DECIMAL确保精度）
    close_price = Column(DECIMAL(10, 4), nullable=False, comment='收盘价')
    open_price = Column(DECIMAL(10, 4), nullable=True, comment='开盘价')
    high_price = Column(DECIMAL(10, 4), nullable=True, comment='最高价')
    low_price = Column(DECIMAL(10, 4), nullable=True, comment='最低价')
    
    # 交易量和金额
    volume = Column(BigInteger, nullable=False, default=0, comment='成交量（手）')
    turnover = Column(DECIMAL(20, 2), nullable=False, default=0, comment='成交额（元）')
    
    # 涨跌相关
    price_change = Column(DECIMAL(10, 4), nullable=True, comment='涨跌额')
    price_change_pct = Column(DECIMAL(8, 4), nullable=True, comment='涨跌幅（%）')
    
    # 基金特有字段
    premium_rate = Column(DECIMAL(8, 4), nullable=True, comment='溢价率（%，仅适用于基金）')
    
    # 市场信息
    market_code = Column(String(10), nullable=False, comment='市场代码（SH/SZ）')
    
    # 数据更新时间
    created_at = Column(DateTime, default=get_china_time, nullable=False, comment='记录创建时间')
    updated_at = Column(DateTime, default=get_china_time, onupdate=get_china_time, nullable=False, comment='记录更新时间')
    
    # 创建索引以优化查询性能
    __table_args__ = (
        # 复合索引：按股票代码和日期查询
        Index('idx_symbol_date', 'symbol', 'trade_date'),
        # 市场代码索引
        Index('idx_market_code', 'market_code'),
        # 交易日期索引
        Index('idx_trade_date', 'trade_date'),
        # 股票名称索引（支持模糊搜索）
        Index('idx_stock_name', 'stock_name'),
        {'comment': '股票日行情数据表，使用TimescaleDB时序存储'}
    )
    
    def __repr__(self) -> str:
        return f"<StockDailyData(symbol='{self.symbol}', trade_date='{self.trade_date}', close_price={self.close_price})>"
    
    @classmethod
    def create_hypertable(cls, db_session):
        """创建 TimescaleDB 超表
        
        Args:
            db_session: 数据库会话
        """
        try:
            # 创建超表，以 trade_date 作为时间列
            db_session.execute(text(
                f"SELECT create_hypertable('{cls.__tablename__}', 'trade_date', "
                "chunk_time_interval => INTERVAL '1 month', "
                "if_not_exists => TRUE);"
            ))
            
            # 设置数据压缩策略（7天后压缩）
            db_session.execute(text(
                f"ALTER TABLE {cls.__tablename__} SET (timescaledb.compress, "
                "timescaledb.compress_segmentby = 'symbol', "
                "timescaledb.compress_orderby = 'trade_date DESC');"
            ))
            
            # 添加压缩策略
            db_session.execute(text(
                f"SELECT add_compression_policy('{cls.__tablename__}', INTERVAL '7 days');"
            ))
            
            # 添加数据保留策略（保留3年数据）
            db_session.execute(text(
                f"SELECT add_retention_policy('{cls.__tablename__}', INTERVAL '3 years');"
            ))
            
            db_session.commit()
            print(f"TimescaleDB超表 '{cls.__tablename__}' 创建成功")
            
        except Exception as e:
            db_session.rollback()
            # 如果超表已存在，忽略错误
            if "already exists" not in str(e).lower():
                print(f"创建超表时出错: {e}")
                raise


class StockInfo(Base):
    """股票基础信息表
    
    存储股票的基本信息，如名称、市场、行业等静态数据
    """
    
    __tablename__ = 'stock_info'
    
    # 主键
    symbol = Column(String(20), primary_key=True, comment='股票代码（含市场前缀）')
    
    # 基础信息
    stock_name = Column(String(100), nullable=False, comment='股票名称')
    stock_code = Column(String(10), nullable=False, comment='股票代码（不含市场前缀）')
    market_code = Column(String(10), nullable=False, comment='市场代码（SH/SZ）')
    
    # 股票分类
    stock_type = Column(String(20), nullable=True, comment='股票类型（股票/基金/债券等）')
    industry = Column(String(100), nullable=True, comment='所属行业')
    sector = Column(String(100), nullable=True, comment='所属板块')
    
    # 上市信息
    list_date = Column(DateTime, nullable=True, comment='上市日期')
    delist_date = Column(DateTime, nullable=True, comment='退市日期')
    
    # 状态
    is_active = Column(String(1), default='Y', nullable=False, comment='是否活跃（Y/N）')
    
    # ETF标记
    is_etf = Column(String(1), default='N', nullable=False, comment='是否为ETF（Y/N）')
    
    # 同步进度跟踪
    last_sync_date = Column(DateTime, nullable=True, comment='最后同步的行情日期')
    first_fetch_time = Column(DateTime, nullable=True, comment='首次获取时间')
    
    # 时间戳
    created_at = Column(DateTime, default=get_china_time, nullable=False, comment='记录创建时间')
    updated_at = Column(DateTime, default=get_china_time, onupdate=get_china_time, nullable=False, comment='记录更新时间')
    
    __table_args__ = (
        Index('idx_stock_code', 'stock_code'),
        Index('idx_market_code_info', 'market_code'),
        Index('idx_stock_name_info', 'stock_name'),
        Index('idx_is_active', 'is_active'),
        Index('idx_is_etf', 'is_etf'),
        Index('idx_etf_market', 'market_code', 'is_etf'),
        {'comment': '股票基础信息表'}
    )
    
    def __repr__(self) -> str:
        etf_status = "ETF" if self.is_etf == 'Y' else "Stock"
        return f"<StockInfo(symbol='{self.symbol}', name='{self.stock_name}', type='{etf_status}', market='{self.market_code}')>"
    
    def __validate_is_etf(self):
        """验证 is_etf 字段值"""
        if self.is_etf not in ['Y', 'N']:
            raise ValueError(f"is_etf 字段值必须是 'Y' 或 'N'，当前值: {self.is_etf}")
    
    def __setattr__(self, name, value):
        """重写属性设置以添加验证"""
        super().__setattr__(name, value)
        
        # 在设置 is_etf 后进行验证
        if name == 'is_etf' and hasattr(self, 'symbol'):
            try:
                self.__validate_is_etf()
            except ValueError as e:
                raise ValueError(f"ETF字段验证失败: {e}")
    
    @property
    def is_etf_stock(self) -> bool:
        """检查是否为ETF"""
        return self.is_etf == 'Y'
    
    @classmethod
    def validate_etf_marker(cls, is_etf: str) -> bool:
        """验证ETF标记值
        
        Args:
            is_etf: ETF标记值
            
        Returns:
            bool: 是否为有效的ETF标记
            
        Raises:
            ValueError: 如果值无效
        """
        if is_etf not in ['Y', 'N']:
            raise ValueError(f"is_etf 必须是 'Y' 或 'N'，当前值: {is_etf}")
        return is_etf == 'Y'