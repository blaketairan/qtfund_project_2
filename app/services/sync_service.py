"""
同步服务模块

提供数据同步的核心业务逻辑，包括：
1. 交易所信息同步
2. 股票清单同步
3. 股票行情数据同步
"""

from typing import Dict, List, Any, Optional
import json
import os
import logging
from datetime import datetime, date
import time

logger = logging.getLogger(__name__)


class SyncService:
    """同步服务类"""
    
    def __init__(self):
        # 从环境变量获取API token，确保安全性
        self.token = os.getenv('STOCK_API_TOKEN')
        if not self.token:
            raise ValueError("STOCK_API_TOKEN not found in environment variables. Please check your .env file.")
    
    def sync_exchanges_info(self, 
                          force_update: bool = False,
                          target_file: str = 'exchange_code.json') -> Dict[str, Any]:
        """
        同步交易所信息到本地文件
        
        Args:
            force_update: 是否强制更新
            target_file: 目标文件名
            
        Returns:
            Dict: 同步结果
        """
        try:
            # 这里模拟从远程API获取交易所信息
            # 实际项目中，这应该是真正的API调用
            
            # 检查文件是否存在且是否需要更新
            if os.path.exists(target_file) and not force_update:
                file_stats = os.stat(target_file)
                file_age_hours = (time.time() - file_stats.st_mtime) / 3600
                
                if file_age_hours < 24:  # 文件不超过24小时，跳过更新
                    return {
                        'success': True,
                        'action': 'skipped',
                        'message': '交易所信息文件较新，跳过更新',
                        'file_path': target_file,
                        'file_age_hours': round(file_age_hours, 2)
                    }
            
            # 读取现有文件作为模拟的"远程API"数据
            if os.path.exists(target_file):
                with open(target_file, 'r', encoding='utf-8') as f:
                    exchanges_data = json.load(f)
                
                # 更新时间戳
                for exchange in exchanges_data:
                    exchange['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                
                # 保存更新后的数据
                with open(target_file, 'w', encoding='utf-8') as f:
                    json.dump(exchanges_data, f, ensure_ascii=False, indent=2)
                
                return {
                    'success': True,
                    'action': 'updated',
                    'message': '交易所信息同步成功',
                    'file_path': target_file,
                    'exchanges_count': len(exchanges_data),
                    'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                }
            else:
                return {
                    'success': False,
                    'action': 'failed',
                    'error': f'交易所信息文件不存在: {target_file}',
                    'message': '请确保exchange_code.json文件存在'
                }
                
        except Exception as e:
            logger.error(f"同步交易所信息失败: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': '交易所信息同步失败'
            }
    
    def sync_stock_lists(self,
                        exchange_codes: Optional[List[str]] = None,
                        force_update: bool = False,
                        output_dir: str = 'constants/stock_lists') -> Dict[str, Any]:
        """
        同步股票清单到本地JSON文件
        
        Args:
            exchange_codes: 要同步的交易所代码列表
            force_update: 是否强制更新
            output_dir: 输出目录
            
        Returns:
            Dict: 同步结果
        """
        try:
            if exchange_codes is None:
                exchange_codes = ['XSHG', 'XSHE', 'BJSE']
            
            from data_fetcher.exchange_stocks import fetch_all_chinese_exchange_stocks
            
            # 执行同步
            sync_results = fetch_all_chinese_exchange_stocks(
                token=self.token,
                output_dir=output_dir
            )
            
            # 统计结果
            total_stocks = 0
            successful_exchanges = 0
            failed_exchanges = []
            
            for result in sync_results:
                if result['success']:
                    successful_exchanges += 1
                    total_stocks += result['total_stocks']
                else:
                    failed_exchanges.append({
                        'exchange_code': result['exchange_code'],
                        'error': result['error']
                    })
            
            success = len(failed_exchanges) == 0
            
            return {
                'success': success,
                'action': 'completed',
                'message': f'股票清单同步完成，成功: {successful_exchanges}，失败: {len(failed_exchanges)}',
                'total_exchanges': len(sync_results),
                'successful_exchanges': successful_exchanges,
                'failed_exchanges': failed_exchanges,
                'total_stocks': total_stocks,
                'output_dir': output_dir,
                'sync_results': sync_results
            }
            
        except Exception as e:
            logger.error(f"同步股票清单失败: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': '股票清单同步失败'
            }
    
    def sync_stock_prices(self,
                         symbols: Optional[List[str]] = None,
                         start_year: int = 2000,
                         batch_size: int = 10,
                         force_update: bool = False,
                         max_stocks: int = 100,
                         stop_flag = None,
                         progress_callback = None) -> Dict[str, Any]:
        """
        同步股票行情数据到TimescaleDB
        
        Args:
            symbols: 指定股票代码列表，为空则自动获取
            start_year: 开始年份
            batch_size: 批处理大小
            force_update: 是否强制更新
            max_stocks: 最大股票数量限制
            
        Returns:
            Dict: 同步结果
        """
        try:
            # 如果没有指定股票列表，从本地JSON文件获取
            if not symbols:
                symbols = self._get_all_stock_symbols(limit=max_stocks)
            
            if not symbols:
                return {
                    'success': False,
                    'action': 'failed',
                    'error': '没有找到需要同步的股票代码',
                    'message': '请先同步股票清单或指定股票代码'
                }
            
            # 限制股票数量
            if len(symbols) > max_stocks:
                symbols = symbols[:max_stocks]
                logger.info(f"限制同步股票数量为: {max_stocks}")
            
            from data_fetcher.stock_api import StockDataFetcher
            from utils.data_integration import integrate_stock_data
            
            fetcher = StockDataFetcher(self.token)
            
            # 同步统计
            successful_stocks = 0
            failed_stocks = []
            total_records = 0
            
            # 分批处理
            for i in range(0, len(symbols), batch_size):
                batch_symbols = symbols[i:i + batch_size]
                
                batch_num = i//batch_size + 1
                total_batches = (len(symbols)-1)//batch_size + 1
                logger.info(f"\n{'='*70}")
                logger.info(f"处理批次 {batch_num}/{total_batches}: {len(batch_symbols)}只股票")
                logger.info(f"批次范围: 第{i+1}-{min(i+len(batch_symbols), len(symbols))}只 / 总计{len(symbols)}只")
                logger.info(f"{'='*70}")
                
                for idx, symbol in enumerate(batch_symbols, 1):
                    # 检查停止标志
                    if stop_flag and stop_flag.is_set():
                        logger.warning(f"\n⚠️ 收到停止信号，任务中断于第{i + idx}只股票")
                        break
                    
                    stock_num = i + idx
                    
                    # 更新进度
                    if progress_callback:
                        progress_callback(stock_num, len(symbols), f"正在处理: {symbol}")
                    
                    try:
                        logger.info(f"\n[{stock_num}/{len(symbols)}] 🔄 正在处理: {symbol}")
                        
                        # 获取数据
                        start_date = f"{start_year}-01-01"
                        logger.info(f"[{stock_num}/{len(symbols)}] 📡 获取数据: {symbol} (从{start_date}开始)")
                        records = fetcher.fetch_by_symbol(symbol, start_date=start_date)
                        
                        if records:
                            logger.info(f"[{stock_num}/{len(symbols)}] 📥 接收数据: {symbol} - {len(records)}条记录")
                            
                            # 集成到数据库（开启断点续传）
                            logger.info(f"[{stock_num}/{len(symbols)}] 💾 写入数据库: {symbol}")
                            result = integrate_stock_data(
                                symbol=symbol,
                                api_records=records,
                                force_update=force_update,
                                skip_existing=True  # 启用断点续传
                            )
                            
                            if result['success']:
                                successful_stocks += 1
                                inserted = result.get('inserted_count', 0)
                                skipped = result.get('skipped_count', 0)
                                total_records += inserted
                                
                                if skipped > 0:
                                    logger.info(f"[{stock_num}/{len(symbols)}] ⏭️  {symbol} - 已跳过(已有{skipped}条记录) - {result.get('stock_name', symbol)}")
                                else:
                                    logger.info(f"[{stock_num}/{len(symbols)}] ✅ {symbol} - 成功插入{inserted}条 - {result.get('stock_name', symbol)}")
                            else:
                                failed_stocks.append({
                                    'symbol': symbol,
                                    'error': result.get('error', 'Unknown error')
                                })
                                logger.error(f"[{stock_num}/{len(symbols)}] ❌ {symbol} - 失败: {result.get('error')}")
                        else:
                            failed_stocks.append({
                                'symbol': symbol,
                                'error': 'No data received from API'
                            })
                            logger.warning(f"[{stock_num}/{len(symbols)}] ⚠️  {symbol} - 无数据返回")
                            
                    except Exception as e:
                        failed_stocks.append({
                            'symbol': symbol,
                            'error': str(e)
                        })
                        logger.error(f"[{stock_num}/{len(symbols)}] ❌ {symbol} - 异常: {e}")
                
                # 检查是否被停止
                if stop_flag and stop_flag.is_set():
                    break
                
                # 批次完成统计
                logger.info(f"\n{'─'*70}")
                logger.info(f"批次 {batch_num}/{total_batches} 完成 - 成功: {successful_stocks}只, 失败: {len(failed_stocks)}只")
                logger.info(f"{'─'*70}\n")
                
                # 批次间暂停
                if i + batch_size < len(symbols):
                    time.sleep(1)  # 避免API限流
            
            success_rate = successful_stocks / len(symbols) if symbols else 0
            
            return {
                'success': success_rate > 0.5,  # 成功率超过50%认为成功
                'action': 'completed',
                'message': f'股票行情同步完成，成功率: {success_rate:.1%}',
                'total_symbols': len(symbols),
                'successful_stocks': successful_stocks,
                'failed_stocks_count': len(failed_stocks),
                'failed_stocks': failed_stocks[:10],  # 只返回前10个失败的
                'total_records': total_records,
                'start_year': start_year,
                'batch_size': batch_size,
                'success_rate': success_rate
            }
            
        except Exception as e:
            logger.error(f"同步股票行情数据失败: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': '股票行情数据同步失败'
            }
    
    def sync_single_stock(self,
                         symbol: str,
                         start_date: Optional[str] = None,
                         end_date: Optional[str] = None,
                         force_update: bool = False) -> Dict[str, Any]:
        """
        同步单只股票的行情数据
        
        Args:
            symbol: 股票代码
            start_date: 开始日期
            end_date: 结束日期
            force_update: 是否强制更新
            
        Returns:
            Dict: 同步结果
        """
        try:
            from data_fetcher.stock_api import StockDataFetcher
            from utils.data_integration import integrate_stock_data
            
            fetcher = StockDataFetcher(self.token)
            
            # 获取数据
            records = fetcher.fetch_by_symbol(symbol, start_date, end_date)
            
            if not records:
                return {
                    'success': False,
                    'action': 'failed',
                    'error': 'API未返回数据',
                    'message': f'股票{symbol}没有获取到数据'
                }
            
            # 集成到数据库（开启断点续传）
            result = integrate_stock_data(
                symbol=symbol,
                api_records=records,
                force_update=force_update,
                skip_existing=False  # 单个股票同步不跳过
            )
            
            if result['success']:
                return {
                    'success': True,
                    'action': 'completed',
                    'message': f'股票{symbol}行情数据同步成功',
                    'symbol': symbol,
                    'records_count': len(records),
                    'inserted_count': result.get('inserted_count', 0),
                    'updated_count': result.get('updated_count', 0),
                    'date_range': {
                        'start': records[-1].date if records else None,
                        'end': records[0].date if records else None
                    }
                }
            else:
                return {
                    'success': False,
                    'action': 'failed',
                    'error': result.get('error', 'Database integration failed'),
                    'message': f'股票{symbol}数据库集成失败'
                }
                
        except Exception as e:
            logger.error(f"同步单只股票失败 {symbol}: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': f'股票{symbol}同步失败'
            }
    
    def full_sync(self,
                 include_exchanges: bool = True,
                 include_stock_lists: bool = True,
                 include_stock_prices: bool = False,
                 max_stocks: int = 50,
                 start_year: int = 2020) -> Dict[str, Any]:
        """
        执行完整同步
        
        Args:
            include_exchanges: 是否包含交易所信息同步
            include_stock_lists: 是否包含股票清单同步
            include_stock_prices: 是否包含股票行情同步
            max_stocks: 行情同步的最大股票数
            start_year: 行情同步的起始年份
            
        Returns:
            Dict: 同步结果
        """
        try:
            results: Dict[str, Optional[Dict[str, Any]]] = {
                'exchanges': None,
                'stock_lists': None,
                'stock_prices': None
            }
            
            overall_success = True
            
            # 1. 同步交易所信息
            if include_exchanges:
                logger.info("开始同步交易所信息...")
                results['exchanges'] = self.sync_exchanges_info()
                if not results['exchanges']['success']:
                    overall_success = False
            
            # 2. 同步股票清单
            if include_stock_lists:
                logger.info("开始同步股票清单...")
                results['stock_lists'] = self.sync_stock_lists()
                if not results['stock_lists']['success']:
                    overall_success = False
            
            # 3. 同步股票行情（可选，因为耗时较长）
            if include_stock_prices:
                logger.info("开始同步股票行情数据...")
                results['stock_prices'] = self.sync_stock_prices(
                    max_stocks=max_stocks,
                    start_year=start_year
                )
                if not results['stock_prices']['success']:
                    overall_success = False
            
            return {
                'success': overall_success,
                'action': 'completed',
                'message': '完整同步任务完成',
                'included_tasks': {
                    'exchanges': include_exchanges,
                    'stock_lists': include_stock_lists,
                    'stock_prices': include_stock_prices
                },
                'results': results,
                'completed_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            logger.error(f"完整同步失败: {e}")
            return {
                'success': False,
                'action': 'failed',
                'error': str(e),
                'message': '完整同步失败'
            }
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        获取同步状态信息
        
        Returns:
            Dict: 状态信息
        """
        try:
            status = {
                'exchanges': self._get_exchanges_status(),
                'stock_lists': self._get_stock_lists_status(),
                'database': self._get_database_status(),
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
            return status
            
        except Exception as e:
            logger.error(f"获取同步状态失败: {e}")
            return {
                'error': str(e),
                'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
    
    def _get_all_stock_symbols(self, limit: int = 100) -> List[str]:
        """从本地JSON文件获取所有股票代码"""
        try:
            from app.services.stock_info_service import StockInfoService
            service = StockInfoService()
            
            result = service.query_from_local_files(limit=limit)
            
            if result['success']:
                symbols = []
                for stock in result['data']:
                    ticker = stock.get('ticker', '')
                    exchange_code = stock.get('exchange_code', '')
                    
                    # 转换为项目内部格式
                    if exchange_code == 'XSHG' and ticker:
                        symbols.append(f"SH.{ticker}")
                    elif exchange_code == 'XSHE' and ticker:
                        symbols.append(f"SZ.{ticker}")
                    elif exchange_code == 'BJSE' and ticker:
                        symbols.append(f"BJ.{ticker}")
                
                return symbols
            
            return []
            
        except Exception as e:
            logger.error(f"获取股票代码列表失败: {e}")
            return []
    
    def _get_exchanges_status(self) -> Dict[str, Any]:
        """获取交易所信息状态"""
        try:
            file_path = 'exchange_code.json'
            if os.path.exists(file_path):
                stat = os.stat(file_path)
                return {
                    'file_exists': True,
                    'file_path': file_path,
                    'file_size': stat.st_size,
                    'last_modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'age_hours': round((time.time() - stat.st_mtime) / 3600, 2)
                }
            else:
                return {
                    'file_exists': False,
                    'file_path': file_path,
                    'message': '交易所信息文件不存在'
                }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_stock_lists_status(self) -> Dict[str, Any]:
        """获取股票清单状态"""
        try:
            stock_lists_dir = 'constants/stock_lists'
            files = ['xshg_stocks.json', 'xshe_stocks.json', 'bjse_stocks.json']
            
            status = {}
            total_stocks = 0
            
            for filename in files:
                file_path = os.path.join(stock_lists_dir, filename)
                if os.path.exists(file_path):
                    stat = os.stat(file_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        stock_count = len(data) if isinstance(data, list) else 0
                        total_stocks += stock_count
                    
                    status[filename] = {
                        'exists': True,
                        'stock_count': stock_count,
                        'file_size': stat.st_size,
                        'last_modified': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S')
                    }
                else:
                    status[filename] = {
                        'exists': False,
                        'message': '文件不存在'
                    }
            
            status['total_stocks'] = total_stocks
            return status
            
        except Exception as e:
            return {'error': str(e)}
    
    def _get_database_status(self) -> Dict[str, Any]:
        """获取数据库状态"""
        try:
            from database.connection import db_manager
            
            # 测试连接
            db_connected = db_manager.test_connection()
            
            status: Dict[str, Any] = {
                'connected': db_connected
            }
            
            if db_connected:
                # 获取数据库中的股票数据统计
                try:
                    with db_manager.get_session() as session:
                        from models.stock_data import StockDailyData, StockInfo
                        
                        # 股票信息统计
                        stock_info_count = session.query(StockInfo).count()
                        
                        # 行情数据统计
                        stock_data_count = session.query(StockDailyData).count()
                        
                        # 最新数据日期
                        latest_data = session.query(StockDailyData.trade_date).order_by(
                            StockDailyData.trade_date.desc()
                        ).first()
                        
                        status.update({
                            'stock_info_count': stock_info_count,
                            'stock_data_count': stock_data_count,
                            'latest_data_date': latest_data[0].strftime('%Y-%m-%d') if latest_data else None
                        })
                        
                except Exception as e:
                    status['query_error'] = str(e)
            
            return status
            
        except Exception as e:
            return {
                'connected': False,
                'error': str(e)
            }