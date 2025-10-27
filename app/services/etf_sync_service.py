"""
ETF同步服务模块

提供ETF数据同步的核心业务逻辑
"""

from typing import Dict, List, Any, Optional
import os
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ETFSyncService:
    """ETF同步服务类"""
    
    def __init__(self):
        # 从环境变量获取API token
        self.token = os.getenv('STOCK_API_TOKEN')
        if not self.token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables.")
    
    def sync_etf_lists(self, exchange_codes: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        同步ETF列表
        
        Args:
            exchange_codes: 要同步的交易所代码列表，默认为 ['XSHG', 'XSHE']
            
        Returns:
            Dict: 同步结果
        """
        try:
            if exchange_codes is None:
                exchange_codes = ['XSHG', 'XSHE']
            
            from data_fetcher.etf_api import ETFDataFetcher
            from database.connection import db_manager
            from models.stock_data import StockInfo
            
            fetcher = ETFDataFetcher(self.token)
            
            total_etfs = 0
            new_etfs = 0
            updated_etfs = 0
            failed_exchanges = []
            
            for exchange_code in exchange_codes:
                try:
                    logger.info(f"开始同步 {exchange_code} 的ETF列表...")
                    
                    # 获取ETF列表
                    etf_list = fetcher.fetch_etf_list(exchange_code)
                    
                    # 存储到数据库
                    with db_manager.get_session() as session:
                        for etf in etf_list:
                            # 确定市场代码
                            if exchange_code == 'XSHG':
                                market_code = 'SH'
                            elif exchange_code == 'XSHE':
                                market_code = 'SZ'
                            elif exchange_code == 'BJSE':
                                market_code = 'BJ'
                            else:
                                market_code = 'UNKNOWN'
                            
                            symbol = f"{market_code}.{etf.ticker}"
                            
                            # 检查是否已存在
                            existing = session.query(StockInfo).filter(
                                StockInfo.symbol == symbol
                            ).first()
                            
                            if existing:
                                # 更新现有记录
                                existing.stock_name = etf.name
                                existing.is_etf = 'Y'
                                existing.is_active = 'Y' if etf.is_active else 'N'
                                existing.updated_at = datetime.now()
                                updated_etfs += 1
                            else:
                                # 创建新记录
                                new_stock = StockInfo(
                                    symbol=symbol,
                                    stock_name=etf.name,
                                    stock_code=etf.ticker,
                                    market_code=market_code,
                                    is_etf='Y',
                                    stock_type='ETF',
                                    is_active='Y' if etf.is_active else 'N'
                                )
                                session.add(new_stock)
                                new_etfs += 1
                            
                            total_etfs += 1
                        
                        session.commit()
                    
                    logger.info(f"✅ {exchange_code} ETF列表同步完成: 新增 {new_etfs}, 更新 {updated_etfs}")
                    
                except Exception as e:
                    logger.error(f"❌ 同步 {exchange_code} 失败: {e}")
                    failed_exchanges.append({
                        'exchange_code': exchange_code,
                        'error': str(e)
                    })
            
            success = len(failed_exchanges) == 0
            
            return {
                'success': success,
                'action': 'completed',
                'message': f'ETF列表同步完成，成功: {len(exchange_codes) - len(failed_exchanges)}, 失败: {len(failed_exchanges)}',
                'total_etfs': total_etfs,
                'new_etfs': new_etfs,
                'updated_etfs': updated_etfs,
                'failed_exchanges': failed_exchanges
            }
            
        except Exception as e:
            logger.error(f"ETF列表同步失败: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': 'ETF列表同步失败'
            }
    
    def sync_etf_prices(self, symbol: Optional[str] = None,
                       exchange_code: Optional[str] = None,
                       start_year: int = 2020,
                       force_update: bool = False) -> Dict[str, Any]:
        """
        同步ETF价格数据
        
        Args:
            symbol: ETF符号（如 SH.510050），如果提供则同步单个ETF
            exchange_code: 交易所代码（XSHG/XSHE），如果提供则同步该交易所所有ETF
            start_year: 开始年份
            force_update: 是否强制更新
            
        Returns:
            Dict: 同步结果
        """
        try:
            from data_fetcher.etf_api import ETFDataFetcher
            from database.connection import db_manager
            from models.stock_data import StockInfo, StockDailyData
            from sqlalchemy import and_
            from decimal import Decimal
            
            fetcher = ETFDataFetcher(self.token)
            
            # 确定要同步的ETF列表
            symbols_to_sync = []
            
            with db_manager.get_session() as session:
                if symbol:
                    # 同步单个ETF
                    etf_info = session.query(StockInfo).filter(
                        and_(StockInfo.symbol == symbol, StockInfo.is_etf == 'Y')
                    ).first()
                    
                    if not etf_info:
                        return {
                            'success': False,
                            'error': f'ETF not found: {symbol}'
                        }
                    
                    symbols_to_sync = [symbol]
                    
                elif exchange_code:
                    # 同步指定交易所的ETF
                    market_code = 'SH' if exchange_code == 'XSHG' else 'SZ'
                    etfs = session.query(StockInfo).filter(
                        and_(StockInfo.market_code == market_code, StockInfo.is_etf == 'Y')
                    ).all()
                    
                    symbols_to_sync = [etf.symbol for etf in etfs]
                    
                else:
                    # 同步所有ETF
                    etfs = session.query(StockInfo).filter(
                        StockInfo.is_etf == 'Y'
                    ).all()
                    
                    symbols_to_sync = [etf.symbol for etf in etfs]
            
            # 执行同步
            successful_count = 0
            failed_symbols = []
            total_records = 0
            
            for idx, symbol_item in enumerate(symbols_to_sync, 1):
                try:
                    logger.info(f"[{idx}/{len(symbols_to_sync)}] 同步ETF价格: {symbol_item}")
                    
                    # 检查是否需要更新
                    if not force_update:
                        with db_manager.get_session() as session:
                            latest = session.query(StockDailyData).filter(
                                StockDailyData.symbol == symbol_item
                            ).order_by(StockDailyData.trade_date.desc()).first()
                            
                            if latest:
                                logger.info(f"{symbol_item} 已有数据，跳过（使用 force_update=True 强制更新）")
                                continue
                    
                    # 获取数据
                    start_date = f"{start_year}-01-01"
                    price_records = fetcher.fetch_by_symbol(symbol_item, start_date=start_date)
                    
                    if not price_records:
                        logger.warning(f"{symbol_item} 无价格数据")
                        failed_symbols.append({'symbol': symbol_item, 'error': 'No data'})
                        continue
                    
                    # 存储到数据库
                    with db_manager.get_session() as session:
                        for record in price_records:
                            # 检查是否已存在（交易日期）
                            trade_date = datetime.strptime(record.date, '%Y-%m-%d').date()
                            
                            existing = session.query(StockDailyData).filter(
                                and_(
                                    StockDailyData.symbol == symbol_item,
                                    StockDailyData.trade_date == trade_date
                                )
                            ).first()
                            
                            if existing and not force_update:
                                continue
                            
                            # 确定市场代码
                            market_code = symbol_item.split('.')[0]
                            stock_name_query = session.query(StockInfo).filter(
                                StockInfo.symbol == symbol_item
                            ).first()
                            
                            price_data = StockDailyData(
                                symbol=symbol_item,
                                trade_date=trade_date,
                                stock_name=stock_name_query.stock_name if stock_name_query else symbol_item,
                                close_price=Decimal(str(record.close)),
                                open_price=Decimal(str(record.open)),
                                high_price=Decimal(str(record.high)),
                                low_price=Decimal(str(record.low)),
                                volume=record.volume,
                                turnover=Decimal(str(record.volume * record.close)),
                                market_code=market_code
                            )
                            
                            if existing:
                                # 更新现有记录
                                existing.close_price = price_data.close_price
                                existing.open_price = price_data.open_price
                                existing.high_price = price_data.high_price
                                existing.low_price = price_data.low_price
                                existing.volume = price_data.volume
                                existing.turnover = price_data.turnover
                                existing.updated_at = datetime.now()
                            else:
                                # 插入新记录
                                session.add(price_data)
                                total_records += 1
                        
                        session.commit()
                    
                    successful_count += 1
                    logger.info(f"✅ {symbol_item} 价格同步完成: {len(price_records)} 条记录")
                    
                except Exception as e:
                    logger.error(f"❌ 同步 {symbol_item} 失败: {e}")
                    failed_symbols.append({
                        'symbol': symbol_item,
                        'error': str(e)
                    })
            
            success_rate = successful_count / len(symbols_to_sync) if symbols_to_sync else 0
            
            return {
                'success': success_rate > 0.5,
                'action': 'completed',
                'message': f'ETF价格同步完成，成功率: {success_rate:.1%}',
                'total_symbols': len(symbols_to_sync),
                'successful_count': successful_count,
                'failed_symbols': failed_symbols[:10],
                'total_records': total_records
            }
            
        except Exception as e:
            logger.error(f"ETF价格同步失败: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': 'ETF价格同步失败'
            }
