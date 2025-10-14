"""
中国交易所常量定义

从 exchange_code.json 中提取的中国证券交易所信息
"""

from dataclasses import dataclass
from typing import Dict, List, Optional
from enum import Enum


@dataclass(frozen=True)
class ExchangeInfo:
    """交易所信息数据类"""
    exchange_code: str
    exchange_name: str
    exchange_name_short: str
    country_code: str
    currency_code: str
    local_open: str
    local_close: str
    beijing_open: str
    beijing_close: str
    timezone: str
    delay: Optional[str]
    notes: Optional[str]


class ChineseExchanges:
    """中国证券交易所常量类"""
    
    # 北京证券交易所
    BJSE = ExchangeInfo(
        exchange_code="BJSE",
        exchange_name="北京证券交易所",
        exchange_name_short="北交所",
        country_code="CHN",
        currency_code="CNY",
        local_open="09:30:00",
        local_close="15:00:00",
        beijing_open="09:00:00",
        beijing_close="15:00:00",
        timezone="Asia/Shanghai",
        delay="实时",
        notes=None
    )
    
    # 深圳证券交易所
    XSHE = ExchangeInfo(
        exchange_code="XSHE",
        exchange_name="深圳证券交易所",
        exchange_name_short="深交所",
        country_code="CHN",
        currency_code="CNY",
        local_open="09:30:00",
        local_close="15:00:00",
        beijing_open="09:00:00",
        beijing_close="15:00:00",
        timezone="Asia/Shanghai",
        delay="实时",
        notes=None
    )
    
    # 深圳证券交易所（B股）
    XSHEB = ExchangeInfo(
        exchange_code="XSHEB",
        exchange_name="深圳证券交易所（B股）",
        exchange_name_short="深交所B股",
        country_code="CHN",
        currency_code="HKD",
        local_open="09:30:00",
        local_close="15:00:00",
        beijing_open="09:00:00",
        beijing_close="15:00:00",
        timezone="Asia/Shanghai",
        delay="实时",
        notes=None
    )
    
    # 上海证券交易所
    XSHG = ExchangeInfo(
        exchange_code="XSHG",
        exchange_name="上海证券交易所",
        exchange_name_short="上交所",
        country_code="CHN",
        currency_code="CNY",
        local_open="09:30:00",
        local_close="15:00:00",
        beijing_open="09:00:00",
        beijing_close="15:00:00",
        timezone="Asia/Shanghai",
        delay="实时",
        notes=None
    )
    
    # 上海证券交易所（B股）
    XSHGB = ExchangeInfo(
        exchange_code="XSHGB",
        exchange_name="上海证券交易所（B股）",
        exchange_name_short="上交所B股",
        country_code="CHN",
        currency_code="USD",
        local_open="09:30:00",
        local_close="15:00:00",
        beijing_open="09:00:00",
        beijing_close="15:00:00",
        timezone="Asia/Shanghai",
        delay="实时",
        notes=None
    )
    
    @classmethod
    def get_all_exchanges(cls) -> List[ExchangeInfo]:
        """获取所有中国交易所信息列表"""
        return [
            cls.BJSE,
            cls.XSHE,
            cls.XSHEB,
            cls.XSHG,
            cls.XSHGB
        ]
    
    @classmethod
    def get_exchanges_by_code(cls) -> Dict[str, ExchangeInfo]:
        """按交易所代码获取交易所信息字典"""
        return {
            "BJSE": cls.BJSE,
            "XSHE": cls.XSHE,
            "XSHEB": cls.XSHEB,
            "XSHG": cls.XSHG,
            "XSHGB": cls.XSHGB
        }
    
    @classmethod
    def get_main_exchanges(cls) -> List[ExchangeInfo]:
        """获取主要交易所（排除B股）"""
        return [
            cls.BJSE,
            cls.XSHE,
            cls.XSHG
        ]
    
    @classmethod
    def get_b_stock_exchanges(cls) -> List[ExchangeInfo]:
        """获取B股交易所"""
        return [
            cls.XSHEB,
            cls.XSHGB
        ]
    
    @classmethod
    def is_real_time_exchange(cls, exchange_code: str) -> bool:
        """判断是否为实时数据交易所"""
        exchanges = cls.get_exchanges_by_code()
        if exchange_code in exchanges:
            return exchanges[exchange_code].delay == "实时"
        return False
    
    @classmethod
    def get_exchange_by_symbol_prefix(cls, symbol: str) -> Optional[ExchangeInfo]:
        """
        根据股票代码前缀获取对应的交易所信息
        
        Args:
            symbol: 股票代码，如 SH.600519 或 SZ.000001
            
        Returns:
            对应的交易所信息，如果找不到则返回 None
        """
        if not symbol or '.' not in symbol:
            return None
        
        prefix = symbol.split('.')[0].upper()
        
        # 映射项目内部代码到交易所代码
        prefix_mapping = {
            'SH': cls.XSHG,  # 上海证券交易所
            'SZ': cls.XSHE,  # 深圳证券交易所
            'BJ': cls.BJSE,  # 北京证券交易所
        }
        
        return prefix_mapping.get(prefix)


