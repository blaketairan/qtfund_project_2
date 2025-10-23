# 股票数据同步服务

负责从远程HTTP接口获取数据并同步到TimescaleDB的服务。

## 项目简介

本服务专注于数据同步功能，从第三方API获取股票数据并写入TimescaleDB数据库。数据查询功能已拆分到独立的查询服务（`qtfund_project_3`，端口8000）。

## 功能特性

- ✅ 从远程API获取股票数据
- ✅ 数据同步到TimescaleDB
- ✅ 交易所信息同步
- ✅ 股票清单同步
- ✅ 股票行情数据同步
- ✅ 后台任务管理
- ✅ 断点续传支持

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置环境变量

创建 `.env` 文件并配置：

```env
# 数据库配置
DB_HOST=localhost
DB_PORT=5432
DB_NAME=securities_data
DB_USER=your_username
DB_PASSWORD=your_password

# API Token
STOCK_API_TOKEN=your_api_token
```

### 3. 启动服务

```bash
# 前台启动
python start_flask_app.py

# 后台启动
nohup python start_flask_app.py > logs/flask.log 2>&1 &
```

服务将在 **http://localhost:7777** 启动

## API接口

### 健康检查

```bash
GET http://localhost:7777/api/health
```

### 同步任务

```bash
# 同步交易所信息
POST http://localhost:7777/api/sync/exchanges

# 同步股票清单
POST http://localhost:7777/api/sync/stock-lists

# 同步股票行情（后台任务）
POST http://localhost:7777/api/sync/stock-prices
{
    "start_year": 2020,
    "max_stocks": 100,
    "background": true
}

# 同步单只股票
POST http://localhost:7777/api/sync/single-stock
{
    "symbol": "SH.600519"
}

# 完整同步
POST http://localhost:7777/api/sync/full-sync
```

### 任务管理

```bash
# 查询所有任务
GET http://localhost:7777/api/sync/tasks

# 查询任务状态
GET http://localhost:7777/api/sync/tasks/<task_id>

# 停止任务
POST http://localhost:7777/api/sync/tasks/<task_id>/stop
```

## 全量同步脚本

```bash
# 测试模式：同步单只股票
python full_sync_v2.py --test SH.600519

# 同步前100只股票
python full_sync_v2.py --max 100

# 跳过前50只，同步接下来的100只
python full_sync_v2.py --skip 50 --max 100
```

## 项目结构

```
qtfund_project_2/
├── app/                          # Flask应用
│   ├── routes/                   # API路由
│   │   ├── health.py            # 健康检查
│   │   └── sync_tasks.py        # 同步任务
│   ├── services/                # 业务逻辑
│   │   ├── sync_service.py          # 同步服务
│   │   ├── single_stock_sync.py     # 单股同步
│   │   └── background_tasks.py      # 后台任务
│   └── main.py                  # Flask主应用
├── data_fetcher/                # 数据获取模块
│   ├── stock_api.py            # 第三方API封装
│   └── exchange_stocks.py      # 交易所股票清单
├── utils/                       # 工具模块
│   └── data_integration.py     # 数据集成
├── config/                      # 配置
├── database/                    # 数据库连接
├── models/                      # 数据模型
├── constants/                   # 常量和股票清单
├── full_sync_v2.py             # 全量同步脚本
└── start_flask_app.py          # 启动脚本
```

## 与查询服务的关系

- **本服务 (端口7777)**: 负责数据同步和写入
- **查询服务 (端口8000)**: 负责数据查询和读取

两个服务共享同一个TimescaleDB数据库，职责明确分离。

## 核心功能模块

### 1. 数据获取 (data_fetcher)

从第三方API获取股票数据：
- 股票日线数据
- 交易所信息
- 股票清单

### 2. 数据集成 (utils/data_integration.py)

将API数据转换并写入数据库：
- 数据格式转换
- 涨跌幅计算
- 断点续传支持
- 批量插入优化

### 3. 同步服务 (app/services/sync_service.py)

提供完整的同步流程：
- 交易所信息同步
- 股票清单同步
- 股票行情同步（支持批量和单股）

### 4. 后台任务 (app/services/background_tasks.py)

异步任务管理：
- 任务创建和执行
- 任务状态查询
- 任务停止控制

## 注意事项

1. 确保配置了正确的 `STOCK_API_TOKEN`
2. 数据库需要正确连接
3. 建议配合查询服务一起使用
4. 大批量同步建议使用后台任务模式

## 许可证

本项目仅供学习和研究使用。
