# Quickstart: ETF Data Synchronization

**Feature**: 001-etf-sync  
**Date**: 2025-01-27  
**Target Users**: Developers implementing ETF sync functionality

## Prerequisites

- Python 3.9.6+
- PostgreSQL with TimescaleDB extension
- Access to tsanghi.com API with valid token
- Existing stock data sync system running

## Quick Start

### 1. Database Setup

#### Step 1: Apply Schema Migration

```bash
# Connect to database
psql -U postgres -d securities_data

# Run migration
psql -U postgres -d securities_data -f specs/001-etf-sync/migrations/add_etf_support.sql
```

Or using Python:

```python
from database.connection import db_manager
from models.stock_data import StockInfo

# Add is_etf column to stock_info table
with db_manager.get_session() as session:
    session.execute("""
        ALTER TABLE stock_info 
        ADD COLUMN IF NOT EXISTS is_etf VARCHAR(1) NOT NULL DEFAULT 'N';
        
        CREATE INDEX IF NOT EXISTS idx_stock_info_is_etf 
        ON stock_info(is_etf);
        
        CREATE INDEX IF NOT EXISTS idx_stock_info_etf_market 
        ON stock_info(market_code, is_etf) 
        WHERE is_etf = 'Y';
    """)
    session.commit()
```

### 2. Setup ETF API Fetcher

```python
# Create data_fetcher/etf_api.py
from data_fetcher.etf_api import ETFDataFetcher
import os

token = os.getenv('STOCK_API_TOKEN')
fetcher = ETFDataFetcher(token)

# Get ETF list
etf_list = fetcher.fetch_etf_list(exchange_code='XSHG')
```

### 3. First ETF Sync

#### Option A: Using Python Script

```python
# sync_etf.py
from app.services.etf_sync_service import ETFSyncService

# Initialize sync service
sync_service = ETFSyncService()

# Sync ETF list for Shanghai exchange
result = sync_service.sync_etf_lists(exchange_codes=['XSHG'])
print(f"Synced {result['total_etfs']} ETFs from {result['exchange_code']}")

# Sync ETF prices for specific ETF
result = sync_service.sync_etf_prices(symbol='SH.510050', start_year=2020)
print(f"Synced {result['records_count']} price records")
```

#### Option B: Using Flask API

```bash
# Start the Flask app
python start_flask_app.py

# Sync ETF data
curl -X POST http://localhost:5000/api/v1/etf/sync \
  -H "Content-Type: application/json" \
  -d '{
    "exchanges": ["SH", "SZ"],
    "sync_type": "both",
    "force_update": false,
    "start_year": 2020
  }'
```

### 4. Query ETF Data

#### Get ETF List

```bash
# Get all ETFs
curl http://localhost:5000/api/v1/etf/list

# Get ETFs by exchange
curl http://localhost:5000/api/v1/etf/list?exchange_code=SH

# Get ETFs with pagination
curl "http://localhost:5000/api/v1/etf/list?limit=10&offset=0"
```

#### Get ETF Info

```bash
# Get specific ETF information
curl http://localhost:5000/api/v1/etf/info/SH.510050
```

#### Get ETF Price History

```bash
# Get price history for specific ETF
curl http://localhost:5000/api/v1/etf/prices/SH.510050

# Get price history for date range
curl "http://localhost:5000/api/v1/etf/prices/SH.510050?start_date=2024-01-01&end_date=2024-12-31"
```

## Code Examples

### Example 1: Sync ETF List

```python
from app.services.etf_sync_service import ETFSyncService

# Initialize service
sync_service = ETFSyncService()

# Sync ETFs from both exchanges
result = sync_service.sync_etf_lists(
    exchange_codes=['XSHG', 'XSHE']
)

if result['success']:
    print(f"Successfully synced {result['total_etfs']} ETFs")
    print(f"New ETFs: {result['new_etfs']}")
    print(f"Updated ETFs: {result['updated_etfs']}")
else:
    print(f"Error: {result['error']}")
```

### Example 2: Query ETF Data

```python
from app.services.stock_info_service import StockInfoService

# Initialize service
info_service = StockInfoService()

# Get ETF list
result = info_service.query_from_local_files(
    keyword='ETF',
    limit=100
)

if result['success']:
    print(f"Found {result['total']} ETFs")
    for etf in result['data']:
        print(f"  {etf['ticker']}: {etf['name']}")
```

### Example 3: Get ETF Price History

