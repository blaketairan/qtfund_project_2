"""
交易所信息查询路由模块

提供两套接口：
1. 从本地常量查询交易所信息
2. 从远程HTTP API查询交易所信息
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
exchange_info_bp = Blueprint('exchange_info', __name__)


@exchange_info_bp.route('/local', methods=['GET'])
def query_from_local_constants():
    """从本地常量查询交易所信息"""
    try:
        # 获取查询参数
        exchange_code = request.args.get('exchange_code', '').upper()
        country_code = request.args.get('country_code', 'CHN')
        include_b_stocks = request.args.get('include_b_stocks', 'false').lower() == 'true'
        
        from constants.exchanges import ChineseExchanges
        
        if exchange_code:
            # 查询指定交易所
            exchanges = ChineseExchanges.get_exchanges_by_code()
            if exchange_code in exchanges:
                exchange_info = exchanges[exchange_code]
                data = {
                    'exchange_code': exchange_info.exchange_code,
                    'exchange_name': exchange_info.exchange_name,
                    'exchange_name_short': exchange_info.exchange_name_short,
                    'country_code': exchange_info.country_code,
                    'currency_code': exchange_info.currency_code,
                    'local_open': exchange_info.local_open,
                    'local_close': exchange_info.local_close,
                    'beijing_open': exchange_info.beijing_open,
                    'beijing_close': exchange_info.beijing_close,
                    'timezone': exchange_info.timezone,
                    'delay': exchange_info.delay,
                    'notes': exchange_info.notes
                }
                return create_success_response(
                    data=data,
                    message="交易所信息查询成功"
                )
            else:
                return create_error_response(404, f"未找到交易所: {exchange_code}")
        else:
            # 查询所有交易所
            if include_b_stocks:
                exchanges_list = ChineseExchanges.get_all_exchanges()
            else:
                exchanges_list = ChineseExchanges.get_main_exchanges()
            
            data = []
            for exchange in exchanges_list:
                data.append({
                    'exchange_code': exchange.exchange_code,
                    'exchange_name': exchange.exchange_name,
                    'exchange_name_short': exchange.exchange_name_short,
                    'country_code': exchange.country_code,
                    'currency_code': exchange.currency_code,
                    'local_open': exchange.local_open,
                    'local_close': exchange.local_close,
                    'beijing_open': exchange.beijing_open,
                    'beijing_close': exchange.beijing_close,
                    'timezone': exchange.timezone,
                    'delay': exchange.delay,
                    'notes': exchange.notes
                })
            
            return create_data_response(
                data=data,
                total=len(data),
                message="本地交易所信息查询成功"
            )
            
    except Exception as e:
        logger.error(f"本地常量查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@exchange_info_bp.route('/remote', methods=['GET'])
def query_from_remote_api():
    """从远程HTTP API查询交易所信息"""
    try:
        # 获取查询参数
        country_code = request.args.get('country_code', 'CHN')
        limit = request.args.get('limit', 100, type=int)
        
        # 调用远程API（这里使用exchange_code.json的内容模拟）
        from app.services.exchange_info_service import ExchangeInfoService
        service = ExchangeInfoService()
        
        result = service.query_from_remote_api(
            country_code=country_code,
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
            message="远程API交易所信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"远程API查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@exchange_info_bp.route('/compare', methods=['GET'])
def compare_data_sources():
    """对比本地常量和远程API的交易所信息"""
    try:
        country_code = request.args.get('country_code', 'CHN')
        
        from app.services.exchange_info_service import ExchangeInfoService
        service = ExchangeInfoService()
        
        # 同时查询两个数据源
        local_result = service.query_from_local_constants(country_code=country_code)
        remote_result = service.query_from_remote_api(country_code=country_code)
        
        comparison_data = {
            "local_constants": {
                "success": local_result['success'],
                "count": len(local_result['data']) if local_result['success'] else 0,
                "data": local_result['data'] if local_result['success'] else [],
                "error": local_result.get('error')
            },
            "remote_api": {
                "success": remote_result['success'],
                "count": len(remote_result['data']) if remote_result['success'] else 0,
                "data": remote_result['data'] if remote_result['success'] else [],
                "error": remote_result.get('error')
            }
        }
        
        return create_success_response(
            data=comparison_data,
            message="交易所信息数据源对比完成"
        )
        
    except Exception as e:
        logger.error(f"数据源对比异常: {e}")
        return create_error_response(500, "对比失败", str(e))


@exchange_info_bp.route('/trading-hours', methods=['GET'])
def get_trading_hours():
    """获取交易时间信息"""
    try:
        exchange_code = request.args.get('exchange_code', '').upper()
        
        from constants.exchanges import TradingHours, ChineseExchanges
        
        if exchange_code:
            # 获取指定交易所的交易时间
            exchanges = ChineseExchanges.get_exchanges_by_code()
            if exchange_code not in exchanges:
                return create_error_response(404, f"未找到交易所: {exchange_code}")
            
            exchange = exchanges[exchange_code]
            trading_info = {
                'exchange_code': exchange.exchange_code,
                'exchange_name': exchange.exchange_name,
                'local_open': exchange.local_open,
                'local_close': exchange.local_close,
                'beijing_open': exchange.beijing_open,
                'beijing_close': exchange.beijing_close,
                'timezone': exchange.timezone
            }
        else:
            # 获取通用交易时间信息
            trading_info = {
                'morning_session': {
                    'open': TradingHours.A_STOCK_MORNING_OPEN,
                    'close': TradingHours.A_STOCK_MORNING_CLOSE
                },
                'afternoon_session': {
                    'open': TradingHours.A_STOCK_AFTERNOON_OPEN,
                    'close': TradingHours.A_STOCK_AFTERNOON_CLOSE
                },
                'call_auction': {
                    'open': TradingHours.CALL_AUCTION_OPEN,
                    'close': TradingHours.CALL_AUCTION_CLOSE
                },
                'closing_call_auction': {
                    'open': TradingHours.CLOSING_CALL_AUCTION_OPEN,
                    'close': TradingHours.CLOSING_CALL_AUCTION_CLOSE
                }
            }
        
        return create_success_response(
            data=trading_info,
            message="交易时间信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"交易时间查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))


@exchange_info_bp.route('/market-segments', methods=['GET'])
def get_market_segments():
    """获取市场板块信息"""
    try:
        from constants.exchanges import MarketSegments
        
        segments = []
        for segment in MarketSegments:
            segments.append({
                'code': segment.name,
                'name': segment.value,
                'description': f"中国A股{segment.value}市场"
            })
        
        return create_success_response(
            data=segments,
            message="市场板块信息查询成功"
        )
        
    except Exception as e:
        logger.error(f"市场板块查询异常: {e}")
        return create_error_response(500, "查询失败", str(e))