#!/bin/bash

# Docker快速重启脚本 - 保留数据卷
# 使用方法: ./scripts/docker-quick-restart.sh [service_name]

set -e

SERVICE_NAME=${1:-""}

echo "⚡ 快速重启Docker服务..."
echo "==========================================="

if [ -n "$SERVICE_NAME" ]; then
    echo "🔄 重启指定服务: $SERVICE_NAME"
    docker-compose restart $SERVICE_NAME
    docker-compose logs -f $SERVICE_NAME
else
    echo "🔄 重启所有服务..."
    docker-compose down
    docker-compose up -d
    
    echo "📊 服务状态:"
    docker-compose ps
    
    echo "📋 实时日志 (Ctrl+C 退出):"
    echo "==========================================="
    docker-compose logs -f
fi