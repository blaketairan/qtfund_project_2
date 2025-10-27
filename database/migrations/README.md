# 数据库迁移指南：添加ETF字段

## 问题描述

错误信息：
```
column stock_info.is_etf does not exist
```

这是因为代码中使用了`is_etf`字段，但数据库schema还没有这个字段。

## 解决方案

有两种方式执行迁移：

### 方式1：直接执行SQL脚本（推荐）

在远程PostgreSQL/TimescaleDB服务器上执行：

```bash
# 连接到数据库
psql -h <host> -U <user> -d <database_name>

# 或者使用环境变量
psql $DATABASE_URL

# 执行迁移脚本
\i database/migrations/add_etf_field.sql
```

或者直接用psql执行：
```bash
psql $DATABASE_URL -f database/migrations/add_etf_field.sql
```

### 方式2：使用Python脚本

```bash
# 在项目根目录执行
cd /path/to/qtfund_project_2
python database/migrations/add_etf_field.py
```

**注意**：需要确保设置了环境变量 `DATABASE_URL`。

## 验证

执行迁移后，验证字段是否已添加：

```sql
-- 检查字段
SELECT column_name, data_type, column_default
FROM information_schema.columns
WHERE table_name='stock_info' AND column_name='is_etf';

-- 检查索引
SELECT indexname, indexdef
FROM pg_indexes 
WHERE tablename='stock_info' AND indexname IN ('idx_is_etf', 'idx_etf_market');

-- 检查现有记录
SELECT is_etf, COUNT(*) 
FROM stock_info 
GROUP BY is_etf;
```

## 迁移内容

1. **添加字段**：`stock_info.is_etf VARCHAR(1) DEFAULT 'N'`
2. **添加字段注释**：说明该字段用于标识ETF
3. **添加单字段索引**：`idx_is_etf` 用于快速查询ETF
4. **添加复合索引**：`idx_etf_market` 用于按市场查询ETF
5. **更新现有记录**：将所有现有记录设置为 'N'（非ETF）

## 回滚（如果需要）

如果需要移除ETF字段：

```sql
-- 删除索引
DROP INDEX IF EXISTS idx_etf_market;
DROP INDEX IF EXISTS idx_is_etf;

-- 删除字段
ALTER TABLE stock_info DROP COLUMN IF EXISTS is_etf;
```

## 故障排除

### 如果Python脚本报错 "No module named 'database'"

使用纯SQL方式执行：
```bash
psql $DATABASE_URL -f database/migrations/add_etf_field.sql
```

### 如果已经添加了字段但代码仍然报错

检查：
1. 数据库连接配置是否正确
2. 代码是否从正确的数据库读取
3. 是否有多个环境（开发/生产）
