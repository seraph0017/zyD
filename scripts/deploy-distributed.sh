#!/bin/bash

# 分布式验证码系统部署脚本
# 支持单机多容器和多机部署模式

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 显示帮助信息
show_help() {
    cat << EOF
分布式验证码系统部署脚本

用法: $0 [选项] [命令]

命令:
  deploy          部署完整的分布式系统
  start           启动所有服务
  stop            停止所有服务
  restart         重启所有服务
  status          查看服务状态
  logs            查看服务日志
  scale           扩缩容服务
  clean           清理系统资源
  monitor         打开监控面板
  health          健康检查

选项:
  -m, --mode MODE     部署模式 (single|multi) [默认: single]
  -n, --nodes NUM     工作节点数量 [默认: 2]
  -c, --config FILE   配置文件路径
  -e, --env ENV       环境 (dev|prod) [默认: dev]
  -h, --help          显示帮助信息

示例:
  $0 deploy                    # 单机部署
  $0 deploy -m multi -n 3      # 多机部署3个工作节点
  $0 scale worker 4            # 扩容工作节点到4个
  $0 logs gateway              # 查看网关日志

EOF
}

# 默认参数
MODE="single"
NODES=2
ENV="dev"
CONFIG_FILE=""
COMPOSE_FILE="docker/docker-compose.distributed.yml"

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -m|--mode)
                MODE="$2"
                shift 2
                ;;
            -n|--nodes)
                NODES="$2"
                shift 2
                ;;
            -c|--config)
                CONFIG_FILE="$2"
                shift 2
                ;;
            -e|--env)
                ENV="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            deploy|start|stop|restart|status|logs|scale|clean|monitor|health)
                COMMAND="$1"
                shift
                ;;
            *)
                if [[ -z "$COMMAND" ]]; then
                    COMMAND="$1"
                fi
                shift
                ;;
        esac
    done
}

# 检查依赖
check_dependencies() {
    log_info "检查系统依赖..."
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    log_success "依赖检查通过"
}

# 准备配置文件
prepare_config() {
    log_info "准备配置文件..."
    
    if [[ -z "$CONFIG_FILE" ]]; then
        CONFIG_FILE="config/distributed.json"
    fi
    
    if [[ ! -f "$CONFIG_FILE" ]]; then
        if [[ -f "config/distributed.example.json" ]]; then
            cp "config/distributed.example.json" "$CONFIG_FILE"
            log_info "已从示例文件创建配置文件: $CONFIG_FILE"
        else
            log_error "配置文件不存在: $CONFIG_FILE"
            exit 1
        fi
    fi
    
    # 设置环境变量
    export DISTRIBUTED_CONFIG_PATH="$CONFIG_FILE"
    export DEPLOYMENT_MODE="$MODE"
    export WORKER_NODES_COUNT="$NODES"
    export ENVIRONMENT="$ENV"
    
    log_success "配置文件准备完成"
}

# 构建镜像
build_images() {
    log_info "构建Docker镜像..."
    
    docker-compose -f "$COMPOSE_FILE" build --parallel
    
    log_success "镜像构建完成"
}

# 部署系统
deploy_system() {
    log_info "开始部署分布式验证码系统..."
    
    check_dependencies
    prepare_config
    
    # 停止现有服务
    log_info "停止现有服务..."
    docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans 2>/dev/null || true
    
    # 清理旧资源
    log_info "清理旧资源..."
    docker system prune -f
    
    # 构建镜像
    build_images
    
    # 启动基础服务
    log_info "启动基础服务 (Redis, Selenium Hub)..."
    docker-compose -f "$COMPOSE_FILE" up -d redis-master redis-sentinel selenium-hub
    
    # 等待基础服务就绪
    log_info "等待基础服务就绪..."
    sleep 10
    
    # 启动Chrome节点
    log_info "启动Chrome浏览器节点..."
    docker-compose -f "$COMPOSE_FILE" up -d chrome-node
    
    # 启动调度器
    log_info "启动任务调度器..."
    docker-compose -f "$COMPOSE_FILE" up -d task-scheduler
    
    # 启动工作节点
    log_info "启动工作节点..."
    for i in $(seq 1 $NODES); do
        log_info "启动工作节点 $i..."
        docker-compose -f "$COMPOSE_FILE" up -d worker-node-$i 2>/dev/null || \
        docker-compose -f "$COMPOSE_FILE" up -d --scale worker-node=$i worker-node
    done
    
    # 启动API网关
    log_info "启动API网关..."
    docker-compose -f "$COMPOSE_FILE" up -d api-gateway
    
    # 启动监控服务
    log_info "启动监控服务..."
    docker-compose -f "$COMPOSE_FILE" up -d monitoring
    
    # 等待所有服务启动
    log_info "等待所有服务启动完成..."
    sleep 15
    
    # 健康检查
    health_check
    
    log_success "分布式系统部署完成！"
    show_access_info
}

