"""
交易所股票清单获取模块

从第三方API获取各交易所的股票清单并存储为JSON文件
"""

import requests
import json
import os
from typing import List, Dict, Any, Optional
from datetime import datetime
from dataclasses import dataclass, asdict
import logging

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class StockListItem:
    """股票清单项"""
    ticker: str
    name: str
    is_active: int
    exchange_code: str
    country_code: str
    currency_code: str
    exchange_name_cn: str  # 交易所中文名
    first_fetch_time: str  # 首次获取时间


class ExchangeStockListFetcher:
    """交易所股票清单获取器"""
    
    def __init__(self, token: str):
        """
        初始化股票清单获取器

        Args:
            token: API访问令牌
        """
        self.token = token
        self.base_url = "https://www.tsanghi.com/api/fin/stock"
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Securities Data Storage System/1.0'
        })
    
    def fetch_exchange_stock_list(self, exchange_code: str, exchange_name_cn: str) -> List[StockListItem]:
        """
        获取指定交易所的股票清单
        
        Args:
            exchange_code: 交易所代码 (如: XSHG, XSHE)
            exchange_name_cn: 交易所中文名称
            
        Returns:
            List[StockListItem]: 股票清单
            
        Raises:
            requests.RequestException: 网络请求异常
            ValueError: 数据格式异常
        """
        url = f"{self.base_url}/{exchange_code}/list"
        params = {'token': self.token}
        
        try:
            logger.info(f"正在获取 {exchange_code} ({exchange_name_cn}) 的股票清单...")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # 检查API响应格式
            if data.get('code') != 200:
                raise ValueError(f"API error: {data.get('msg', 'Unknown error')}")
            
            stock_list = []
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            for item in data.get('data', []):
                stock_item = StockListItem(
                    ticker=item['ticker'],
                    name=item['name'],
                    is_active=item['is_active'],
                    exchange_code=item['exchange_code'],
                    country_code=item['country_code'],
                    currency_code=item['currency_code'],
                    exchange_name_cn=exchange_name_cn,
                    first_fetch_time=current_time
                )
                stock_list.append(stock_item)
            
            logger.info(f"成功获取 {exchange_code} 股票清单: {len(stock_list)} 只股票")
            return stock_list
            
        except requests.RequestException as e:
            logger.error(f"网络错误 - {exchange_code}: {e}")
            raise
        except (ValueError, KeyError) as e:
            logger.error(f"数据格式错误 - {exchange_code}: {e}")
            raise ValueError(f"Invalid data format: {e}")
    
    def load_existing_stock_list(self, file_path: str) -> Dict[str, StockListItem]:
        """
        加载已存在的股票清单
        
        Args:
            file_path: JSON文件路径
            
        Returns:
            Dict[str, StockListItem]: 以ticker为key的股票字典
        """
        if not os.path.exists(file_path):
            return {}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            existing_stocks = {}
            for item in data:
                stock_item = StockListItem(**item)
                existing_stocks[stock_item.ticker] = stock_item
            
            logger.info(f"加载已存在股票清单: {len(existing_stocks)} 只")
            return existing_stocks
            
        except Exception as e:
            logger.warning(f"加载已存在股票清单失败: {e}")
            return {}
    
    def merge_stock_lists(self, new_stocks: List[StockListItem], 
                         existing_stocks: Dict[str, StockListItem]) -> List[StockListItem]:
        """
        合并新旧股票清单，保持首次获取时间不变
        
        Args:
            new_stocks: 新获取的股票清单
            existing_stocks: 已存在的股票字典
            
        Returns:
            List[StockListItem]: 合并后的股票清单
        """
        merged_stocks = {}
        new_count = 0
        updated_count = 0
        
        # 先添加已存在的股票（保持原有的首次获取时间）
        for ticker, stock in existing_stocks.items():
            merged_stocks[ticker] = stock
        
        # 处理新获取的股票
        for new_stock in new_stocks:
            if new_stock.ticker in merged_stocks:
                # 已存在的股票：更新信息但保持首次获取时间
                existing_stock = merged_stocks[new_stock.ticker]
                merged_stocks[new_stock.ticker] = StockListItem(
                    ticker=new_stock.ticker,
                    name=new_stock.name,
                    is_active=new_stock.is_active,
                    exchange_code=new_stock.exchange_code,
                    country_code=new_stock.country_code,
                    currency_code=new_stock.currency_code,
                    exchange_name_cn=new_stock.exchange_name_cn,
                    first_fetch_time=existing_stock.first_fetch_time  # 保持原有时间
                )
                updated_count += 1
            else:
                # 新股票：使用当前时间作为首次获取时间
                merged_stocks[new_stock.ticker] = new_stock
                new_count += 1
        
        logger.info(f"合并结果: 新增 {new_count} 只, 更新 {updated_count} 只, 总计 {len(merged_stocks)} 只")
        return list(merged_stocks.values())
    
    def save_stock_list(self, stock_list: List[StockListItem], file_path: str):
        """
        保存股票清单到JSON文件
        
        Args:
            stock_list: 股票清单
            file_path: 保存路径
        """
        # 确保目录存在
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        
        # 转换为字典列表并排序
        data = [asdict(stock) for stock in stock_list]
        data.sort(key=lambda x: x['ticker'])  # 按股票代码排序
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"股票清单已保存: {file_path} ({len(data)} 只股票)")
            
        except Exception as e:
            logger.error(f"保存股票清单失败: {e}")
            raise
    
    def fetch_and_save_exchange_stocks(self, exchange_code: str, exchange_name_cn: str, 
                                     output_dir: str = "constants/stock_lists") -> Dict[str, Any]:
        """
        获取并保存指定交易所的股票清单
        
        Args:
            exchange_code: 交易所代码
            exchange_name_cn: 交易所中文名称
            output_dir: 输出目录
            
        Returns:
            Dict: 操作结果统计
        """
        result = {
            'exchange_code': exchange_code,
            'exchange_name_cn': exchange_name_cn,
            'success': False,
            'total_stocks': 0,
            'new_stocks': 0,
            'updated_stocks': 0,
            'file_path': '',
            'error': None
        }
        
        try:
            # 文件路径
            file_path = os.path.join(output_dir, f"{exchange_code.lower()}_stocks.json")
            result['file_path'] = file_path
            
            # 加载已存在的股票清单
            existing_stocks = self.load_existing_stock_list(file_path)
            
            # 获取最新的股票清单
            new_stocks = self.fetch_exchange_stock_list(exchange_code, exchange_name_cn)
            
            # 合并股票清单
            merged_stocks = self.merge_stock_lists(new_stocks, existing_stocks)
            
            # 保存到文件
            self.save_stock_list(merged_stocks, file_path)
            
            # 统计结果
            result['success'] = True
            result['total_stocks'] = len(merged_stocks)
            result['new_stocks'] = len(merged_stocks) - len(existing_stocks)
            result['updated_stocks'] = len(existing_stocks)
            
        except Exception as e:
            result['error'] = str(e)
            logger.error(f"处理 {exchange_code} 失败: {e}")
        
        return result


