"""
股票信息服务模块

提供股票信息的统一访问接口，支持本地JSON文件和远程API
"""

from typing import Dict, List, Any, Optional
import json
import os
import logging

logger = logging.getLogger(__name__)


class StockInfoService:
    """股票信息服务类"""

    def __init__(self):
        # 从环境变量获取API token，确保安全性
        self.token = os.getenv('STOCK_API_TOKEN')
        if not self.token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables. Please check your .env file.")
        self.stock_lists_dir = "constants/stock_lists"
    
    def query_from_local_files(self,
                             exchange_code: str = '',
                             symbol: str = '',
                             keyword: str = '',
                             is_active: str = '1',
                             limit: int = 100,
                             offset: int = 0) -> Dict[str, Any]:
        """
        从本地JSON文件查询股票信息
        
        Args:
            exchange_code: 交易所代码
            symbol: 股票代码
            keyword: 搜索关键字
            is_active: 是否活跃
            limit: 返回数量限制
            offset: 偏移量
            
        Returns:
            Dict: 查询结果
        """
        try:
            all_stocks = []
            
            # 确定要查询的文件
            if exchange_code:
                # 查询指定交易所
                file_mapping = {
                    'XSHG': 'xshg_stocks.json',
                    'XSHE': 'xshe_stocks.json', 
                    'BJSE': 'bjse_stocks.json'
                }
                
                if exchange_code in file_mapping:
                    file_path = os.path.join(self.stock_lists_dir, file_mapping[exchange_code])
                    stocks = self._load_json_file(file_path)
                    if stocks:
                        all_stocks.extend(stocks)
            else:
                # 查询所有交易所
                for filename in ['xshg_stocks.json', 'xshe_stocks.json', 'bjse_stocks.json']:
                    file_path = os.path.join(self.stock_lists_dir, filename)
                    stocks = self._load_json_file(file_path)
                    if stocks:
                        all_stocks.extend(stocks)
            
            # 过滤条件
            filtered_stocks = []
            for stock in all_stocks:
                # 按symbol过滤
                if symbol and symbol not in stock.get('ticker', ''):
                    continue
                
                # 按活跃状态过滤
                if is_active and str(stock.get('is_active', 1)) != str(is_active):
                    continue
                
                # 按关键字过滤（名称或代码）
                if keyword:
                    stock_name = stock.get('name', '').lower()
                    stock_ticker = stock.get('ticker', '').lower()
                    if keyword.lower() not in stock_name and keyword.lower() not in stock_ticker:
                        continue
                
                filtered_stocks.append(stock)
            
            # 排序（按ticker）
            filtered_stocks.sort(key=lambda x: x.get('ticker', ''))
            
            # 分页
            total_count = len(filtered_stocks)
            start_idx = offset
            if limit == 0:
                # limit为0表示不限制，返回从offset开始的所有数据
                result_stocks = filtered_stocks[start_idx:]
            else:
                end_idx = offset + limit
                result_stocks = filtered_stocks[start_idx:end_idx]
            
            return {
                'success': True,
                'data': result_stocks,
                'total': total_count,
                'count': len(result_stocks),
                'offset': offset,
                'limit': limit
            }
            
        except Exception as e:
            logger.error(f"本地JSON文件查询错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'count': 0,
                'error': str(e)
            }
    
    def query_from_remote_api(self,
                            exchange_code: str,
                            limit: int = 100) -> Dict[str, Any]:
        """
        从远程API查询股票信息
        
        Args:
            exchange_code: 交易所代码
            limit: 返回数量限制
            
        Returns:
            Dict: 查询结果
        """
        try:
            from data_fetcher.exchange_stocks import ExchangeStockListFetcher
            from constants.exchanges import ChineseExchanges
            
            # 获取交易所中文名
            exchange_mapping = {
                'XSHG': '上海证券交易所',
                'XSHE': '深圳证券交易所',
                'BJSE': '北京证券交易所'
            }
            
            exchange_name_cn = exchange_mapping.get(exchange_code, exchange_code)
            
            fetcher = ExchangeStockListFetcher(self.token)
            stock_list = fetcher.fetch_exchange_stock_list(exchange_code, exchange_name_cn)
            
            # 转换为标准格式
            api_stocks = []
            for stock in stock_list:
                api_stocks.append({
                    'ticker': stock.ticker,
                    'name': stock.name,
                    'is_active': stock.is_active,
                    'exchange_code': stock.exchange_code,
                    'country_code': stock.country_code,
                    'currency_code': stock.currency_code,
                    'exchange_name_cn': stock.exchange_name_cn,
                    'first_fetch_time': stock.first_fetch_time
                })
            
            # 应用limit限制
            if limit and len(api_stocks) > limit:
                api_stocks = api_stocks[:limit]
            
            return {
                'success': True,
                'data': api_stocks,
                'total': len(stock_list),
                'count': len(api_stocks)
            }
            
        except Exception as e:
            logger.error(f"远程API查询错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'count': 0,
                'error': str(e)
            }
    
    def search_stocks_local(self,
                          query_text: str,
                          exchange_code: str = '',
                          market_code: str = '',
                          limit: int = 50) -> Dict[str, Any]:
        """
        在本地数据中搜索股票
        
        Args:
            query_text: 搜索关键字
            exchange_code: 交易所代码
            market_code: 市场代码 (SH/SZ/BJ)
            limit: 返回数量限制
            
        Returns:
            Dict: 搜索结果
        """
        try:
            # 如果有市场代码，转换为交易所代码
            if market_code and not exchange_code:
                market_mapping = {
                    'SH': 'XSHG',
                    'SZ': 'XSHE', 
                    'BJ': 'BJSE'
                }
                exchange_code = market_mapping.get(market_code.upper(), '')
            
            # 基础查询
            result = self.query_from_local_files(
                exchange_code=exchange_code,
                keyword=query_text,
                limit=limit * 2  # 放宽限制，然后再筛选
            )
            
            if not result['success']:
                return result
            
            # 进一步搜索过滤（支持代码和名称搜索）
            search_results = []
            query_lower = query_text.lower()
            
            for stock in result['data']:
                ticker = stock.get('ticker', '').lower()
                name = stock.get('name', '').lower()
                
                # 计算匹配度
                score = 0
                if query_lower in ticker:
                    score += 10  # 代码匹配得分高
                if query_lower in name:
                    score += 5   # 名称匹配得分
                
                if score > 0:
                    stock['match_score'] = score
                    search_results.append(stock)
            
            # 按匹配度排序
            search_results.sort(key=lambda x: x.get('match_score', 0), reverse=True)
            
            # 限制结果数量
            if len(search_results) > limit:
                search_results = search_results[:limit]
            
            return {
                'success': True,
                'data': search_results,
                'total': len(search_results),
                'count': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"本地搜索错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'count': 0,
                'error': str(e)
            }
    
    def search_stocks_remote(self,
                           query_text: str,
                           exchange_code: str = '',
                           limit: int = 50) -> Dict[str, Any]:
        """
        通过远程API搜索股票（简单实现）
        
        Args:
            query_text: 搜索关键字
            exchange_code: 交易所代码
            limit: 返回数量限制
            
        Returns:
            Dict: 搜索结果
        """
        try:
            # 远程API可能不支持搜索，这里获取全部然后本地过滤
            if not exchange_code:
                exchange_code = 'XSHG'  # 默认上交所
            
            result = self.query_from_remote_api(exchange_code, limit=1000)
            
            if not result['success']:
                return result
            
            # 本地过滤
            search_results = []
            query_lower = query_text.lower()
            
            for stock in result['data']:
                ticker = stock.get('ticker', '').lower()
                name = stock.get('name', '').lower()
                
                if query_lower in ticker or query_lower in name:
                    search_results.append(stock)
            
            # 限制结果数量
            if len(search_results) > limit:
                search_results = search_results[:limit]
            
            return {
                'success': True,
                'data': search_results,
                'total': len(search_results),
                'count': len(search_results)
            }
            
        except Exception as e:
            logger.error(f"远程搜索错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'count': 0,
                'error': str(e)
            }
    
    def get_stock_statistics(self) -> Dict[str, Any]:
        """
        获取股票信息统计数据
        
        Returns:
            Dict: 统计信息
        """
        try:
            stats = {
                'exchanges': {},
                'total_stocks': 0,
                'active_stocks': 0,
                'inactive_stocks': 0,
                'last_updated': None
            }
            
            # 统计各交易所数据
            exchange_files = {
                'XSHG': 'xshg_stocks.json',
                'XSHE': 'xshe_stocks.json',
                'BJSE': 'bjse_stocks.json'
            }
            
            for exchange_code, filename in exchange_files.items():
                file_path = os.path.join(self.stock_lists_dir, filename)
                stocks = self._load_json_file(file_path)
                
                if stocks:
                    total = len(stocks)
                    active = sum(1 for stock in stocks if stock.get('is_active', 1) == 1)
                    inactive = total - active
                    
                    stats['exchanges'][exchange_code] = {
                        'name': self._get_exchange_name(exchange_code),
                        'total': total,
                        'active': active,
                        'inactive': inactive
                    }
                    
                    stats['total_stocks'] += total
                    stats['active_stocks'] += active
                    stats['inactive_stocks'] += inactive
            
            # 获取最后更新时间
            try:
                file_path = os.path.join(self.stock_lists_dir, 'xshg_stocks.json')
                if os.path.exists(file_path):
                    from datetime import datetime
                    mtime = os.path.getmtime(file_path)
                    stats['last_updated'] = datetime.fromtimestamp(mtime).strftime('%Y-%m-%d %H:%M:%S')
            except Exception:
                pass
            
            return stats
            
        except Exception as e:
            logger.error(f"统计信息获取错误: {e}")
            return {
                'error': str(e),
                'exchanges': {},
                'total_stocks': 0
            }
    
    def _load_json_file(self, file_path: str) -> List[Dict[str, Any]]:
        """加载JSON文件"""
        try:
            if not os.path.exists(file_path):
                logger.warning(f"文件不存在: {file_path}")
                return []
            
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data if isinstance(data, list) else []
                
        except Exception as e:
            logger.error(f"加载JSON文件失败 {file_path}: {e}")
            return []
    
    def _get_exchange_name(self, exchange_code: str) -> str:
        """获取交易所中文名"""
        exchange_names = {
            'XSHG': '上海证券交易所',
            'XSHE': '深圳证券交易所',
            'BJSE': '北京证券交易所'
        }
        return exchange_names.get(exchange_code, exchange_code)
    
    def get_etf_list(self, 
                     exchange_code: str = '',
                     limit: int = 100,
                     offset: int = 0,
                     is_active: str = 'Y') -> Dict[str, Any]:
        """
        获取ETF列表
        
        Args:
            exchange_code: 交易所代码
            limit: 返回数量限制
            offset: 偏移量
            is_active: 是否活跃
            
        Returns:
            Dict: ETF查询结果
        """
        try:
            from database.connection import db_manager
            from models.stock_data import StockInfo
            from sqlalchemy import and_
            
            with db_manager.get_session() as session:
                # 构建查询
                query = session.query(StockInfo).filter(
                    and_(
                        StockInfo.is_etf == 'Y',
                        StockInfo.is_active == is_active
                    )
                )
                
                # 按交易所过滤
                if exchange_code:
                    # 转换为市场代码
                    market_mapping = {
                        'XSHG': 'SH',
                        'XSHE': 'SZ',
                        'BJSE': 'BJ'
                    }
                    market_code = market_mapping.get(exchange_code)
                    if market_code:
                        query = query.filter(StockInfo.market_code == market_code)
                
                # 获取总数
                total_count = query.count()
                
                # 分页
                etfs = query.limit(limit).offset(offset).all()
                
                # 转换为字典格式
                etf_list = []
                for etf in etfs:
                    etf_list.append({
                        'symbol': etf.symbol,
                        'stock_name': etf.stock_name,
                        'stock_code': etf.stock_code,
                        'market_code': etf.market_code,
                        'is_etf': etf.is_etf,
                        'stock_type': etf.stock_type,
                        'industry': etf.industry,
                        'is_active': etf.is_active,
                        'created_at': etf.created_at.isoformat() if etf.created_at else None
                    })
                
                return {
                    'success': True,
                    'data': etf_list,
                    'total': total_count,
                    'count': len(etf_list),
                    'offset': offset,
                    'limit': limit
                }
                
        except Exception as e:
            logger.error(f"获取ETF列表失败: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'count': 0,
                'error': str(e)
            }
    
    def get_etf_count_by_market(self) -> Dict[str, Any]:
        """
        获取各交易所ETF数量
        
        Returns:
            Dict: 各交易所ETF数量统计
        """
        try:
            from database.connection import db_manager
            from models.stock_data import StockInfo
            from sqlalchemy import and_, func
            
            with db_manager.get_session() as session:
                # 按市场分组统计
                results = session.query(
                    StockInfo.market_code,
                    func.count(StockInfo.symbol).label('count')
                ).filter(
                    and_(
                        StockInfo.is_etf == 'Y',
                        StockInfo.is_active == 'Y'
                    )
                ).group_by(StockInfo.market_code).all()
                
                counts = {}
                for market_code, count in results:
                    counts[market_code] = count
                
                total = sum(counts.values())
                
                return {
                    'success': True,
                    'data': counts,
                    'total': total,
                    'markets': len(counts)
                }
                
        except Exception as e:
            logger.error(f"获取ETF统计失败: {e}")
            return {
                'success': False,
                'data': {},
                'total': 0,
                'error': str(e)
            }