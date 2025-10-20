#!/usr/bin/env python3
"""
数据库表结构修复脚本
修复 stock_info 表缺失的 last_sync_date 字段
"""

from sqlalchemy import text
from database.connection import db_manager
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_column_exists(session, table_name: str, column_name: str) -> bool:
    """检查表中是否存在指定字段"""
    result = session.execute(text("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = :table_name
        AND column_name = :column_name
    """), {
        'table_name': table_name,
        'column_name': column_name
    })

    return result.fetchone() is not None

def get_table_schema(session, table_name: str):
    """获取表的所有字段信息"""
    result = session.execute(text("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = :table_name
        ORDER BY ordinal_position
    """), {'table_name': table_name})

    return result.fetchall()

def add_missing_columns():
    """添加缺失的字段到 stock_info 表"""

    # 需要检查和添加的字段定义
    missing_columns = [
        {
            'name': 'last_sync_date',
            'definition': 'TIMESTAMP NULL',
            'comment': '最后同步的行情日期'
        },
        {
            'name': 'first_fetch_time',
            'definition': 'TIMESTAMP NULL',
            'comment': '首次获取时间'
        }
    ]

    try:
        with db_manager.get_session() as session:
            logger.info("开始检查 stock_info 表结构...")

            # 首先检查表是否存在
            table_exists = session.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'stock_info'
                )
            """)).fetchone()[0]

            if not table_exists:
                logger.error("表 stock_info 不存在，请先运行数据库初始化脚本")
                return False

            # 显示当前表结构
            logger.info("当前 stock_info 表结构:")
            current_schema = get_table_schema(session, 'stock_info')
            for row in current_schema:
                logger.info(f"  - {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})")

            # 检查并添加缺失的字段
            columns_added = 0
            for column_info in missing_columns:
                column_name = column_info['name']

                if not check_column_exists(session, 'stock_info', column_name):
                    logger.info(f"添加缺失字段: {column_name}")

                    # 添加字段
                    session.execute(text(f"""
                        ALTER TABLE stock_info
                        ADD COLUMN {column_name} {column_info['definition']}
                    """))

                    # 添加字段注释
                    session.execute(text(f"""
                        COMMENT ON COLUMN stock_info.{column_name} IS '{column_info['comment']}'
                    """))

                    columns_added += 1
                    logger.info(f"✅ 字段 {column_name} 添加成功")
                else:
                    logger.info(f"✓ 字段 {column_name} 已存在")

            if columns_added > 0:
                session.commit()
                logger.info(f"🎉 成功添加了 {columns_added} 个字段")
            else:
                logger.info("📋 所有字段都已存在，无需修改")

            # 显示修复后的表结构
            logger.info("修复后的 stock_info 表结构:")
            updated_schema = get_table_schema(session, 'stock_info')
            for row in updated_schema:
                logger.info(f"  - {row.column_name}: {row.data_type} ({'NULL' if row.is_nullable == 'YES' else 'NOT NULL'})")

            return True

    except Exception as e:
        logger.error(f"修复数据库表结构时出错: {e}")
        return False

def create_missing_tables():
    """如果表不存在，创建所有必要的表"""
    try:
        logger.info("检查并创建缺失的数据库表...")

        # 导入模型以确保表定义被加载
        from models.stock_data import StockInfo, StockDailyData

        # 创建表
        db_manager.create_tables()

        # 为 StockDailyData 创建 TimescaleDB 超表
        with db_manager.get_session() as session:
            try:
                StockDailyData.create_hypertable(session)
            except Exception as e:
                if "already exists" not in str(e).lower():
                    logger.warning(f"创建超表时出现警告: {e}")

        logger.info("✅ 数据库表创建/检查完成")
        return True

    except Exception as e:
        logger.error(f"创建数据库表时出错: {e}")
        return False

def main():
    """主函数"""
    logger.info("🚀 开始数据库表结构修复...")

    # 测试数据库连接
    if not db_manager.test_connection():
        logger.error("❌ 数据库连接失败，请检查配置")
        return False

    # 检查并创建表
    if not create_missing_tables():
        logger.error("❌ 创建数据库表失败")
        return False

    # 修复表结构
    if not add_missing_columns():
        logger.error("❌ 修复表结构失败")
        return False

    logger.info("🎉 数据库表结构修复完成！")
    logger.info("现在可以正常运行股票数据同步功能了")

    return True

if __name__ == "__main__":
    main()