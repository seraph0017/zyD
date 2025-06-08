#!/bin/bash

# Docker调试脚本 - 快速重建和启动服务
# 使用方法: ./scripts/docker-debug.sh

set -e  # 遇到错误立即退出

echo "🔧 开始Docker调试模式..."
echo "==========================================="

# 1. 停止并删除所有容器和网络
echo "📦 停止并清理现有容器..."
docker-compose down -v --remove-orphans

# 2. 清理Docker缓存和未使用的资源
echo "🧹 清理Docker缓存..."
docker system prune -f
docker volume prune -f

# 3. 删除项目相关的镜像（可选，取消注释以启用）
# echo "🗑️  删除项目镜像..."
# docker-compose down --rmi all

# 4. 无缓存重新构建所有服务
echo "🔨 无缓存重新构建服务..."
docker-compose build --no-cache --pull

# 5. 启动所有服务
echo "🚀 启动服务..."
docker-compose up -d

# 6. 显示服务状态
echo "📊 服务状态:"
docker-compose ps

# 7. 显示日志（可选）
echo "📋 实时日志 (Ctrl+C 退出):"
echo "==========================================="
docker-compose logs -f