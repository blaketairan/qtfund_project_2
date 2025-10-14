"""
数据集成工具模块

提供API数据到数据库的集成功能
"""

from typing import Dict, List, Any, Optional
from datetime import datetime, timezone, timedelta
from decimal import Decimal
import logging
import json
import os

logger = logging.getLogger(__name__)

# 中国时区 UTC+8
CHINA_TZ = timezone(timedelta(hours=8))


def get_china_time() -> datetime:
    """获取中国时区当前时间"""
    return datetime.now(CHINA_TZ)


def get_stock_name_from_json(symbol: str) -> str:
    """
    从本地JSON文件获取股票中文名称
    
    Args:
        symbol: 股票代码 (如: SH.600519, SZ.000001)
        
    Returns:
        str: 股票中文名称，如果找不到则返回代码本身
    """
    try:
        if '.' not in symbol:
            return symbol
        
        market_code, ticker = symbol.split('.', 1)
        
        # 市场代码到文件映射
        market_files = {
            'SH': 'constants/stock_lists/xshg_stocks.json',
            'SZ': 'constants/stock_lists/xshe_stocks.json',
            'BJ': 'constants/stock_lists/bjse_stocks.json'
        }
        
        file_path = market_files.get(market_code)
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"找不到市场{market_code}的股票清单文件")
            return symbol
        
        # 读取JSON文件
        with open(file_path, 'r', encoding='utf-8') as f:
            stocks = json.load(f)
        
        # 查找股票名称
        for stock in stocks:
            if stock.get('ticker') == ticker:
                return stock.get('name', symbol)
        
        logger.warning(f"在清单中未找到股票{symbol}的名称信息")
        return symbol
        
    except Exception as e:
        logger.error(f"获取股票名称失败 {symbol}: {e}")
        return symbol


def integrate_stock_data(symbol: str, 
                        api_records: List[Any], 
                        force_update: bool = False,
                        skip_existing: bool = True) -> Dict[str, Any]:
    """
    将API数据集成到TimescaleDB数据库
    
    Args:
        symbol: 股票代码
        api_records: API返回的数据记录
        force_update: 是否强制更新已存在数据
        skip_existing: 是否跳过已存在的股票（用于断点续传）
        
    Returns:
        Dict: 集成结果
    """
    from database.connection import db_manager
    from models.stock_data import StockDailyData, StockInfo
    from data_fetcher.stock_api import convert_to_database_format
    
    # 从JSON文件获取股票中文名称
    stock_name = get_stock_name_from_json(symbol)
    
    # 转换API数据为数据库格式
    api_data_dicts = []
    for record in api_records:
        api_data_dicts.append({
            'ticker': record.ticker,
            'date': record.date,
            'open': record.open,
            'high': record.high,
            'low': record.low,
            'close': record.close,
            'volume': record.volume
        })
    
    db_records = convert_to_database_format(api_data_dicts, symbol, stock_name)
    
    if not db_records:
        return {
            'success': False,
            'error': '数据转换失败',
            'inserted_count': 0,
            'updated_count': 0,
            'skipped_count': 0
        }
    
    inserted_count = 0
    updated_count = 0
    skipped_count = 0
    
    # 使用新的session，确保事务独立
    if db_manager.SessionLocal is None:
        return {
            'success': False,
            'error': 'Database session factory not initialized',
            'inserted_count': 0,
            'updated_count': 0,
            'skipped_count': 0
        }
    
    session = db_manager.SessionLocal()
    
    try:
        # 检查是否已有该股票的数据（用于断点续传）
        if skip_existing:
            existing_count = session.query(StockDailyData).filter(
                StockDailyData.symbol == symbol
            ).count()
            
            if existing_count > 0 and not force_update:
                logger.info(f"股票{symbol}已有{existing_count}条记录，跳过同步")
                return {
                    'success': True,
                    'inserted_count': 0,
                    'updated_count': 0,
                    'skipped_count': existing_count,
                    'total_processed': 0,
                    'symbol': symbol,
                    'message': f'已跳过（已有{existing_count}条记录）'
                }
        
        # 确保股票信息存在
        stock_info = session.query(StockInfo).filter(
            StockInfo.symbol == symbol
        ).first()
        
        if not stock_info:
            # 创建股票信息记录
            market_code = symbol.split('.')[0] if '.' in symbol else 'UNKNOWN'
            stock_code = symbol.split('.')[1] if '.' in symbol else symbol
            
            china_now = get_china_time()
            
            stock_info = StockInfo(
                symbol=symbol,
                stock_name=stock_name,
                stock_code=stock_code,
                market_code=market_code,
                is_active='Y',
                created_at=china_now,
                updated_at=china_now
            )
            
            try:
                session.add(stock_info)
                session.flush()  # 刷新以获取ID
                logger.info(f"创建股票信息: {symbol} - {stock_name}")
            except Exception as e:
                # 可能已存在，忽略
                session.rollback()
                logger.warning(f"股票信息可能已存在: {symbol} - {e}")
        
        # 批量插入或更新行情数据
        batch_size = 1000
        for i in range(0, len(db_records), batch_size):
            batch = db_records[i:i + batch_size]
            
            for record_data in batch:
                try:
                    # 检查是否已存在
                    existing_record = session.query(StockDailyData).filter(
                        StockDailyData.symbol == symbol,
                        StockDailyData.trade_date == record_data['trade_date']
                    ).first()
                    
                    if existing_record:
                        if force_update:
                            # 更新现有记录
                            for key, value in record_data.items():
                                if key not in ['symbol', 'trade_date', 'created_at']:
                                    setattr(existing_record, key, value)
                            # 更新时间戳
                            setattr(existing_record, 'updated_at', get_china_time())
                            updated_count += 1
                        else:
                            skipped_count += 1
                    else:
                        # 创建新记录
                        new_record = StockDailyData(**record_data)
                        session.add(new_record)
                        inserted_count += 1
                        
                except Exception as e:
                    logger.error(f"处理记录失败 {symbol} {record_data.get('trade_date')}: {e}")
                    continue
                
            # 每批次提交一次
            try:
                session.commit()
            except Exception as e:
                logger.error(f"批次提交失败: {e}")
                session.rollback()
                raise
        
        return {
            'success': True,
            'inserted_count': inserted_count,
            'updated_count': updated_count,
            'skipped_count': skipped_count,
            'total_processed': len(db_records),
            'symbol': symbol,
            'stock_name': stock_name
        }
        
    except Exception as e:
        session.rollback()
        logger.error(f"数据集成失败 {symbol}: {e}")
        return {
            'success': False,
            'error': str(e),
            'inserted_count': 0,
            'updated_count': 0,
            'skipped_count': 0
        }
    finally:
        session.close()


