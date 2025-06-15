# 分布式验证码系统部署指南

本文档详细介绍如何部署和管理分布式验证码识别系统。

## 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Gateway   │    │  Task Scheduler │    │  Monitoring     │
│   (Port 8080)   │    │   (Port 8000)   │    │  (Port 9090)    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Worker Node 1  │    │  Worker Node 2  │    │  Worker Node N  │
│   (Port 8001)   │    │   (Port 8002)   │    │   (Port 800N)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │
         ┌───────────────────────┼───────────────────────┐
         │                       │                       │
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Selenium Hub   │    │   Redis Cluster │    │  Chrome Nodes   │
│   (Port 4444)   │    │   (Port 6379)   │    │   (Scaled)      │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 核心组件

### 1. API Gateway (网关服务)
- **功能**: 统一入口，负载均衡，限流控制
- **端口**: 8080
- **特性**:
  - 请求路由和负载均衡
  - 速率限制和CORS支持
  - 健康检查和监控
  - 任务提交和状态查询

### 2. Task Scheduler (任务调度器)
- **功能**: 分布式任务调度和管理
- **端口**: 8000
- **特性**:
  - 任务分发和负载均衡
  - 工作节点管理和故障恢复
  - 任务超时处理
  - Prometheus指标导出

### 3. Worker Nodes (工作节点)
- **功能**: 执行验证码识别任务
- **端口**: 8001, 8002, ...
- **特性**:
  - 并发任务处理
  - 心跳监控
  - 浏览器驱动管理
  - 任务结果上报

### 4. Monitoring (监控服务)
- **功能**: 系统监控和可视化
- **端口**: 9090
- **特性**:
  - 实时性能监控
  - 系统资源统计
  - Web仪表板
  - Prometheus指标收集

### 5. Redis Cluster (缓存集群)
- **功能**: 任务队列和结果存储
- **端口**: 6379
- **特性**:
  - 高可用性配置
  - 主从复制
  - 哨兵模式

### 6. Selenium Grid (浏览器集群)
- **功能**: 分布式浏览器管理
- **端口**: 4444
- **特性**:
  - 多浏览器节点
  - 会话管理
  - 负载均衡

## 快速开始

### 1. 环境要求

- Docker >= 20.10
- Docker Compose >= 2.0
- 内存 >= 8GB
- CPU >= 4核
- 磁盘空间 >= 20GB

### 2. 克隆项目

```bash
git clone <repository-url>
cd zyD
```

### 3. 配置系统

```bash
# 复制配置文件
cp config/distributed.example.json config/distributed.json

# 编辑配置文件（可选）
vim config/distributed.json
```

### 4. 部署系统

```bash
# 单机部署（默认2个工作节点）
./scripts/deploy-distributed.sh deploy

# 多机部署（指定工作节点数量）
./scripts/deploy-distributed.sh deploy -m multi -n 4

# 生产环境部署
./scripts/deploy-distributed.sh deploy -e prod -n 6
```

### 5. 验证部署

```bash
# 检查服务状态
./scripts/deploy-distributed.sh status

# 健康检查
./scripts/deploy-distributed.sh health

# 查看日志
./scripts/deploy-distributed.sh logs
```

## 配置说明

### 分布式配置文件 (config/distributed.json)

```json
{
  "redis": {
    "master": {
      "host": "redis-master",
      "port": 6379,
      "password": "",
      "db": 0
    },
    "sentinel": {
      "hosts": ["redis-sentinel:26379"],
      "master_name": "mymaster",
      "password": ""
    }
  },
  "selenium": {
    "hub_url": "http://selenium-hub:4444",
    "max_sessions": 10,
    "session_timeout": 300
  },
  "worker": {
    "max_workers_per_node": 4,
    "task_timeout": 120,
    "heartbeat_interval": 30,
    "max_retry_attempts": 3
  },
  "scheduler": {
    "task_distribution_interval": 5,
    "worker_health_check_interval": 60,
    "cleanup_interval": 300
  },
  "gateway": {
    "rate_limit": {
      "requests_per_minute": 100,
      "burst_size": 20
    },
    "load_balancer": {
      "algorithm": "round_robin",
      "health_check_interval": 30
    }
  }
}
```