def fetch_all_chinese_exchange_stocks(token: Optional[str] = None,
                                    output_dir: str = "constants/stock_lists") -> List[Dict[str, Any]]:
    """
    获取所有中国交易所的股票清单

    Args:
        token: API令牌，如果为None则从环境变量获取
        output_dir: 输出目录

    Returns:
        List[Dict]: 每个交易所的处理结果
    """
    if token is None:
        token = os.getenv('STOCK_API_TOKEN')
        if not token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables. Please check your .env file.")

    # 导入交易所常量
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    from constants.exchanges import ChineseExchanges

    fetcher = ExchangeStockListFetcher(token)
    results = []
    
    # 获取所有主要中国交易所（排除B股）
    main_exchanges = ChineseExchanges.get_main_exchanges()
    
    print(f"开始获取 {len(main_exchanges)} 个中国交易所的股票清单...")
    print("=" * 60)
    
    for i, exchange in enumerate(main_exchanges, 1):
        print(f"\n[{i}/{len(main_exchanges)}] 处理交易所: {exchange.exchange_code} ({exchange.exchange_name_short})")
        
        result = fetcher.fetch_and_save_exchange_stocks(
            exchange.exchange_code,
            exchange.exchange_name,
            output_dir
        )
        
        results.append(result)
        
        # 显示结果
        if result['success']:
            print(f"  ✅ 成功: 总计 {result['total_stocks']} 只股票")
            print(f"     文件: {result['file_path']}")
            if result['new_stocks'] > 0:
                print(f"     新增: {result['new_stocks']} 只股票")
        else:
            print(f"  ❌ 失败: {result['error']}")
    
    # 总结
    print("\n" + "=" * 60)
    print("获取完成统计:")
    
    successful = [r for r in results if r['success']]
    failed = [r for r in results if not r['success']]
    
    print(f"  成功: {len(successful)}/{len(results)} 个交易所")
    print(f"  总股票数: {sum(r['total_stocks'] for r in successful)}")
    print(f"  新增股票: {sum(r['new_stocks'] for r in successful)}")
    
    if failed:
        print(f"\n失败的交易所:")
        for result in failed:
            print(f"  - {result['exchange_code']}: {result['error']}")
    
    return results


if __name__ == "__main__":
    # 使用示例
    try:
        results = fetch_all_chinese_exchange_stocks()
        
        print(f"\n🎉 股票清单获取完成!")
        print("生成的文件:")
        for result in results:
            if result['success']:
                print(f"  - {result['file_path']}")
        
    except Exception as e:
        print(f"❌ 执行失败: {e}")
        import traceback
        traceback.print_exc()