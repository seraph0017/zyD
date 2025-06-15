#!/bin/bash

# 分布式验证码系统测试脚本
# 用于验证系统功能和性能

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

# 配置
API_GATEWAY_URL="http://localhost:8080"
MONITORING_URL="http://localhost:9090"
SELENIUM_HUB_URL="http://localhost:4444"
TEST_URL="https://httpbin.org/html"
TEST_COUNT=5
CONCURRENT_TESTS=3

# 显示帮助信息
show_help() {
    cat << EOF
分布式验证码系统测试脚本

用法: $0 [选项] [测试类型]

测试类型:
  health          健康检查测试
  api             API功能测试
  load            负载测试
  stress          压力测试
  failover        故障转移测试
  all             运行所有测试

选项:
  -u, --url URL       API网关地址 [默认: http://localhost:8080]
  -c, --count NUM     测试任务数量 [默认: 5]
  -p, --parallel NUM  并发数量 [默认: 3]
  -t, --timeout SEC   超时时间 [默认: 60]
  -h, --help          显示帮助信息

示例:
  $0 health                    # 健康检查
  $0 api -c 10                 # API测试，10个任务
  $0 load -c 50 -p 10          # 负载测试，50个任务，10并发
  $0 all                       # 运行所有测试

EOF
}

# 解析命令行参数
parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -u|--url)
                API_GATEWAY_URL="$2"
                shift 2
                ;;
            -c|--count)
                TEST_COUNT="$2"
                shift 2
                ;;
            -p|--parallel)
                CONCURRENT_TESTS="$2"
                shift 2
                ;;
            -t|--timeout)
                TIMEOUT="$2"
                shift 2
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            health|api|load|stress|failover|all)
                TEST_TYPE="$1"
                shift
                ;;
            *)
                if [[ -z "$TEST_TYPE" ]]; then
                    TEST_TYPE="$1"
                fi
                shift
                ;;
        esac
    done
}

# 检查服务可用性
check_service() {
    local url="$1"
    local name="$2"
    
    if curl -s --max-time 5 "$url" > /dev/null; then
        log_success "$name 服务可用"
        return 0
    else
        log_error "$name 服务不可用: $url"
        return 1
    fi
}

# 健康检查测试
test_health() {
    log_info "开始健康检查测试..."
    
    local failed=0
    
    # 检查API网关
    if ! check_service "$API_GATEWAY_URL/health" "API网关"; then
        ((failed++))
    fi
    
    # 检查监控服务
    if ! check_service "$MONITORING_URL/health" "监控服务"; then
        ((failed++))
    fi
    
    # 检查Selenium Hub
    if ! check_service "$SELENIUM_HUB_URL/status" "Selenium Hub"; then
        ((failed++))
    fi
    
    # 检查系统统计
    log_info "检查系统统计接口..."
    if curl -s "$API_GATEWAY_URL/stats" | jq . > /dev/null 2>&1; then
        log_success "系统统计接口正常"
    else
        log_error "系统统计接口异常"
        ((failed++))
    fi
    
    # 检查工作节点
    log_info "检查工作节点状态..."
    local workers=$(curl -s "$API_GATEWAY_URL/workers" | jq -r '.active_workers // 0' 2>/dev/null || echo "0")
    if [[ "$workers" -gt 0 ]]; then
        log_success "发现 $workers 个活跃工作节点"
    else
        log_error "没有发现活跃的工作节点"
        ((failed++))
    fi
    
    if [[ $failed -eq 0 ]]; then
        log_success "健康检查测试通过"
    else
        log_error "健康检查测试失败，$failed 个服务异常"
        return 1
    fi
}

