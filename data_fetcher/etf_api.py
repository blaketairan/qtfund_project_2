"""
ETF数据API接口模块

封装第三方API调用，获取ETF列表和历史价格数据
"""

import requests
import os
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
class ETFListItem:
    """ETF列表项"""
    ticker: str
    name: str
    is_active: int
    exchange_code: str
    country_code: str
    currency_code: str


@dataclass
class ETFPriceRecord:
    """ETF价格数据记录"""
    ticker: str
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


class ETFDataFetcher:
    """ETF数据获取器"""
    
    def __init__(self, token: str):
        """
        初始化ETF数据获取器

        Args:
            token: API访问令牌
        """
        self.token = token
        self.base_url = "https://www.tsanghi.com/api/fin/etf"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Securities Data Storage System/1.0'
        })
    
    def fetch_etf_list(self, exchange_code: str) -> List[ETFListItem]:
        """
        获取指定交易所的ETF列表
        
        Args:
            exchange_code: 交易所代码 (XSHG: 上海证券交易所, XSHE: 深圳证券交易所)
            
        Returns:
            List[ETFListItem]: ETF列表
            
        Raises:
            requests.RequestException: 网络请求异常
            ValueError: 数据格式异常
        """
        url = f"{self.base_url}/{exchange_code}/list"
        params = {'token': self.token}
        
        try:
            logger.info(f"正在获取 {exchange_code} 的ETF列表...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ HTTP响应: {exchange_code} - 状态码 {response.status_code}")
            
            data = response.json()
            
            # 检查API响应格式
            if data.get('code') != 200:
                raise ValueError(f"API error: {data.get('msg', 'Unknown error')}")
            
            etf_list = []
            for item in data.get('data', []):
                etf_item = ETFListItem(
                    ticker=item['ticker'],
                    name=item['name'],
                    is_active=item['is_active'],
                    exchange_code=item['exchange_code'],
                    country_code=item['country_code'],
                    currency_code=item['currency_code']
                )
                etf_list.append(etf_item)
            
            logger.info(f"成功获取 {exchange_code} ETF列表: {len(etf_list)} 只ETF")
            return etf_list
            
        except requests.RequestException as e:
            logger.error(f"网络错误 - {exchange_code}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"数据格式错误 - {exchange_code}: {e}")
            raise ValueError(f"Invalid data format: {e}")
    
    def fetch_etf_daily_data(self, exchange_code: str, ticker: str,
                            start_date: Optional[str] = None,
                            end_date: Optional[str] = None) -> List[ETFPriceRecord]:
        """
        获取ETF日线数据
        
        Args:
            exchange_code: 交易所代码 (XSHG/XSHE)
            ticker: ETF代码 (如: 510050)
            start_date: 开始日期 (可选，格式: YYYY-MM-DD)
            end_date: 结束日期 (可选，格式: YYYY-MM-DD)
            
        Returns:
            List[ETFPriceRecord]: ETF价格数据列表
            
        Raises:
            requests.RequestException: 网络请求异常
            ValueError: 数据格式异常
        """
        url = f"{self.base_url}/{exchange_code}/daily"  # 使用 /daily 获取历史数据
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
            logger.info(f"🌐 HTTP请求: GET {url} - {exchange_code}.{ticker}{date_range}")
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            logger.info(f"✅ HTTP响应: {exchange_code}.{ticker} - 状态码 {response.status_code}")
            
            data = response.json()
            
            # 检查API响应格式
            if data.get('code') != 200:
                raise ValueError(f"API error: {data.get('msg', 'Unknown error')}")
            
            records = []
            for item in data.get('data', []):
                record = ETFPriceRecord(
                    ticker=item['ticker'],
                    date=item['date'],
                    open=float(item['open']),
                    high=float(item['high']),
                    low=float(item['low']),
                    close=float(item['close']),
                    volume=int(item['volume'])
                )
                records.append(record)
            
            logger.info(f"成功获取 {len(records)} 条价格数据 for {exchange_code}.{ticker}")
            return records
            
        except requests.RequestException as e:
            logger.error(f"网络错误获取ETF价格数据 {exchange_code}.{ticker}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"数据格式错误 for {exchange_code}.{ticker}: {e}")
            raise ValueError(f"Invalid data format: {e}")
    
    def convert_symbol_format(self, symbol: str) -> tuple[str, str]:
        """
        转换股票代码格式
        
        Args:
            symbol: 项目内部格式 (如: SH.510050, SZ.159001)
            
        Returns:
            tuple: (exchange_code, ticker) - (XSHG/XSHE, 510050)
            
        Raises:
            ValueError: 无效的股票代码格式
        """
        if '.' not in symbol:
            raise ValueError(f"Invalid symbol format: {symbol}")
        
        market_code, ticker = symbol.split('.', 1)
        
        # 市场代码映射
        market_mapping = {
            'SH': 'XSHG',  # 上海证券交易所
            'SZ': 'XSHE',  # 深圳证券交易所
            'BJ': 'BJSE'  # 北京证券交易所
        }
        
        if market_code not in market_mapping:
            raise ValueError(f"Unsupported market code: {market_code}")
        
        return market_mapping[market_code], ticker
    
    def fetch_by_symbol(self, symbol: str,
                       start_date: Optional[str] = None,
                       end_date: Optional[str] = None) -> List[ETFPriceRecord]:
        """
        使用项目内部股票代码格式获取数据
        
        Args:
            symbol: ETF代码 (如: SH.510050, SZ.159001)
            start_date: 开始日期 (可选)
            end_date: 结束日期 (可选)
            
        Returns:
            List[ETFPriceRecord]: ETF价格数据列表
        """
        exchange_code, ticker = self.convert_symbol_format(symbol)
        return self.fetch_etf_daily_data(exchange_code, ticker, start_date, end_date)


# 便捷函数
def fetch_etf_list(exchange_code: str, token: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    便捷函数：获取ETF列表

    Args:
        exchange_code: 交易所代码
        token: API访问令牌，如果为None则从环境变量获取

    Returns:
        List[Dict]: ETF列表数据
    """
    if token is None:
        token = os.getenv('STOCK_API_TOKEN')
        if not token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables.")

    fetcher = ETFDataFetcher(token)
    etf_list = fetcher.fetch_etf_list(exchange_code)
    
    # 转换为字典格式
    return [
        {
            'ticker': item.ticker,
            'name': item.name,
            'is_active': item.is_active,
            'exchange_code': item.exchange_code,
            'country_code': item.country_code,
            'currency_code': item.currency_code
        }
        for item in etf_list
    ]


def fetch_etf_daily_data_by_symbol(symbol: str,
                                   token: Optional[str] = None,
                                   start_date: Optional[str] = None,
                                   end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    便捷函数：获取ETF历史价格数据

    Args:
        symbol: ETF代码 (如: SH.510050, SZ.159001)
        token: API访问令牌
        start_date: 开始日期 (可选)
        end_date: 结束日期 (可选)

    Returns:
        List[Dict]: 标准化的ETF价格数据
    """
    if token is None:
        token = os.getenv('STOCK_API_TOKEN')
        if not token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables.")

    fetcher = ETFDataFetcher(token)
    records = fetcher.fetch_by_symbol(symbol, start_date, end_date)
    
    # 转换为字典格式
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


if __name__ == '__main__':
    # 使用示例
    try:
        token = os.getenv('STOCK_API_TOKEN')
        if not token:
            print("Error: STOCK_API_TOKEN not found in environment variables")
            exit(1)
        
        fetcher = ETFDataFetcher(token)
        
        # 获取ETF列表
        print("获取上海ETF列表...")
        sh_etfs = fetcher.fetch_etf_list('XSHG')
        print(f"获取到 {len(sh_etfs)} 只ETF")
        if sh_etfs:
            print(f"示例: {sh_etfs[0]}")
        
        # 获取ETF价格数据
        if sh_etfs:
            first_etf = sh_etfs[0]
            print(f"\n获取 {first_etf.ticker} 的价格数据...")
            prices = fetcher.fetch_etf_daily_data('XSHG', first_etf.ticker, start_date='2024-01-01')
            print(f"获取到 {len(prices)} 条价格数据")
            if prices:
                print(f"最新价格: {prices[0]}")
        
    except Exception as e:
        print(f"执行失败: {e}")
        import traceback
        traceback.print_exc()
