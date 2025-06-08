#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import redis
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from src.core.browser_driver import BrowserDriver
from src.ai.volcengine_ai import VolcEngineAI
from src.config.config import get_config
import logging
import os

config = get_config()
logger = logging.getLogger(__name__)

class TaskScheduler:
    def __init__(self):
        self.redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))
        self.selenium_hub_url = os.getenv('SELENIUM_HUB_URL', 'http://localhost:4444/wd/hub')
        self.max_workers = int(os.getenv('MAX_WORKERS', '4'))
        
    def add_task(self, task_data):
        """添加任务到队列"""
        task_json = json.dumps(task_data)
        self.redis_client.lpush('captcha_tasks', task_json)
        logger.info(f"任务已添加到队列: {task_data.get('task_id')}")
    
    def process_task(self, task_data):
        """处理单个验证码任务"""
        task_id = task_data.get('task_id')
        target_url = task_data.get('url')
        
        logger.info(f"开始处理任务 {task_id}")
        
        driver = None
        try:
            # 初始化远程浏览器驱动
            driver = BrowserDriver(remote_url=self.selenium_hub_url)
            
            # 访问目标页面
            driver.get_page(target_url)
            
            # 初始化AI
            ai = VolcEngineAI(api_key=config.ai.api_key)
            
            # 处理验证码
            from run import process_captcha_and_submit, check_success_page
            
            if process_captcha_and_submit(driver, ai):
                if check_success_page(driver):
                    logger.info(f"任务 {task_id} 执行成功")
                    self.redis_client.hset('task_results', task_id, json.dumps({
                        'status': 'success',
                        'timestamp': time.time()
                    }))
                else:
                    logger.warning(f"任务 {task_id} 验证码识别成功但页面跳转失败")
                    self.redis_client.hset('task_results', task_id, json.dumps({
                        'status': 'partial_success',
                        'timestamp': time.time()
                    }))
            else:
                logger.error(f"任务 {task_id} 执行失败")
                self.redis_client.hset('task_results', task_id, json.dumps({
                    'status': 'failed',
                    'timestamp': time.time()
                }))
                
        except Exception as e:
            logger.exception(f"任务 {task_id} 执行异常: {e}")
            self.redis_client.hset('task_results', task_id, json.dumps({
                'status': 'error',
                'error': str(e),
                'timestamp': time.time()
            }))
        finally:
            if driver:
                driver.close()
    
    def worker(self):
        """工作线程"""
        while True:
            try:
                # 从队列中获取任务
                task_json = self.redis_client.brpop('captcha_tasks', timeout=10)
                if task_json:
                    task_data = json.loads(task_json[1])
                    self.process_task(task_data)
            except Exception as e:
                logger.exception(f"工作线程异常: {e}")
                time.sleep(5)
    
    def start(self):
        """启动调度器"""
        logger.info(f"启动任务调度器，工作线程数: {self.max_workers}")
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # 启动工作线程
            for i in range(self.max_workers):
                executor.submit(self.worker)
            
            # 保持主线程运行
            try:
                while True:
                    time.sleep(60)
                    # 可以在这里添加健康检查逻辑
                    active_tasks = self.redis_client.llen('captcha_tasks')
                    logger.info(f"队列中待处理任务数: {active_tasks}")
            except KeyboardInterrupt:
                logger.info("收到停止信号，正在关闭调度器...")

if __name__ == "__main__":
    scheduler = TaskScheduler()
    scheduler.start()