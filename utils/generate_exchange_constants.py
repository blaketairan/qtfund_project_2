#!/usr/bin/env python3
"""
交易所常量生成工具

从 exchange_code.json 文件自动生成中国交易所常量定义
"""

import json
import sys
import os
from typing import Dict, List, Any

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def load_exchange_data(json_file_path: str) -> List[Dict[str, Any]]:
    """从JSON文件加载交易所数据"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('data', [])
    except Exception as e:
        print(f"读取文件失败: {e}")
        return []


def filter_chinese_exchanges(exchanges: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """筛选出中国的交易所"""
    return [exchange for exchange in exchanges if exchange.get('country_code') == 'CHN']


def generate_exchange_info_code(exchange: Dict[str, Any]) -> str:
    """生成单个交易所的ExchangeInfo代码"""
    code = exchange.get('exchange_code', '')
    name = exchange.get('exchange_name', '')
    short_name = exchange.get('exchange_name_short', '')
    country = exchange.get('country_code', '')
    currency = exchange.get('currency_code', '')
    local_open = exchange.get('local_open', '')
    local_close = exchange.get('local_close', '')
    beijing_open = exchange.get('beijing_open', '')
    beijing_close = exchange.get('beijing_close', '')
    timezone = exchange.get('timezone', '')
    delay = exchange.get('delay')
    notes = exchange.get('notes')
    
    delay_str = f'"{delay}"' if delay else "None"
    notes_str = f'"{notes}"' if notes else "None"
    
    return f'''    # {name}
    {code} = ExchangeInfo(
        exchange_code="{code}",
        exchange_name="{name}",
        exchange_name_short="{short_name}",
        country_code="{country}",
        currency_code="{currency}",
        local_open="{local_open}",
        local_close="{local_close}",
        beijing_open="{beijing_open}",
        beijing_close="{beijing_close}",
        timezone="{timezone}",
        delay={delay_str},
        notes={notes_str}
    )'''


def generate_constants_file(chinese_exchanges: List[Dict[str, Any]]) -> str:
    """生成完整的常量文件代码"""
    
    # 生成各个交易所的定义
    exchange_definitions = []
    exchange_codes = []
    
    for exchange in chinese_exchanges:
        code = exchange.get('exchange_code', '')
        exchange_definitions.append(generate_exchange_info_code(exchange))
        exchange_codes.append(code)
    
    # 生成get_all_exchanges方法的返回列表
    all_exchanges_list = ',\n            '.join([f'cls.{code}' for code in exchange_codes])
    
    # 生成get_exchanges_by_code方法的字典
    exchanges_dict = ',\n            '.join([f'"{code}": cls.{code}' for code in exchange_codes])
    
    file_content = f'''"""
中国交易所常量定义

从 exchange_code.json 中自动生成的中国证券交易所信息
此文件由 generate_exchange_constants.py 自动生成，请勿手动修改
"""

from dataclasses import dataclass
from typing import Dict, List, Optional


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
    
{chr(10).join(exchange_definitions)}
    
    @classmethod
    def get_all_exchanges(cls) -> List[ExchangeInfo]:
        """获取所有中国交易所信息列表"""
        return [
            {all_exchanges_list}
        ]
    
    @classmethod
    def get_exchanges_by_code(cls) -> Dict[str, ExchangeInfo]:
        """按交易所代码获取交易所信息字典"""
        return {{
            {exchanges_dict}
        }}
    
    @classmethod
    def get_main_exchanges(cls) -> List[ExchangeInfo]:
        """获取主要交易所（排除B股）"""
        main_codes = ['BJSE', 'XSHE', 'XSHG']
        return [getattr(cls, code) for code in main_codes if hasattr(cls, code)]
    
    @classmethod
    def get_b_stock_exchanges(cls) -> List[ExchangeInfo]:
        """获取B股交易所"""
        b_codes = ['XSHEB', 'XSHGB']
        return [getattr(cls, code) for code in b_codes if hasattr(cls, code)]
    
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
        prefix_mapping = {{
            'SH': cls.XSHG if hasattr(cls, 'XSHG') else None,  # 上海证券交易所
            'SZ': cls.XSHE if hasattr(cls, 'XSHE') else None,  # 深圳证券交易所
            'BJ': cls.BJSE if hasattr(cls, 'BJSE') else None,  # 北京证券交易所
        }}
        
        return prefix_mapping.get(prefix)


# 便捷访问常量
CHINESE_EXCHANGES = ChineseExchanges.get_all_exchanges()
MAIN_EXCHANGES = ChineseExchanges.get_main_exchanges()
B_STOCK_EXCHANGES = ChineseExchanges.get_b_stock_exchanges()
EXCHANGE_CODE_MAPPING = ChineseExchanges.get_exchanges_by_code()


def get_exchange_info(exchange_code: str) -> Optional[ExchangeInfo]:
    """根据交易所代码获取交易所信息"""
    return EXCHANGE_CODE_MAPPING.get(exchange_code.upper())


def get_exchange_by_symbol(symbol: str) -> Optional[ExchangeInfo]:
    """根据股票代码获取对应的交易所信息"""
    return ChineseExchanges.get_exchange_by_symbol_prefix(symbol)


if __name__ == "__main__":
    # 使用示例
    print("中国证券交易所信息:")
    print("=" * 50)
    
    for exchange in CHINESE_EXCHANGES:
        print(f"代码: {{exchange.exchange_code}}")
        print(f"名称: {{exchange.exchange_name}}")
        print(f"简称: {{exchange.exchange_name_short}}")
        print(f"币种: {{exchange.currency_code}}")
        print(f"交易时间: {{exchange.local_open}} - {{exchange.local_close}}")
        print(f"数据延迟: {{exchange.delay}}")
        print("-" * 30)
'''
    
    return file_content


def main():
    """主函数"""
    # 获取JSON文件路径
    json_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'exchange_code.json')
    
    if not os.path.exists(json_file):
        print(f"错误: 找不到文件 {json_file}")
        return False
    
    # 加载数据
    print("正在加载交易所数据...")
    exchanges = load_exchange_data(json_file)
    print(f"加载了 {len(exchanges)} 个交易所")
    
    # 筛选中国交易所
    chinese_exchanges = filter_chinese_exchanges(exchanges)
    print(f"筛选出 {len(chinese_exchanges)} 个中国交易所:")
    
    for exchange in chinese_exchanges:
        print(f"  - {exchange['exchange_code']}: {exchange['exchange_name']}")
    
    # 生成常量文件
    print("\n正在生成常量文件...")
    constants_code = generate_constants_file(chinese_exchanges)
    
    # 写入文件
    output_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                              'constants', 'exchanges_generated.py')
    
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(constants_code)
    
    print(f"✅ 常量文件已生成: {output_file}")
    
    # 验证生成的文件
    try:
        exec(constants_code)
        print("✅ 生成的代码语法验证通过")
    except Exception as e:
        print(f"❌ 生成的代码存在语法错误: {e}")
        return False
    
    return True


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)