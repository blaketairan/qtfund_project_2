# 项目拆分说明文档

## 📋 拆分概述

原项目 `qtfund_project_2` 已拆分为两个独立的Flask应用，实现功能职责的清晰分离。

## 🎯 拆分逻辑

### 1. 同步服务 (qtfund_project_2)
**端口**: 7777  
**职责**: 数据同步和写入

**保留功能**:
- ✅ 访问远程HTTP接口
- ✅ 从API获取股票数据
- ✅ 数据同步到TimescaleDB
- ✅ 交易所信息同步
- ✅ 股票清单同步
- ✅ 股票行情数据同步
- ✅ 后台任务管理
- ✅ 断点续传支持

**移除功能**:
- ❌ 股票行情查询路由 (`/api/stock-price/`)
- ❌ 股票信息查询路由 (`/api/stock-info/`)
- ❌ 交易所信息查询路由 (`/api/exchange-info/`)

### 2. 查询服务 (qtfund_project_3)
**端口**: 8000  
**职责**: 数据库查询和读取

**包含功能**:
- ✅ 股票行情数据查询 (TimescaleDB)
- ✅ 股票基础信息查询 (数据库)
- ✅ 股票信息查询 (本地JSON)
- ✅ 列出所有股票
- ✅ 健康检查和版本信息

**不包含功能**:
- ❌ 数据同步功能
- ❌ 远程API调用
- ❌ 数据写入操作

## 📁 目录结构对比

### 同步服务 (qtfund_project_2)
```
qtfund_project_2/
├── app/
│   ├── routes/
│   │   ├── health.py              # 健康检查
│   │   └── sync_tasks.py          # 同步任务 ✅
│   ├── services/
│   │   ├── sync_service.py        # 同步服务 ✅
│   │   ├── single_stock_sync.py   # 单股同步 ✅
│   │   └── background_tasks.py    # 后台任务 ✅
│   └── main.py                    # Flask应用（端口7777）
├── data_fetcher/                  # 数据获取 ✅
├── utils/
│   └── data_integration.py        # 数据集成 ✅
├── full_sync_v2.py               # 全量同步脚本 ✅
└── start_flask_app.py            # 启动（端口7777）
```

### 查询服务 (qtfund_project_3)
```
qtfund_project_3/
├── app/
│   ├── routes/
│   │   ├── health.py              # 健康检查
│   │   ├── stock_price.py         # 行情查询 ✅
│   │   └── stock_info.py          # 信息查询 ✅
│   ├── services/
│   │   ├── stock_data_service.py  # 数据查询服务 ✅
│   │   └── stock_info_service.py  # 信息查询服务 ✅
│   └── main.py                    # Flask应用（端口8000）
├── database/                      # 数据库连接（共享）
├── models/                        # 数据模型（共享）
├── config/                        # 配置（共享）
└── start_flask_app.py            # 启动（端口8000）
```

## 🔗 共享模块

两个服务共享以下模块（已复制到新项目）:

1. **database/** - 数据库连接管理
2. **models/** - 数据模型定义
3. **config/** - 配置管理
4. **constants/** - 常量和股票清单

## 🌐 API接口对比

### 同步服务 (http://localhost:7777)

| 接口路径 | 方法 | 功能 |
|---------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/sync/exchanges` | POST | 同步交易所信息 |
| `/api/sync/stock-lists` | POST | 同步股票清单 |
| `/api/sync/stock-prices` | POST | 同步股票行情 |
| `/api/sync/single-stock` | POST | 同步单只股票 |
| `/api/sync/full-sync` | POST | 完整同步 |
| `/api/sync/tasks` | GET | 查询所有任务 |
| `/api/sync/tasks/<id>` | GET | 查询任务状态 |
| `/api/sync/tasks/<id>/stop` | POST | 停止任务 |

### 查询服务 (http://localhost:8000)

| 接口路径 | 方法 | 功能 |
|---------|------|------|
| `/api/health` | GET | 健康检查 |
| `/api/version` | GET | 版本信息 |
| `/api/stock-price/query` | GET/POST | 查询股票行情 |
| `/api/stock-price/info/<symbol>` | GET | 获取股票信息 |
| `/api/stock-price/list` | GET | 列出所有股票 |
| `/api/stock-info/local` | GET | 本地JSON查询 |
| `/api/stock-info/statistics` | GET | 统计信息 |

## 🚀 启动顺序

1. **启动同步服务** (端口7777)
   ```bash
   cd /Users/terrell/qt/qtfund_project_2
   python start_flask_app.py
   ```

2. **启动查询服务** (端口8000)
   ```bash
   cd /Users/terrell/qt/qtfund_project_3
   python start_flask_app.py
   ```

## 💡 使用场景

### 场景1: 首次部署
```bash
# 1. 启动同步服务
cd qtfund_project_2
python start_flask_app.py

# 2. 同步基础数据
curl -X POST http://localhost:7777/api/sync/stock-lists

# 3. 启动查询服务
cd qtfund_project_3
python start_flask_app.py

# 4. 查询数据
curl "http://localhost:8000/api/stock-info/local?limit=10"
```

### 场景2: 数据同步
```bash
# 同步单只股票
curl -X POST http://localhost:7777/api/sync/single-stock \
  -H "Content-Type: application/json" \
  -d '{"symbol": "SH.600519"}'

# 全量同步
python qtfund_project_2/full_sync_v2.py --max 100
```

### 场景3: 数据查询
```bash
# 查询股票行情
curl "http://localhost:8000/api/stock-price/query?symbol=SH.600519&limit=10"

# 获取股票信息
curl "http://localhost:8000/api/stock-price/info/SH.600519"

# 列出所有股票
curl "http://localhost:8000/api/stock-price/list?limit=100"
```

## 🔧 配置说明

### 环境变量 (.env)

两个服务需要相同的数据库配置：

```env
# 数据库配置（两个服务共享）
DB_HOST=localhost
DB_PORT=5432
DB_NAME=securities_data
DB_USER=your_username
DB_PASSWORD=your_password

# API Token（仅同步服务需要）
STOCK_API_TOKEN=your_api_token
```

## ⚠️ 注意事项

1. **数据库共享**: 两个服务使用同一个TimescaleDB数据库
2. **端口冲突**: 确保7777和8000端口未被占用
3. **依赖安装**: 两个服务都需要安装requirements.txt
4. **启动顺序**: 建议先启动同步服务，再启动查询服务
5. **API Token**: 查询服务不需要API Token，仅同步服务需要

## 📊 性能优化

### 同步服务优化
- 批量插入（1000条/批）
- 断点续传（避免重复同步）
- 后台任务异步执行
- API限流控制

### 查询服务优化
- 索引优化（symbol, trade_date）
- 查询限制（最大10000条）
- 日期范围过滤
- 本地JSON缓存

## 📝 总结

拆分后的架构实现了：
- ✅ **职责分离**: 同步与查询功能独立
- ✅ **独立部署**: 可以单独更新和扩展
- ✅ **性能优化**: 各自专注核心功能
- ✅ **维护简化**: 代码结构更清晰
- ✅ **扩展性强**: 便于水平扩展

## 🎉 完成状态

- [x] 创建新项目目录结构
- [x] 复制共享模块
- [x] 创建查询服务
- [x] 配置Flask应用（端口8000）
- [x] 更新同步服务（端口7777）
- [x] 创建文档和README
- [ ] 测试验证功能分离

建议进行完整的功能测试以确保拆分成功！

