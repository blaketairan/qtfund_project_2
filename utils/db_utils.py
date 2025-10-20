"""
数据库工具模块

提供便捷的数据库操作工具函数
"""

from typing import List, Dict, Any, Optional
from datetime import datetime, date
from decimal import Decimal
from sqlalchemy import and_, or_, func
from database.connection import db_manager
from models.stock_data import StockDailyData, StockInfo


class StockDataManager:
    """股票数据管理器"""
    
    @staticmethod
    def add_stock_info(symbol: str, stock_name: str, market_code: str, **kwargs) -> bool:
        """
        添加股票基础信息
        
        Args:
            symbol: 股票代码（如 SH.000001）
            stock_name: 股票名称
            market_code: 市场代码（SH/SZ）
            **kwargs: 其他可选字段
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with db_manager.get_session() as session:
                stock_code = symbol.split('.')[1] if '.' in symbol else symbol
                
                stock_info = StockInfo(
                    symbol=symbol,
                    stock_name=stock_name,
                    stock_code=stock_code,
                    market_code=market_code,
                    **kwargs
                )
                session.add(stock_info)
                return True
                
        except Exception as e:
            print(f"添加股票信息失败: {e}")
            return False
    
    @staticmethod
    def add_daily_data(trade_date: datetime, symbol: str, stock_name: str,
                      close_price: Decimal, volume: int, turnover: Decimal,
                      market_code: str, **kwargs) -> bool:
        """
        添加日行情数据
        
        Args:
            trade_date: 交易日期
            symbol: 股票代码
            stock_name: 股票名称
            close_price: 收盘价
            volume: 成交量
            turnover: 成交额
            market_code: 市场代码
            **kwargs: 其他可选字段
            
        Returns:
            bool: 操作是否成功
        """
        try:
            with db_manager.get_session() as session:
                daily_data = StockDailyData(
                    trade_date=trade_date,
                    symbol=symbol,
                    stock_name=stock_name,
                    close_price=close_price,
                    volume=volume,
                    turnover=turnover,
                    market_code=market_code,
                    **kwargs
                )
                session.add(daily_data)
                return True
                
        except Exception as e:
            print(f"添加日行情数据失败: {e}")
            return False
    
    @staticmethod
    def batch_add_daily_data(data_list: List[Dict[str, Any]]) -> int:
        """
        批量添加日行情数据
        
        Args:
            data_list: 数据字典列表
            
        Returns:
            int: 成功添加的记录数
        """
        success_count = 0
        try:
            with db_manager.get_session() as session:
                for data in data_list:
                    try:
                        daily_data = StockDailyData(**data)
                        session.add(daily_data)
                        success_count += 1
                    except Exception as e:
                        print(f"跳过无效数据: {e}")
                        continue
                
                print(f"批量添加完成，成功 {success_count} 条")
                return success_count
                
        except Exception as e:
            print(f"批量添加失败: {e}")
            return success_count
    
    @staticmethod
    def get_stock_latest_data(symbol: str) -> Optional[StockDailyData]:
        """
        获取股票最新行情数据
        
        Args:
            symbol: 股票代码
            
        Returns:
            StockDailyData: 最新行情数据或 None
        """
        try:
            with db_manager.get_session() as session:
                return (session.query(StockDailyData)
                       .filter(StockDailyData.symbol == symbol)
                       .order_by(StockDailyData.trade_date.desc())
                       .first())
        except Exception as e:
            print(f"查询最新数据失败: {e}")
            return None
    
    @staticmethod
    def get_stock_data_by_date_range(symbol: str, start_date: date, end_date: date) -> List[StockDailyData]:
        """
        按日期范围查询股票数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            
        Returns:
            List[StockDailyData]: 数据列表
        """
        try:
            with db_manager.get_session() as session:
                return (session.query(StockDailyData)
                       .filter(and_(
                           StockDailyData.symbol == symbol,
                           StockDailyData.trade_date >= start_date,
                           StockDailyData.trade_date <= end_date
                       ))
                       .order_by(StockDailyData.trade_date.asc())
                       .all())
        except Exception as e:
            print(f"按日期范围查询失败: {e}")
            return []
    
    @staticmethod
    def get_market_data_by_date(market_code: str, trade_date: date) -> List[StockDailyData]:
        """
        获取指定市场指定日期的所有股票数据
        
        Args:
            market_code: 市场代码（SH/SZ）
            trade_date: 交易日期
            
        Returns:
            List[StockDailyData]: 数据列表
        """
        try:
            with db_manager.get_session() as session:
                return (session.query(StockDailyData)
                       .filter(and_(
                           StockDailyData.market_code == market_code,
                           StockDailyData.trade_date == trade_date
                       ))
                       .order_by(StockDailyData.symbol.asc())
                       .all())
        except Exception as e:
            print(f"按市场和日期查询失败: {e}")
            return []
    
    @staticmethod
    def get_top_gainers(trade_date: date, limit: int = 10) -> List[StockDailyData]:
        """
        获取指定日期涨幅前N的股票
        
        Args:
            trade_date: 交易日期
            limit: 返回数量限制
            
        Returns:
            List[StockDailyData]: 涨幅榜数据
        """
        try:
            with db_manager.get_session() as session:
                return (session.query(StockDailyData)
                       .filter(and_(
                           StockDailyData.trade_date == trade_date,
                           StockDailyData.price_change_pct.isnot(None)
                       ))
                       .order_by(StockDailyData.price_change_pct.desc())
                       .limit(limit)
                       .all())
        except Exception as e:
            print(f"查询涨幅榜失败: {e}")
            return []
    
    @staticmethod
    def get_database_stats() -> Dict[str, Any]:
        """
        获取数据库统计信息
        
        Returns:
            Dict: 统计信息
        """
        stats = {}
        try:
            with db_manager.get_session() as session:
                # 股票基础信息统计
                stock_count = session.query(StockInfo).count()
                stats['total_stocks'] = stock_count
                
                # 日行情数据统计
                daily_count = session.query(StockDailyData).count()
                stats['total_daily_records'] = daily_count
                
                # 按市场统计
                market_stats = (session.query(
                    StockInfo.market_code,
                    func.count(StockInfo.symbol).label('count')
                ).group_by(StockInfo.market_code).all())
                
                stats['market_breakdown'] = {market: count for market, count in market_stats}
                
                # 数据日期范围
                date_range = (session.query(
                    func.min(StockDailyData.trade_date).label('min_date'),
                    func.max(StockDailyData.trade_date).label('max_date')
                ).first())
                
                if date_range and date_range.min_date:
                    stats['date_range'] = {
                        'start': date_range.min_date.strftime('%Y-%m-%d'),
                        'end': date_range.max_date.strftime('%Y-%m-%d')
                    }
                
        except Exception as e:
            print(f"获取统计信息失败: {e}")
            
        return stats


def print_stock_data(stock_data: StockDailyData):
    """
    格式化输出股票数据
    
    Args:
        stock_data: 股票数据对象
    """
    if not stock_data:
        print("无数据")
        return
    
    print(f"股票代码: {stock_data.symbol}")
    print(f"股票名称: {stock_data.stock_name}")
    print(f"交易日期: {stock_data.trade_date.strftime('%Y-%m-%d')}")
    print(f"收盘价: {stock_data.close_price}")
    print(f"成交量: {stock_data.volume:,} 手")
    print(f"成交额: {stock_data.turnover:,.2f} 元")
    if stock_data.price_change_pct is not None:
        print(f"涨跌幅: {stock_data.price_change_pct}%")
    if stock_data.premium_rate is not None:
        print(f"溢价率: {stock_data.premium_rate}%")
    print("-" * 40)


def validate_symbol_format(symbol: str) -> bool:
    """
    验证股票代码格式
    
    Args:
        symbol: 股票代码
        
    Returns:
        bool: 格式是否正确
    """
    if not symbol or '.' not in symbol:
        return False
    
    parts = symbol.split('.')
    if len(parts) != 2:
        return False
    
    market, code = parts
    if market not in ['SH', 'SZ']:
        return False
    
    if not code.isdigit() or len(code) != 6:
        return False
    
    return True


def format_market_code(symbol: str) -> str:
    """
    从股票代码中提取市场代码
    
    Args:
        symbol: 股票代码（如 SH.000001）
        
    Returns:
        str: 市场代码（SH/SZ）
    """
    if '.' in symbol:
        return symbol.split('.')[0]
    return 'UNKNOWN'