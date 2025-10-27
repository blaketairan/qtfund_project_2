-- =====================================================
-- 数据库迁移脚本：添加ETF标记字段
-- 适用于TimescaleDB/PostgreSQL
-- =====================================================

-- 1. 检查并添加 is_etf 字段
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name='stock_info' AND column_name='is_etf'
    ) THEN
        -- 添加字段
        ALTER TABLE stock_info 
        ADD COLUMN is_etf VARCHAR(1) NOT NULL DEFAULT 'N';
        
        -- 添加注释
        COMMENT ON COLUMN stock_info.is_etf IS '是否为ETF（Y/N）';
        
        RAISE NOTICE '✅ is_etf 字段添加成功';
    ELSE
        RAISE NOTICE '⚠️  is_etf 字段已存在，跳过添加';
    END IF;
END
$$;

-- 2. 添加单字段索引
CREATE INDEX IF NOT EXISTS idx_is_etf ON stock_info(is_etf);

-- 3. 添加复合索引
CREATE INDEX IF NOT EXISTS idx_etf_market ON stock_info(market_code, is_etf);

-- 4. 更新现有记录（确保所有记录都有默认值 'N'）
UPDATE stock_info 
SET is_etf = 'N' 
WHERE is_etf IS NULL OR is_etf = '';

-- 5. 验证结果
SELECT 
    column_name, 
    data_type, 
    column_default, 
    is_nullable
FROM information_schema.columns
WHERE table_name='stock_info' AND column_name='is_etf';

-- 6. 显示索引信息
SELECT 
    indexname,
    indexdef
FROM pg_indexes 
WHERE tablename='stock_info' AND indexname IN ('idx_is_etf', 'idx_etf_market');

RAISE NOTICE '=====================================================';
RAISE NOTICE '✅ ETF字段迁移完成！';
RAISE NOTICE '=====================================================';

