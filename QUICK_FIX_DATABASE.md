# 快速修复：数据库Schema问题

## 错误信息
```
column stock_info.is_etf does not exist
```

## 原因
代码中添加了`is_etf`字段，但远程数据库还没有执行migration。

## 解决步骤

### 最简单的方法（推荐）

在远程服务器上执行SQL脚本：

```bash
# 1. 复制SQL脚本到远程服务器（如果需要）
# scp database/migrations/add_etf_field.sql user@remote:/path/

# 2. 连接到远程数据库并执行
psql $DATABASE_URL -f database/migrations/add_etf_field.sql
```

如果没有`$DATABASE_URL`环境变量：
```bash
psql -h <DB_HOST> -U <DB_USER> -d <DB_NAME> -f database/migrations/add_etf_field.sql
```

### 或手动执行SQL

如果需要，你也可以手动在psql中逐行执行：

```sql
-- 连接到数据库
psql -h <host> -U <user> -d <database_name>

-- 然后复制粘贴以下SQL：
\i database/migrations/add_etf_field.sql
```

## 验证

执行后，检查是否成功：

```sql
-- 查询字段
\d stock_info

-- 或
SELECT column_name, data_type 
FROM information_schema.columns
WHERE table_name='stock_info' AND column_name='is_etf';
```

应该能看到 `is_etf | character varying` 输出。

## 完成后

重启Flask服务：
```bash
# 停止当前服务
kill <flask_pid>

# 重新启动
python start_flask_app.py
```

然后再次运行同步脚本：
```bash
python full_sync_v2.py --max 1
```

## 如果还有问题

查看完整迁移指南：
```bash
cat database/migrations/README.md
```
