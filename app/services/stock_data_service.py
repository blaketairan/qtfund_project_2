"""
股票数据服务模块

提供股票数据的统一访问接口，支持从数据库和远程API获取数据
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import os
import logging

logger = logging.getLogger(__name__)


class StockDataService:
    """股票数据服务类"""

    def __init__(self):
        # 从环境变量获取API token，确保安全性
        self.token = os.getenv('STOCK_API_TOKEN')
        if not self.token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables. Please check your .env file.")
    
    def query_stock_data_from_db(self, 
                               symbol: str,
                               start_date: Optional[str] = None,
                               end_date: Optional[str] = None,
                               limit: int = 100) -> Dict[str, Any]:
        """
        从TimescaleDB查询股票数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            limit: 数据条数限制
            
        Returns:
            Dict: 查询结果
        """
        try:
            from database.connection import db_manager
            from models.stock_data import StockDailyData, StockInfo
            from sqlalchemy import desc
            
            with db_manager.get_session() as session:
                # 构建查询
                query = session.query(StockDailyData).filter(
                    StockDailyData.symbol == symbol
                )
                
                # 添加日期范围过滤
                if start_date:
                    start_dt = datetime.strptime(start_date, '%Y-%m-%d').date()
                    query = query.filter(StockDailyData.trade_date >= start_dt)
                
                if end_date:
                    end_dt = datetime.strptime(end_date, '%Y-%m-%d').date()
                    query = query.filter(StockDailyData.trade_date <= end_dt)
                
                # 按日期降序排列
                query = query.order_by(desc(StockDailyData.trade_date))
                
                # 获取总记录数
                total_count = query.count()
                
                # 限制返回数量
                results = query.limit(limit).all()
                
                return {
                    'success': True,
                    'data': results,
                    'total': total_count,
                    'count': len(results)
                }
                
        except Exception as e:
            logger.error(f"数据库查询错误: {e}")
            return {
                'success': False,
                'data': [],
                'total': 0,
                'count': 0,
                'error': str(e)
            }
    
    def query_stock_data_from_api(self,
                                symbol: str,
                                start_date: Optional[str] = None,
                                end_date: Optional[str] = None) -> Dict[str, Any]:
        """
        从远程API查询股票数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            Dict: 查询结果
        """
        try:
            from data_fetcher.stock_api import StockDataFetcher
            
            fetcher = StockDataFetcher(self.token)
            records = fetcher.fetch_by_symbol(symbol, start_date, end_date)
            
            # 转换为字典格式
            api_data = []
            for record in records:
                api_data.append({
                    'ticker': record.ticker,
                    'date': record.date,
                    'open': record.open,
                    'high': record.high,
                    'low': record.low,
                    'close': record.close,
                    'volume': record.volume
                })
            
            return {
                'success': True,
                'data': api_data,
                'count': len(api_data),
                'stock_name': symbol  # API可能不提供股票名称
            }
            
        except Exception as e:
            logger.error(f"远程API查询错误: {e}")
            return {
                'success': False,
                'data': [],
                'count': 0,
                'error': str(e)
            }
    
    def get_stock_info_from_db(self, symbol: str) -> Dict[str, Any]:
        """
        从数据库获取股票基础信息
        
        Args:
            symbol: 股票代码
            
        Returns:
            Dict: 股票信息
        """
        try:
            from database.connection import db_manager
            from models.stock_data import StockInfo
            
            with db_manager.get_session() as session:
                stock_info = session.query(StockInfo).filter(
                    StockInfo.symbol == symbol
                ).first()
                
                if stock_info:
                    return {
                        'success': True,
                        'data': {
                            'symbol': stock_info.symbol,
                            'stock_name': stock_info.stock_name,
                            'stock_code': stock_info.stock_code,
                            'market_code': stock_info.market_code,
                            'stock_type': stock_info.stock_type,
                            'industry': stock_info.industry,
                            'is_active': stock_info.is_active,
                            'created_at': stock_info.created_at.isoformat() if stock_info.created_at is not None else None
                        }
                    }
                else:
                    return {
                        'success': False,
                        'data': None,
                        'error': '未找到股票信息'
                    }
                    
        except Exception as e:
            logger.error(f"获取股票信息错误: {e}")
            return {
                'success': False,
                'data': None,
                'error': str(e)
            }
    
    def validate_symbol_exists(self, symbol: str) -> bool:
        """
        验证股票代码是否存在于数据库中
        
        Args:
            symbol: 股票代码
            
        Returns:
            bool: 是否存在
        """
        try:
            result = self.get_stock_info_from_db(symbol)
            return result['success']
        except Exception:
            return False