#!/usr/bin/env bash
#
# 健康检查脚本
# 检查股票数据同步服务的运行状态
# 兼容: Linux, macOS
#

set -e  # 遇到错误立即退出

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

echo -e "${BLUE}🔍 股票数据同步服务 - 健康检查${NC}"
echo "=================================================="
echo ""

# 1. 检查进程是否运行
echo "📍 检查进程状态..."
PID_FILE="logs/sync_service.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    # 使用kill -0检查进程是否存在（兼容Linux和macOS）
    if kill -0 $PID 2>/dev/null; then
        echo -e "   ${GREEN}✅ 进程运行中 (PID: $PID)${NC}"
    else
        echo -e "   ${RED}❌ 进程未运行 (PID文件存在但进程不存在)${NC}"
        echo "   建议: 删除PID文件并重新启动"
        echo "   rm logs/sync_service.pid && ./bin/start.sh"
        exit 1
    fi
else
    echo -e "   ${YELLOW}⚠️  未找到PID文件${NC}"
fi

echo ""

# 2. 检查端口监听（兼容Linux和macOS）
echo "📍 检查端口监听..."
PORT_CHECK=false
if command -v lsof >/dev/null 2>&1; then
    # 使用lsof（macOS和大多数Linux）
    if lsof -Pi :7777 -sTCP:LISTEN -t >/dev/null 2>&1; then
        PORT_CHECK=true
    fi
elif command -v netstat >/dev/null 2>&1; then
    # 使用netstat（Linux fallback）
    if netstat -tuln 2>/dev/null | grep -q ':7777 '; then
        PORT_CHECK=true
    fi
elif command -v ss >/dev/null 2>&1; then
    # 使用ss（现代Linux）
    if ss -tuln 2>/dev/null | grep -q ':7777 '; then
        PORT_CHECK=true
    fi
fi

if [ "$PORT_CHECK" = true ]; then
    echo -e "   ${GREEN}✅ 端口 7777 正在监听${NC}"
else
    echo -e "   ${RED}❌ 端口 7777 未监听${NC}"
    exit 1
fi

echo ""

# 3. 健康检查API
echo "📍 调用健康检查API..."
RESPONSE=$(curl -s -w "\n%{http_code}" http://localhost:7777/api/health 2>/dev/null)
HTTP_CODE=$(echo "$RESPONSE" | tail -n1)
BODY=$(echo "$RESPONSE" | head -n-1)

if [ "$HTTP_CODE" = "200" ]; then
    echo -e "   ${GREEN}✅ API响应正常 (HTTP $HTTP_CODE)${NC}"
    
    # 解析JSON（如果有jq命令）
    if command -v jq &> /dev/null; then
        echo ""
        echo "📊 服务详情:"
        echo "$BODY" | jq -r '
            "   版本: \(.data.version // "未知")",
            "   状态: \(.data.status // "未知")",
            "   数据库: \(.data.database // "未知")",
            "   时间: \(.timestamp // "未知")"
        '
    else
        echo ""
        echo "📊 API响应内容:"
        echo "$BODY" | python3 -m json.tool 2>/dev/null || echo "$BODY"
    fi
else
    echo -e "   ${RED}❌ API响应异常 (HTTP $HTTP_CODE)${NC}"
    if [ -n "$BODY" ]; then
        echo "   响应内容: $BODY"
    fi
    exit 1
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✅ 服务运行正常！${NC}"
echo ""
echo "🌐 服务地址:"
echo "   主页: http://localhost:7777"
echo "   健康检查: http://localhost:7777/api/health"
echo "   同步任务: http://localhost:7777/api/sync/*"
echo ""
echo "📝 查看日志:"
echo "   tail -f logs/sync_service.log"
echo "   tail -f logs/flask_server.log"
echo ""

