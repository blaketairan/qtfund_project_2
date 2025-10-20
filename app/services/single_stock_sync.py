"""
单股票同步服务

提供单只股票历史行情数据的同步功能
"""

import logging
import os
import requests
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from sqlalchemy import text
from data_fetcher.stock_api import StockDataFetcher
from database.connection import db_manager
from models.stock_data import StockInfo, StockDailyData, get_china_time

logger = logging.getLogger(__name__)


def get_stock_name_from_api(symbol: str) -> Optional[str]:
    """
    从本地JSON API获取股票中文名称

    Args:
        symbol: 股票代码（如: SH.600519, SZ.000001）

    Returns:
        str: 股票中文名称，如果未找到返回None
    """
    try:
        # 解析symbol获取market和ticker
        if '.' not in symbol:
            return None

        market_prefix, ticker = symbol.split('.')

        # 市场代码映射
        exchange_mapping = {
            'SH': 'XSHG',
            'SZ': 'XSHE',
            'BJ': 'BJSE'
        }

        exchange_code = exchange_mapping.get(market_prefix)
        if not exchange_code:
            return None

        # 调用本地API
        url = "http://localhost:8000/api/stock-info/local"
        params = {
            'exchange_code': exchange_code,
            'symbol': ticker,
            'limit': 1
        }

        response = requests.get(url, params=params, timeout=10)
        if response.status_code == 200:
            result = response.json()
            if result.get('code') == 200:
                data = result.get('data', [])
                for stock in data:
                    if stock.get('ticker') == ticker:
                        return stock.get('name', '').strip()

        return None

    except Exception as e:
        logger.warning(f"获取股票名称失败 {symbol}: {e}")
        return None


