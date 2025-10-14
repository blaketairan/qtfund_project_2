"""
股票数据API接口模块

封装第三方API调用，获取股票历史日线数据
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from dataclasses import dataclass

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))

def get_china_time() -> datetime:
    """获取中国时区当前时间"""
    return datetime.now(CHINA_TZ)

# 设置日志
logger = logging.getLogger(__name__)


@dataclass
class StockDailyRecord:
    """股票日线数据记录"""
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class StockDataFetcher:
    """股票数据获取器"""
    
    def __init__(self, token: str = "aa029acaec9548e9b8ba844722746760"):
        """
        初始化数据获取器
        
        Args:
            token: API访问令牌
        """
        self.token = token
        self.base_url = "https://www.tsanghi.com/api/fin/stock"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Securities Data Storage System/1.0'
        })
    
    def fetch_daily_data(self, market: str, ticker: str, 
                        start_date: Optional[str] = None, 
                        end_date: Optional[str] = None) -> List[StockDailyRecord]:
        """
        获取股票日线数据
        
        Args:
            market: 市场代码 (XSHG: 上海证券交易所, XSHE: 深圳证券交易所)
            ticker: 股票代码 (如: 600519)
            start_date: 开始日期 (可选，格式: YYYY-MM-DD)
            end_date: 结束日期 (可选，格式: YYYY-MM-DD)
            
        Returns:
            List[StockDailyRecord]: 股票日线数据列表
            
        Raises:
            requests.RequestException: 网络请求异常
            ValueError: 数据格式异常
        """
        url = f"{self.base_url}/{market}/daily"
        params = {
            'token': self.token,
            'ticker': ticker
        }
        
        # 添加日期参数（如果提供）
        if start_date:
            params['start_date'] = start_date
        if end_date:
            params['end_date'] = end_date
        
        try:
            # 记录HTTP请求信息
            date_range = ""
            if start_date or end_date:
                date_range = f" (日期范围: {start_date or '最早'} ~ {end_date or '最新'})"
            logger.info(f"🌐 HTTP请求: GET {url} - {market}.{ticker}{date_range}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ HTTP响应: {market}.{ticker} - 状态码 {response.status_code}")
            
            data = response.json()
            
            # 检查API响应格式
            if data.get('code') != 200:
                raise ValueError(f"API error: {data.get('msg', 'Unknown error')}")
            
            records = []
            for item in data.get('data', []):
                record = StockDailyRecord(
                    ticker=item['ticker'],
                    date=item['date'],
                    open=float(item['open']),
                    high=float(item['high']),
                    low=float(item['low']),
                    close=float(item['close']),
                    volume=int(item['volume'])
                )
                records.append(record)
            
            logger.info(f"Successfully fetched {len(records)} records for {market}.{ticker}")
            return records
            
        except requests.RequestException as e:
            logger.error(f"Network error fetching data for {market}.{ticker}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"Data format error for {market}.{ticker}: {e}")
            raise ValueError(f"Invalid data format: {e}")
    
    def convert_symbol_format(self, symbol: str) -> tuple[str, str]:
        """
        转换股票代码格式
        
        Args:
            symbol: 项目内部格式 (如: SH.600519, SZ.000001)
            
        Returns:
            tuple: (market, ticker) - (XSHG/XSHE, 600519)
            
        Raises:
            ValueError: 无效的股票代码格式
        """
        if '.' not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        market_code, ticker = symbol.split('.', 1)
        
        # 市场代码映射
        market_mapping = {
            'SH': 'XSHG',  # 上海证券交易所
            'SZ': 'XSHE'   # 深圳证券交易所
        }
        
        if market_code not in market_mapping:
            raise ValueError(f"Unsupported market code: {market_code}")
        
        return market_mapping[market_code], ticker
    
    def fetch_by_symbol(self, symbol: str, 
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[StockDailyRecord]:
        """
        使用项目内部股票代码格式获取数据
        
        Args:
            symbol: 股票代码 (如: SH.600519, SZ.000001)
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)
            
        Returns:
            List[StockDailyRecord]: 股票日线数据列表
        """
        market, ticker = self.convert_symbol_format(symbol)
        return self.fetch_daily_data(market, ticker, start_date, end_date)


def fetch_stock_daily_data(symbol: str, 
                          token: str = "aa029acaec9548e9b8ba844722746760",
                          start_date: Optional[str] = None,
                          end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    便捷函数：获取股票日线数据
    
    Args:
        symbol: 股票代码 (如: SH.600519, SZ.000001)
        token: API访问令牌
        start_date: 开始日期 (可选，格式: YYYY-MM-DD)
        end_date: 结束日期 (可选，格式: YYYY-MM-DD)
        
    Returns:
        List[Dict]: 标准化的股票数据字典列表
        
    Example:
        >>> data = fetch_stock_daily_data("SH.600519")
        >>> print(f"获取到 {len(data)} 条数据")
    """
    fetcher = StockDataFetcher(token)
    records = fetcher.fetch_by_symbol(symbol, start_date, end_date)
    
    # 转换为字典格式，便于后续处理
    return [
        {
            'ticker': record.ticker,
            'date': record.date,
            'open': record.open,
            'high': record.high,
            'low': record.low,
            'close': record.close,
            'volume': record.volume
        }
        for record in records
    ]


