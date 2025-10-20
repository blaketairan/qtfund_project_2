"""
股票信息查询路由模块

提供两套接口：
1. 从本地JSON文件查询股票清单
2. 从远程HTTP API查询股票信息
"""

from flask import Blueprint, request
from app.utils.responses import (
    create_success_response,
    create_error_response,
    create_data_response
)
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
stock_info_bp = Blueprint('stock_info', __name__)


@stock_info_bp.route('/local', methods=['GET'])
def query_from_local_json():
    """从本地JSON文件查询股票信息"""
    try:
        # 获取查询参数
        exchange_code = request.args.get('exchange_code', '').upper()
        symbol = request.args.get('symbol', '')
        keyword = request.args.get('keyword', '')  # 股票名称关键字搜索
        is_active = request.args.get('is_active', '1')  # 是否活跃
        limit = request.args.get('limit', 0, type=int)  # 0表示不限制
        offset = request.args.get('offset', 0, type=int)
        
        # 从本地JSON加载数据
        from app.services.stock_info_service import StockInfoService
        service = StockInfoService()
        
        result = service.query_from_local_files(
            exchange_code=exchange_code,
            symbol=symbol,
            keyword=keyword,
            is_active=is_active,
            limit=limit,
            offset=offset
        )
        
        if not result['success']:
            return create_error_response(
                500,
                "本地数据查询失败",
                result['error']
            )
        
        return create_data_response(
            data=result['data'],
            total=result['total'],
            page=offset // limit + 1 if limit > 0 else 1,
            limit=limit,
            message="本地股票信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"本地JSON查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@stock_info_bp.route('/remote', methods=['GET'])
def query_from_remote_api():
    """从远程HTTP API查询股票信息"""
    try:
        # 获取查询参数
        exchange_code = request.args.get('exchange_code', '').upper()
        limit = request.args.get('limit', 100, type=int)
        
        if not exchange_code:
            return create_error_response(400, "交易所代码不能为空")
        
        # 验证交易所代码
        valid_exchanges = ['XSHG', 'XSHE', 'BJSE']
        if exchange_code not in valid_exchanges:
            return create_error_response(
                400,
                f"不支持的交易所代码，仅支持: {', '.join(valid_exchanges)}"
            )
        
        # 调用远程API
        from app.services.stock_info_service import StockInfoService
        service = StockInfoService()
        
        result = service.query_from_remote_api(
            exchange_code=exchange_code,
            limit=limit
        )
        
        if not result['success']:
            return create_error_response(
                500,
                "远程API查询失败",
                result['error']
            )
        
        return create_data_response(
            data=result['data'],
            total=result['total'],
            message="远程API股票信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"远程API查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@stock_info_bp.route('/search', methods=['GET'])
def search_stocks():
    """搜索股票信息（支持多种条件）"""
    try:
        # 获取搜索参数
        query_text = request.args.get('q', '')  # 搜索关键字
        exchange_code = request.args.get('exchange_code', '')
        market_code = request.args.get('market_code', '')  # SH/SZ/BJ
        source = request.args.get('source', 'local')  # local/remote
        limit = request.args.get('limit', 50, type=int)
        
        if not query_text:
            return create_error_response(400, "搜索关键字不能为空")
        
        from app.services.stock_info_service import StockInfoService
        service = StockInfoService()
        
        if source == 'local':
            result = service.search_stocks_local(
                query_text=query_text,
                exchange_code=exchange_code,
                market_code=market_code,
                limit=limit
            )
        else:
            result = service.search_stocks_remote(
                query_text=query_text,
                exchange_code=exchange_code,
                limit=limit
            )
        
        if not result['success']:
            return create_error_response(
                500,
                f"{source}搜索失败",
                result['error']
            )
        
        return create_data_response(
            data=result['data'],
            total=result['total'],
            message=f"{source}股票搜索完成"
        )
        
    except Exception as e:
        logger.error(f"股票搜索异常: {e}")
        return create_error_response(500, "搜索失败", str(e))


@stock_info_bp.route('/compare', methods=['GET'])
def compare_data_sources():
    """对比本地JSON和远程API的股票信息"""
    try:
        exchange_code = request.args.get('exchange_code', 'XSHG')
        limit = request.args.get('limit', 10, type=int)
        
        from app.services.stock_info_service import StockInfoService
        service = StockInfoService()
        
        # 同时查询两个数据源
        local_result = service.query_from_local_files(
            exchange_code=exchange_code,
            limit=limit
        )
        
        remote_result = service.query_from_remote_api(
            exchange_code=exchange_code,
            limit=limit
        )
        
        comparison_data = {
            "local_json": {
                "success": local_result['success'],
                "count": len(local_result['data']) if local_result['success'] else 0,
                "data": local_result['data'][:limit] if local_result['success'] else [],
                "error": local_result.get('error')
            },
            "remote_api": {
                "success": remote_result['success'],
                "count": len(remote_result['data']) if remote_result['success'] else 0,
                "data": remote_result['data'][:limit] if remote_result['success'] else [],
                "error": remote_result.get('error')
            }
        }
        
        return create_success_response(
            data=comparison_data,
            message="股票信息数据源对比完成"
        )
        
    except Exception as e:
        logger.error(f"数据源对比异常: {e}")
        return create_error_response(500, "对比失败", str(e))


@stock_info_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """获取股票信息统计数据"""
    try:
        from app.services.stock_info_service import StockInfoService
        service = StockInfoService()
        
        stats = service.get_stock_statistics()
        
        return create_success_response(
            data=stats,
            message="股票统计信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"统计信息查询异常: {e}")
        return create_error_response(500, "统计查询失败", str(e))