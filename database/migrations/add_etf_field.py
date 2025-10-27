"""
数据库迁移脚本：添加ETF标记字段

此脚本为 stock_info 表添加 is_etf 字段，用于标识ETF产品。
"""

from database.connection import db_manager
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)


def add_etf_field():
    """添加 is_etf 字段到 stock_info 表"""
    
    with db_manager.get_session() as session:
        try:
            # 检查字段是否已存在
            check_column_sql = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='stock_info' AND column_name='is_etf';
            """)
            
            result = session.execute(check_column_sql).fetchone()
            
            if result:
                logger.info("is_etf 字段已存在，跳过添加")
                return {'success': True, 'skipped': True, 'message': '字段已存在'}
            
            # 添加 is_etf 字段
            add_column_sql = text("""
                ALTER TABLE stock_info 
                ADD COLUMN is_etf VARCHAR(1) NOT NULL DEFAULT 'N';
            """)
            
            session.execute(add_column_sql)
            
            # 添加注释
            add_comment_sql = text("""
                COMMENT ON COLUMN stock_info.is_etf IS '是否为ETF（Y/N）';
            """)
            
            session.execute(add_comment_sql)
            
            # 添加索引
            add_index_sql = text("""
                CREATE INDEX IF NOT EXISTS idx_is_etf 
                ON stock_info(is_etf);
            """)
            
            session.execute(add_index_sql)
            
            # 添加复合索引
            add_composite_index_sql = text("""
                CREATE INDEX IF NOT EXISTS idx_etf_market 
                ON stock_info(market_code, is_etf);
            """)
            
            session.execute(add_composite_index_sql)
            
            # 更新现有记录的默认值
            update_existing_sql = text("""
                UPDATE stock_info 
                SET is_etf = 'N' 
                WHERE is_etf IS NULL OR is_etf = '';
            """)
            
            session.execute(update_existing_sql)
            
            session.commit()
            
            logger.info("✅ is_etf 字段添加成功")
            
            return {
                'success': True,
                'skipped': False,
                'message': 'is_etf 字段添加成功，索引已创建'
            }
            
        except Exception as e:
            session.rollback()
            logger.error(f"❌ 添加 is_etf 字段失败: {e}")
            raise


def verify_etf_field():
    """验证 is_etf 字段是否正确添加"""
    
    with db_manager.get_session() as session:
        try:
            # 检查字段是否存在
            check_sql = text("""
                SELECT column_name, data_type, column_default, is_nullable
                FROM information_schema.columns
                WHERE table_name='stock_info' AND column_name='is_etf';
            """)
            
            result = session.execute(check_sql).fetchone()
            
            if not result:
                logger.error("❌ is_etf 字段不存在")
                return False
            
            logger.info(f"✅ is_etf 字段验证成功: {result}")
            
            # 检查索引是否存在
            check_index_sql = text("""
                SELECT indexname 
                FROM pg_indexes 
                WHERE tablename='stock_info' AND indexname IN ('idx_is_etf', 'idx_etf_market');
            """)
            
            indexes = session.execute(check_index_sql).fetchall()
            logger.info(f"✅ ETF索引验证成功: {len(indexes)} 个索引")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ 验证失败: {e}")
            return False


if __name__ == '__main__':
    import sys
    
    print("=" * 60)
    print("ETF字段迁移脚本")
    print("=" * 60)
    
    try:
        # 执行迁移
        result = add_etf_field()
        print(f"\n迁移结果: {result['message']}")
        
        # 验证迁移
        if verify_etf_field():
            print("\n✅ 迁移验证成功")
            sys.exit(0)
        else:
            print("\n❌ 迁移验证失败")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 迁移失败: {e}")
        sys.exit(1)
