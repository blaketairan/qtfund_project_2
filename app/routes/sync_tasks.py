"""
同步任务路由模块

提供三类同步任务接口：
1. 同步交易所信息到本地
2. 同步股票清单信息到本地
3. 同步全量股票行情数据到TimescaleDB
"""

from flask import Blueprint, request
from app.utils.responses import (
    create_sync_task_response,
    create_error_response,
    create_success_response
)
import logging
import time

logger = logging.getLogger(__name__)

# 创建蓝图
sync_tasks_bp = Blueprint('sync_tasks', __name__)


@sync_tasks_bp.route('/exchanges', methods=['POST'])
def sync_exchanges():
    """同步交易所信息到本地"""
    start_time = time.time()
    
    try:
        # 获取请求参数
        data = request.get_json() or {}
        force_update = data.get('force_update', False)
        target_file = data.get('target_file', 'exchange_code.json')
        
        from app.services.sync_service import SyncService
        service = SyncService()
        
        result = service.sync_exchanges_info(
            force_update=force_update,
            target_file=target_file
        )
        
        duration = time.time() - start_time
        
        if result['success']:
            return create_sync_task_response(
                task_name="同步交易所信息",
                status="success",
                result=result,
                duration=duration
            )
        else:
            return create_sync_task_response(
                task_name="同步交易所信息",
                status="failed",
                result=result,
                duration=duration
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"同步交易所信息异常: {e}")
        return create_sync_task_response(
            task_name="同步交易所信息",
            status="failed",
            result={'error': str(e)},
            duration=duration
        )


@sync_tasks_bp.route('/stock-lists', methods=['POST'])
def sync_stock_lists():
    """同步股票清单信息到本地JSON文件"""
    start_time = time.time()
    
    try:
        # 获取请求参数
        data = request.get_json() or {}
        exchange_codes = data.get('exchange_codes', ['XSHG', 'XSHE', 'BJSE'])
        force_update = data.get('force_update', False)
        output_dir = data.get('output_dir', 'constants/stock_lists')
        
        from app.services.sync_service import SyncService
        service = SyncService()
        
        result = service.sync_stock_lists(
            exchange_codes=exchange_codes,
            force_update=force_update,
            output_dir=output_dir
        )
        
        duration = time.time() - start_time
        
        if result['success']:
            return create_sync_task_response(
                task_name="同步股票清单",
                status="success",
                result=result,
                duration=duration
            )
        else:
            return create_sync_task_response(
                task_name="同步股票清单",
                status="failed",
                result=result,
                duration=duration
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"同步股票清单异常: {e}")
        return create_sync_task_response(
            task_name="同步股票清单",
            status="failed",
            result={'error': str(e)},
            duration=duration
        )


