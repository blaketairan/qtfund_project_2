# ETF同步API调用快速修复

## 问题

curl命令缺少Content-Type header，导致415错误。

## 正确的curl命令

### 1. 同步ETF列表

**正确的命令**：
```bash
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{"exchange_codes": ["XSHG", "XSHE"]}'
```

**或者发送空body**：
```bash
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{}'
```

### 2. 同步ETF价格

```bash
curl -X POST http://localhost:7777/api/sync/etf/prices \
  -H "Content-Type: application/json" \
  -d '{"start_year": 2020}'
```

## 关键点

✅ **必须包含**：`-H "Content-Type: application/json"`  
✅ **Body可以为空**：`-d '{}'`  
❌ **错误**：缺少Content-Type header

## 完整流程

```bash
# Step 1: 同步ETF列表到数据库
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{}'

# 等待完成...

# Step 2: 使用full_sync_v2.py逐只同步ETF价格
python full_sync_v2.py --etf --max 10
```

## 错误对比

**错误的命令**（缺少Content-Type）：
```bash
curl -X POST http://localhost:7777/api/sync/etf/lists  # ❌ 415错误
```

**正确的命令**：
```bash
curl -X POST http://localhost:7777/api/sync/etf/lists \
  -H "Content-Type: application/json" \
  -d '{}'  # ✅ 成功
```

## 额外提示

如果你不想每次都输入Content-Type，可以创建一个alias：

```bash
# 添加到 ~/.bashrc
alias curl-json='curl -H "Content-Type: application/json"'

# 使用
curl-json -X POST http://localhost:7777/api/sync/etf/lists -d '{}'
```
