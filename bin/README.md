# 服务管理脚本

这个目录包含了管理股票数据同步服务的便捷脚本。

## 📋 脚本列表

| 脚本 | 功能 | 说明 |
|------|------|------|
| `start.sh` | 启动服务 | 后台启动同步服务（端口7777） |
| `health.sh` | 健康检查 | 检查服务运行状态和健康状况 |
| `stop.sh` | 停止服务 | 优雅停止服务，清理进程 |

## 🚀 使用方法

### 启动服务
```bash
./bin/start.sh
```

功能：
- ✅ 自动检查端口占用
- ✅ 激活虚拟环境（如果存在）
- ✅ 检查依赖包
- ✅ 后台启动服务
- ✅ 保存PID到文件
- ✅ 显示服务信息和日志位置

### 健康检查
```bash
./bin/health.sh
```

检查内容：
- ✅ 进程是否运行
- ✅ 端口是否监听
- ✅ API健康检查
- ✅ 数据库连接状态
- ✅ 服务版本信息

### 停止服务
```bash
./bin/stop.sh
```

停止方式（多重保险）：
- 🛑 通过PID文件停止
- 🛑 通过端口查找并停止
- 🛑 通过进程名查找并停止
- 🛑 强制停止未响应的进程

## 📝 使用示例

### 完整流程
```bash
# 1. 启动服务
./bin/start.sh

# 2. 检查服务状态
./bin/health.sh

# 3. 查看实时日志（可选）
tail -f logs/sync_service.log

# 4. 停止服务
./bin/stop.sh
```

### 快速重启
```bash
./bin/stop.sh && ./bin/start.sh
```

### 定时健康检查
```bash
# 添加到crontab，每5分钟检查一次
*/5 * * * * cd /Users/terrell/qt/qtfund_project_2 && ./bin/health.sh >> logs/health_check.log 2>&1
```

## 📊 日志文件

启动后会生成以下日志文件：

| 文件 | 内容 |
|------|------|
| `logs/sync_service.pid` | 服务进程ID |
| `logs/sync_service.log` | 服务启动日志 |
| `logs/flask_server.log` | Flask详细日志 |

## 🔍 故障排查

### 服务无法启动
```bash
# 检查端口占用
lsof -i :7777

# 查看启动日志
cat logs/sync_service.log

# 检查依赖
pip install -r requirements.txt
```

### 服务无法停止
```bash
# 查找所有相关进程
ps aux | grep start_flask_app

# 手动强制停止
kill -9 <PID>

# 释放端口
lsof -ti:7777 | xargs kill -9
```

### 健康检查失败
```bash
# 检查进程
ps aux | grep start_flask_app

# 检查端口
lsof -i :7777

# 手动调用API
curl http://localhost:7777/api/health
```

## ⚠️ 注意事项

1. **工作目录**: 脚本会自动切换到项目根目录，可以从任意位置调用
2. **虚拟环境**: 如果存在 `.venv` 目录，会自动激活
3. **PID文件**: 服务停止后会自动清理PID文件
4. **多重保险**: stop.sh 会尝试多种方式停止服务，确保完全清理

## 🎯 高级用法

### 查看服务信息
```bash
# 查看PID
cat logs/sync_service.pid

# 查看进程详情
ps -p $(cat logs/sync_service.pid) -f

# 查看端口占用
lsof -i :7777
```

### 监控服务
```bash
# 实时监控日志
tail -f logs/sync_service.log

# 监控进程资源使用
top -pid $(cat logs/sync_service.pid)

# 监控端口连接
watch -n 1 'lsof -i :7777'
```

### 与systemd集成（可选）
如果要集成到systemd：
```bash
# 创建服务文件
sudo vim /etc/systemd/system/stock-sync.service

# 内容示例：
[Unit]
Description=Stock Data Sync Service
After=network.target

[Service]
Type=forking
User=terrell
WorkingDirectory=/Users/terrell/qt/qtfund_project_2
ExecStart=/Users/terrell/qt/qtfund_project_2/bin/start.sh
ExecStop=/Users/terrell/qt/qtfund_project_2/bin/stop.sh
Restart=on-failure

[Install]
WantedBy=multi-user.target

# 启用服务
sudo systemctl enable stock-sync
sudo systemctl start stock-sync
```

## 📞 支持

如有问题，请查看：
- 项目文档: `../README.md`
- 测试指南: `../TESTING_GUIDE.md`
- 拆分说明: `../PROJECT_SPLIT_GUIDE.md`

