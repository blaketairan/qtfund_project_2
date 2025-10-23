#!/usr/bin/env bash
#
# 停止股票数据同步服务
# 兼容: Linux, macOS
#

set +e  # 允许命令失败，因为我们要尝试多种停止方式

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}🛑 停止股票数据同步服务...${NC}"
echo ""

# 方法1: 通过PID文件停止
PID_FILE="logs/sync_service.pid"

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    echo "📍 找到PID文件 (PID: $PID)"
    
    # 使用kill -0检查进程是否存在（兼容Linux和macOS）
    if kill -0 $PID 2>/dev/null; then
        echo "   正在停止进程..."
        kill $PID 2>/dev/null
        
        # 等待进程结束
        for i in $(seq 1 10); do
            if ! kill -0 $PID 2>/dev/null; then
                echo -e "   ${GREEN}✅ 进程已停止${NC}"
                rm -f "$PID_FILE"
                break
            fi
            sleep 1
        done
        
        # 如果进程还在运行，强制停止
        if kill -0 $PID 2>/dev/null; then
            echo "   进程未响应，强制停止..."
            kill -9 $PID 2>/dev/null
            sleep 1
            if ! kill -0 $PID 2>/dev/null; then
                echo -e "   ${GREEN}✅ 进程已强制停止${NC}"
                rm -f "$PID_FILE"
            else
                echo -e "   ${RED}❌ 无法停止进程${NC}"
                exit 1
            fi
        fi
    else
        echo -e "   ${YELLOW}⚠️  进程不存在，清理PID文件${NC}"
        rm -f "$PID_FILE"
    fi
else
    echo -e "${YELLOW}⚠️  未找到PID文件${NC}"
fi

echo ""

# 方法2: 通过端口查找并停止（兼容Linux和macOS）
echo "📍 检查端口 7777..."
PORT_PID=""

# 尝试使用lsof
if command -v lsof >/dev/null 2>&1; then
    PORT_PID=$(lsof -ti:7777 2>/dev/null || true)
# 如果没有lsof，尝试使用fuser（Linux）
elif command -v fuser >/dev/null 2>&1; then
    PORT_PID=$(fuser 7777/tcp 2>/dev/null | tr -d ' ' || true)
# 如果没有fuser，尝试使用ss（现代Linux）
elif command -v ss >/dev/null 2>&1; then
    PORT_PID=$(ss -tlnp 2>/dev/null | grep ':7777 ' | grep -oP 'pid=\K[0-9]+' || true)
fi

if [ -n "$PORT_PID" ]; then
    echo "   发现占用端口的进程 (PID: $PORT_PID)"
    echo "   正在停止..."
    
    for pid in $PORT_PID; do
        kill $pid 2>/dev/null || true
    done
    sleep 2
    
    # 检查是否停止
    PORT_CHECK=false
    if command -v lsof >/dev/null 2>&1; then
        lsof -Pi :7777 -sTCP:LISTEN -t >/dev/null 2>&1 && PORT_CHECK=true
    elif command -v netstat >/dev/null 2>&1; then
        netstat -tuln 2>/dev/null | grep -q ':7777 ' && PORT_CHECK=true
    fi
    
    if [ "$PORT_CHECK" = true ]; then
        echo "   进程未响应，强制停止..."
        for pid in $PORT_PID; do
            kill -9 $pid 2>/dev/null || true
        done
        sleep 1
    fi
    
    # 再次检查
    PORT_CHECK=false
    if command -v lsof >/dev/null 2>&1; then
        lsof -Pi :7777 -sTCP:LISTEN -t >/dev/null 2>&1 && PORT_CHECK=true
    fi
    
    if [ "$PORT_CHECK" = false ]; then
        echo -e "   ${GREEN}✅ 端口已释放${NC}"
    else
        echo -e "   ${RED}❌ 端口仍被占用${NC}"
    fi
else
    echo "   端口未被占用"
fi

echo ""

# 方法3: 通过进程名查找并停止
echo "📍 检查相关Python进程..."
PYTHON_PIDS=""

# 尝试使用pgrep（macOS和大多数Linux都有）
if command -v pgrep >/dev/null 2>&1; then
    PYTHON_PIDS=$(pgrep -f "start_flask_app.py" 2>/dev/null || true)
# 如果没有pgrep，使用ps和grep（兼容性更好）
else
    PYTHON_PIDS=$(ps aux | grep "[s]tart_flask_app.py" | awk '{print $2}' || true)
fi

if [ -n "$PYTHON_PIDS" ]; then
    echo "   发现相关进程:"
    for pid in $PYTHON_PIDS; do
        if kill -0 $pid 2>/dev/null; then
            echo "   - PID: $pid"
        fi
    done
    
    echo "   正在停止所有相关进程..."
    for pid in $PYTHON_PIDS; do
        kill $pid 2>/dev/null || true
    done
    sleep 2
    
    # 检查是否还有进程
    REMAINING=""
    if command -v pgrep >/dev/null 2>&1; then
        REMAINING=$(pgrep -f "start_flask_app.py" 2>/dev/null || true)
    else
        REMAINING=$(ps aux | grep "[s]tart_flask_app.py" | awk '{print $2}' || true)
    fi
    
    if [ -n "$REMAINING" ]; then
        echo "   强制停止残留进程..."
        if command -v pkill >/dev/null 2>&1; then
            pkill -9 -f "start_flask_app.py" 2>/dev/null || true
        else
            for pid in $REMAINING; do
                kill -9 $pid 2>/dev/null || true
            done
        fi
    fi
    
    echo -e "   ${GREEN}✅ 所有进程已清理${NC}"
else
    echo "   未发现相关进程"
fi

echo ""
echo "=================================================="
echo -e "${GREEN}✅ 服务已完全停止${NC}"
echo ""
echo "🚀 重新启动服务:"
echo "   ./bin/start.sh"
echo ""

