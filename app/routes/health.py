"""
健康检查路由模块
"""

from flask import Blueprint
from app.utils.responses import create_success_response, create_error_response
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# 创建蓝图
health_bp = Blueprint('health', __name__)


@health_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    try:
        # 测试数据库连接
        from database.connection import db_manager
        
        db_status = "unknown"
        try:
            if db_manager.test_connection():
                db_status = "connected"
            else:
                db_status = "disconnected"
        except Exception as e:
            db_status = f"error: {str(e)}"
        
        # 健康状态
        is_healthy = "connected" in db_status
        status = "healthy" if is_healthy else "unhealthy"
        
        health_info = {
            "status": status,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "database": db_status,
            "version": "2.0.0 (Flask版)",
            "api_server": "running"
        }
        
        if is_healthy:
            return create_success_response(
                data=health_info, 
                message="系统运行正常"
            )
        else:
            return create_error_response(
                code=503,
                message="系统异常",
                detail="数据库连接失败",
                data=health_info
            )
            
    except Exception as e:
        logger.error(f"健康检查失败: {e}")
        return create_error_response(
            code=500,
            message="健康检查失败",
            detail=str(e)
        )


@health_bp.route('/version', methods=['GET'])
def version_info():
    """版本信息接口"""
    version_data = {
        "name": "股票数据API服务",
        "version": "2.0.0",
        "framework": "Flask",
        "database": "TimescaleDB",
        "python_version": "3.9+",
        "build_date": "2025-10-12",
        "features": [
            "股票行情数据查询 (TimescaleDB + 远程API)",
            "股票信息查询 (本地JSON + 远程API)", 
            "交易所信息查询 (本地常量 + 远程API)",
            "数据同步任务 (交易所、股票清单、行情数据)"
        ]
    }
    
    return create_success_response(
        data=version_data,
        message="版本信息查询成功"
    )