def convert_to_database_format(api_data: List[Dict[str, Any]], symbol: str, stock_name: str) -> List[Dict[str, Any]]:
    """
    将API数据转换为数据库存储格式
    
    Args:
        api_data: API返回的原始数据
        symbol: 股票代码 (如: SH.600519)
        stock_name: 股票名称
        
    Returns:
        List[Dict]: 适合数据库存储的数据格式
    """
    db_records = []
    market_code = symbol.split('.')[0] if '.' in symbol else 'UNKNOWN'
    
    china_now = get_china_time()
    
    for item in api_data:
        # 转换日期格式 - 使用中国时区
        trade_date_naive = datetime.strptime(item['date'], '%Y-%m-%d')
        # 设置为中国时区当天的开始时间
        trade_date = trade_date_naive.replace(tzinfo=CHINA_TZ)
        
        # 计算涨跌信息（需要有前一天的数据才能计算）
        record = {
            'trade_date': trade_date,
            'symbol': symbol,
            'stock_name': stock_name,
            'close_price': Decimal(str(item['close'])),
            'open_price': Decimal(str(item['open'])),
            'high_price': Decimal(str(item['high'])),
            'low_price': Decimal(str(item['low'])),
            'volume': item['volume'],
            'turnover': Decimal(str(item['volume'] * item['close'])),  # 估算成交额
            'market_code': market_code,
            'price_change': None,  # 需要计算
            'price_change_pct': None,  # 需要计算
            'premium_rate': None,  # 基金类产品需要单独设置
            'created_at': china_now,
            'updated_at': china_now
        }
        db_records.append(record)
    
    # 计算涨跌幅（按日期排序后计算）
    db_records.sort(key=lambda x: x['trade_date'])
    
    for i in range(1, len(db_records)):
        current = db_records[i]
        previous = db_records[i-1]
        
        price_change = current['close_price'] - previous['close_price']
        price_change_pct = (price_change / previous['close_price']) * 100
        
        current['price_change'] = price_change
        current['price_change_pct'] = price_change_pct
    
    return db_records


# 使用示例
if __name__ == "__main__":
    # 基础使用示例
    try:
        # 方式1: 使用便捷函数
        data = fetch_stock_daily_data("SH.600519")
        print(f"获取到 {len(data)} 条数据")
        if data:
            print(f"最新数据: {data[0]}")
        
        # 方式2: 使用类
        fetcher = StockDataFetcher()
        records = fetcher.fetch_by_symbol("SH.600519", start_date="2024-01-01", end_date="2024-01-10")
        print(f"指定时间范围数据: {len(records)} 条")
        
        # 方式3: 转换为数据库格式
        db_data = convert_to_database_format(data, "SH.600519", "贵州茅台")
        print(f"数据库格式数据: {len(db_data)} 条")
        
    except Exception as e:
        print(f"获取数据失败: {e}")