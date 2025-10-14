"""
股票行情数据查询路由模块

提供两套接口：
1. 从TimescaleDB查询历史数据
2. 从远程HTTP API查询实时数据
"""

from flask import Blueprint, request
from app.utils.responses import (
    create_stock_data_response, 
    create_error_response,
    format_stock_price_data,
    format_api_stock_data,
    validate_date_range,
    validate_symbol_format
)
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
stock_price_bp = Blueprint('stock_price', __name__)


@stock_price_bp.route('/query', methods=['GET', 'POST'])
def query_from_database():
    """从TimescaleDB查询股票行情数据"""
    try:
        # 获取请求参数
        if request.method == 'POST':
            data = request.get_json() or {}
            symbol = data.get('symbol', '')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            limit = data.get('limit', 100)
        else:
            symbol = request.args.get('symbol', '')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            limit = request.args.get('limit', 100, type=int)
        
        # 验证参数
        if not symbol:
            return create_error_response(400, "股票代码不能为空")
        
        symbol = validate_symbol_format(symbol)
        date_range = validate_date_range(start_date, end_date)
        
        if limit <= 0 or limit > 10000:
            return create_error_response(400, "数据条数限制应在1-10000之间")
        
        # 查询数据库
        from app.services.stock_data_service import StockDataService
        service = StockDataService()
        
        db_result = service.query_stock_data_from_db(
            symbol=symbol,
            start_date=date_range['start_date'],
            end_date=date_range['end_date'],
            limit=limit
        )
        
        if not db_result['success']:
            return create_error_response(
                500, 
                "数据库查询失败", 
                db_result['error']
            )
        
        # 格式化响应
        stock_data = [format_stock_price_data(record) for record in db_result['data']]
        
        # 计算日期范围
        actual_date_range = None
        if stock_data:
            dates = [item['trade_date'] for item in stock_data]
            actual_date_range = {
                "start": min(dates),
                "end": max(dates),
                "count": len(stock_data)
            }
        
        return create_stock_data_response(
            data=stock_data,
            symbol=symbol,
            source="database",
            date_range=actual_date_range,
            total=db_result['total']
        )
        
    except ValueError as e:
        return create_error_response(400, "参数错误", str(e))
    except Exception as e:
        logger.error(f"数据库查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@stock_price_bp.route('/remote', methods=['GET', 'POST'])
def query_from_remote_api():
    """从远程HTTP API查询股票行情数据"""
    try:
        # 获取请求参数
        if request.method == 'POST':
            data = request.get_json() or {}
            symbol = data.get('symbol', '')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            limit = data.get('limit', 100)
        else:
            symbol = request.args.get('symbol', '')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            limit = request.args.get('limit', 100, type=int)
        
        # 验证参数
        if not symbol:
            return create_error_response(400, "股票代码不能为空")
        
        symbol = validate_symbol_format(symbol)
        date_range = validate_date_range(start_date, end_date)
        
        # 调用远程API
        from app.services.stock_data_service import StockDataService
        service = StockDataService()
        
        api_result = service.query_stock_data_from_api(
            symbol=symbol,
            start_date=date_range['start_date'],
            end_date=date_range['end_date']
        )
        
        if not api_result['success']:
            return create_error_response(
                500,
                "远程API查询失败",
                api_result['error']
            )
        
        # 格式化响应
        stock_data = []
        stock_name = api_result.get('stock_name', symbol)
        
        for api_record in api_result['data']:
            formatted_data = format_api_stock_data(api_record, symbol, stock_name)
            stock_data.append(formatted_data)
        
        # 应用limit限制
        if limit and len(stock_data) > limit:
            stock_data = stock_data[:limit]
        
        # 计算日期范围
        actual_date_range = None
        if stock_data:
            dates = [item['trade_date'] for item in stock_data]
            actual_date_range = {
                "start": min(dates),
                "end": max(dates),
                "count": len(stock_data)
            }
        
        return create_stock_data_response(
            data=stock_data,
            symbol=symbol,
            source="remote_api",
            date_range=actual_date_range,
            total=len(api_result['data'])
        )
        
    except ValueError as e:
        return create_error_response(400, "参数错误", str(e))
    except Exception as e:
        logger.error(f"远程API查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@stock_price_bp.route('/compare', methods=['GET', 'POST'])
def compare_data_sources():
    """对比数据库和远程API的数据"""
    try:
        # 获取请求参数
        if request.method == 'POST':
            data = request.get_json() or {}
            symbol = data.get('symbol', '')
            start_date = data.get('start_date')
            end_date = data.get('end_date')
            limit = data.get('limit', 10)
        else:
            symbol = request.args.get('symbol', '')
            start_date = request.args.get('start_date')
            end_date = request.args.get('end_date')
            limit = request.args.get('limit', 10, type=int)
        
        # 验证参数
        if not symbol:
            return create_error_response(400, "股票代码不能为空")
        
        symbol = validate_symbol_format(symbol)
        date_range = validate_date_range(start_date, end_date)
        
        from app.services.stock_data_service import StockDataService
        service = StockDataService()
        
        # 同时查询两个数据源
        db_result = service.query_stock_data_from_db(
            symbol=symbol,
            start_date=date_range['start_date'],
            end_date=date_range['end_date'],
            limit=limit
        )
        
        api_result = service.query_stock_data_from_api(
            symbol=symbol,
            start_date=date_range['start_date'],
            end_date=date_range['end_date']
        )
        
        # 格式化对比数据
        comparison_data = {
            "database": {
                "success": db_result['success'],
                "count": len(db_result['data']) if db_result['success'] else 0,
                "data": [format_stock_price_data(record) for record in db_result['data'][:limit]] if db_result['success'] else [],
                "error": db_result.get('error')
            },
            "remote_api": {
                "success": api_result['success'],
                "count": len(api_result['data']) if api_result['success'] else 0,
                "data": [format_api_stock_data(record, symbol) for record in api_result['data'][:limit]] if api_result['success'] else [],
                "error": api_result.get('error')
            }
        }
        
        from app.utils.responses import create_success_response
        return create_success_response(
            data=comparison_data,
            message="数据源对比查询完成"
        )
        
    except ValueError as e:
        return create_error_response(400, "参数错误", str(e))
    except Exception as e:
        logger.error(f"数据对比查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))