# ETF价格同步问题修复

## 问题诊断

**现象**：ETF显示"已是最新"，但数据库中无价格数据

**根本原因**：
- `/api/sync/single-stock`使用`StockDataFetcher`
- ETF需要调用ETF API (`https://www.tsanghi.com/api/fin/etf/`)
- 股票调用股票API (`https://www.tsanghi.com/api/fin/stock/`)
- `StockDataFetcher`无法获取ETF数据，返回空 → 显示"已是最新"

## 修复内容

### 修改文件：`app/services/single_stock_sync.py`

#### 1. 添加ETF检测逻辑（第94-106行）

```python
# 先检查是否为ETF
with db_manager.get_session() as check_session:
    stock_info_check = check_session.query(StockInfo).filter(
        StockInfo.symbol == symbol
    ).first()
    is_etf = stock_info_check.is_etf == 'Y' if stock_info_check else False

# 根据是否为ETF选择不同的fetcher
if is_etf:
    from data_fetcher.etf_api import ETFDataFetcher
    fetcher = ETFDataFetcher(token)
    logger.info(f"🔍 检测到ETF: {symbol}，使用ETF API获取器")
else:
    fetcher = StockDataFetcher(token)
    logger.info(f"🔍 股票: {symbol}，使用股票API获取器")
```

#### 2. 统一数据转换（第188-205行）

ETF和股票使用相同的数据转换函数，因为数据结构相同。

## 使用步骤

### 1. 重启Flask服务

```bash
# 停止现有服务
pkill -f start_flask_app.py

# 重启
nohup python start_flask_app.py > logs/flask.log 2>&1 &
```

### 2. 重新同步ETF价格

```bash
# 停止之前的同步
pkill -f full_sync_v2.py

# 重新运行（测试少量ETF）
python full_sync_v2.py --etf --max 5
```

### 3. 验证数据

```sql
-- 检查ETF价格数据是否已写入
SELECT symbol, COUNT(*) as record_count,
       MIN(trade_date) as earliest, 
       MAX(trade_date) as latest
FROM stock_daily_data 
WHERE symbol IN (
    SELECT symbol FROM stock_info WHERE is_etf = 'Y' LIMIT 1
)
GROUP BY symbol;

-- 检查last_sync_date是否已更新
SELECT symbol, stock_name, last_sync_date, is_etf
FROM stock_info 
WHERE is_etf = 'Y' 
LIMIT 5;
```

## 修复前后对比

| 项目 | 修复前 | 修复后 |
|------|--------|--------|
| ETF检测 | ❌ 无 | ✅ 自动检测is_etf字段 |
| API获取器 | ❌ 只用StockDataFetcher | ✅ 根据is_etf选择fetcher |
| 数据获取 | ❌ ETF无法获取数据 | ✅ 使用ETF API |
| 显示状态 | ❌ 误报"已是最新" | ✅ 正确同步 |
| 数据库 | ❌ 无价格数据 | ✅ 正确写入 |

## 预期结果

修复后，ETF价格同步应该：
1. ✅ 检测到ETF并记录日志
2. ✅ 调用ETF API获取数据
3. ✅ 正确写入stock_daily_data表
4. ✅ 更新stock_info表的last_sync_date字段
5. ✅ 显示"新增X条记录"而非"已是最新"

## 测试命令

```bash
# 测试单只ETF
python full_sync_v2.py --etf --test SZ.159997

# 同步前5只ETF
python full_sync_v2.py --etf --max 5

# 全量同步
python full_sync_v2.py --etf
```
