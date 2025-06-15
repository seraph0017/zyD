# -*- coding: utf-8 -*-
"""
分布式工作节点
负责执行具体的验证码识别任务
"""

import redis
import json
import time
import threading
import os
import logging
from datetime import datetime
from typing import Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from prometheus_client import Counter, Gauge, Histogram, start_http_server
from flask import Flask, jsonify

# 导入现有的核心模块
from src.core.browser_driver import BrowserDriver
from src.ai.volcengine_ai import VolcEngineAI
from src.config.config import get_config

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class DistributedWorker:
    """分布式工作节点"""
    
    def __init__(self):
        self.config = get_config()
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.node_id = os.getenv('NODE_ID', f'worker-{int(time.time())}')
        self.max_workers = int(os.getenv('MAX_WORKERS', '4'))
        self.selenium_hub_url = os.getenv('SELENIUM_HUB_URL', 'http://localhost:4444/wd/hub')
        
        # 工作节点状态
        self.current_tasks = 0
        self.total_processed = 0
        self.running = True
        
        # Prometheus指标
        self.tasks_processed = Counter('worker_tasks_processed_total', 'Total tasks processed', ['worker_id'])
        self.tasks_failed = Counter('worker_tasks_failed_total', 'Total tasks failed', ['worker_id'])
        self.current_tasks_gauge = Gauge('worker_current_tasks', 'Current number of tasks', ['worker_id'])
        self.task_duration = Histogram('worker_task_duration_seconds', 'Task processing duration', ['worker_id'])
        
        # 初始化AI服务
        self.ai_service = VolcEngineAI(api_key=self.config.ai.api_key)
        
        # 启动心跳和任务处理
        self.start_background_threads()
        
        logger.info(f"Worker {self.node_id} initialized with {self.max_workers} concurrent workers")
    
    def start_background_threads(self):
        """启动后台线程"""
        # 心跳线程
        threading.Thread(target=self.heartbeat_loop, daemon=True).start()
        
        # 任务处理线程池
        self.executor = ThreadPoolExecutor(max_workers=self.max_workers)
        
        # 任务监听线程
        threading.Thread(target=self.task_listener, daemon=True).start()
        
        logger.info("Background threads started")
    
    def heartbeat_loop(self):
        """心跳循环"""
        while self.running:
            try:
                heartbeat_data = {
                    'node_id': self.node_id,
                    'max_concurrent': self.max_workers,
                    'current_tasks': self.current_tasks,
                    'total_processed': self.total_processed,
                    'status': 'active',
                    'last_heartbeat': datetime.now().isoformat(),
                    'selenium_hub': self.selenium_hub_url
                }
                
                # 发送心跳到Redis
                self.redis_client.setex(
                    f'worker_heartbeat:{self.node_id}',
                    60,  # 60秒过期
                    json.dumps(heartbeat_data)
                )
                
                # 更新Prometheus指标
                self.current_tasks_gauge.labels(worker_id=self.node_id).set(self.current_tasks)
                
                time.sleep(30)  # 每30秒发送一次心跳
                
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
                time.sleep(10)
    
    def task_listener(self):
        """任务监听器"""
        worker_queue = f'worker_tasks:{self.node_id}'
        logger.info(f"Listening for tasks on queue: {worker_queue}")
        
        while self.running:
            try:
                # 阻塞式获取任务
                task_data = self.redis_client.brpop(worker_queue, timeout=10)
                
                if task_data:
                    task_json = task_data[1].decode()
                    task_info = json.loads(task_json)
                    
                    # 提交任务到线程池
                    if self.current_tasks < self.max_workers:
                        future = self.executor.submit(self.process_task, task_info)
                        self.current_tasks += 1
                        
                        # 处理完成后的回调
                        future.add_done_callback(lambda f: self.task_completed())
                    else:
                        # 如果当前任务已满，重新放回队列
                        self.redis_client.lpush(worker_queue, task_json)
                        time.sleep(1)
                
            except Exception as e:
                logger.error(f"Task listener error: {str(e)}")
                time.sleep(5)
    
    def process_task(self, task_data: dict) -> dict:
        """处理单个任务"""
        task_id = task_data.get('task_id')
        target_url = task_data.get('url')
        start_time = time.time()
        
        logger.info(f"Processing task {task_id} on worker {self.node_id}")
        
        driver = None
        try:
            # 更新任务状态为处理中
            self.update_task_status(task_id, 'processing', {
                'worker_id': self.node_id,
                'started_at': datetime.now().isoformat()
            })
            
            # 初始化浏览器驱动
            driver = BrowserDriver(remote_url=self.selenium_hub_url)
            
            # 访问目标页面
            driver.get_page(target_url)
            
            # 处理验证码
            result = self.process_captcha_task(driver, task_data)
            
            # 记录成功
            self.tasks_processed.labels(worker_id=self.node_id).inc()
            self.total_processed += 1
            
            # 更新任务结果
            self.update_task_result(task_id, 'completed', result)
            
            logger.info(f"Task {task_id} completed successfully")
            return result
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Task {task_id} failed: {error_msg}")
            
            # 记录失败
            self.tasks_failed.labels(worker_id=self.node_id).inc()
            
            # 更新任务结果
            self.update_task_result(task_id, 'failed', {'error': error_msg})
            
            return {'error': error_msg}
            
        finally:
            # 清理资源
            if driver:
                try:
                    driver.quit()
                except:
                    pass
            
            # 记录处理时间
            duration = time.time() - start_time
            self.task_duration.labels(worker_id=self.node_id).observe(duration)
            
            # 清理任务分配记录
            self.redis_client.hdel('task_assignments', task_id)
    
    def process_captcha_task(self, driver: BrowserDriver, task_data: dict) -> dict:
        """处理验证码任务的核心逻辑"""
        try:
            # 查找验证码图片元素
            captcha_element = driver.find_captcha_image()
            if not captcha_element:
                raise Exception("未找到验证码图片")
            
            # 截取验证码图片
            screenshot_path = driver.take_captcha_screenshot(captcha_element)
            
            # 使用AI识别验证码
            captcha_code = self.ai_service.recognize_captcha(screenshot_path)
            
            if not captcha_code:
                raise Exception("验证码识别失败")
            
            # 输入验证码
            success = driver.input_captcha_code(captcha_code)
            
            if success:
                # 检查是否成功
                if self.check_success_page(driver):
                    return {
                        'status': 'success',
                        'captcha_code': captcha_code,
                        'screenshot_path': screenshot_path,
                        'final_url': driver.driver.current_url
                    }
                else:
                    return {
                        'status': 'captcha_solved_but_failed',
                        'captcha_code': captcha_code,
                        'screenshot_path': screenshot_path,
                        'message': '验证码识别正确但页面跳转失败'
                    }
            else:
                return {
                    'status': 'input_failed',
                    'captcha_code': captcha_code,
                    'screenshot_path': screenshot_path,
                    'message': '验证码输入失败'
                }
                
        except Exception as e:
            raise Exception(f"验证码处理失败: {str(e)}")
    
    def check_success_page(self, driver: BrowserDriver) -> bool:
        """检查是否成功跳转到目标页面"""
        try:
            from selenium.webdriver.common.by import By
            from selenium.webdriver.support.ui import WebDriverWait
            from selenium.webdriver.support import expected_conditions as EC
            from selenium.common.exceptions import TimeoutException
            
            # 检查成功页面标志
            try:
                WebDriverWait(driver.driver, self.config.web.success_check_timeout).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, self.config.web.success_page_selector))
                )
                return True
            except TimeoutException:
                pass
            
            # 检查URL关键词
            current_url = driver.driver.current_url.lower()
            for keyword in self.config.web.success_url_keywords:
                if keyword in current_url:
                    return True
            
            # 检查页面文本关键词
            page_text = driver.driver.page_source.lower()
            for keyword in self.config.web.success_keywords:
                if keyword in page_text:
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Success page check failed: {str(e)}")
            return False
    
    def update_task_status(self, task_id: str, status: str, additional_data: dict = None):
        """更新任务状态"""
        try:
            status_data = {
                'task_id': task_id,
                'status': status,
                'worker_id': self.node_id,
                'updated_at': datetime.now().isoformat()
            }
            
            if additional_data:
                status_data.update(additional_data)
            
            self.redis_client.hset('task_status', task_id, json.dumps(status_data))
            
        except Exception as e:
            logger.error(f"Error updating task status: {str(e)}")
    
    def update_task_result(self, task_id: str, status: str, result_data: dict):
        """更新任务结果"""
        try:
            result = {
                'task_id': task_id,
                'status': status,
                'worker_id': self.node_id,
                'completed_at': datetime.now().isoformat(),
                **result_data
            }
            
            self.redis_client.hset('task_results', task_id, json.dumps(result))
            
        except Exception as e:
            logger.error(f"Error updating task result: {str(e)}")
    
    def task_completed(self):
        """任务完成回调"""
        self.current_tasks = max(0, self.current_tasks - 1)
    
    def get_health_status(self) -> dict:
        """获取健康状态"""
        return {
            'node_id': self.node_id,
            'status': 'healthy' if self.running else 'unhealthy',
            'current_tasks': self.current_tasks,
            'max_workers': self.max_workers,
            'total_processed': self.total_processed,
            'selenium_hub': self.selenium_hub_url,
            'timestamp': datetime.now().isoformat()
        }
    
    def shutdown(self):
        """优雅关闭"""
        logger.info(f"Shutting down worker {self.node_id}...")
        self.running = False
        
        # 等待当前任务完成
        self.executor.shutdown(wait=True)
        
        # 清理心跳记录
        self.redis_client.delete(f'worker_heartbeat:{self.node_id}')

# Flask应用用于健康检查
app = Flask(__name__)
worker_instance = None

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查端点"""
    if worker_instance:
        return jsonify(worker_instance.get_health_status())
    else:
        return jsonify({'status': 'initializing'}), 503

@app.route('/metrics', methods=['GET'])
def metrics():
    """Prometheus指标端点"""
    from prometheus_client import generate_latest
    return generate_latest()

def start_health_server():
    """启动健康检查服务器"""
    app.run(host='0.0.0.0', port=8000, debug=False)

def main():
    """主函数"""
    global worker_instance
    
    logger.info("Starting Distributed Worker Node")
    
    # 启动Prometheus指标服务器
    start_http_server(9090)
    logger.info("Prometheus metrics server started on port 9090")
    
    # 启动健康检查服务器
    threading.Thread(target=start_health_server, daemon=True).start()
    logger.info("Health check server started on port 8000")
    
    # 创建并启动工作节点
    worker_instance = DistributedWorker()
    
    try:
        # 保持主线程运行
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
        if worker_instance:
            worker_instance.shutdown()

if __name__ == '__main__':
    main()