```python
from app.services.stock_data_service import StockDataService
from datetime import datetime, timedelta

# Initialize service
data_service = StockDataService()

# Get price history for last 30 days
end_date = datetime.now()
start_date = end_date - timedelta(days=30)

result = data_service.query_stock_data_from_db(
    symbol='SH.510050',
    start_date=start_date.strftime('%Y-%m-%d'),
    end_date=end_date.strftime('%Y-%m-%d'),
    limit=100
)

if result['success']:
    print(f"Found {result['count']} price records")
    for record in result['data']:
        print(f"{record.trade_date}: Close={record.close_price}")
```

### Example 4: Filter ETFs by Exchange

```python
from database.connection import db_manager
from models.stock_data import StockInfo

# Query ETFs from Shanghai exchange
with db_manager.get_session() as session:
    etfs = session.query(StockInfo).filter(
        StockInfo.is_etf == 'Y',
        StockInfo.market_code == 'SH',
        StockInfo.is_active == 'Y'
    ).all()
    
    print(f"Found {len(etfs)} ETFs from Shanghai exchange")
    for etf in etfs:
        print(f"  {etf.symbol}: {etf.stock_name}")
```

## Directory Structure

```
app/
├── routes/
│   └── etf_routes.py          # ETF API routes
├── services/
│   └── etf_sync_service.py    # ETF sync service
data_fetcher/
└── etf_api.py                  # ETF API fetcher
models/
└── stock_data.py              # Extended with is_etf field
```

## API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/etf/list` | GET | Get ETF list (with filters) |
| `/api/v1/etf/list/{exchange_code}` | GET | Get ETFs by exchange |
| `/api/v1/etf/info/{symbol}` | GET | Get ETF information |
| `/api/v1/etf/prices/{symbol}` | GET | Get ETF price history |
| `/api/v1/etf/sync` | POST | Trigger ETF sync |

## Common Tasks

### Task 1: Sync ETFs for First Time

```bash
# 1. Ensure database schema is updated
python -c "from specs.001-etf-sync.scripts.apply_schema import main; main()"

# 2. Sync ETF list
python -c "from app.services.etf_sync_service import ETFSyncService; ETFSyncService().sync_etf_lists(['XSHG', 'XSHE'])"

# 3. Verify data
curl http://localhost:5000/api/v1/etf/list | jq '.total'
```

### Task 2: Update ETF Price Data

```python
# Sync prices for all ETFs
from app.services.etf_sync_service import ETFSyncService

sync_service = ETFSyncService()

# Get all ETF symbols
import json
with open('constants/stock_lists/xshg_stocks.json') as f:
    stocks = json.load(f)
    etf_symbols = [f"SH.{s['ticker']}" for s in stocks if 'ETF' in s['name']]

# Sync prices
for symbol in etf_symbols[:10]:  # Start with 10 ETFs
    result = sync_service.sync_etf_prices(
        symbol=symbol,
        start_year=2020
    )
    print(f"{symbol}: {result['records_count']} records")
```

### Task 3: Query ETF Statistics

```python
from app.services.stock_info_service import StockInfoService

service = StockInfoService()

# Get ETF count by exchange
stats = service.get_stock_statistics()
print(f"Total stocks: {stats['total_stocks']}")

# Filter ETFs
result = service.query_from_local_files(
    keyword='ETF',
    is_active='1',
    limit=0  # Get all
)

print(f"Total ETFs: {result['total']}")
```

## Troubleshooting

### Issue: ETF list sync fails

**Symptoms**: 
```
ERROR: ETF list sync failed: API error
```

**Solutions**:
1. Check API token: `echo $STOCK_API_TOKEN`
2. Verify API endpoint is accessible
3. Check network connectivity

### Issue: ETF not showing up

**Symptoms**: 
```
ETF list returns 0 results
```

**Solutions**:
1. Verify `is_etf='Y'` flag is set in database
2. Check if ETF exists in stock_info table
3. Verify ETF name contains 'ETF' keyword

### Issue: Price sync fails

**Symptoms**:
```
ERROR: ETF price sync failed
```

**Solutions**:
1. Verify ETF exists in stock_info with is_etf='Y'
2. Check API rate limits
3. Verify date range is valid

## Next Steps

1. Review [data-model.md](data-model.md) for detailed schema information
2. Review [research.md](research.md) for technical decisions
3. Review [contracts/openapi.yaml](contracts/openapi.yaml) for API specification
4. See [plan.md](plan.md) for implementation overview

## Support

For issues or questions:
- Check existing documentation in `docs/`
- Review API logs at `logs/app.log`
- Open an issue in project repository