### 环境变量

```bash
# 部署模式
DEPLOYMENT_MODE=single|multi

# 工作节点数量
WORKER_NODES_COUNT=2

# 环境类型
ENVIRONMENT=dev|prod

# 配置文件路径
DISTRIBUTED_CONFIG_PATH=config/distributed.json

# Redis配置
REDIS_URL=redis://redis-master:6379/0

# Selenium Hub配置
SELENIUM_HUB_URL=http://selenium-hub:4444
```

## 管理命令

### 服务管理

```bash
# 启动所有服务
./scripts/deploy-distributed.sh start

# 停止所有服务
./scripts/deploy-distributed.sh stop

# 重启所有服务
./scripts/deploy-distributed.sh restart

# 查看服务状态
./scripts/deploy-distributed.sh status
```

### 扩缩容

```bash
# 扩容工作节点到4个
./scripts/deploy-distributed.sh scale worker-node 4

# 扩容Chrome节点到6个
./scripts/deploy-distributed.sh scale chrome-node 6
```

### 日志管理

```bash
# 查看所有服务日志
./scripts/deploy-distributed.sh logs

# 查看特定服务日志
./scripts/deploy-distributed.sh logs api-gateway
./scripts/deploy-distributed.sh logs task-scheduler
./scripts/deploy-distributed.sh logs worker-node-1
./scripts/deploy-distributed.sh logs monitoring
```

### 监控和诊断

```bash
# 健康检查
./scripts/deploy-distributed.sh health

# 打开监控面板
./scripts/deploy-distributed.sh monitor

# 查看系统统计
curl http://localhost:8080/stats
```

## API 使用

### 任务提交

```bash
# 提交验证码识别任务
curl -X POST http://localhost:8080/submit_task \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/captcha",
    "timeout": 60,
    "retry_count": 3
  }'

# 响应示例
{
  "task_id": "task_123456789",
  "status": "pending",
  "estimated_wait_time": 30
}
```

### 任务状态查询

```bash
# 查询任务状态
curl http://localhost:8080/task_status/task_123456789

# 响应示例
{
  "task_id": "task_123456789",
  "status": "completed",
  "result": {
    "success": true,
    "captcha_text": "ABCD123",
    "confidence": 0.95
  },
  "created_at": "2024-01-01T10:00:00Z",
  "completed_at": "2024-01-01T10:01:30Z"
}
```

### 系统统计

```bash
# 获取系统统计信息
curl http://localhost:8080/stats

# 响应示例
{
  "active_workers": 4,
  "pending_tasks": 12,
  "completed_tasks": 1543,
  "failed_tasks": 23,
  "average_processing_time": 45.2,
  "system_load": {
    "cpu_usage": 65.4,
    "memory_usage": 78.2,
    "disk_usage": 45.1
  }
}
```

## 性能优化

### 1. 资源配置

```yaml
# docker-compose.yml 中的资源限制
services:
  worker-node:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

### 2. 并发设置

```json
{
  "worker": {
    "max_workers_per_node": 4,  // 根据CPU核心数调整
    "task_timeout": 120,        // 任务超时时间
    "batch_size": 10            // 批处理大小
  }
}
```

### 3. 缓存优化

```json
{
  "redis": {
    "max_connections": 100,
    "connection_pool_size": 20,
    "task_result_ttl": 3600     // 结果缓存时间
  }
}
```

## 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查Docker状态
docker ps -a

# 查看服务日志
docker-compose -f docker/docker-compose.distributed.yml logs <service-name>

# 检查端口占用
lsof -i :8080
lsof -i :6379
```

#### 2. 任务处理缓慢

```bash
# 检查工作节点状态
curl http://localhost:8080/workers

# 查看队列长度
curl http://localhost:8080/queue_status

# 扩容工作节点
./scripts/deploy-distributed.sh scale worker-node 6
```

