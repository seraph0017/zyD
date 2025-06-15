# -*- coding: utf-8 -*-
"""
分布式任务调度器
负责任务分发、监控和协调工作节点
"""

import redis
import json
import time
import threading
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List
from concurrent.futures import ThreadPoolExecutor
from prometheus_client import Counter, Gauge, Histogram, start_http_server

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DistributedScheduler:
    """分布式任务调度器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.node_id = os.getenv('NODE_ID', 'scheduler-main')
        self.max_workers = int(os.getenv('MAX_WORKERS', '8'))
        self.health_check_interval = int(os.getenv('HEALTH_CHECK_INTERVAL', '30'))
        self.task_timeout = int(os.getenv('TASK_TIMEOUT', '300'))
        
        # Prometheus指标
        self.tasks_scheduled = Counter('scheduler_tasks_scheduled_total', 'Total tasks scheduled')
        self.tasks_completed = Counter('scheduler_tasks_completed_total', 'Total tasks completed')
        self.tasks_failed = Counter('scheduler_tasks_failed_total', 'Total tasks failed')
        self.queue_size = Gauge('scheduler_queue_size', 'Current queue size')
        self.active_workers = Gauge('scheduler_active_workers', 'Number of active workers')
        self.task_duration = Histogram('scheduler_task_duration_seconds', 'Task processing duration')
        
        # 工作节点状态
        self.worker_nodes = {}
        self.last_heartbeat = {}
        
        # 启动监控线程
        self.running = True
        self.start_monitoring_threads()
    
    def start_monitoring_threads(self):
        """启动监控线程"""
        # 队列监控线程
        threading.Thread(target=self.monitor_queue, daemon=True).start()
        
        # 工作节点健康检查线程
        threading.Thread(target=self.monitor_workers, daemon=True).start()
        
        # 任务超时检查线程
        threading.Thread(target=self.monitor_timeouts, daemon=True).start()
        
        # 统计更新线程
        threading.Thread(target=self.update_metrics, daemon=True).start()
        
        logger.info("All monitoring threads started")
    
    def monitor_queue(self):
        """监控任务队列"""
        logger.info("Queue monitoring started")
        
        while self.running:
            try:
                # 检查队列长度
                queue_length = self.redis_client.llen('captcha_tasks')
                self.queue_size.set(queue_length)
                
                # 检查是否有待处理任务
                if queue_length > 0:
                    self.distribute_tasks()
                
                # 清理过期任务结果
                self.cleanup_expired_results()
                
                time.sleep(5)  # 每5秒检查一次
                
            except Exception as e:
                logger.error(f"Queue monitoring error: {str(e)}")
                time.sleep(10)
    
    def distribute_tasks(self):
        """分发任务给工作节点"""
        try:
            # 获取可用的工作节点
            available_workers = self.get_available_workers()
            
            if not available_workers:
                logger.warning("No available workers for task distribution")
                return
            
            # 为每个可用工作节点分配任务
            for worker_id in available_workers:
                worker_info = self.worker_nodes.get(worker_id, {})
                max_concurrent = worker_info.get('max_concurrent', 4)
                current_tasks = worker_info.get('current_tasks', 0)
                
                # 计算可以分配的任务数量
                available_slots = max_concurrent - current_tasks
                
                for _ in range(available_slots):
                    task_json = self.redis_client.rpop('captcha_tasks')
                    if not task_json:
                        break
                    
                    task_data = json.loads(task_json)
                    task_id = task_data['task_id']
                    
                    # 分配任务给工作节点
                    self.assign_task_to_worker(task_id, worker_id, task_data)
                    
                    self.tasks_scheduled.inc()
                    logger.info(f"Task {task_id} assigned to worker {worker_id}")
        
        except Exception as e:
            logger.error(f"Task distribution error: {str(e)}")
    
    def assign_task_to_worker(self, task_id: str, worker_id: str, task_data: dict):
        """将任务分配给特定工作节点"""
        try:
            # 更新任务状态
            task_data.update({
                'status': 'assigned',
                'worker_id': worker_id,
                'assigned_at': datetime.now().isoformat()
            })
            
            # 添加到工作节点的任务队列
            worker_queue = f'worker_tasks:{worker_id}'
            self.redis_client.lpush(worker_queue, json.dumps(task_data))
            
            # 记录任务分配
            self.redis_client.hset('task_assignments', task_id, json.dumps({
                'worker_id': worker_id,
                'assigned_at': datetime.now().isoformat(),
                'status': 'assigned'
            }))
            
            # 更新工作节点状态
            if worker_id in self.worker_nodes:
                self.worker_nodes[worker_id]['current_tasks'] += 1
        
        except Exception as e:
            logger.error(f"Error assigning task {task_id} to worker {worker_id}: {str(e)}")
    
    def monitor_workers(self):
        """监控工作节点状态"""
        logger.info("Worker monitoring started")
        
        while self.running:
            try:
                # 检查工作节点心跳
                current_time = datetime.now()
                
                for worker_id in list(self.worker_nodes.keys()):
                    last_heartbeat = self.last_heartbeat.get(worker_id)
                    
                    if last_heartbeat:
                        time_diff = current_time - last_heartbeat
                        if time_diff > timedelta(seconds=self.health_check_interval * 2):
                            logger.warning(f"Worker {worker_id} appears to be offline")
                            self.handle_worker_failure(worker_id)
                
                # 发现新的工作节点
                self.discover_workers()
                
                # 更新活跃工作节点数量
                self.active_workers.set(len(self.get_available_workers()))
                
                time.sleep(self.health_check_interval)
                
            except Exception as e:
                logger.error(f"Worker monitoring error: {str(e)}")
                time.sleep(10)
    
    def discover_workers(self):
        """发现新的工作节点"""
        try:
            # 从Redis中获取工作节点注册信息
            worker_keys = self.redis_client.keys('worker_heartbeat:*')
            
            for key in worker_keys:
                worker_id = key.decode().split(':')[1]
                heartbeat_data = self.redis_client.get(key)
                
                if heartbeat_data:
                    heartbeat_info = json.loads(heartbeat_data)
                    self.register_worker(worker_id, heartbeat_info)
        
        except Exception as e:
            logger.error(f"Worker discovery error: {str(e)}")
    
    def register_worker(self, worker_id: str, worker_info: dict):
        """注册工作节点"""
        if worker_id not in self.worker_nodes:
            logger.info(f"Discovered new worker: {worker_id}")
        
        self.worker_nodes[worker_id] = {
            'id': worker_id,
            'max_concurrent': worker_info.get('max_concurrent', 4),
            'current_tasks': worker_info.get('current_tasks', 0),
            'status': 'active',
            'last_seen': datetime.now()
        }
        
        self.last_heartbeat[worker_id] = datetime.now()
    
    def handle_worker_failure(self, worker_id: str):
        """处理工作节点故障"""
        logger.error(f"Handling failure for worker {worker_id}")
        
        try:
            # 重新分配该工作节点的任务
            worker_queue = f'worker_tasks:{worker_id}'
            
            while True:
                task_json = self.redis_client.rpop(worker_queue)
                if not task_json:
                    break
                
                # 将任务重新放回主队列
                task_data = json.loads(task_json)
                task_data['status'] = 'queued'
                task_data['retry_count'] = task_data.get('retry_count', 0) + 1
                
                if task_data['retry_count'] <= 3:
                    self.redis_client.lpush('captcha_tasks', json.dumps(task_data))
                    logger.info(f"Task {task_data['task_id']} requeued due to worker failure")
                else:
                    # 标记为失败
                    self.mark_task_failed(task_data['task_id'], "Max retries exceeded")
            
            # 移除失败的工作节点
            if worker_id in self.worker_nodes:
                del self.worker_nodes[worker_id]
            if worker_id in self.last_heartbeat:
                del self.last_heartbeat[worker_id]
        
        except Exception as e:
            logger.error(f"Error handling worker failure: {str(e)}")
    
    def monitor_timeouts(self):
        """监控任务超时"""
        logger.info("Timeout monitoring started")
        
        while self.running:
            try:
                current_time = datetime.now()
                
                # 检查分配的任务是否超时
                assignments = self.redis_client.hgetall('task_assignments')
                
                for task_id, assignment_json in assignments.items():
                    assignment_data = json.loads(assignment_json)
                    assigned_at = datetime.fromisoformat(assignment_data['assigned_at'])
                    
                    if current_time - assigned_at > timedelta(seconds=self.task_timeout):
                        logger.warning(f"Task {task_id.decode()} timed out")
                        self.handle_task_timeout(task_id.decode(), assignment_data)
                
                time.sleep(60)  # 每分钟检查一次
                
            except Exception as e:
                logger.error(f"Timeout monitoring error: {str(e)}")
                time.sleep(60)
    
    def handle_task_timeout(self, task_id: str, assignment_data: dict):
        """处理任务超时"""
        try:
            worker_id = assignment_data['worker_id']
            
            # 标记任务为超时失败
            self.mark_task_failed(task_id, "Task timeout")
            
            # 清理分配记录
            self.redis_client.hdel('task_assignments', task_id)
            
            # 更新工作节点状态
            if worker_id in self.worker_nodes:
                self.worker_nodes[worker_id]['current_tasks'] = max(0, 
                    self.worker_nodes[worker_id]['current_tasks'] - 1)
        
        except Exception as e:
            logger.error(f"Error handling task timeout: {str(e)}")
    
    def mark_task_failed(self, task_id: str, error_message: str):
        """标记任务为失败"""
        try:
            result_data = {
                'task_id': task_id,
                'status': 'failed',
                'error': error_message,
                'completed_at': datetime.now().isoformat()
            }
            
            self.redis_client.hset('task_results', task_id, json.dumps(result_data))
            self.tasks_failed.inc()
            
            logger.error(f"Task {task_id} marked as failed: {error_message}")
        
        except Exception as e:
            logger.error(f"Error marking task as failed: {str(e)}")
    
    def get_available_workers(self) -> List[str]:
        """获取可用的工作节点列表"""
        available = []
        
        for worker_id, worker_info in self.worker_nodes.items():
            if (worker_info['status'] == 'active' and 
                worker_info['current_tasks'] < worker_info['max_concurrent']):
                available.append(worker_id)
        
        return available
    
    def cleanup_expired_results(self):
        """清理过期的任务结果"""
        try:
            # 清理24小时前的结果
            cutoff_time = datetime.now() - timedelta(hours=24)
            
            results = self.redis_client.hgetall('task_results')
            expired_tasks = []
            
            for task_id, result_json in results.items():
                result_data = json.loads(result_json)
                completed_at = datetime.fromisoformat(result_data['completed_at'])
                
                if completed_at < cutoff_time:
                    expired_tasks.append(task_id)
            
            if expired_tasks:
                self.redis_client.hdel('task_results', *expired_tasks)
                logger.info(f"Cleaned up {len(expired_tasks)} expired task results")
        
        except Exception as e:
            logger.error(f"Error cleaning up expired results: {str(e)}")
    
    def update_metrics(self):
        """更新Prometheus指标"""
        while self.running:
            try:
                # 更新队列大小
                queue_length = self.redis_client.llen('captcha_tasks')
                self.queue_size.set(queue_length)
                
                # 更新活跃工作节点数量
                active_count = len(self.get_available_workers())
                self.active_workers.set(active_count)
                
                time.sleep(30)  # 每30秒更新一次
                
            except Exception as e:
                logger.error(f"Metrics update error: {str(e)}")
                time.sleep(30)
    
    def shutdown(self):
        """优雅关闭"""
        logger.info("Shutting down scheduler...")
        self.running = False

def main():
    """主函数"""
    logger.info("Starting Distributed Task Scheduler")
    
    # 启动Prometheus指标服务器
    start_http_server(8000)
    logger.info("Prometheus metrics server started on port 8000")
    
    # 创建并启动调度器
    scheduler = DistributedScheduler()
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        scheduler.shutdown()

if __name__ == '__main__':
    main()