# 🚀 分布式验证码系统快速开始

本指南将帮助您在5分钟内快速部署和运行分布式验证码识别系统。

## 📋 前置要求

确保您的系统已安装以下软件：

- ✅ Docker >= 20.10
- ✅ Docker Compose >= 2.0
- ✅ 内存 >= 8GB
- ✅ CPU >= 4核
- ✅ 磁盘空间 >= 20GB

## 🎯 一键部署

### 步骤 1: 克隆项目

```bash
git clone <repository-url>
cd zyD
```

### 步骤 2: 配置系统

```bash
# 复制配置文件
cp config/distributed.example.json config/distributed.json

# 可选：编辑配置文件
# vim config/distributed.json
```

### 步骤 3: 一键部署

```bash
# 方式1: 使用部署脚本（推荐）
./scripts/deploy-distributed.sh deploy

# 方式2: 使用Makefile
make -f Makefile.distributed deploy
```

### 步骤 4: 验证部署

```bash
# 检查服务状态
./scripts/deploy-distributed.sh status

# 或使用Makefile
make -f Makefile.distributed status
```

## 🎉 访问系统

部署完成后，您可以通过以下地址访问系统：

| 服务 | 地址 | 说明 |
|------|------|------|
| 🌐 API网关 | http://localhost:8080 | 主要API入口 |
| 📊 监控面板 | http://localhost:9090 | 系统监控和统计 |
| 🔧 Selenium Hub | http://localhost:4444 | 浏览器集群管理 |

## 🧪 快速测试

### 健康检查

```bash
# 使用脚本
./scripts/test-distributed.sh health

# 使用Makefile
make -f Makefile.distributed test-health

# 手动检查
curl http://localhost:8080/health
```

### 提交测试任务

```bash
# 提交验证码识别任务
curl -X POST http://localhost:8080/submit_task \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://httpbin.org/html",
    "timeout": 60
  }'

# 响应示例
{
  "task_id": "task_123456789",
  "status": "pending",
  "estimated_wait_time": 30
}
```

### 查询任务状态

```bash
# 替换为实际的task_id
curl http://localhost:8080/task_status/task_123456789

# 响应示例
{
  "task_id": "task_123456789",
  "status": "completed",
  "result": {
    "success": true,
    "processing_time": 45.2
  }
}
```

### 查看系统统计

```bash
curl http://localhost:8080/stats

# 响应示例
{
  "active_workers": 2,
  "pending_tasks": 0,
  "completed_tasks": 15,
  "failed_tasks": 1,
  "average_processing_time": 42.5
}
```

## 📈 监控面板

访问 http://localhost:9090 查看实时监控面板，包括：

- 📊 系统性能指标
- 🔄 任务处理统计
- 💻 资源使用情况
- 🏥 服务健康状态

## ⚙️ 常用管理命令

### 使用部署脚本

```bash
# 查看帮助
./scripts/deploy-distributed.sh -h

# 查看服务状态
./scripts/deploy-distributed.sh status

# 查看日志
./scripts/deploy-distributed.sh logs

# 扩容工作节点到4个
./scripts/deploy-distributed.sh scale worker-node 4

# 健康检查
./scripts/deploy-distributed.sh health

# 停止服务
./scripts/deploy-distributed.sh stop

# 重启服务
./scripts/deploy-distributed.sh restart
```

### 使用Makefile

```bash
# 查看所有可用命令
make -f Makefile.distributed help

# 部署4个工作节点
make -f Makefile.distributed deploy NODES=4

# 查看服务状态
make -f Makefile.distributed status

# 运行负载测试
make -f Makefile.distributed test-load

# 扩容工作节点
make -f Makefile.distributed scale-workers NODES=6

# 查看系统信息
make -f Makefile.distributed info
```

## 🔧 扩缩容

### 扩容工作节点

```bash
# 扩容到4个工作节点
./scripts/deploy-distributed.sh scale worker-node 4

# 或使用Makefile
make -f Makefile.distributed scale-workers NODES=4
```