#### 3. 内存不足

```bash
# 查看内存使用
docker stats

# 调整资源限制
vim docker/docker-compose.distributed.yml

# 重启服务
./scripts/deploy-distributed.sh restart
```

#### 4. Redis连接问题

```bash
# 检查Redis状态
docker exec -it redis-master redis-cli ping

# 查看Redis日志
docker logs redis-master

# 重启Redis服务
docker-compose -f docker/docker-compose.distributed.yml restart redis-master
```

### 日志分析

```bash
# 查看错误日志
docker-compose -f docker/docker-compose.distributed.yml logs | grep ERROR

# 查看特定时间段日志
docker-compose -f docker/docker-compose.distributed.yml logs --since="2024-01-01T10:00:00"

# 实时监控日志
docker-compose -f docker/docker-compose.distributed.yml logs -f
```

## 安全配置

### 1. 网络安全

```yaml
# 自定义网络配置
networks:
  distributed-network:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16
```

### 2. 访问控制

```json
{
  "security": {
    "api_key_required": true,
    "allowed_origins": ["https://yourdomain.com"],
    "rate_limiting": {
      "enabled": true,
      "requests_per_minute": 100
    }
  }
}
```

### 3. 数据加密

```bash
# 设置Redis密码
export REDIS_PASSWORD="your-secure-password"

# 启用TLS
export REDIS_TLS_ENABLED=true
```

## 备份和恢复

### 数据备份

```bash
# 备份Redis数据
docker exec redis-master redis-cli BGSAVE
docker cp redis-master:/data/dump.rdb ./backup/

# 备份配置文件
cp config/distributed.json ./backup/
```

### 数据恢复

```bash
# 恢复Redis数据
docker cp ./backup/dump.rdb redis-master:/data/
docker restart redis-master

# 恢复配置
cp ./backup/distributed.json config/
```

## 升级指南

### 滚动升级

```bash
# 1. 备份数据
./scripts/deploy-distributed.sh backup

# 2. 更新代码
git pull origin main

# 3. 重新构建镜像
docker-compose -f docker/docker-compose.distributed.yml build

# 4. 逐个重启服务
docker-compose -f docker/docker-compose.distributed.yml up -d --no-deps worker-node-1
docker-compose -f docker/docker-compose.distributed.yml up -d --no-deps worker-node-2

# 5. 验证升级
./scripts/deploy-distributed.sh health
```

## 监控和告警

### Prometheus指标

访问 `http://localhost:9090/metrics` 查看可用指标：

- `captcha_tasks_total`: 总任务数
- `captcha_tasks_pending`: 待处理任务数
- `captcha_tasks_processing`: 处理中任务数
- `captcha_tasks_completed`: 已完成任务数
- `captcha_tasks_failed`: 失败任务数
- `worker_nodes_active`: 活跃工作节点数
- `system_cpu_usage`: CPU使用率
- `system_memory_usage`: 内存使用率

### 告警配置

```yaml
# alertmanager.yml
groups:
- name: captcha-system
  rules:
  - alert: HighTaskFailureRate
    expr: rate(captcha_tasks_failed[5m]) > 0.1
    for: 2m
    annotations:
      summary: "验证码任务失败率过高"
      
  - alert: WorkerNodeDown
    expr: worker_nodes_active < 2
    for: 1m
    annotations:
      summary: "工作节点数量不足"
```

## 最佳实践

1. **资源规划**: 根据预期负载合理配置CPU、内存和存储
2. **监控告警**: 设置完善的监控和告警机制
3. **定期备份**: 定期备份重要数据和配置
4. **安全更新**: 及时更新依赖和安全补丁
5. **性能测试**: 定期进行性能测试和优化
6. **文档维护**: 保持部署和运维文档的更新

## 技术支持

如果遇到问题，请：

1. 查看本文档的故障排除部分
2. 检查系统日志和错误信息
3. 在项目仓库提交Issue
4. 联系技术支持团队

---

更多详细信息请参考项目文档和源代码注释。