#!/bin/bash

# Docker深度清理脚本
# 使用方法: ./scripts/docker-clean.sh

set -e

echo "🧹 Docker深度清理..."
echo "==========================================="

# 停止所有容器
echo "⏹️  停止所有容器..."
docker-compose down -v --remove-orphans

# 删除所有未使用的容器
echo "🗑️  删除未使用的容器..."
docker container prune -f

# 删除所有未使用的镜像
echo "🗑️  删除未使用的镜像..."
docker image prune -a -f

# 删除所有未使用的卷
echo "🗑️  删除未使用的数据卷..."
docker volume prune -f

# 删除所有未使用的网络
echo "🗑️  删除未使用的网络..."
docker network prune -f

# 显示清理后的磁盘使用情况
echo "📊 清理完成，当前Docker磁盘使用:"
docker system df

echo "✅ 深度清理完成！"