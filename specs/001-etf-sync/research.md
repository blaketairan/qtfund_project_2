# Research: ETF Data Synchronization

**Feature**: 001-etf-sync  
**Date**: 2025-01-27  
**Status**: Complete

## Overview

本文档研究如何将ETF数据同步功能集成到现有股票数据同步系统中，包括API端点、数据库schema变更、以及集成模式。

## Research Topics

### 1. ETF API端点分析

#### API规格

根据spec要求，需要支持以下ETF API端点：

- **ETF列表API**: `https://www.tsanghi.com/api/fin/etf/{exchange_code}/list`
  - 支持上海 (XSHG) 和深圳 (XSHE) 交易所
  - 返回ETF列表，包含代码、名称等基本信息
  
- **ETF历史价格API**: `https://www.tsanghi.com/api/fin/etf/{exchange_code}/daily/realtime`
  - 支持获取ETF历史日线数据
  - 数据格式与股票API类似

#### API数据结构研究

**Decision**: 采用与现有股票API相同的数据格式

**Rationale**: 
- ETF在交易和定价上与股票类似
- 复用现有数据处理逻辑
- 减少代码重复

**Alternatives considered**:
- 创建独立的ETF数据结构：被拒绝，因为会增加不必要的复杂度
- 使用不同的API格式：被拒绝，因为API已标准化

### 2. 数据库Schema扩展策略

#### 当前Schema分析

从 `models/stock_data.py` 分析：

```python
class StockInfo(Base):
    __tablename__ = 'stock_info'
    
    symbol = Column(String(20), primary_key=True)
    stock_name = Column(String(100), nullable=False)
    stock_code = Column(String(10), nullable=False)
    market_code = Column(String(10), nullable=False)
    stock_type = Column(String(20), nullable=True)  # 现有字段
    # ... 其他字段
```

```python
class StockDailyData(Base):
    __tablename__ = 'stock_daily_data'
    
    trade_date = Column(DateTime, primary_key=True)
    symbol = Column(String(20), primary_key=True)
    close_price = Column(DECIMAL(10, 4), nullable=False)
    # ... 其他字段
```

#### Schema扩展方案

**Decision**: 添加 `is_etf` boolean字段到 `StockInfo` 表，而不是创建新表

**Rationale**:
- ETF本质上是一种证券类型，与股票共享大部分属性
- 现有 `stock_type` 字段可以扩展，但使用独立boolean更清晰
- 避免创建重复的数据表
- 查询可以通过简单boolean filter实现

**Implementation**:
```python
class StockInfo(Base):
    # ... 现有字段
    
    # 新增字段
    is_etf = Column(String(1), default='N', nullable=False, comment='是否为ETF (Y/N)')
    
    # 添加索引
    __table_args__ = (
        # ... 现有索引
        Index('idx_is_etf', 'is_etf'),
        # ...
    )
```

**Alternatives considered**:
- 创建单独的 `etf_info` 表：被拒绝，因为ETF数据与股票数据高度一致
- 仅使用 `stock_type` 字段：被拒绝，因为需要独立于股票类型的ETF标识
- 在现有 `stock_type` 中使用枚举：可以考虑，但独立字段更直观

### 3. API集成模式

#### 现有集成模式分析

从 `data_fetcher/stock_api.py` 和 `data_fetcher/exchange_stocks.py` 分析：

1. **Fetch-Fetch Pattern**: 获取API数据 → 处理 → 存储
2. **Incremental Sync**: 支持跳过已存在数据
3. **Batch Processing**: 支持批量处理多只证券
4. **Error Handling**: 单只失败不影响整体流程

#### ETF集成策略

**Decision**: 创建 `data_fetcher/etf_api.py`，复用现有模式但独立实现

**Rationale**:
- ETF API端点不同，需要独立处理
- 数据格式相似，可以复用转换逻辑
- 保持模块化，便于维护

**Implementation Approach**:
```python
class ETFDataFetcher:
    """ETF数据获取器 - 复用股票API模式"""
    
    def fetch_etf_list(self, exchange_code: str) -> List[ETFInfo]:
        """获取ETF列表"""
        # 使用 https://www.tsanghi.com/api/fin/etf/{exchange_code}/list
        
    def fetch_etf_daily_data(self, exchange_code: str, ticker: str) -> List[ETFPriceData]:
        """获取ETF历史价格"""
        # 使用 https://www.tsanghi.com/api/fin/etf/{exchange_code}/daily/realtime
```

