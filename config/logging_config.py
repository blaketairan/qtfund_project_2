"""
Flask服务端日志配置

自动将Flask服务器日志输出到文件，包括所有详细的同步进度信息
"""

import os
import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
from datetime import datetime


def setup_flask_logging(app=None, log_dir='logs'):
    """
    配置Flask应用的文件日志
    
    Args:
        app: Flask应用实例（可选）
        log_dir: 日志文件目录
    
    Returns:
        配置好的logger实例
    """
    # 创建日志目录
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)
    
    # 生成日志文件名（不带时间戳，TimedRotatingFileHandler会自动添加）
    log_file = log_path / 'flask_server.log'
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有的handlers，避免重复日志
    root_logger.handlers.clear()
    
    # 1. 文件处理器 - 按天轮换，保留30天
    file_handler = TimedRotatingFileHandler(
        log_file,
        when='midnight',  # 每天午夜轮换
        interval=1,       # 间隔1天
        backupCount=30,   # 保留30天
        encoding='utf-8',
        utc=False         # 使用本地时间
    )
    file_handler.suffix = '%Y%m%d'  # 备份文件后缀格式：flask_server.log.20251013
    file_handler.setLevel(logging.INFO)
    
    # 2. 控制台处理器 - 同时输出到终端
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 定义详细的日志格式
    detailed_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    file_handler.setFormatter(detailed_formatter)
    console_handler.setFormatter(detailed_formatter)
    
    # 添加处理器到根日志记录器
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # 配置Flask应用日志（如果提供了app实例）
    if app:
        app.logger.handlers.clear()
        app.logger.addHandler(file_handler)
        app.logger.addHandler(console_handler)
        app.logger.setLevel(logging.INFO)
    
    # 记录启动信息
    logger = logging.getLogger(__name__)
    logger.info("="*70)
    logger.info("📝 Flask服务器日志系统已启动")
    logger.info(f"📁 日志文件: {log_file}")
    logger.info(f"📊 日志级别: INFO")
    logger.info(f"🔄 轮换设置: 每天午夜轮换, 保留30天")
    logger.info(f"📅 备份格式: flask_server.log.YYYYMMDD")
    logger.info("="*70)
    
    return root_logger


def get_latest_log_file(log_dir='logs'):
    """
    获取最新的Flask服务器日志文件路径
    
    Args:
        log_dir: 日志文件目录
    
    Returns:
        最新日志文件的Path对象，如果不存在返回None
    """
    log_path = Path(log_dir)
    
    # 当前日志文件
    current_log = log_path / 'flask_server.log'
    if current_log.exists():
        return current_log
    
    # 查找最新的备份日志文件
    log_files = sorted(log_path.glob('flask_server.log.*'), reverse=True)
    return log_files[0] if log_files else None


def tail_log_file(log_file, lines=50):
    """
    读取日志文件的最后N行
    
    Args:
        log_file: 日志文件路径
        lines: 读取的行数
    
    Returns:
        日志内容字符串
    """
    try:
        with open(log_file, 'r', encoding='utf-8') as f:
            return ''.join(f.readlines()[-lines:])
    except Exception as e:
        return f"读取日志文件失败: {e}"


if __name__ == '__main__':
    # 测试日志配置
    setup_flask_logging()
    
    logger = logging.getLogger('test')
    logger.info("测试日志消息 1")
    logger.warning("测试警告消息 2")
    logger.error("测试错误消息 3")
    
    # 显示最新日志文件
    latest = get_latest_log_file()
    if latest:
        print(f"\n最新日志文件: {latest}")
        print("\n最后10行:")
        print(tail_log_file(latest, 10))