# API功能测试
test_api() {
    log_info "开始API功能测试..."
    
    local failed=0
    local task_ids=()
    
    # 提交测试任务
    log_info "提交 $TEST_COUNT 个测试任务..."
    for i in $(seq 1 $TEST_COUNT); do
        local response=$(curl -s -X POST "$API_GATEWAY_URL/submit_task" \
            -H "Content-Type: application/json" \
            -d "{
                \"url\": \"$TEST_URL\",
                \"timeout\": 60,
                \"retry_count\": 2
            }")
        
        local task_id=$(echo "$response" | jq -r '.task_id // empty' 2>/dev/null)
        if [[ -n "$task_id" ]]; then
            task_ids+=("$task_id")
            log_success "任务 $i 提交成功: $task_id"
        else
            log_error "任务 $i 提交失败: $response"
            ((failed++))
        fi
        
        sleep 0.5
    done
    
    # 等待任务处理
    log_info "等待任务处理..."
    sleep 10
    
    # 检查任务状态
    log_info "检查任务状态..."
    local completed=0
    local pending=0
    local failed_tasks=0
    
    for task_id in "${task_ids[@]}"; do
        local status_response=$(curl -s "$API_GATEWAY_URL/task_status/$task_id")
        local status=$(echo "$status_response" | jq -r '.status // "unknown"' 2>/dev/null)
        
        case "$status" in
            "completed")
                ((completed++))
                log_success "任务 $task_id: 已完成"
                ;;
            "pending"|"processing")
                ((pending++))
                log_warning "任务 $task_id: $status"
                ;;
            "failed")
                ((failed_tasks++))
                log_error "任务 $task_id: 失败"
                ;;
            *)
                log_error "任务 $task_id: 状态未知 ($status)"
                ((failed++))
                ;;
        esac
    done
    
    # 输出统计
    log_info "任务统计: 完成=$completed, 处理中=$pending, 失败=$failed_tasks"
    
    if [[ $failed -eq 0 ]] && [[ $completed -gt 0 ]]; then
        log_success "API功能测试通过"
    else
        log_error "API功能测试失败"
        return 1
    fi
}

# 负载测试
test_load() {
    log_info "开始负载测试 (任务数: $TEST_COUNT, 并发: $CONCURRENT_TESTS)..."
    
    local start_time=$(date +%s)
    local pids=()
    local task_ids_file=$(mktemp)
    
    # 并发提交任务
    for i in $(seq 1 $CONCURRENT_TESTS); do
        {
            local batch_size=$((TEST_COUNT / CONCURRENT_TESTS))
            local start_idx=$(((i-1) * batch_size + 1))
            local end_idx=$((i * batch_size))
            
            for j in $(seq $start_idx $end_idx); do
                local response=$(curl -s -X POST "$API_GATEWAY_URL/submit_task" \
                    -H "Content-Type: application/json" \
                    -d "{
                        \"url\": \"$TEST_URL\",
                        \"timeout\": 60
                    }")
                
                local task_id=$(echo "$response" | jq -r '.task_id // empty' 2>/dev/null)
                if [[ -n "$task_id" ]]; then
                    echo "$task_id" >> "$task_ids_file"
                fi
                
                sleep 0.1
            done
        } &
        pids+=("$!")
    done
    
    # 等待所有并发任务完成
    for pid in "${pids[@]}"; do
        wait "$pid"
    done
    
    local submit_time=$(date +%s)
    local submit_duration=$((submit_time - start_time))
    
    log_info "任务提交完成，耗时: ${submit_duration}秒"
    
    # 等待任务处理
    log_info "等待任务处理完成..."
    local max_wait=300  # 最大等待5分钟
    local wait_time=0
    
    while [[ $wait_time -lt $max_wait ]]; do
        local stats=$(curl -s "$API_GATEWAY_URL/stats")
        local pending=$(echo "$stats" | jq -r '.pending_tasks // 0' 2>/dev/null)
        
        if [[ "$pending" -eq 0 ]]; then
            break
        fi
        
        log_info "等待中... 剩余任务: $pending"
        sleep 10
        wait_time=$((wait_time + 10))
    done
    
    local end_time=$(date +%s)
    local total_duration=$((end_time - start_time))
    
    # 统计结果
    local total_tasks=$(wc -l < "$task_ids_file")
    local throughput=$(echo "scale=2; $total_tasks / $total_duration" | bc -l)
    
    log_info "负载测试完成:"
    log_info "  总任务数: $total_tasks"
    log_info "  总耗时: ${total_duration}秒"
    log_info "  吞吐量: ${throughput}任务/秒"
    
    # 清理临时文件
    rm -f "$task_ids_file"
    
    log_success "负载测试完成"
}

# 压力测试
test_stress() {
    log_info "开始压力测试..."
    
    local stress_count=$((TEST_COUNT * 5))
    local stress_concurrent=$((CONCURRENT_TESTS * 2))
    
    log_info "压力测试参数: 任务数=$stress_count, 并发=$stress_concurrent"
    
    # 监控系统资源
    {
        while true; do
            local stats=$(curl -s "$API_GATEWAY_URL/stats" 2>/dev/null || echo '{}')
            local cpu=$(echo "$stats" | jq -r '.system_load.cpu_usage // "N/A"' 2>/dev/null)
            local memory=$(echo "$stats" | jq -r '.system_load.memory_usage // "N/A"' 2>/dev/null)
            local pending=$(echo "$stats" | jq -r '.pending_tasks // "N/A"' 2>/dev/null)
            
            echo "$(date '+%H:%M:%S') - CPU: ${cpu}%, 内存: ${memory}%, 待处理: $pending" >> stress_monitor.log
            sleep 5
        done
    } &
    local monitor_pid=$!
    
    # 执行压力测试
    TEST_COUNT=$stress_count CONCURRENT_TESTS=$stress_concurrent test_load
    
    # 停止监控
    kill $monitor_pid 2>/dev/null || true
    
    log_info "压力测试监控日志已保存到 stress_monitor.log"
    log_success "压力测试完成"
}