### 4. 同步逻辑设计

#### 现有同步流程分析

从 `app/services/sync_service.py` 分析：

1. **sync_stock_lists()**: 同步股票清单到本地JSON
2. **sync_stock_prices()**: 同步股票价格到TimescaleDB
3. **批量处理**: 支持批量同步多只股票
4. **断点续传**: 支持增量同步

#### ETF同步策略

**Decision**: 扩展现有同步服务，添加ETF专用方法

**Implementation**:
- 在 `SyncService` 中添加 `sync_etf_lists()` 方法
- 复用现有 `sync_stock_prices()` 逻辑处理ETF价格数据
- 复用增量同步和错误处理机制

**Code Structure**:
```python
class SyncService:
    # ... 现有方法
    
    def sync_etf_lists(self, exchange_codes: List[str]) -> Dict:
        """同步ETF列表"""
        # 调用 etf_api 获取ETF列表
        # 标记 is_etf = True
        # 存储到 stock_info 表
        
    def sync_etf_prices(self, ...):
        """同步ETF价格（复用股票价格同步逻辑）"""
        # 调用 etf_api 获取价格
        # 存储到 stock_daily_data 表
        # ETF和股票共享同一张价格表
```

### 5. API路由设计

#### 现有路由模式

从 `app/routes/stock_info.py` 和 `app/routes/stock_price.py` 分析：

- Flask-RESTful 或 Flask蓝图模式
- 统一的响应格式
- 错误处理和日志记录

#### ETF路由策略

**Decision**: 创建独立的 `app/routes/etf_routes.py` 或扩展现有路由

**Rationale**:
- ETF需要专门的查询和过滤
- 可以重用现有响应格式
- 保持路由模块化

**Proposed Endpoints**:
```python
# GET /api/v1/etf/list
# GET /api/v1/etf/list/{exchange_code}
# GET /api/v1/etf/info/{symbol}
# GET /api/v1/etf/prices/{symbol}
# POST /api/v1/etf/sync
```

### 6. 数据格式兼容性

#### 测试数据格式

**Decision**: ETF数据使用与股票相同的TimescaleDB schema

**Rationale**:
- 开高低收量等字段与股票完全一致
- 复用现有查询和索引
- 简化数据管理

**Data Format**:
```python
# ETF存储在同一个 stock_daily_data 表
# 通过 symbol 和 is_etf 字段区分
{
    'symbol': 'SH.510050',
    'is_etf': 'Y',  # 在stock_info表中
    'trade_date': '2025-01-27',
    'close_price': 3.52,
    # ... 其他字段与股票完全相同
}
```

## Key Design Decisions

1. **数据库Schema**: 添加 `is_etf` boolean字段而不是创建新表
2. **API集成**: 复用现有数据获取和处理模式
3. **数据存储**: ETF和股票共享价格表，通过is_etf区分
4. **同步逻辑**: 扩展而不是重写现有同步服务
5. **API路由**: 创建独立ETF路由但遵循现有模式

## Implementation Notes

### 迁移策略

1. **Schema变更**: 
   - ALTER TABLE stock_info ADD COLUMN is_etf VARCHAR(1) DEFAULT 'N'
   - 更新现有数据：UPDATE stock_info SET is_etf = 'N' WHERE is_etf IS NULL

2. **向后兼容**:
   - 现有查询不需要修改
   - 新查询通过 `WHERE is_etf = 'Y'` 过滤ETF

3. **索引优化**:
   - 添加 is_etf 索引以支持快速查询

### 测试策略

1. **单元测试**: 测试ETF数据获取和转换
2. **集成测试**: 测试完整同步流程
3. **性能测试**: 验证批量同步性能

## Conclusion

所有关键设计决策已确认，可以开始实现：

- ✅ ETF API端点已确认
- ✅ 数据库schema扩展方案已确定
- ✅ 集成模式已设计
- ✅ 同步逻辑已规划
- ✅ API路由已设计
- ✅ 数据格式兼容性已验证

下一步进入 Phase 1: 详细设计阶段。
