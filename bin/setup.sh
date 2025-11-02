#!/usr/bin/env bash
#
# 项目初始化脚本 - 自动设置虚拟环境和依赖
# 兼容: Linux, macOS
#

set -e  # 遇到错误立即退出

# 获取脚本所在目录的父目录（项目根目录）
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_ROOT"

# 颜色定义
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  股票数据查询服务 - 环境设置  ${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# 1. 检查Python版本
echo -e "${BLUE}[1/5] 检查Python版本...${NC}"
if command -v python3 >/dev/null 2>&1; then
    PYTHON_CMD="python3"
    PIP_CMD="pip3"
elif command -v python >/dev/null 2>&1; then
    PYTHON_CMD="python"
    PIP_CMD="pip"
else
    echo -e "${RED}❌ 错误: 未找到Python，请先安装Python 3.9+${NC}"
    exit 1
fi

PYTHON_VERSION=$($PYTHON_CMD --version 2>&1 | awk '{print $2}')
echo -e "${GREEN}   ✅ 找到Python版本: $PYTHON_VERSION${NC}"
echo ""

# 2. 创建虚拟环境
echo -e "${BLUE}[2/5] 创建虚拟环境...${NC}"
if [ -d ".venv" ]; then
    echo -e "${YELLOW}   ⚠️  虚拟环境已存在，跳过创建${NC}"
else
    echo "   正在创建虚拟环境 .venv ..."
    $PYTHON_CMD -m venv .venv
    echo -e "${GREEN}   ✅ 虚拟环境创建成功${NC}"
fi
echo ""

# 3. 激活虚拟环境
echo -e "${BLUE}[3/5] 激活虚拟环境...${NC}"
source .venv/bin/activate
echo -e "${GREEN}   ✅ 虚拟环境已激活${NC}"
echo ""

# 5. 安装依赖
echo -e "${BLUE}[5/5] 安装项目依赖...${NC}"
if [ -f "requirements.txt" ]; then
    echo "   正在安装依赖包..."
    pip install -r requirements.txt -q
    echo -e "${GREEN}   ✅ 依赖安装完成${NC}"
else
    echo -e "${RED}   ❌ 未找到requirements.txt文件${NC}"
    exit 1
fi
echo ""

# 6. 创建必要的目录
echo -e "${BLUE}创建必要的目录...${NC}"
mkdir -p logs
echo -e "${GREEN}✅ logs目录已创建${NC}"
echo ""

# 7. 检查环境变量配置
echo -e "${BLUE}检查环境变量配置...${NC}"
if [ ! -f ".env" ]; then
    echo -e "${YELLOW}⚠️  未找到.env文件${NC}"
    echo ""
    echo "请执行以下步骤配置环境变量："
    echo "  1. 复制配置模板:"
    echo -e "     ${BLUE}cp .env.example .env${NC}"
    echo ""
    echo "  2. 生成安全的SECRET_KEY:"
    echo -e "     ${BLUE}python -c \"import secrets; print(secrets.token_hex(32))\"${NC}"
    echo ""
    echo "  3. 编辑.env文件，设置必要的配置:"
    echo "     - SECRET_KEY (必须修改)"
    echo "     - DB_HOST, DB_PORT, DB_NAME"
    echo "     - DB_USER, DB_PASSWORD"
    echo ""
else
    echo -e "${GREEN}✅ .env文件已存在${NC}"
fi
echo ""

# 完成
echo -e "${GREEN}================================${NC}"
echo -e "${GREEN}  ✅ 环境设置完成！${NC}"
echo -e "${GREEN}================================${NC}"
echo ""
echo "接下来的步骤："
echo ""
echo "1. ${YELLOW}配置环境变量${NC}（如果还没配置）:"
echo "   cp .env.example .env"
echo "   编辑 .env 文件"
echo ""
echo "2. ${YELLOW}启动服务${NC}:"
echo "   ./bin/start.sh"
echo ""
echo "3. ${YELLOW}查看服务状态${NC}:"
echo "   ./bin/health.sh"
echo ""
echo "4. ${YELLOW}停止服务${NC}:"
echo "   ./bin/stop.sh"
echo ""
echo -e "${BLUE}提示: 下次使用前，激活虚拟环境:${NC}"
echo -e "   ${GREEN}source .venv/bin/activate${NC}"
echo ""