def sync_single_stock_history(symbol: str) -> Dict[str, Any]:
    """
    同步单只股票的历史行情数据（从2000年开始查至最新）

    每次成功写入数据库后，更新stock_info表中的last_sync_date

    Args:
        symbol: 股票代码（如: SH.600519, SZ.000001）

    Returns:
        Dict: 同步结果
    """
    try:
        logger.info(f"="*70)
        logger.info(f"开始同步股票 {symbol} 的历史行情数据")
        logger.info(f"="*70)

        # 从环境变量获取API token，确保安全性
        token = os.getenv('STOCK_API_TOKEN')
        if not token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables. Please check your .env file.")

        fetcher = StockDataFetcher(token)
        
        # 测试数据库连接
        try:
            with db_manager.get_session() as test_session:
                test_session.execute(text("SELECT 1"))
        except Exception as db_error:
            logger.error(f"❌ 数据库连接失败: {db_error}")
            logger.error(f"   请检查：")
            logger.error(f"   1. PostgreSQL/TimescaleDB 是否正在运行")
            logger.error(f"   2. .env 文件中的数据库配置是否正确")
            logger.error(f"   3. 网络连接是否正常")
            return {
                'success': False,
                'action': 'db_error',
                'symbol': symbol,
                'error': f'数据库连接失败: {db_error}',
                'message': '无法连接到数据库，请检查数据库服务状态'
            }
        
        # 获取股票信息
        with db_manager.get_session() as session:
            stock_info = session.query(StockInfo).filter(StockInfo.symbol == symbol).first()
            
            if not stock_info:
                logger.warning(f"股票 {symbol} 不存在于stock_info表，创建新记录")

                # 从API获取股票中文名称
                stock_name = get_stock_name_from_api(symbol)
                if not stock_name:
                    stock_name = symbol  # 如果无法获取，使用symbol作为fallback
                    logger.warning(f"无法获取股票 {symbol} 的中文名称，使用代码作为名称")
                else:
                    logger.info(f"获取到股票名称: {symbol} -> {stock_name}")

                # 创建新的股票信息记录
                market_code = symbol.split('.')[0] if '.' in symbol else 'UNKNOWN'
                stock_code = symbol.split('.')[1] if '.' in symbol else symbol

                stock_info = StockInfo(
                    symbol=symbol,
                    stock_code=stock_code,
                    stock_name=stock_name,  # 使用获取到的中文名称
                    market_code=market_code,
                    is_active='Y',
                    first_fetch_time=get_china_time(),
                    created_at=get_china_time(),
                    updated_at=get_china_time()
                )
                session.add(stock_info)
                session.commit()
            
            # 确定开始日期
            last_sync = stock_info.last_sync_date if stock_info else None  # type: ignore
            if last_sync is not None:
                # 从上次同步日期的下一天开始
                start_date = (last_sync + timedelta(days=1)).strftime('%Y-%m-%d')
                logger.info(f"检测到上次同步日期: {last_sync.strftime('%Y-%m-%d')}, 从 {start_date} 继续同步")
            else:
                # 从2000年开始
                start_date = '2000-01-01'
                logger.info(f"首次同步，从 {start_date} 开始")
            
            # 获取行情数据
            logger.info(f"📡 获取数据: {symbol} (从{start_date}至今)")
            records = fetcher.fetch_by_symbol(symbol, start_date=start_date)
            
            if not records:
                logger.info(f"✅ {symbol} 已是最新，无需同步")
                return {
                    'success': True,
                    'action': 'up_to_date',
                    'symbol': symbol,
                    'message': '数据已是最新'
                }
            
            logger.info(f"📥 接收数据: {symbol} - {len(records)}条记录")
            
            # 写入数据库
            inserted_count = 0
            latest_date = None
            
            from data_fetcher.stock_api import convert_to_database_format
            stock_name = str(stock_info.stock_name) if stock_info else symbol
            db_records = convert_to_database_format(
                [vars(r) for r in records],
                symbol,
                stock_name
            )
            
            for record in db_records:
                try:
                    # 检查是否已存在
                    exists = session.query(StockDailyData).filter(
                        StockDailyData.symbol == symbol,
                        StockDailyData.trade_date == record['trade_date']
                    ).first()
                    
                    if not exists:
                        daily_data = StockDailyData(**record)
                        session.add(daily_data)
                        inserted_count += 1
                        
                        # 记录最新日期
                        if latest_date is None or record['trade_date'] > latest_date:
                            latest_date = record['trade_date']
                    
                except Exception as e:
                    logger.error(f"写入记录失败 {symbol} {record.get('trade_date')}: {e}")
                    continue
            
            # 提交事务
            session.commit()
            
            # 更新stock_info的last_sync_date
            if latest_date and inserted_count > 0 and stock_info:
                stock_info.last_sync_date = latest_date  # type: ignore
                stock_info.updated_at = get_china_time()  # type: ignore
                session.commit()
                
                logger.info(f"💾 更新同步进度: {symbol} -> {latest_date.strftime('%Y-%m-%d')}")
            
            logger.info(f"✅ {symbol} 同步完成 - 新增{inserted_count}条记录")
            logger.info(f"="*70)
            
            return {
                'success': True,
                'action': 'completed',
                'symbol': symbol,
                'inserted_count': inserted_count,
                'total_records': len(records),
                'latest_sync_date': latest_date.strftime('%Y-%m-%d') if latest_date else None,
                'message': f'成功同步{inserted_count}条记录'
            }
            
    except Exception as e:
        logger.error(f"❌ 同步股票 {symbol} 失败: {e}")
        return {
            'success': False,
            'action': 'failed',
            'symbol': symbol,
            'error': str(e),
            'message': f'同步失败: {e}'
        }


def get_all_stocks() -> list:
    """
    从stock_info表获取所有股票信息
    
    Returns:
        List[Dict]: 股票信息列表
    """
    with db_manager.get_session() as session:
        stocks = session.query(StockInfo).filter(StockInfo.is_active == 'Y').all()
        return [
            {
                'symbol': str(s.symbol),
                'stock_name': str(s.stock_name),
                'market_code': str(s.market_code),
                'last_sync_date': s.last_sync_date.strftime('%Y-%m-%d') if s.last_sync_date else None  # type: ignore
            }
            for s in stocks
        ]
