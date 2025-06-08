#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from flask import Flask, request, jsonify
import redis
import json
import uuid
import os
from datetime import datetime

app = Flask(__name__)
redis_client = redis.from_url(os.getenv('REDIS_URL', 'redis://localhost:6379'))

@app.route('/submit_task', methods=['POST'])
def submit_task():
    """提交验证码处理任务"""
    try:
        data = request.get_json()
        
        if not data or 'url' not in data:
            return jsonify({'error': '缺少必要参数 url'}), 400
        
        task_id = str(uuid.uuid4())
        task_data = {
            'task_id': task_id,
            'url': data['url'],
            'created_at': datetime.now().isoformat(),
            'priority': data.get('priority', 'normal')
        }
        
        # 添加到任务队列
        task_json = json.dumps(task_data)
        redis_client.lpush('captcha_tasks', task_json)
        
        return jsonify({
            'task_id': task_id,
            'status': 'queued',
            'message': '任务已提交到队列'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/task_status/<task_id>', methods=['GET'])
def get_task_status(task_id):
    """查询任务状态"""
    try:
        result = redis_client.hget('task_results', task_id)
        
        if result:
            return jsonify(json.loads(result))
        else:
            # 检查是否还在队列中
            queue_length = redis_client.llen('captcha_tasks')
            return jsonify({
                'status': 'pending',
                'queue_position': queue_length,
                'message': '任务正在队列中等待处理'
            })
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/health', methods=['GET'])
def health_check():
    """健康检查"""
    try:
        # 检查Redis连接
        redis_client.ping()
        
        # 获取队列状态
        queue_length = redis_client.llen('captcha_tasks')
        
        return jsonify({
            'status': 'healthy',
            'queue_length': queue_length,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)