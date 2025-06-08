# 验证码自动识别解决方案

基于Docker和Selenium Grid的分布式验证码自动识别解决方案，支持高并发处理和智能任务调度。

## 🌟 功能特性

- 🚀 **Docker容器化部署** - 一键部署，环境隔离
- 🕷️ **Selenium Grid分布式** - 支持多节点并发处理
- 🤖 **AI驱动识别** - 集成火山引擎AI进行验证码识别
- 📊 **任务队列管理** - Redis队列支持异步任务处理
- 🔄 **自动重试机制** - 智能重试和错误恢复
- 📈 **实时监控** - 完整的日志记录和状态监控
- ⚙️ **灵活配置** - 支持环境变量和配置文件
- 🔌 **RESTful API** - 提供HTTP接口便于集成

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Server    │    │  Task Scheduler │    │   Redis Queue   │
│   (Flask)       │◄──►│   (Python)      │◄──►│   (Message)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Selenium Hub    │    │  Chrome Node 1  │    │  Chrome Node 2  │
│   (Grid)        │◄──►│   (Browser)     │    │   (Browser)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 环境要求

- **Python**: 3.9+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **内存**: 建议4GB+
- **磁盘**: 建议2GB+可用空间

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/captcha-solver.git
cd captcha-solver
```

### 2. 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑配置文件
vim .env
```

### 3. 启动服务

```bash
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 4. 验证部署

```bash
# 测试WebDriver连接
docker-compose exec app python test_webdriver.py

# 访问Selenium Grid控制台
open http://localhost:4444

# 测试API接口
curl http://localhost:8000/health
```

## 🔧 本地开发环境

### 使用Conda（推荐）

```bash
# 创建conda环境
conda env create -f environment.yml

# 激活环境
conda activate captcha-solver

# 安装依赖
pip install -r requirements.txt
```

### 使用pip

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或 venv\Scripts\activate  # Windows

# 安装依赖
pip install -r requirements.txt
```

## 📖 API文档

### 提交任务

```bash
POST /api/submit
Content-Type: application/json

{
  "url": "https://example.com/captcha-page",
  "config": {
    "timeout": 30,
    "retry_count": 3
  }
}
```

**响应示例：**
```json
{
  "task_id": "task_123456",
  "status": "submitted",
  "message": "Task submitted successfully"
}
```

### 查询任务状态

```bash
GET /api/status/{task_id}
```

**响应示例：**
```json
{
  "task_id": "task_123456",
  "status": "completed",
  "result": {
    "captcha_code": "ABC123",
    "success": true,
    "screenshot_path": "/screenshots/task_123456.png"
  },
  "created_at": "2024-01-01T12:00:00Z",
  "completed_at": "2024-01-01T12:00:30Z"
}
```

### 健康检查

```bash
GET /health
```

## ⚙️ 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 |
|--------|------|--------|
| `SELENIUM_HUB_URL` | Selenium Hub地址 | `http://selenium-hub:4444` |
| `REDIS_URL` | Redis连接地址 | `redis://redis:6379/0` |
| `AI_API_KEY` | 火山引擎API密钥 | - |
| `AI_API_SECRET` | 火山引擎API密钥 | - |
| `LOG_LEVEL` | 日志级别 | `INFO` |
| `MAX_RETRY_COUNT` | 最大重试次数 | `3` |
| `TASK_TIMEOUT` | 任务超时时间(秒) | `300` |

### 配置文件

项目支持通过 `config.json` 文件进行详细配置：

```json
{
  "browser": {
    "headless": true,
    "window_size": [1920, 1080],
    "user_agent": "custom-user-agent"
  },
  "ai": {
    "model": "doubao-vision-pro",
    "max_tokens": 1000,
    "temperature": 0.1
  },
  "retry": {
    "max_attempts": 3,
    "backoff_factor": 2,
    "max_delay": 60
  }
}
```

## 🔍 监控和调试

### 查看服务状态

```bash
# 查看所有容器状态
docker-compose ps

# 查看特定服务日志
docker-compose logs app
docker-compose logs selenium-hub
docker-compose logs chrome-node

# 实时查看日志
docker-compose logs -f app
```

### Selenium Grid控制台

访问 http://localhost:4444 查看：
- 节点状态
- 活跃会话
- 队列情况

### Redis监控

```bash
# 连接Redis查看队列
docker-compose exec redis redis-cli

# 查看队列长度
LLEN task_queue

# 查看队列内容
LRANGE task_queue 0 -1
```

## 📈 性能优化

### 扩展Chrome节点

```bash
# 动态增加Chrome节点
docker-compose up -d --scale chrome-node=5

# 查看扩展后的节点
docker-compose ps chrome-node
```

### 资源限制

在 `docker-compose.yml` 中调整资源限制：

```yaml
services:
  chrome-node:
    deploy:
      resources:
        limits:
          memory: 2G
          cpus: '1.0'
        reservations:
          memory: 1G
          cpus: '0.5'
```

## 🛠️ 故障排除

### 常见问题

1. **Chrome节点无法连接到Hub**
   ```bash
   # 检查网络连接
   docker-compose exec chrome-node ping selenium-hub
   
   # 重启服务
   docker-compose restart selenium-hub chrome-node
   ```

2. **验证码识别失败**
   ```bash
   # 检查AI配置
   docker-compose exec app python -c "from volcengine_ai import VolcEngineAI; print('AI配置正常')"
   
   # 查看截图文件
   ls -la screenshots/
   ```

3. **任务队列堆积**
   ```bash
   # 清空队列
   docker-compose exec redis redis-cli FLUSHDB
   
   # 增加处理节点
   docker-compose up -d --scale chrome-node=3
   ```

### 日志分析

```bash
# 查看错误日志
docker-compose logs app | grep ERROR

# 查看性能指标
docker stats

# 导出日志
docker-compose logs app > app.log
```

## 🧪 测试

### 运行测试套件

```bash
# 单元测试
python -m pytest tests/

# 集成测试
python test_webdriver.py

# API测试
curl -X POST http://localhost:8000/api/submit \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

### 性能测试

```bash
# 使用ab进行压力测试
ab -n 100 -c 10 http://localhost:8000/health

# 监控资源使用
docker stats --no-stream
```

## 📦 部署到生产环境

### 使用Docker Swarm

```bash
# 初始化Swarm
docker swarm init

# 部署服务栈
docker stack deploy -c docker-compose.yml captcha-solver

# 查看服务状态
docker service ls
```

### 使用Kubernetes

```bash
# 生成Kubernetes配置
kompose convert

# 部署到集群
kubectl apply -f .

# 查看Pod状态
kubectl get pods
```

## 🤝 贡献指南

1. Fork 项目
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🙏 致谢

- [Selenium](https://selenium.dev/) - Web自动化框架
- [Docker](https://docker.com/) - 容器化平台
- [火山引擎](https://volcengine.com/) - AI服务提供商
- [Redis](https://redis.io/) - 内存数据库
- [Flask](https://flask.palletsprojects.com/) - Web框架

## 📞 支持

如果您遇到问题或有建议，请：

- 提交 [Issue](https://github.com/your-username/captcha-solver/issues)
- 发送邮件至 your-email@example.com
- 查看 [Wiki](https://github.com/your-username/captcha-solver/wiki) 文档

---

**注意**: 请确保遵守相关网站的使用条款和法律法规，本工具仅用于学习和研究目的。
```
        