# 启动服务
start_services() {
    log_info "启动所有服务..."
    docker-compose -f "$COMPOSE_FILE" up -d
    log_success "服务启动完成"
}

# 停止服务
stop_services() {
    log_info "停止所有服务..."
    docker-compose -f "$COMPOSE_FILE" down
    log_success "服务停止完成"
}

# 重启服务
restart_services() {
    log_info "重启所有服务..."
    docker-compose -f "$COMPOSE_FILE" restart
    log_success "服务重启完成"
}

# 查看服务状态
show_status() {
    log_info "服务状态:"
    docker-compose -f "$COMPOSE_FILE" ps
    
    echo ""
    log_info "系统资源使用情况:"
    docker stats --no-stream --format "table {{.Container}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}\t{{.BlockIO}}"
}

# 查看日志
show_logs() {
    local service="$1"
    if [[ -n "$service" ]]; then
        log_info "查看 $service 服务日志:"
        docker-compose -f "$COMPOSE_FILE" logs -f "$service"
    else
        log_info "查看所有服务日志:"
        docker-compose -f "$COMPOSE_FILE" logs -f
    fi
}

# 扩缩容服务
scale_service() {
    local service="$1"
    local replicas="$2"
    
    if [[ -z "$service" ]] || [[ -z "$replicas" ]]; then
        log_error "用法: $0 scale <服务名> <副本数>"
        exit 1
    fi
    
    log_info "扩缩容 $service 服务到 $replicas 个副本..."
    docker-compose -f "$COMPOSE_FILE" up -d --scale "$service=$replicas" "$service"
    log_success "扩缩容完成"
}

# 清理系统
clean_system() {
    log_warning "这将删除所有容器、镜像和数据，确定要继续吗？(y/N)"
    read -r response
    if [[ "$response" =~ ^[Yy]$ ]]; then
        log_info "清理系统资源..."
        
        # 停止并删除所有容器
        docker-compose -f "$COMPOSE_FILE" down -v --remove-orphans
        
        # 删除相关镜像
        docker images | grep "zyd" | awk '{print $3}' | xargs docker rmi -f 2>/dev/null || true
        
        # 清理系统
        docker system prune -af
        docker volume prune -f
        
        log_success "系统清理完成"
    else
        log_info "取消清理操作"
    fi
}

# 健康检查
health_check() {
    log_info "执行健康检查..."
    
    local services=("api-gateway" "task-scheduler" "worker-node-1" "monitoring")
    local failed=0
    
    for service in "${services[@]}"; do
        if docker-compose -f "$COMPOSE_FILE" ps "$service" | grep -q "Up"; then
            log_success "$service: 运行正常"
        else
            log_error "$service: 服务异常"
            ((failed++))
        fi
    done
    
    # 检查API端点
    log_info "检查API端点..."
    
    if curl -s http://localhost:8080/health > /dev/null; then
        log_success "API网关: 健康检查通过"
    else
        log_error "API网关: 健康检查失败"
        ((failed++))
    fi
    
    if curl -s http://localhost:9090/health > /dev/null; then
        log_success "监控服务: 健康检查通过"
    else
        log_error "监控服务: 健康检查失败"
        ((failed++))
    fi
    
    if [[ $failed -eq 0 ]]; then
        log_success "所有服务健康检查通过"
    else
        log_error "$failed 个服务健康检查失败"
        return 1
    fi
}

# 打开监控面板
open_monitor() {
    log_info "打开监控面板..."
    
    if command -v open &> /dev/null; then
        open http://localhost:9090
    elif command -v xdg-open &> /dev/null; then
        xdg-open http://localhost:9090
    else
        log_info "请在浏览器中访问: http://localhost:9090"
    fi
}

# 显示访问信息
show_access_info() {
    cat << EOF

${GREEN}=== 分布式验证码系统访问信息 ===${NC}

${BLUE}API网关:${NC}     http://localhost:8080
${BLUE}监控面板:${NC}     http://localhost:9090
${BLUE}Selenium Hub:${NC} http://localhost:4444

${YELLOW}API使用示例:${NC}
# 提交任务
curl -X POST http://localhost:8080/submit_task \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/captcha"}'

# 查询任务状态
curl http://localhost:8080/task_status/<task_id>

# 查看系统统计
curl http://localhost:8080/stats

${YELLOW}管理命令:${NC}
# 查看服务状态
$0 status

# 查看日志
$0 logs [服务名]

# 扩缩容
$0 scale worker-node 4

# 健康检查
$0 health

EOF
}

# 主函数
main() {
    parse_args "$@"
    
    case "$COMMAND" in
        deploy)
            deploy_system
            ;;
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        status)
            show_status
            ;;
        logs)
            show_logs "$1"
            ;;
        scale)
            scale_service "$1" "$2"
            ;;
        clean)
            clean_system
            ;;
        monitor)
            open_monitor
            ;;
        health)
            health_check
            ;;
        "")
            log_error "请指定命令，使用 -h 查看帮助"
            exit 1
            ;;
        *)
            log_error "未知命令: $COMMAND"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"