"""
交易所信息服务模块

提供交易所信息的统一访问接口
"""

from typing import Dict, List, Any, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)


class ExchangeInfoService:
    """交易所信息服务类"""
    
    def __init__(self):
        self.exchange_code_file = "exchange_code.json"
    
    def query_from_local_constants(self, country_code: str = 'CHN') -> Dict[str, Any]:
        """
        从本地常量查询交易所信息
        
        Args:
            country_code: 国家代码
            
        Returns:
            Dict: 查询结果
        """
        try:
            from constants.exchanges import ChineseExchanges
            
            exchanges_list = ChineseExchanges.get_all_exchanges()
            
            data = []
            for exchange in exchanges_list:
                if exchange.country_code == country_code:
                    data.append({
                        'exchange_code': exchange.exchange_code,
                        'exchange_name': exchange.exchange_name,
                        'exchange_name_short': exchange.exchange_name_short,
                        'country_code': exchange.country_code,
                        'currency_code': exchange.currency_code,
                        'local_open': exchange.local_open,
                        'local_close': exchange.local_close,
                        'beijing_open': exchange.beijing_open,
                        'beijing_close': exchange.beijing_close,
                        'timezone': exchange.timezone,
                        'delay': exchange.delay,
                        'notes': exchange.notes
                    })
            
            return {
                'success': True,
                'data': data,
                'total': len(data)
            }
            
        except Exception as e:
            logger.error(f"本地常量查询错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'error': str(e)
            }
    
    def query_from_remote_api(self, 
                            country_code: str = 'CHN',
                            limit: int = 100) -> Dict[str, Any]:
        """
        从远程API查询交易所信息（这里模拟从exchange_code.json读取）
        
        Args:
            country_code: 国家代码
            limit: 返回数量限制
            
        Returns:
            Dict: 查询结果
        """
        try:
            # 读取exchange_code.json文件
            if not os.path.exists(self.exchange_code_file):
                raise FileNotFoundError(f"交易所数据文件不存在: {self.exchange_code_file}")
            
            with open(self.exchange_code_file, 'r', encoding='utf-8') as f:
                all_exchanges = json.load(f)
            
            # 按国家代码过滤
            filtered_exchanges = []
            for exchange in all_exchanges:
                if exchange.get('country_code') == country_code:
                    filtered_exchanges.append(exchange)
            
            # 应用限制
            if limit and len(filtered_exchanges) > limit:
                filtered_exchanges = filtered_exchanges[:limit]
            
            return {
                'success': True,
                'data': filtered_exchanges,
                'total': len(filtered_exchanges)
            }
            
        except Exception as e:
            logger.error(f"远程API查询错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'error': str(e)
            }