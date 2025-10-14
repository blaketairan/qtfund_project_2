"""
API响应工具模块

提供统一的API响应格式处理
"""

from flask import jsonify
from typing import Any, Dict, Optional, Union
from datetime import datetime


def create_success_response(data: Any = None, 
                          message: str = "success", 
                          code: int = 200,
                          total: Optional[int] = None,
                          **kwargs) -> tuple:
    """
    创建成功响应
    
    Args:
        data: 响应数据
        message: 响应消息
        code: 状态码
        total: 总记录数（分页时使用）
        **kwargs: 其他参数
        
    Returns:
        tuple: (响应数据, HTTP状态码)
    """
    response_data = {
        "code": code,
        "message": message,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data": data
    }
    
    # 添加总记录数
    if total is not None:
        response_data["total"] = total
    
    # 添加其他参数
    response_data.update(kwargs)
    
    return jsonify(response_data), code


def create_error_response(code: int = 400, 
                        message: str = "error", 
                        detail: Optional[str] = None,
                        **kwargs) -> tuple:
    """
    创建错误响应
    
    Args:
        code: 错误状态码
        message: 错误消息
        detail: 错误详情
        **kwargs: 其他参数
        
    Returns:
        tuple: (错误响应数据, HTTP状态码)
    """
    response_data = {
        "code": code,
        "message": message,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "error": True
    }
    
    if detail:
        response_data["detail"] = detail
    
    # 添加其他参数
    response_data.update(kwargs)
    
    return jsonify(response_data), code


def create_data_response(data: Any,
                        total: Optional[int] = None,
                        page: Optional[int] = None,
                        limit: Optional[int] = None,
                        message: str = "查询成功") -> tuple:
    """
    创建数据查询响应（支持分页）
    
    Args:
        data: 数据列表
        total: 总记录数
        page: 当前页码
        limit: 每页记录数
        message: 响应消息
        
    Returns:
        tuple: (响应数据, HTTP状态码)
    """
    response_data = {
        "code": 200,
        "message": message,
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data": data
    }
    
    # 分页信息
    if total is not None:
        response_data["total"] = total
    if page is not None:
        response_data["page"] = page
    if limit is not None:
        response_data["limit"] = limit
        
    # 如果是列表数据，添加数量信息
    if isinstance(data, list):
        response_data["count"] = len(data)
    
    return jsonify(response_data), 200


def create_stock_data_response(data: list,
                             symbol: str,
                             source: str,
                             date_range: Optional[Dict] = None,
                             total: Optional[int] = None) -> tuple:
    """
    创建股票数据专用响应
    
    Args:
        data: 股票数据列表
        symbol: 股票代码
        source: 数据源 (database/remote)
        date_range: 日期范围信息
        total: 总记录数
        
    Returns:
        tuple: (响应数据, HTTP状态码)
    """
    response_data = {
        "code": 200,
        "message": "查询成功",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "data": data,
        "symbol": symbol,
        "source": source,
        "count": len(data)
    }
    
    if total is not None:
        response_data["total"] = total
        
    if date_range:
        response_data["date_range"] = date_range
    
    return jsonify(response_data), 200


def create_sync_task_response(task_name: str,
                            status: str,
                            result: Dict[str, Any],
                            duration: Optional[float] = None) -> tuple:
    """
    创建同步任务响应
    
    Args:
        task_name: 任务名称
        status: 任务状态 (success/failed/running)
        result: 任务结果
        duration: 执行时长（秒）
        
    Returns:
        tuple: (响应数据, HTTP状态码)
    """
    response_data = {
        "code": 200 if status == "success" else 500,
        "message": f"同步任务{status}",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "task": {
            "name": task_name,
            "status": status,
            "result": result
        }
    }
    
    if duration is not None:
        response_data["task"]["duration"] = f"{duration:.2f}s"
    
    status_code = 200 if status == "success" else 500
    return jsonify(response_data), status_code


