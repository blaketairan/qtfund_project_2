# 股票数据同步系统

基于Flask和TimescaleDB的股票行情数据同步系统。

## 项目结构

```
.
├── app/                    # Flask应用
│   ├── routes/            # API路由
│   ├── services/          # 业务逻辑
│   └── utils/             # 工具函数
├── config/                # 配置文件
├── database/              # 数据库连接
├── models/                # 数据模型
├── data_fetcher/          # 数据获取
├── constants/             # 常量和股票清单
├── utils/                 # 通用工具
├── logs/                  # 日志文件
├── start_flask_app.py     # Flask启动脚本
└── full_sync_v2.py        # 全量同步脚本
```

## 快速开始

环境初始化请参考 [SETUP.md](./SETUP.md)

## Project Structure

```
project_2/
├── __init__.py              # 项目初始化文件
├── requirements.txt         # Python 依赖包
├── .env.template           # 配置文件模板
├── test_simple.py          # 数据库连接测试脚本
├── README.md               # 项目说明文档
│
├── config/                 # 配置模块
│   ├── __init__.py
│   └── settings.py         # 数据库和应用配置
│
├── database/               # 数据库连接模块
│   ├── __init__.py
│   └── connection.py       # TimescaleDB 连接管理
│
├── models/                 # 数据模型
│   ├── __init__.py
│   └── stock_data.py       # 股票行情数据模型
│
└── utils/                  # 工具模块
    └── __init__.py
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置数据库

复制配置模板并修改连接信息：

```bash
cp .env.template .env
```

编辑 `.env` 文件，填入您的 TimescaleDB 连接信息：

```env
DB_HOST=localhost
DB_PORT=5432
DB_NAME=securities_data
DB_USER=your_username
DB_PASSWORD=your_password
```

### 3. 测试连接

运行测试脚本验证配置：

```bash
python test_simple.py
```

### 4. 数据库初始化（可选）

如果需要创建 TimescaleDB 超表和优化策略，可以在 Python 中执行：

```python
from database.connection import db_manager
from models.stock_data import StockDailyData

# 创建超表（需要 TimescaleDB 扩展）
with db_manager.get_session() as session:
    StockDailyData.create_hypertable(session)
```

## 数据模型

### 股票日行情数据 (StockDailyData)

用于存储股票的日级别行情数据，支持 TimescaleDB 时序优化。

**主要字段：**
- `trade_date`: 交易日期（主键）
- `symbol`: 股票代码，格式：市场+代码（如 SH.000001, SZ.159998）
- `stock_name`: 股票名称
- `close_price`: 收盘价
- `volume`: 成交量（手）
- `turnover`: 成交额（元）
- `price_change_pct`: 涨跌幅（%）
- `premium_rate`: 溢价率（%，基金专用）

### 股票基础信息 (StockInfo)

存储股票的基本信息和分类数据。

**主要字段：**
- `symbol`: 股票代码（主键）
- `stock_name`: 股票名称
- `market_code`: 市场代码（SH/SZ）
- `stock_type`: 股票类型
- `industry`: 所属行业

## 使用示例

```python
from database.connection import db_manager
from models.stock_data import StockDailyData, StockInfo
from datetime import datetime
from decimal import Decimal

# 插入股票基础信息
with db_manager.get_session() as session:
    stock = StockInfo(
        symbol="SH.000001",
        stock_name="平安银行",
        stock_code="000001",
        market_code="SH",
        stock_type="股票",
        industry="银行"
    )
    session.add(stock)

# 插入行情数据
with db_manager.get_session() as session:
    data = StockDailyData(
        trade_date=datetime.now(),
        symbol="SH.000001",
        stock_name="平安银行",
        close_price=Decimal("12.50"),
        volume=100000,
        turnover=Decimal("1250000.00"),
        price_change_pct=Decimal("1.63"),
        market_code="SH"
    )
    session.add(data)
```

## TimescaleDB 特性

### 时序优化
- 按月分区 (chunk_time_interval = 1 month)
- 自动数据压缩（7天后压缩）
- 数据保留策略（保留3年）

### 索引优化
- 复合索引：`(symbol, trade_date)`
- 市场代码索引：`market_code`
- 交易日期索引：`trade_date`

## 配置说明

### 数据库配置
- `DB_HOST`: 数据库主机地址
- `DB_PORT`: 数据库端口
- `DB_NAME`: 数据库名称
- `DB_USER/DB_PASSWORD`: 认证信息

### 连接池配置
- `DB_POOL_SIZE`: 连接池大小（默认10）
- `DB_MAX_OVERFLOW`: 最大溢出连接（默认20）
- `DB_POOL_TIMEOUT`: 连接超时（默认30秒）

### TimescaleDB 策略
- `COMPRESSION_INTERVAL_DAYS`: 压缩间隔（默认7天）
- `DATA_RETENTION_DAYS`: 数据保留天数（默认1095天）

## 注意事项

1. **TimescaleDB 扩展**：系统兼容普通 PostgreSQL，但建议使用 TimescaleDB 以获得最佳性能
2. **数据精度**：价格使用 DECIMAL 类型确保精度
3. **主键设计**：`(trade_date, symbol)` 复合主键支持时序查询
4. **市场标识**：统一使用 "SH.代码" 和 "SZ.代码" 格式

## 许可证

本项目仅供学习和研究使用。