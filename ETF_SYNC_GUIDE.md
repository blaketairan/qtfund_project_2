# ETF数据同步使用指南

## 概述

ETF同步功能已经实现，但**与股票同步是独立的两套流程**：

- **股票同步**：`full_sync_v2.py` → 同步普通股票
- **ETF同步**：通过Flask API手动触发 → 同步ETF

## ETF同步逻辑位置

### 1. 核心逻辑文件

```
app/services/etf_sync_service.py    # ETF同步服务（主要业务逻辑）
data_fetcher/etf_api.py              # ETF API数据获取器
app/routes/sync_tasks.py             # Flask API端点定义
```

### 2. 核心功能

#### 2.1 ETF列表同步
**方法**：`ETFSyncService.sync_etf_lists()`
**位置**：`app/services/etf_sync_service.py` 第24-126行
**功能**：
- 从远程API获取ETF列表（`https://www.tsanghi.com/api/fin/etf/{exchange}/list`）
- 存储到 `stock_info` 表
- 自动设置 `is_etf='Y'`
- 支持增量同步（检测重复记录）

#### 2.2 ETF价格数据同步
**方法**：`ETFSyncService.sync_etf_prices()`
**位置**：`app/services/etf_sync_service.py` 第128-232行
**功能**：
- 从远程API获取ETF历史价格（`https://www.tsanghi.com/api/fin/etf/{exchange}/daily/realtime`）
- 存储到 `stock_daily_data` 表
- 支持按ETF symbol或交易所批量同步
- 支持增量同步（跳过已有日期）

## 如何使用

### 方法1：通过Flask API触发（推荐）

#### 同步ETF列表

```bash
# 1. 确保Flask服务运行在端口7777
python start_flask_app.py

# 2. 在另一个终端执行
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{"exchange_codes": ["XSHG", "XSHE"]}'
```

**返回示例**：
```json
{
  "code": 200,
  "message": "同步ETF列表",
  "data": {
    "task": {
      "status": "success",
      "result": {
        "action": "completed",
        "total_etfs": 150,
        "new_etfs": 100,
        "updated_etfs": 50
      }
    }
  }
}
```

#### 同步ETF价格数据

```bash
# 同步所有ETF的价格数据
curl -X POST http://localhost:7777/api/sync/etf/prices \
  -H "Content-Type: application/json" \
  -d '{"start_year": 2020}'

# 同步指定ETF的价格
curl -X POST http://localhost:7777/api/sync/etf/prices \
  -H "Content-Type: application/json" \
  -d '{"symbol": "SH.510050", "start_year": 2020}'

# 同步指定交易所的ETF价格
curl -X POST http://localhost:7777/api/sync/etf/prices \
  -H "Content-Type: application/json" \
  -d '{"exchange_code": "XSHG", "start_year": 2020}'
```

### 方法2：扩展full_sync_v2.py（待实现）

目前 `full_sync_v2.py` 只同步股票。如果要让它也同步ETF，需要：

1. 添加ETF同步参数
2. 先同步ETF列表
3. 再同步ETF价格

**示例扩展**（未来实现）：
```bash
python full_sync_v2.py --sync-etf  # 新增参数
```

## 完整同步流程

### 第一次同步（完整流程）

```bash
# Step 1: 同步ETF列表
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{}'

# Step 2: 等待列表同步完成，然后同步价格
curl -X POST http://localhost:7777/api/sync/etf/prices \
  -H "Content-Type: application/json" \
  -d '{"start_year": 2020}'
```

### 日常增量同步

只需要同步ETF价格（列表通常不变）：

```bash
# 仅同步ETF价格（增量）
curl -X POST http://localhost:7777/api/sync/etf/prices \
  -H "Content-Type: application/json" \
  -d '{"start_year": 2024}'  # 只同步2024年的价格
```

## 数据验证

### 检查ETF是否已同步到数据库

```sql
-- 查询ETF数量
SELECT is_etf, COUNT(*) 
FROM stock_info 
GROUP BY is_etf;

-- 查询具体ETF
SELECT symbol, stock_name, is_etf
FROM stock_info 
WHERE is_etf = 'Y'
LIMIT 10;

-- 查询ETF价格数据
SELECT symbol, COUNT(*) as price_count, 
       MIN(trade_date) as earliest, 
       MAX(trade_date) as latest
FROM stock_daily_data 
WHERE symbol IN (
    SELECT symbol FROM stock_info WHERE is_etf = 'Y'
)
GROUP BY symbol
ORDER BY symbol;
```

## 当前状态

✅ **已完成**：
- ETF列表同步逻辑（`sync_etf_lists()`）
- ETF价格同步逻辑（`sync_etf_prices()`）
- Flask API端点（`/api/sync/etf/lists` 和 `/api/sync/etf/prices`）
- 数据获取器（`ETFDataFetcher`）

⏳ **待测试**：
- 需要先执行数据库迁移（添加 `is_etf` 字段）
- 然后才能执行ETF同步

## 故障排除

### 问题：ETF同步失败，报"is_etf does not exist"

**解决**：先执行数据库迁移
```bash
psql $DATABASE_URL -f database/migrations/add_etf_field.sql
```

### 问题：API返回401错误

**解决**：检查环境变量
```bash
export STOCK_API_TOKEN="your_token_here"
```

### 问题：找不到ETF数据

**检查**：
1. ETF列表是否已同步（检查 `stock_info` 表）
2. API token是否正确
3. 网络连接是否正常

## 后续改进建议

1. **扩展 full_sync_v2.py**：添加 `--sync-etf` 参数
2. **定时任务**：配置cron定期同步ETF价格
3. **自动触发**：ETF列表同步后自动触发价格同步
4. **日志改进**：更详细的ETF同步进度日志

## 总结

**ETF同步逻辑在**：
- `app/services/etf_sync_service.py`（主要业务逻辑）
- `app/routes/sync_tasks.py`（API端点，第380-493行）

**通过API触发**：
```bash
POST http://localhost:7777/api/sync/etf/lists    # 同步列表
POST http://localhost:7777/api/sync/etf/prices    # 同步价格
```

**与股票同步独立**：ETF同步是单独的流程，需要通过API手动触发。
