# 环境初始化

## 1. 创建虚拟环境

```bash
# 创建虚拟环境
python3 -m venv .venv

# 激活虚拟环境
source .venv/bin/activate
```

## 2. 安装依赖

```bash
pip install -r requirements.txt
```

## 3. 后台启动应用

```bash
# 后台启动Flask服务
nohup python start_flask_app.py > logs/flask.log 2>&1 &

# 查看日志
tail -f logs/flask_server.log
```