class MarketSegments(Enum):
    """市场板块枚举"""
    MAIN_BOARD = "主板"          # 主板市场
    SME_BOARD = "中小板"         # 中小企业板
    CHINEXT = "创业板"           # 创业板
    STAR_MARKET = "科创板"       # 科创板
    BEIJING_STOCK = "北交所"     # 北京证券交易所
    B_STOCK = "B股"             # B股市场


class TradingHours:
    """交易时间常量"""
    
    # 中国A股交易时间
    A_STOCK_MORNING_OPEN = "09:30:00"
    A_STOCK_MORNING_CLOSE = "11:30:00"
    A_STOCK_AFTERNOON_OPEN = "13:00:00"
    A_STOCK_AFTERNOON_CLOSE = "15:00:00"
    
    # 集合竞价时间
    CALL_AUCTION_OPEN = "09:15:00"
    CALL_AUCTION_CLOSE = "09:25:00"
    
    # 收盘集合竞价时间（深交所）
    CLOSING_CALL_AUCTION_OPEN = "14:57:00"
    CLOSING_CALL_AUCTION_CLOSE = "15:00:00"
    
    @classmethod
    def is_trading_time(cls, time_str: str) -> bool:
        """判断是否为交易时间"""
        from datetime import datetime, time
        
        try:
            current_time = datetime.strptime(time_str, "%H:%M:%S").time()
            morning_open = datetime.strptime(cls.A_STOCK_MORNING_OPEN, "%H:%M:%S").time()
            morning_close = datetime.strptime(cls.A_STOCK_MORNING_CLOSE, "%H:%M:%S").time()
            afternoon_open = datetime.strptime(cls.A_STOCK_AFTERNOON_OPEN, "%H:%M:%S").time()
            afternoon_close = datetime.strptime(cls.A_STOCK_AFTERNOON_CLOSE, "%H:%M:%S").time()
            
            return (morning_open <= current_time <= morning_close) or \
                   (afternoon_open <= current_time <= afternoon_close)
        except ValueError:
            return False


# 便捷访问常量
CHINESE_EXCHANGES = ChineseExchanges.get_all_exchanges()
MAIN_EXCHANGES = ChineseExchanges.get_main_exchanges()
B_STOCK_EXCHANGES = ChineseExchanges.get_b_stock_exchanges()

# 交易所代码映射（用于快速查找）
EXCHANGE_CODE_MAPPING = ChineseExchanges.get_exchanges_by_code()

# 项目内部代码到交易所信息的映射
SYMBOL_PREFIX_TO_EXCHANGE = {
    'SH': ChineseExchanges.XSHG,
    'SZ': ChineseExchanges.XSHE,
    'BJ': ChineseExchanges.BJSE,
}


def get_exchange_info(exchange_code: str) -> Optional[ExchangeInfo]:
    """
    根据交易所代码获取交易所信息
    
    Args:
        exchange_code: 交易所代码
        
    Returns:
        交易所信息或None
    """
    return EXCHANGE_CODE_MAPPING.get(exchange_code.upper())


def get_exchange_by_symbol(symbol: str) -> Optional[ExchangeInfo]:
    """
    根据股票代码获取对应的交易所信息
    
    Args:
        symbol: 股票代码，如 SH.600519
        
    Returns:
        交易所信息或None
        
    Example:
        >>> exchange = get_exchange_by_symbol("SH.600519")
        >>> print(exchange.exchange_name)  # 上海证券交易所
    """
    return ChineseExchanges.get_exchange_by_symbol_prefix(symbol)


if __name__ == "__main__":
    # 使用示例
    print("中国证券交易所信息:")
    print("=" * 50)
    
    for exchange in CHINESE_EXCHANGES:
        print(f"代码: {exchange.exchange_code}")
        print(f"名称: {exchange.exchange_name}")
        print(f"简称: {exchange.exchange_name_short}")
        print(f"币种: {exchange.currency_code}")
        print(f"交易时间: {exchange.local_open} - {exchange.local_close}")
        print(f"数据延迟: {exchange.delay}")
        print("-" * 30)
    
    # 测试根据股票代码获取交易所
    test_symbols = ["SH.600519", "SZ.000001", "BJ.430047"]
    print("\n股票代码对应交易所:")
    for symbol in test_symbols:
        exchange = get_exchange_by_symbol(symbol)
        if exchange:
            print(f"{symbol} -> {exchange.exchange_name_short}")
        else:
            print(f"{symbol} -> 未找到对应交易所")