### 扩容Chrome浏览器节点

```bash
# 扩容到6个Chrome节点
./scripts/deploy-distributed.sh scale chrome-node 6

# 或使用Makefile
make -f Makefile.distributed scale-chrome NODES=6
```

## 🧪 性能测试

### 功能测试

```bash
# 基本功能测试
./scripts/test-distributed.sh api

# 或使用Makefile
make -f Makefile.distributed test
```

### 负载测试

```bash
# 负载测试（20个任务，5并发）
./scripts/test-distributed.sh load -c 20 -p 5

# 或使用Makefile
make -f Makefile.distributed test-load
```

### 压力测试

```bash
# 压力测试
./scripts/test-distributed.sh stress

# 或使用Makefile
make -f Makefile.distributed test-stress
```

## 🚨 故障排除

### 常见问题

#### 1. 服务启动失败

```bash
# 检查Docker状态
docker ps -a

# 查看服务日志
./scripts/deploy-distributed.sh logs

# 检查端口占用
lsof -i :8080
lsof -i :9090
```

#### 2. 内存不足

```bash
# 查看内存使用
docker stats

# 减少工作节点数量
./scripts/deploy-distributed.sh scale worker-node 1
```

#### 3. 任务处理缓慢

```bash
# 检查工作节点状态
curl http://localhost:8080/workers

# 扩容工作节点
./scripts/deploy-distributed.sh scale worker-node 4
```

### 诊断命令

```bash
# 系统诊断
make -f Makefile.distributed diagnose

# 性能监控
make -f Makefile.distributed perf

# 快速测试
make -f Makefile.distributed quick-test
```

## 🛑 停止和清理

### 停止服务

```bash
# 停止所有服务
./scripts/deploy-distributed.sh stop

# 或使用Makefile
make -f Makefile.distributed stop
```

### 完全清理

```bash
# ⚠️ 警告：这将删除所有数据
./scripts/deploy-distributed.sh clean

# 或使用Makefile
make -f Makefile.distributed clean
```

## 📚 进阶配置

### 自定义配置

编辑 `config/distributed.json` 文件来自定义系统配置：

```json
{
  "worker": {
    "max_workers_per_node": 4,
    "task_timeout": 120
  },
  "gateway": {
    "rate_limit": {
      "requests_per_minute": 100
    }
  }
}
```

### 生产环境部署

```bash
# 生产环境部署（6个工作节点）
./scripts/deploy-distributed.sh deploy -e prod -n 6

# 或使用Makefile
make -f Makefile.distributed deploy-prod NODES=6
```

### 多机部署

```bash
# 多机部署模式
./scripts/deploy-distributed.sh deploy -m multi -n 4

# 或使用Makefile
make -f Makefile.distributed deploy-multi NODES=4
```

## 🔗 相关文档

- 📖 [详细部署指南](docs/DISTRIBUTED_DEPLOYMENT.md)
- 🏗️ [系统架构说明](README.md#系统架构)
- 🔧 [配置参考](config/distributed.example.json)
- 🧪 [API文档](README.md#api-接口)

## 💡 提示

1. **首次部署**：建议先使用默认配置进行部署，确认系统正常运行后再进行自定义配置
2. **资源监控**：定期查看监控面板，根据负载情况调整工作节点数量
3. **日志查看**：遇到问题时，首先查看服务日志进行排查
4. **定期备份**：生产环境建议定期备份Redis数据和配置文件
5. **性能测试**：部署后建议运行性能测试，确认系统满足预期性能要求

## 🆘 获取帮助

如果遇到问题：

1. 查看本文档的故障排除部分
2. 运行诊断命令：`make -f Makefile.distributed diagnose`
3. 查看详细日志：`./scripts/deploy-distributed.sh logs`
4. 在项目仓库提交Issue
5. 联系技术支持团队

---

🎉 **恭喜！** 您已成功部署分布式验证码识别系统！

现在可以开始使用API提交验证码识别任务，或访问监控面板查看系统状态。