def batch_integrate_stock_data(stock_data_list: List[Dict[str, Any]], 
                              force_update: bool = False) -> Dict[str, Any]:
    """
    批量集成股票数据
    
    Args:
        stock_data_list: 股票数据列表，每个元素包含symbol和api_records
        force_update: 是否强制更新
        
    Returns:
        Dict: 批量集成结果
    """
    try:
        total_processed = 0
        total_inserted = 0
        total_updated = 0
        successful_stocks = 0
        failed_stocks = []
        
        for stock_data in stock_data_list:
            symbol = stock_data.get('symbol')
            api_records = stock_data.get('api_records', [])
            
            if not symbol or not api_records:
                failed_stocks.append({
                    'symbol': symbol or 'Unknown',
                    'error': 'Missing symbol or api_records'
                })
                continue
            
            result = integrate_stock_data(symbol, api_records, force_update)
            
            if result['success']:
                successful_stocks += 1
                total_inserted += result['inserted_count']
                total_updated += result['updated_count']
                total_processed += result['total_processed']
            else:
                failed_stocks.append({
                    'symbol': symbol,
                    'error': result['error']
                })
        
        success_rate = successful_stocks / len(stock_data_list) if stock_data_list else 0
        
        return {
            'success': success_rate > 0.5,  # 成功率超过50%认为成功
            'total_stocks': len(stock_data_list),
            'successful_stocks': successful_stocks,
            'failed_stocks': len(failed_stocks),
            'failed_stocks_detail': failed_stocks[:10],  # 只返回前10个失败的
            'total_processed': total_processed,
            'total_inserted': total_inserted,
            'total_updated': total_updated,
            'success_rate': success_rate
        }
        
    except Exception as e:
        logger.error(f"批量数据集成失败: {e}")
        return {
            'success': False,
            'error': str(e),
            'total_stocks': len(stock_data_list) if stock_data_list else 0,
            'successful_stocks': 0,
            'failed_stocks': len(stock_data_list) if stock_data_list else 0
        }