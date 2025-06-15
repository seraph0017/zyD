# -*- coding: utf-8 -*-
"""
API网关 - 分布式系统统一入口
负责请求路由、负载均衡、限流等功能
"""

from flask import Flask, request, jsonify
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_cors import CORS
import redis
import json
import uuid
import os
import requests
import time
from datetime import datetime
from prometheus_client import Counter, Histogram, generate_latest
import logging
from typing import List, Dict

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# 配置限流器
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Redis连接
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

# 工作节点列表
WORKER_NODES = os.getenv('WORKER_NODES', 'localhost:8001,localhost:8002').split(',')

# Prometheus指标
request_count = Counter('gateway_requests_total', 'Total requests', ['method', 'endpoint'])
request_duration = Histogram('gateway_request_duration_seconds', 'Request duration')
task_count = Counter('gateway_tasks_total', 'Total tasks submitted')

class LoadBalancer:
    """简单的轮询负载均衡器"""
    
    def __init__(self, nodes: List[str]):
        self.nodes = nodes
        self.current = 0
    
    def get_next_node(self) -> str:
        """获取下一个可用节点"""
        if not self.nodes:
            raise Exception("No available worker nodes")
        
        node = self.nodes[self.current]
        self.current = (self.current + 1) % len(self.nodes)
        return node
    
    def health_check(self) -> Dict[str, bool]:
        """检查所有节点健康状态"""
        health_status = {}
        for node in self.nodes:
            try:
                response = requests.get(f"http://{node}/health", timeout=5)
                health_status[node] = response.status_code == 200
            except:
                health_status[node] = False
        return health_status

load_balancer = LoadBalancer(WORKER_NODES)

@app.route('/health', methods=['GET'])
def health_check():
    """网关健康检查"""
    try:
        # 检查Redis连接
        redis_client.ping()
        
        # 检查工作节点
        worker_health = load_balancer.health_check()
        healthy_workers = sum(1 for status in worker_health.values() if status)
        
        return jsonify({
            'status': 'healthy',
            'redis': 'connected',
            'workers': {
                'total': len(WORKER_NODES),
                'healthy': healthy_workers,
                'details': worker_health
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/submit_task', methods=['POST'])
@limiter.limit("10 per minute")
def submit_task():
    """提交验证码处理任务"""
    start_time = time.time()
    request_count.labels(method='POST', endpoint='/submit_task').inc()
    
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': '缺少必要参数 url'}), 400
        
        task_id = str(uuid.uuid4())
        task_data = {
            'task_id': task_id,
            'url': data['url'],
            'created_at': datetime.now().isoformat(),
            'priority': data.get('priority', 'normal'),
            'gateway_node': os.getenv('HOSTNAME', 'gateway'),
            'client_ip': get_remote_address()
        }
        
        # 添加到Redis任务队列
        task_json = json.dumps(task_data)
        redis_client.lpush('captcha_tasks', task_json)
        
        # 记录任务提交
        task_count.inc()
        
        logger.info(f"Task {task_id} submitted to queue")
        
        return jsonify({
            'task_id': task_id,
            'status': 'queued',
            'message': '任务已提交到队列',
            'estimated_wait_time': get_estimated_wait_time()
        })
        
    except Exception as e:
        logger.error(f"Error submitting task: {str(e)}")
        return jsonify({'error': str(e)}), 500
    finally:
        request_duration.observe(time.time() - start_time)

@app.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """查询任务状态"""
    request_count.labels(method='GET', endpoint='/task_status').inc()
    
    try:
        result = redis_client.hget('task_results', task_id)
        
        if result:
            result_data = json.loads(result)
            return jsonify(result_data)
        else:
            # 检查任务是否还在队列中
            queue_position = get_task_queue_position(task_id)
            if queue_position >= 0:
                return jsonify({
                    'task_id': task_id,
                    'status': 'queued',
                    'queue_position': queue_position,
                    'estimated_wait_time': get_estimated_wait_time()
                })
            else:
                return jsonify({
                    'task_id': task_id,
                    'status': 'not_found',
                    'message': '任务不存在或已过期'
                }), 404
                
    except Exception as e:
        logger.error(f"Error getting task status: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/stats', methods=['GET'])
def get_stats():
    """获取系统统计信息"""
    try:
        queue_length = redis_client.llen('captcha_tasks')
        completed_tasks = redis_client.hlen('task_results')
        worker_health = load_balancer.health_check()
        
        return jsonify({
            'queue': {
                'length': queue_length,
                'estimated_wait_time': get_estimated_wait_time()
            },
            'tasks': {
                'completed': completed_tasks,
                'processing_rate': get_processing_rate()
            },
            'workers': {
                'total': len(WORKER_NODES),
                'healthy': sum(1 for status in worker_health.values() if status),
                'details': worker_health
            },
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus指标端点"""
    return generate_latest()

def get_task_queue_position(task_id: str) -> int:
    """获取任务在队列中的位置"""
    try:
        tasks = redis_client.lrange('captcha_tasks', 0, -1)
        for i, task_json in enumerate(tasks):
            task_data = json.loads(task_json)
            if task_data.get('task_id') == task_id:
                return i
        return -1
    except:
        return -1

def get_estimated_wait_time() -> int:
    """估算等待时间（秒）"""
    try:
        queue_length = redis_client.llen('captcha_tasks')
        # 假设每个任务平均处理时间为30秒，每个工作节点并发处理4个任务
        healthy_workers = sum(1 for status in load_balancer.health_check().values() if status)
        if healthy_workers == 0:
            return 999999  # 无可用工作节点
        
        concurrent_capacity = healthy_workers * 4  # 每个节点4个并发
        avg_processing_time = 30  # 秒
        
        if queue_length <= concurrent_capacity:
            return avg_processing_time
        else:
            return int((queue_length / concurrent_capacity) * avg_processing_time)
    except:
        return 60  # 默认1分钟

def get_processing_rate() -> float:
    """获取任务处理速率（任务/分钟）"""
    try:
        # 这里可以实现更复杂的统计逻辑
        # 暂时返回估算值
        healthy_workers = sum(1 for status in load_balancer.health_check().values() if status)
        return healthy_workers * 4 * 2  # 每个工作节点每分钟处理8个任务
    except:
        return 0.0

if __name__ == '__main__':
    logger.info(f"Starting API Gateway with worker nodes: {WORKER_NODES}")
    app.run(host='0.0.0.0', port=8080, debug=False)