# -*- coding: utf-8 -*-
"""
分布式系统监控服务
提供系统状态监控、指标收集和可视化界面
"""

from flask import Flask, jsonify, render_template_string
import redis
import json
import os
import time
import threading
from datetime import datetime, timedelta
from typing import Dict, List
import logging
from prometheus_client import Counter, Gauge, Histogram, generate_latest
import psutil

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

class SystemMonitor:
    """系统监控器"""
    
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        
        # Prometheus指标
        self.system_cpu_usage = Gauge('system_cpu_usage_percent', 'System CPU usage')
        self.system_memory_usage = Gauge('system_memory_usage_percent', 'System memory usage')
        self.redis_connections = Gauge('redis_connections_total', 'Redis connections')
        self.queue_length = Gauge('queue_length_total', 'Queue length')
        self.active_workers = Gauge('active_workers_total', 'Active workers')
        self.tasks_per_minute = Gauge('tasks_per_minute', 'Tasks processed per minute')
        
        # 统计数据
        self.stats_history = []
        self.max_history_size = 1440  # 24小时的分钟数
        
        # 启动监控线程
        self.running = True
        self.start_monitoring_threads()
    
    def start_monitoring_threads(self):
        """启动监控线程"""
        threading.Thread(target=self.collect_system_metrics, daemon=True).start()
        threading.Thread(target=self.collect_redis_metrics, daemon=True).start()
        threading.Thread(target=self.collect_application_metrics, daemon=True).start()
        logger.info("Monitoring threads started")
    
    def collect_system_metrics(self):
        """收集系统指标"""
        while self.running:
            try:
                # CPU使用率
                cpu_percent = psutil.cpu_percent(interval=1)
                self.system_cpu_usage.set(cpu_percent)
                
                # 内存使用率
                memory = psutil.virtual_memory()
                self.system_memory_usage.set(memory.percent)
                
                time.sleep(30)  # 每30秒收集一次
                
            except Exception as e:
                logger.error(f"System metrics collection error: {str(e)}")
                time.sleep(30)
    
    def collect_redis_metrics(self):
        """收集Redis指标"""
        while self.running:
            try:
                # Redis连接数
                info = self.redis_client.info()
                connected_clients = info.get('connected_clients', 0)
                self.redis_connections.set(connected_clients)
                
                # 队列长度
                queue_length = self.redis_client.llen('captcha_tasks')
                self.queue_length.set(queue_length)
                
                time.sleep(30)  # 每30秒收集一次
                
            except Exception as e:
                logger.error(f"Redis metrics collection error: {str(e)}")
                time.sleep(30)
    
    def collect_application_metrics(self):
        """收集应用指标"""
        while self.running:
            try:
                # 活跃工作节点数
                worker_keys = self.redis_client.keys('worker_heartbeat:*')
                active_count = 0
                
                current_time = datetime.now()
                for key in worker_keys:
                    heartbeat_data = self.redis_client.get(key)
                    if heartbeat_data:
                        heartbeat_info = json.loads(heartbeat_data)
                        last_heartbeat = datetime.fromisoformat(heartbeat_info['last_heartbeat'])
                        if current_time - last_heartbeat < timedelta(minutes=2):
                            active_count += 1
                
                self.active_workers.set(active_count)
                
                # 任务处理速率
                tasks_per_min = self.calculate_tasks_per_minute()
                self.tasks_per_minute.set(tasks_per_min)
                
                # 保存历史数据
                self.save_stats_snapshot()
                
                time.sleep(60)  # 每分钟收集一次
                
            except Exception as e:
                logger.error(f"Application metrics collection error: {str(e)}")
                time.sleep(60)
    
    def calculate_tasks_per_minute(self) -> float:
        """计算每分钟任务处理数"""
        try:
            # 获取最近完成的任务数量
            results = self.redis_client.hgetall('task_results')
            
            one_minute_ago = datetime.now() - timedelta(minutes=1)
            recent_tasks = 0
            
            for task_id, result_json in results.items():
                result_data = json.loads(result_json)
                completed_at = datetime.fromisoformat(result_data['completed_at'])
                if completed_at > one_minute_ago:
                    recent_tasks += 1
            
            return recent_tasks
            
        except Exception as e:
            logger.error(f"Error calculating tasks per minute: {str(e)}")
            return 0.0
    
    def save_stats_snapshot(self):
        """保存统计快照"""
        try:
            snapshot = {
                'timestamp': datetime.now().isoformat(),
                'queue_length': self.redis_client.llen('captcha_tasks'),
                'active_workers': int(self.active_workers._value.get()),
                'cpu_usage': psutil.cpu_percent(),
                'memory_usage': psutil.virtual_memory().percent,
                'tasks_per_minute': self.calculate_tasks_per_minute()
            }
            
            self.stats_history.append(snapshot)
            
            # 保持历史数据大小
            if len(self.stats_history) > self.max_history_size:
                self.stats_history.pop(0)
                
        except Exception as e:
            logger.error(f"Error saving stats snapshot: {str(e)}")
    
    def get_system_overview(self) -> Dict:
        """获取系统概览"""
        try:
            # 基本统计
            queue_length = self.redis_client.llen('captcha_tasks')
            total_results = self.redis_client.hlen('task_results')
            
            # 工作节点状态
            worker_keys = self.redis_client.keys('worker_heartbeat:*')
            workers_info = []
            active_workers = 0
            
            current_time = datetime.now()
            for key in worker_keys:
                heartbeat_data = self.redis_client.get(key)
                if heartbeat_data:
                    worker_info = json.loads(heartbeat_data)
                    last_heartbeat = datetime.fromisoformat(worker_info['last_heartbeat'])
                    is_active = current_time - last_heartbeat < timedelta(minutes=2)
                    
                    if is_active:
                        active_workers += 1
                    
                    workers_info.append({
                        'node_id': worker_info['node_id'],
                        'status': 'active' if is_active else 'inactive',
                        'current_tasks': worker_info.get('current_tasks', 0),
                        'max_concurrent': worker_info.get('max_concurrent', 4),
                        'total_processed': worker_info.get('total_processed', 0),
                        'last_heartbeat': worker_info['last_heartbeat']
                    })
            
            # 系统资源
            cpu_percent = psutil.cpu_percent()
            memory = psutil.virtual_memory()
            
            # Redis信息
            redis_info = self.redis_client.info()
            
            return {
                'overview': {
                    'queue_length': queue_length,
                    'total_completed': total_results,
                    'active_workers': active_workers,
                    'total_workers': len(worker_keys),
                    'tasks_per_minute': self.calculate_tasks_per_minute()
                },
                'system': {
                    'cpu_usage': cpu_percent,
                    'memory_usage': memory.percent,
                    'memory_total': memory.total,
                    'memory_available': memory.available
                },
                'redis': {
                    'connected_clients': redis_info.get('connected_clients', 0),
                    'used_memory': redis_info.get('used_memory_human', 'N/A'),
                    'uptime_in_seconds': redis_info.get('uptime_in_seconds', 0)
                },
                'workers': workers_info,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error getting system overview: {str(e)}")
            return {'error': str(e)}
    
    def get_performance_history(self, hours: int = 24) -> List[Dict]:
        """获取性能历史数据"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_history = [
                snapshot for snapshot in self.stats_history
                if datetime.fromisoformat(snapshot['timestamp']) > cutoff_time
            ]
            
            return filtered_history
            
        except Exception as e:
            logger.error(f"Error getting performance history: {str(e)}")
            return []

# 全局监控器实例
monitor = SystemMonitor()

@app.route('/', methods=['GET'])
def dashboard():
    """监控仪表板"""
    dashboard_html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>分布式验证码系统监控</title>
        <meta charset="utf-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background-color: #f5f5f5; }
            .container { max-width: 1200px; margin: 0 auto; }
            .header { text-align: center; margin-bottom: 30px; }
            .stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-bottom: 30px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-value { font-size: 2em; font-weight: bold; color: #2196F3; }
            .stat-label { color: #666; margin-top: 5px; }
            .chart-container { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); margin-bottom: 20px; }
            .workers-table { width: 100%; border-collapse: collapse; }
            .workers-table th, .workers-table td { padding: 10px; text-align: left; border-bottom: 1px solid #ddd; }
            .workers-table th { background-color: #f8f9fa; }
            .status-active { color: #4CAF50; font-weight: bold; }
            .status-inactive { color: #f44336; font-weight: bold; }
            .refresh-btn { background: #2196F3; color: white; border: none; padding: 10px 20px; border-radius: 4px; cursor: pointer; }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>分布式验证码系统监控</h1>
                <button class="refresh-btn" onclick="location.reload()">刷新数据</button>
            </div>
            
            <div class="stats-grid" id="stats-grid">
                <!-- 统计卡片将通过JavaScript动态加载 -->
            </div>
            
            <div class="chart-container">
                <h3>系统性能趋势</h3>
                <canvas id="performanceChart" width="400" height="200"></canvas>
            </div>
            
            <div class="chart-container">
                <h3>工作节点状态</h3>
                <table class="workers-table" id="workers-table">
                    <thead>
                        <tr>
                            <th>节点ID</th>
                            <th>状态</th>
                            <th>当前任务</th>
                            <th>最大并发</th>
                            <th>已处理总数</th>
                            <th>最后心跳</th>
                        </tr>
                    </thead>
                    <tbody id="workers-tbody">
                        <!-- 工作节点数据将通过JavaScript动态加载 -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <script>
            // 加载系统数据
            async function loadSystemData() {
                try {
                    const response = await fetch('/api/overview');
                    const data = await response.json();
                    
                    // 更新统计卡片
                    updateStatsCards(data.overview, data.system);
                    
                    // 更新工作节点表格
                    updateWorkersTable(data.workers);
                    
                } catch (error) {
                    console.error('Error loading system data:', error);
                }
            }
            
            function updateStatsCards(overview, system) {
                const statsGrid = document.getElementById('stats-grid');
                statsGrid.innerHTML = `
                    <div class="stat-card">
                        <div class="stat-value">${overview.queue_length}</div>
                        <div class="stat-label">队列长度</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${overview.active_workers}/${overview.total_workers}</div>
                        <div class="stat-label">活跃工作节点</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${overview.total_completed}</div>
                        <div class="stat-label">已完成任务</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${overview.tasks_per_minute.toFixed(1)}</div>
                        <div class="stat-label">任务/分钟</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${system.cpu_usage.toFixed(1)}%</div>
                        <div class="stat-label">CPU使用率</div>
                    </div>
                    <div class="stat-card">
                        <div class="stat-value">${system.memory_usage.toFixed(1)}%</div>
                        <div class="stat-label">内存使用率</div>
                    </div>
                `;
            }
            
            function updateWorkersTable(workers) {
                const tbody = document.getElementById('workers-tbody');
                tbody.innerHTML = workers.map(worker => `
                    <tr>
                        <td>${worker.node_id}</td>
                        <td><span class="status-${worker.status}">${worker.status}</span></td>
                        <td>${worker.current_tasks}</td>
                        <td>${worker.max_concurrent}</td>
                        <td>${worker.total_processed}</td>
                        <td>${new Date(worker.last_heartbeat).toLocaleString()}</td>
                    </tr>
                `).join('');
            }
            
            // 加载性能历史数据并绘制图表
            async function loadPerformanceChart() {
                try {
                    const response = await fetch('/api/performance?hours=6');
                    const data = await response.json();
                    
                    const ctx = document.getElementById('performanceChart').getContext('2d');
                    new Chart(ctx, {
                        type: 'line',
                        data: {
                            labels: data.map(d => new Date(d.timestamp).toLocaleTimeString()),
                            datasets: [
                                {
                                    label: '队列长度',
                                    data: data.map(d => d.queue_length),
                                    borderColor: 'rgb(75, 192, 192)',
                                    tension: 0.1
                                },
                                {
                                    label: 'CPU使用率(%)',
                                    data: data.map(d => d.cpu_usage),
                                    borderColor: 'rgb(255, 99, 132)',
                                    tension: 0.1
                                },
                                {
                                    label: '任务/分钟',
                                    data: data.map(d => d.tasks_per_minute),
                                    borderColor: 'rgb(54, 162, 235)',
                                    tension: 0.1
                                }
                            ]
                        },
                        options: {
                            responsive: true,
                            scales: {
                                y: {
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                } catch (error) {
                    console.error('Error loading performance chart:', error);
                }
            }
            
            // 页面加载时初始化
            document.addEventListener('DOMContentLoaded', function() {
                loadSystemData();
                loadPerformanceChart();
                
                // 每30秒自动刷新数据
                setInterval(loadSystemData, 30000);
            });
        </script>
    </body>
    </html>
    """
    return dashboard_html

@app.route('/api/overview', methods=['GET'])
def api_overview():
    """系统概览API"""
    return jsonify(monitor.get_system_overview())

@app.route('/api/performance', methods=['GET'])
def api_performance():
    """性能历史API"""
    from flask import request
    hours = int(request.args.get('hours', 24))
    return jsonify(monitor.get_performance_history(hours))

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        monitor.redis_client.ping()
        return jsonify({
            'status': 'healthy',
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus指标"""
    return generate_latest()

def main():
    """主函数"""
    logger.info("Starting Monitoring Service")
    app.run(host='0.0.0.0', port=9090, debug=False)

if __name__ == '__main__':
    main()