def format_stock_price_data(db_record) -> Dict[str, Any]:
    """
    格式化数据库股票数据记录
    
    Args:
        db_record: 数据库记录对象
        
    Returns:
        Dict: 格式化的股票数据
    """
    return {
        "trade_date": db_record.trade_date.strftime('%Y-%m-%d'),
        "symbol": str(db_record.symbol),
        "stock_name": str(db_record.stock_name),
        "open_price": float(db_record.open_price) if db_record.open_price is not None else None,
        "high_price": float(db_record.high_price) if db_record.high_price is not None else None,
        "low_price": float(db_record.low_price) if db_record.low_price is not None else None,
        "close_price": float(db_record.close_price),
        "volume": int(db_record.volume),
        "turnover": float(db_record.turnover),
        "price_change": float(db_record.price_change) if db_record.price_change is not None else None,
        "price_change_pct": float(db_record.price_change_pct) if db_record.price_change_pct is not None else None,
        "premium_rate": float(db_record.premium_rate) if db_record.premium_rate is not None else None,
        "market_code": str(db_record.market_code)
    }


def format_api_stock_data(api_data: Dict[str, Any], symbol: str, stock_name: str = "") -> Dict[str, Any]:
    """
    格式化API股票数据
    
    Args:
        api_data: API返回的原始数据
        symbol: 股票代码
        stock_name: 股票名称
        
    Returns:
        Dict: 格式化的股票数据
    """
    market_code = symbol.split('.')[0] if '.' in symbol else 'UNKNOWN'
    
    return {
        "trade_date": api_data.get('date', ''),
        "symbol": symbol,
        "stock_name": stock_name or symbol,
        "open_price": float(api_data.get('open', 0)),
        "high_price": float(api_data.get('high', 0)),
        "low_price": float(api_data.get('low', 0)),
        "close_price": float(api_data.get('close', 0)),
        "volume": int(api_data.get('volume', 0)),
        "turnover": float(api_data.get('volume', 0)) * float(api_data.get('close', 0)),
        "price_change": None,  # API可能不提供
        "price_change_pct": None,  # API可能不提供
        "premium_rate": None,
        "market_code": market_code
    }


def validate_date_range(start_date: Optional[str], end_date: Optional[str]) -> Dict[str, Optional[str]]:
    """
    验证日期范围参数
    
    Args:
        start_date: 开始日期字符串
        end_date: 结束日期字符串
        
    Returns:
        Dict: 验证后的日期范围
        
    Raises:
        ValueError: 日期格式错误
    """
    import re
    from datetime import datetime
    
    date_pattern = r'^\d{4}-\d{2}-\d{2}$'
    
    result: Dict[str, Optional[str]] = {"start_date": None, "end_date": None}
    
    if start_date:
        if not re.match(date_pattern, start_date):
            raise ValueError("开始日期格式错误，应为: YYYY-MM-DD")
        try:
            datetime.strptime(start_date, '%Y-%m-%d')
            result["start_date"] = start_date
        except ValueError:
            raise ValueError("开始日期无效")
    
    if end_date:
        if not re.match(date_pattern, end_date):
            raise ValueError("结束日期格式错误，应为: YYYY-MM-DD")
        try:
            datetime.strptime(end_date, '%Y-%m-%d')
            result["end_date"] = end_date
        except ValueError:
            raise ValueError("结束日期无效")
    
    # 检查日期范围逻辑
    if result["start_date"] and result["end_date"]:
        if result["start_date"] > result["end_date"]:
            raise ValueError("开始日期不能晚于结束日期")
    
    return result


def validate_symbol_format(symbol: str) -> str:
    """
    验证股票代码格式
    
    Args:
        symbol: 股票代码
        
    Returns:
        str: 验证后的股票代码
        
    Raises:
        ValueError: 格式错误
    """
    if not symbol or '.' not in symbol:
        raise ValueError('股票代码格式错误，应为: SH.600519')
    
    parts = symbol.split('.')
    if len(parts) != 2:
        raise ValueError('股票代码格式错误，应为: 市场.代码')
    
    market, code = parts
    if market.upper() not in ['SH', 'SZ', 'BJ']:
        raise ValueError('不支持的市场代码，仅支持: SH, SZ, BJ')
    
    if not code.isdigit() or len(code) != 6:
        raise ValueError('股票代码必须为6位数字')
    
    return f"{market.upper()}.{code}"