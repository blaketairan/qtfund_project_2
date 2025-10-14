from sqlalchemy import create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from contextlib import contextmanager
from typing import Generator
import logging
from config.settings import db_config

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# SQLAlchemy 基础类
Base = declarative_base()

class DatabaseManager:
    """TimescaleDB 数据库管理器"""
    
    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._initialize_engine()
    
    def _initialize_engine(self):
        """初始化数据库引擎"""
        try:
            self.engine = create_engine(
                db_config.database_url,
                poolclass=QueuePool,
                pool_size=db_config.db_pool_size,
                max_overflow=db_config.db_max_overflow,
                pool_timeout=db_config.db_pool_timeout,
                pool_recycle=db_config.db_pool_recycle,
                echo=False,  # 设置为 True 可以看到 SQL 语句
                future=True
            )
            
            self.SessionLocal = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False
            )
            
            logger.info("数据库引擎初始化成功")
            
        except Exception as e:
            logger.error(f"数据库引擎初始化失败: {e}")
            raise
    
    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                if result.fetchone()[0] == 1:
                    logger.info("数据库连接测试成功")
                    return True
            return False
        except Exception as e:
            logger.error(f"数据库连接测试失败: {e}")
            return False
    
    def check_timescaledb_extension(self) -> bool:
        """检查 TimescaleDB 扩展是否已安装"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(
                    text("SELECT 1 FROM pg_extension WHERE extname = 'timescaledb'")
                )
                if result.fetchone():
                    logger.info("TimescaleDB 扩展已安装")
                    return True
                else:
                    logger.warning("TimescaleDB 扩展未安装")
                    return False
        except Exception as e:
            logger.error(f"检查 TimescaleDB 扩展时出错: {e}")
            return False
    
    def create_tables(self):
        """创建所有表"""
        try:
            Base.metadata.create_all(bind=self.engine)
            logger.info("数据表创建成功")
        except Exception as e:
            logger.error(f"数据表创建失败: {e}")
            raise
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """获取数据库会话的上下文管理器"""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"数据库会话出错: {e}")
            raise
        finally:
            session.close()
    
    def close(self):
        """关闭数据库连接"""
        if self.engine:
            self.engine.dispose()
            logger.info("数据库连接已关闭")


# 全局数据库管理器实例
db_manager = DatabaseManager()