# 故障转移测试
test_failover() {
    log_info "开始故障转移测试..."
    
    # 获取当前工作节点数量
    local initial_workers=$(curl -s "$API_GATEWAY_URL/workers" | jq -r '.active_workers // 0' 2>/dev/null)
    log_info "当前活跃工作节点: $initial_workers"
    
    if [[ "$initial_workers" -lt 2 ]]; then
        log_error "故障转移测试需要至少2个工作节点"
        return 1
    fi
    
    # 提交一些任务
    log_info "提交测试任务..."
    local task_ids=()
    for i in $(seq 1 5); do
        local response=$(curl -s -X POST "$API_GATEWAY_URL/submit_task" \
            -H "Content-Type: application/json" \
            -d "{
                \"url\": \"$TEST_URL\",
                \"timeout\": 120
            }")
        
        local task_id=$(echo "$response" | jq -r '.task_id // empty' 2>/dev/null)
        if [[ -n "$task_id" ]]; then
            task_ids+=("$task_id")
        fi
    done
    
    # 模拟节点故障（停止一个工作节点）
    log_warning "模拟节点故障..."
    docker-compose -f docker/docker-compose.distributed.yml stop worker-node-1 2>/dev/null || true
    
    sleep 10
    
    # 检查系统是否继续工作
    local remaining_workers=$(curl -s "$API_GATEWAY_URL/workers" | jq -r '.active_workers // 0' 2>/dev/null)
    log_info "故障后活跃工作节点: $remaining_workers"
    
    if [[ "$remaining_workers" -lt "$initial_workers" ]]; then
        log_success "故障检测正常"
    else
        log_error "故障检测异常"
    fi
    
    # 提交新任务测试系统恢复能力
    log_info "测试系统恢复能力..."
    local recovery_response=$(curl -s -X POST "$API_GATEWAY_URL/submit_task" \
        -H "Content-Type: application/json" \
        -d "{
            \"url\": \"$TEST_URL\",
            \"timeout\": 60
        }")
    
    local recovery_task_id=$(echo "$recovery_response" | jq -r '.task_id // empty' 2>/dev/null)
    if [[ -n "$recovery_task_id" ]]; then
        log_success "系统在故障后仍能接受新任务"
    else
        log_error "系统在故障后无法接受新任务"
    fi
    
    # 恢复节点
    log_info "恢复故障节点..."
    docker-compose -f docker/docker-compose.distributed.yml start worker-node-1 2>/dev/null || true
    
    sleep 15
    
    # 检查恢复后的状态
    local recovered_workers=$(curl -s "$API_GATEWAY_URL/workers" | jq -r '.active_workers // 0' 2>/dev/null)
    log_info "恢复后活跃工作节点: $recovered_workers"
    
    if [[ "$recovered_workers" -eq "$initial_workers" ]]; then
        log_success "节点恢复正常"
    else
        log_warning "节点恢复可能需要更多时间"
    fi
    
    log_success "故障转移测试完成"
}

# 运行所有测试
test_all() {
    log_info "开始运行所有测试..."
    
    local failed=0
    
    if ! test_health; then
        ((failed++))
    fi
    
    if ! test_api; then
        ((failed++))
    fi
    
    if ! test_load; then
        ((failed++))
    fi
    
    if [[ $failed -eq 0 ]]; then
        log_success "所有测试通过"
    else
        log_error "$failed 个测试失败"
        return 1
    fi
}

# 主函数
main() {
    parse_args "$@"
    
    if [[ -z "$TEST_TYPE" ]]; then
        log_error "请指定测试类型，使用 -h 查看帮助"
        exit 1
    fi
    
    log_info "开始测试分布式验证码系统..."
    log_info "API网关地址: $API_GATEWAY_URL"
    log_info "测试类型: $TEST_TYPE"
    
    case "$TEST_TYPE" in
        health)
            test_health
            ;;
        api)
            test_api
            ;;
        load)
            test_load
            ;;
        stress)
            test_stress
            ;;
        failover)
            test_failover
            ;;
        all)
            test_all
            ;;
        *)
            log_error "未知测试类型: $TEST_TYPE"
            show_help
            exit 1
            ;;
    esac
}

# 执行主函数
main "$@"