from typing import Optional
from pydantic_settings import BaseSettings
from pydantic import Field


class DatabaseConfig(BaseSettings):
    """数据库配置类"""
    
    # 数据库连接信息
    db_host: str = Field(default="localhost", description="数据库主机地址")
    db_port: int = Field(default=5432, description="数据库端口")
    db_name: str = Field(default="securities_data", description="数据库名称")
    db_user: str = Field(default="postgres", description="数据库用户名")
    db_password: str = Field(default="", description="数据库密码")
    
    # 连接池配置
    db_pool_size: int = Field(default=10, description="连接池大小")
    db_max_overflow: int = Field(default=20, description="连接池最大溢出")
    db_pool_timeout: int = Field(default=30, description="连接超时时间")
    db_pool_recycle: int = Field(default=3600, description="连接回收时间")
    
    # TimescaleDB 特定配置
    compression_interval_days: int = Field(default=7, description="数据压缩间隔（天）")
    data_retention_days: int = Field(default=1095, description="数据保留天数")
    
    @property
    def database_url(self) -> str:
        """构建数据库连接URL"""
        from urllib.parse import quote_plus
        # URL encode the password to handle special characters
        encoded_password = quote_plus(self.db_password)
        return f"postgresql://{self.db_user}:{encoded_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # 忽略额外的环境变量
    }


class AppConfig(BaseSettings):
    """应用配置类"""
    
    app_name: str = Field(default="securities_data_storage", description="应用名称")
    log_level: str = Field(default="INFO", description="日志级别")
    log_file: str = Field(default="logs/app.log", description="日志文件路径")
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore"  # 忽略额外的环境变量
    }


# 全局配置实例
db_config = DatabaseConfig()
app_config = AppConfig()