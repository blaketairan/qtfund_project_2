"""
股票清单加载器

从JSON文件加载交易所股票清单到内存，提供快速查询功能
"""

import json
import os
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


@dataclass
class StockInfo:
    """股票信息"""
    ticker: str
    name: str
    is_active: int
    exchange_code: str
    country_code: str
    currency_code: str
    exchange_name_cn: str
    first_fetch_time: str
    
    @property
    def symbol(self) -> str:
        """获取项目内部格式的股票代码"""
        # 根据交易所代码转换为项目格式
        exchange_mapping = {
            'XSHG': 'SH',
            'XSHE': 'SZ', 
            'BJSE': 'BJ'
        }
        prefix = exchange_mapping.get(self.exchange_code, self.exchange_code)
        return f"{prefix}.{self.ticker}"
    
    @property
    def is_active_bool(self) -> bool:
        """判断股票是否活跃"""
        return self.is_active == 1


class StockListsManager:
    """股票清单管理器"""
    
    def __init__(self, stock_lists_dir: str = "constants/stock_lists"):
        """
        初始化股票清单管理器
        
        Args:
            stock_lists_dir: 股票清单文件目录
        """
        self.stock_lists_dir = stock_lists_dir
        self.stocks_by_exchange: Dict[str, List[StockInfo]] = {}
        self.stocks_by_ticker: Dict[str, StockInfo] = {}
        self.stocks_by_symbol: Dict[str, StockInfo] = {}
        self.loaded_at: Optional[datetime] = None
        
    def load_all_stock_lists(self) -> bool:
        """
        加载所有交易所的股票清单
        
        Returns:
            bool: 是否加载成功
        """
        try:
            self.stocks_by_exchange.clear()
            self.stocks_by_ticker.clear()
            self.stocks_by_symbol.clear()
            
            if not os.path.exists(self.stock_lists_dir):
                logger.warning(f"股票清单目录不存在: {self.stock_lists_dir}")
                return False
            
            # 查找所有股票清单文件
            stock_files = [f for f in os.listdir(self.stock_lists_dir) if f.endswith('_stocks.json')]
            
            if not stock_files:
                logger.warning(f"未找到股票清单文件在目录: {self.stock_lists_dir}")
                return False
            
            total_stocks = 0
            loaded_exchanges = []
            
            for file_name in stock_files:
                file_path = os.path.join(self.stock_lists_dir, file_name)
                exchange_code = file_name.replace('_stocks.json', '').upper()
                
                stocks = self._load_exchange_stock_list(file_path, exchange_code)
                if stocks:
                    self.stocks_by_exchange[exchange_code] = stocks
                    total_stocks += len(stocks)
                    loaded_exchanges.append(exchange_code)
                    
                    # 建立索引
                    for stock in stocks:
                        self.stocks_by_ticker[stock.ticker] = stock
                        self.stocks_by_symbol[stock.symbol] = stock
            
            self.loaded_at = datetime.now()
            
            logger.info(f"成功加载 {len(loaded_exchanges)} 个交易所的股票清单，总计 {total_stocks} 只股票")
            logger.info(f"加载的交易所: {', '.join(loaded_exchanges)}")
            
            return True
            
        except Exception as e:
            logger.error(f"加载股票清单失败: {e}")
            return False
    
    def _load_exchange_stock_list(self, file_path: str, exchange_code: str) -> List[StockInfo]:
        """
        加载单个交易所的股票清单
        
        Args:
            file_path: 文件路径
            exchange_code: 交易所代码
            
        Returns:
            List[StockInfo]: 股票信息列表
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            stocks = []
            for item in data:
                stock = StockInfo(**item)
                stocks.append(stock)
            
            logger.info(f"加载 {exchange_code} 股票清单: {len(stocks)} 只")
            return stocks
            
        except Exception as e:
            logger.error(f"加载 {exchange_code} 股票清单失败: {e}")
            return []
    
    def get_stock_by_ticker(self, ticker: str) -> Optional[StockInfo]:
        """
        根据股票代码获取股票信息
        
        Args:
            ticker: 股票代码 (如: 600519)
            
        Returns:
            StockInfo: 股票信息或None
        """
        return self.stocks_by_ticker.get(ticker)
    
    def get_stock_by_symbol(self, symbol: str) -> Optional[StockInfo]:
        """
        根据项目内部格式获取股票信息
        
        Args:
            symbol: 项目格式股票代码 (如: SH.600519)
            
        Returns:
            StockInfo: 股票信息或None
        """
        return self.stocks_by_symbol.get(symbol)
    
    def get_exchange_stocks(self, exchange_code: str) -> List[StockInfo]:
        """
        获取指定交易所的所有股票
        
        Args:
            exchange_code: 交易所代码 (如: XSHG)
            
        Returns:
            List[StockInfo]: 股票列表
        """
        return self.stocks_by_exchange.get(exchange_code.upper(), [])
    
    def get_active_stocks(self, exchange_code: Optional[str] = None) -> List[StockInfo]:
        """
        获取活跃股票
        
        Args:
            exchange_code: 交易所代码，None表示所有交易所
            
        Returns:
            List[StockInfo]: 活跃股票列表
        """
        if exchange_code:
            stocks = self.get_exchange_stocks(exchange_code)
            return [stock for stock in stocks if stock.is_active_bool]
        else:
            all_stocks = []
            for stocks in self.stocks_by_exchange.values():
                all_stocks.extend([stock for stock in stocks if stock.is_active_bool])
            return all_stocks
    
    def search_stocks_by_name(self, keyword: str, exchange_code: Optional[str] = None) -> List[StockInfo]:
        """
        按股票名称搜索
        
        Args:
            keyword: 搜索关键词
            exchange_code: 交易所代码，None表示所有交易所
            
        Returns:
            List[StockInfo]: 匹配的股票列表
        """
        keyword = keyword.lower()
        
        if exchange_code:
            stocks = self.get_exchange_stocks(exchange_code)
        else:
            stocks = list(self.stocks_by_ticker.values())
        
        return [stock for stock in stocks if keyword in (stock.name or '').lower()]
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        获取统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {
            'loaded_at': self.loaded_at.strftime('%Y-%m-%d %H:%M:%S') if self.loaded_at else None,
            'total_stocks': len(self.stocks_by_ticker),
            'total_exchanges': len(self.stocks_by_exchange),
            'exchanges': {}
        }
        
        for exchange_code, stocks in self.stocks_by_exchange.items():
            active_count = sum(1 for stock in stocks if stock.is_active_bool)
            stats['exchanges'][exchange_code] = {
                'total': len(stocks),
                'active': active_count,
                'inactive': len(stocks) - active_count
            }
        
        return stats
    
    def validate_symbol_exists(self, symbol: str) -> bool:
        """
        验证股票代码是否存在
        
        Args:
            symbol: 项目格式股票代码 (如: SH.600519)
            
        Returns:
            bool: 是否存在
        """
        return symbol in self.stocks_by_symbol
    
    def get_newly_added_stocks(self, days: int = 7) -> List[StockInfo]:
        """
        获取最近新增的股票
        
        Args:
            days: 天数
            
        Returns:
            List[StockInfo]: 新增股票列表
        """
        from datetime import timedelta
        
        cutoff_time = datetime.now() - timedelta(days=days)
        new_stocks = []
        
        for stock in self.stocks_by_ticker.values():
            try:
                fetch_time = datetime.strptime(stock.first_fetch_time, '%Y-%m-%d %H:%M:%S')
                if fetch_time >= cutoff_time:
                    new_stocks.append(stock)
            except ValueError:
                continue
        
        return sorted(new_stocks, key=lambda x: x.first_fetch_time, reverse=True)


# 全局股票清单管理器实例
stock_lists_manager = StockListsManager()


def load_stock_lists() -> bool:
    """加载股票清单到内存"""
    return stock_lists_manager.load_all_stock_lists()


def get_stock_by_symbol(symbol: str) -> Optional[StockInfo]:
    """根据项目格式获取股票信息"""
    return stock_lists_manager.get_stock_by_symbol(symbol)


def get_stock_by_ticker(ticker: str) -> Optional[StockInfo]:
    """根据股票代码获取股票信息"""
    return stock_lists_manager.get_stock_by_ticker(ticker)


def validate_stock_symbol(symbol: str) -> bool:
    """验证股票代码是否存在"""
    return stock_lists_manager.validate_symbol_exists(symbol)


if __name__ == "__main__":
    # 使用示例
    print("股票清单加载器测试")
    print("=" * 40)
    
    # 加载股票清单
    if load_stock_lists():
        print("✅ 股票清单加载成功")
        
        # 显示统计信息
        stats = stock_lists_manager.get_statistics()
        print(f"\n📊 统计信息:")
        print(f"  总股票数: {stats['total_stocks']}")
        print(f"  交易所数: {stats['total_exchanges']}")
        print(f"  加载时间: {stats['loaded_at']}")
        
        for exchange, info in stats['exchanges'].items():
            print(f"  {exchange}: {info['total']} 只 (活跃: {info['active']})")
        
        # 测试查询功能
        print(f"\n🔍 查询测试:")
        
        # 按代码查询
        stock = get_stock_by_symbol("SH.600519")
        if stock:
            print(f"  SH.600519 -> {stock.name} ({stock.exchange_name_cn})")
        
        # 按名称搜索
        search_results = stock_lists_manager.search_stocks_by_name("茅台")
        if search_results:
            print(f"  搜索'茅台': 找到 {len(search_results)} 只股票")
            for stock in search_results[:3]:  # 显示前3个
                print(f"    {stock.symbol}: {stock.name}")
        
        # 显示最近新增股票
        new_stocks = stock_lists_manager.get_newly_added_stocks(30)
        if new_stocks:
            print(f"  最近30天新增: {len(new_stocks)} 只股票")
    
    else:
        print("❌ 股票清单加载失败")