@sync_tasks_bp.route('/stock-prices', methods=['POST'])
def sync_stock_prices():
    """同步全量股票行情数据到TimescaleDB（后台任务）"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        symbols = data.get('symbols', [])  # 指定股票代码列表，为空则同步所有
        start_year = data.get('start_year', 2000)  # 从哪一年开始同步
        batch_size = data.get('batch_size', 10)  # 批处理大小
        force_update = data.get('force_update', False)  # 是否强制更新已存在数据
        max_stocks = data.get('max_stocks', 100)  # 最大同步股票数量限制
        background = data.get('background', True)  # 是否后台执行
        
        from app.services.sync_service import SyncService
        
        if background:
            # 后台任务模式
            from app.services.background_tasks import task_manager
            
            service = SyncService()
            task_id = task_manager.create_task(
                task_name="同步股票行情数据",
                task_func=service.sync_stock_prices,
                symbols=symbols,
                start_year=start_year,
                batch_size=batch_size,
                force_update=force_update,
                max_stocks=max_stocks
            )
            
            return create_success_response(
                data={
                    'task_id': task_id,
                    'task_name': '同步股票行情数据',
                    'status': 'running',
                    'message': '后台任务已启动，请使用 /api/sync/tasks/{task_id} 查询进度'
                },
                message="后台任务已启动"
            )
        else:
            # 同步模式（原有逻辑）
            start_time = time.time()
            service = SyncService()
            
            result = service.sync_stock_prices(
                symbols=symbols,
                start_year=start_year,
                batch_size=batch_size,
                force_update=force_update,
                max_stocks=max_stocks
            )
            
            duration = time.time() - start_time
            
            if result['success']:
                return create_sync_task_response(
                    task_name="同步股票行情数据",
                    status="success",
                    result=result,
                    duration=duration
                )
            else:
                return create_sync_task_response(
                    task_name="同步股票行情数据",
                    status="failed",
                    result=result,
                    duration=duration
                )
            
    except Exception as e:
        logger.error(f"同步股票行情数据异常: {e}")
        return create_error_response(500, "同步失败", str(e))


@sync_tasks_bp.route('/single-stock', methods=['POST'])
def sync_single_stock():
    """同步单只股票的历史行情数据（从2000年开始查至最新）"""
    start_time = time.time()
    
    try:
        # 获取请求参数
        data = request.get_json() or {}
        symbol = data.get('symbol', '')
        
        if not symbol:
            return create_error_response(400, "股票代码不能为空")
        
        from app.utils.responses import validate_symbol_format
        symbol = validate_symbol_format(symbol)
        
        from app.services.single_stock_sync import sync_single_stock_history
        
        result = sync_single_stock_history(symbol)
        
        duration = time.time() - start_time
        
        if result['success']:
            return create_sync_task_response(
                task_name=f"同步股票{symbol}历史行情",
                status="success",
                result=result,
                duration=duration
            )
        else:
            return create_sync_task_response(
                task_name=f"同步股票{symbol}历史行情",
                status="failed",
                result=result,
                duration=duration
            )
            
    except ValueError as e:
        duration = time.time() - start_time
        return create_error_response(400, "参数错误", str(e))
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"同步单只股票异常: {e}")
        return create_sync_task_response(
            task_name="同步单只股票历史行情",
            status="failed",
            result={'error': str(e)},
            duration=duration
        )


@sync_tasks_bp.route('/status', methods=['GET'])
def get_sync_status():
    """获取同步任务状态"""
    try:
        from app.services.sync_service import SyncService
        service = SyncService()
        
        status = service.get_sync_status()
        
        return create_success_response(
            data=status,
            message="同步状态查询成功"
        )
        
    except Exception as e:
        logger.error(f"获取同步状态异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@sync_tasks_bp.route('/full-sync', methods=['POST'])
def full_sync():
    """执行完整同步（交易所信息 + 股票清单 + 行情数据）"""
    start_time = time.time()
    
    try:
        # 获取请求参数
        data = request.get_json() or {}
        include_exchanges = data.get('include_exchanges', True)
        include_stock_lists = data.get('include_stock_lists', True)
        include_stock_prices = data.get('include_stock_prices', False)  # 行情数据同步可选
        max_stocks = data.get('max_stocks', 50)  # 限制行情同步的股票数量
        start_year = data.get('start_year', 2020)  # 行情数据起始年份
        
        from app.services.sync_service import SyncService
        service = SyncService()
        
        result = service.full_sync(
            include_exchanges=include_exchanges,
            include_stock_lists=include_stock_lists,
            include_stock_prices=include_stock_prices,
            max_stocks=max_stocks,
            start_year=start_year
        )
        
        duration = time.time() - start_time
        
        if result['success']:
            return create_sync_task_response(
                task_name="完整同步",
                status="success",
                result=result,
                duration=duration
            )
        else:
            return create_sync_task_response(
                task_name="完整同步",
                status="failed",
                result=result,
                duration=duration
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"完整同步异常: {e}")
        return create_sync_task_response(
            task_name="完整同步",
            status="failed",
            result={'error': str(e)},
            duration=duration
        )


# ========== 后台任务管理接口 ==========

@sync_tasks_bp.route('/tasks', methods=['GET'])
def list_tasks():
    """查询所有后台任务"""
    try:
        from app.services.background_tasks import task_manager
        
        status_filter = request.args.get('status')
        tasks = task_manager.list_tasks(status_filter=status_filter)
        
        return create_success_response(
            data={'tasks': tasks, 'total': len(tasks)},
            message=f"查询到 {len(tasks)} 个任务"
        )
    except Exception as e:
        logger.error(f"查询任务列表失败: {e}")
        return create_error_response(500, "查询失败", str(e))


@sync_tasks_bp.route('/tasks/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """查询指定任务状态"""
    try:
        from app.services.background_tasks import task_manager
        
        task_info = task_manager.get_task_status(task_id)
        
        if not task_info:
            return create_error_response(404, "任务不存在", f"找不到任务 ID: {task_id}")
        
        return create_success_response(
            data=task_info,
            message="任务状态查询成功"
        )
    except Exception as e:
        logger.error(f"查询任务状态失败: {e}")
        return create_error_response(500, "查询失败", str(e))


@sync_tasks_bp.route('/tasks/<task_id>/stop', methods=['POST'])
def stop_task(task_id):
    """停止指定任务"""
    try:
        from app.services.background_tasks import task_manager
        
        success = task_manager.stop_task(task_id)
        
        if not success:
            return create_error_response(400, "停止失败", "任务不存在或无法停止")
        
        return create_success_response(
            data={'task_id': task_id, 'status': 'stopping'},
            message="任务停止信号已发送"
        )
    except Exception as e:
        logger.error(f"停止任务失败: {e}")
        return create_error_response(500, "停止失败", str(e))


# ========== ETF同步接口 ==========

@sync_tasks_bp.route('/etf/lists', methods=['POST'])
def sync_etf_lists():
    """同步ETF列表到数据库"""
    start_time = time.time()
    
    try:
        # 获取请求参数
        data = request.get_json() or {}
        exchange_codes = data.get('exchange_codes', ['XSHG', 'XSHE'])
        
        from app.services.etf_sync_service import ETFSyncService
        service = ETFSyncService()
        
        result = service.sync_etf_lists(exchange_codes=exchange_codes)
        
        duration = time.time() - start_time
        
        if result['success']:
            return create_sync_task_response(
                task_name="同步ETF列表",
                status="success",
                result=result,
                duration=duration
            )
        else:
            return create_sync_task_response(
                task_name="同步ETF列表",
                status="failed",
                result=result,
                duration=duration
            )
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"同步ETF列表异常: {e}")
        return create_sync_task_response(
            task_name="同步ETF列表",
            status="failed",
            result={'error': str(e)},
            duration=duration
        )


@sync_tasks_bp.route('/etf/prices', methods=['POST'])
def sync_etf_prices():
    """同步ETF价格数据到数据库（后台任务）"""
    try:
        # 获取请求参数
        data = request.get_json() or {}
        symbol = data.get('symbol')  # 可选：指定ETF symbol
        exchange_code = data.get('exchange_code')  # 可选：按交易所同步
        start_year = data.get('start_year', 2020)
        force_update = data.get('force_update', False)
        background = data.get('background', True)  # 是否后台执行
        
        from app.services.etf_sync_service import ETFSyncService
        
        if background:
            # 后台任务模式
            from app.services.background_tasks import task_manager
            
            service = ETFSyncService()
            
            # 创建后台任务
            task_id = task_manager.create_task(
                task_name="同步ETF价格数据",
                task_func=service.sync_etf_prices,
                symbol=symbol,
                exchange_code=exchange_code,
                start_year=start_year,
                force_update=force_update
            )
            
            return create_success_response(
                data={
                    'task_id': task_id,
                    'task_name': '同步ETF价格数据',
                    'status': 'running',
                    'message': '后台任务已启动，请使用 /api/sync/tasks/{task_id} 查询进度'
                },
                message="ETF价格同步后台任务已启动"
            )
        else:
            # 同步模式
            start_time = time.time()
            service = ETFSyncService()
            
            result = service.sync_etf_prices(
                symbol=symbol,
                exchange_code=exchange_code,
                start_year=start_year,
                force_update=force_update
            )
            
            duration = time.time() - start_time
            
            if result['success']:
                return create_sync_task_response(
                    task_name="同步ETF价格数据",
                    status="success",
                    result=result,
                    duration=duration
                )
            else:
                return create_sync_task_response(
                    task_name="同步ETF价格数据",
                    status="failed",
                    result=result,
                    duration=duration
                )
            
    except Exception as e:
        logger.error(f"同步ETF价格数据异常: {e}")
        return create_error_response(500, "同步失败", str(e))