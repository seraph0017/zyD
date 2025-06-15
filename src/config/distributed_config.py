# -*- coding: utf-8 -*-
"""
分布式系统配置
包含所有分布式相关的配置项
"""

import os
import json
from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path

@dataclass
class RedisConfig:
    """Redis配置"""
    url: str = "redis://localhost:6379"
    max_connections: int = 100
    socket_timeout: int = 30
    socket_connect_timeout: int = 30
    retry_on_timeout: bool = True
    health_check_interval: int = 30
    
    # 集群配置
    cluster_enabled: bool = False
    cluster_nodes: List[str] = None
    
    # 哨兵配置
    sentinel_enabled: bool = False
    sentinel_hosts: List[tuple] = None
    sentinel_service_name: str = "mymaster"
    
    def __post_init__(self):
        if self.cluster_nodes is None:
            self.cluster_nodes = []
        if self.sentinel_hosts is None:
            self.sentinel_hosts = []

@dataclass
class SeleniumGridConfig:
    """Selenium Grid配置"""
    hub_url: str = "http://localhost:4444/wd/hub"
    max_sessions: int = 16
    browser_timeout: int = 300
    grid_timeout: int = 300
    new_session_wait_timeout: int = 10000
    
    # 节点配置
    node_max_instances: int = 2
    node_max_sessions: int = 2
    
    # 健康检查
    health_check_interval: int = 30
    health_check_timeout: int = 10

@dataclass
class WorkerConfig:
    """工作节点配置"""
    max_workers: int = 4
    task_timeout: int = 300
    heartbeat_interval: int = 30
    max_retry_attempts: int = 3
    
    # 资源限制
    max_memory_usage: int = 1024  # MB
    max_cpu_usage: float = 80.0   # 百分比
    
    # 任务队列
    queue_name: str = "captcha_tasks"
    result_queue_name: str = "task_results"
    
    # 优雅关闭
    shutdown_timeout: int = 30

@dataclass
class SchedulerConfig:
    """调度器配置"""
    max_workers: int = 8
    task_distribution_interval: int = 5
    worker_health_check_interval: int = 30
    task_timeout_check_interval: int = 60
    
    # 负载均衡
    load_balance_strategy: str = "round_robin"  # round_robin, least_connections, weighted
    
    # 任务重试
    max_retry_attempts: int = 3
    retry_delay: int = 60  # 秒
    
    # 清理策略
    result_retention_hours: int = 24
    cleanup_interval: int = 3600  # 秒

@dataclass
class GatewayConfig:
    """API网关配置"""
    port: int = 8080
    host: str = "0.0.0.0"
    
    # 限流配置
    rate_limit_per_minute: int = 60
    rate_limit_per_hour: int = 1000
    rate_limit_per_day: int = 10000
    
    # 负载均衡
    worker_nodes: List[str] = None
    health_check_interval: int = 30
    health_check_timeout: int = 5
    
    # 超时配置
    request_timeout: int = 30
    
    def __post_init__(self):
        if self.worker_nodes is None:
            self.worker_nodes = []

@dataclass
class MonitoringConfig:
    """监控配置"""
    port: int = 9090
    host: str = "0.0.0.0"
    
    # 指标收集
    metrics_interval: int = 30
    history_retention_hours: int = 24
    
    # 告警配置
    alert_enabled: bool = True
    alert_thresholds: Dict[str, float] = None
    
    # Prometheus配置
    prometheus_enabled: bool = True
    prometheus_port: int = 9090
    
    def __post_init__(self):
        if self.alert_thresholds is None:
            self.alert_thresholds = {
                'cpu_usage': 80.0,
                'memory_usage': 85.0,
                'queue_length': 1000,
                'error_rate': 10.0
            }

@dataclass
class SecurityConfig:
    """安全配置"""
    # API认证
    api_key_enabled: bool = False
    api_key: Optional[str] = None
    
    # JWT配置
    jwt_enabled: bool = False
    jwt_secret: Optional[str] = None
    jwt_expiration: int = 3600  # 秒
    
    # IP白名单
    ip_whitelist_enabled: bool = False
    allowed_ips: List[str] = None
    
    # HTTPS配置
    ssl_enabled: bool = False
    ssl_cert_path: Optional[str] = None
    ssl_key_path: Optional[str] = None
    
    def __post_init__(self):
        if self.allowed_ips is None:
            self.allowed_ips = []

@dataclass
class DistributedConfig:
    """分布式系统总配置"""
    redis: RedisConfig
    selenium_grid: SeleniumGridConfig
    worker: WorkerConfig
    scheduler: SchedulerConfig
    gateway: GatewayConfig
    monitoring: MonitoringConfig
    security: SecurityConfig
    
    # 部署配置
    deployment_mode: str = "docker"  # docker, kubernetes, standalone
    cluster_name: str = "captcha-cluster"
    node_id: Optional[str] = None
    
    # 日志配置
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    def __post_init__(self):
        if self.node_id is None:
            import socket
            self.node_id = f"{socket.gethostname()}-{os.getpid()}"

def load_distributed_config(config_path: Optional[str] = None) -> DistributedConfig:
    """加载分布式配置"""
    if config_path is None:
        config_path = os.getenv('DISTRIBUTED_CONFIG_PATH', 'config/distributed.json')
    
    # 默认配置
    default_config = {
        'redis': {
            'url': os.getenv('REDIS_URL', 'redis://localhost:6379')
        },
        'selenium_grid': {
            'hub_url': os.getenv('SELENIUM_HUB_URL', 'http://localhost:4444/wd/hub')
        },
        'worker': {
            'max_workers': int(os.getenv('MAX_WORKERS', '4'))
        },
        'scheduler': {
            'max_workers': int(os.getenv('SCHEDULER_MAX_WORKERS', '8'))
        },
        'gateway': {
            'port': int(os.getenv('GATEWAY_PORT', '8080')),
            'worker_nodes': os.getenv('WORKER_NODES', '').split(',') if os.getenv('WORKER_NODES') else []
        },
        'monitoring': {
            'port': int(os.getenv('MONITORING_PORT', '9090'))
        },
        'security': {
            'api_key': os.getenv('API_KEY'),
            'jwt_secret': os.getenv('JWT_SECRET')
        }
    }
    
    # 尝试加载配置文件
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                file_config = json.load(f)
                # 合并配置
                merge_config(default_config, file_config)
        except Exception as e:
            print(f"Warning: Failed to load config file {config_path}: {e}")
    
    # 创建配置对象
    return DistributedConfig(
        redis=RedisConfig(**default_config.get('redis', {})),
        selenium_grid=SeleniumGridConfig(**default_config.get('selenium_grid', {})),
        worker=WorkerConfig(**default_config.get('worker', {})),
        scheduler=SchedulerConfig(**default_config.get('scheduler', {})),
        gateway=GatewayConfig(**default_config.get('gateway', {})),
        monitoring=MonitoringConfig(**default_config.get('monitoring', {})),
        security=SecurityConfig(**default_config.get('security', {})),
        deployment_mode=default_config.get('deployment_mode', 'docker'),
        cluster_name=default_config.get('cluster_name', 'captcha-cluster'),
        node_id=default_config.get('node_id'),
        log_level=default_config.get('log_level', 'INFO'),
        log_format=default_config.get('log_format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )

def merge_config(base: dict, override: dict):
    """递归合并配置字典"""
    for key, value in override.items():
        if key in base and isinstance(base[key], dict) and isinstance(value, dict):
            merge_config(base[key], value)
        else:
            base[key] = value

def save_distributed_config(config: DistributedConfig, config_path: str):
    """保存分布式配置到文件"""
    config_dict = {
        'redis': {
            'url': config.redis.url,
            'max_connections': config.redis.max_connections,
            'socket_timeout': config.redis.socket_timeout,
            'cluster_enabled': config.redis.cluster_enabled,
            'cluster_nodes': config.redis.cluster_nodes,
            'sentinel_enabled': config.redis.sentinel_enabled,
            'sentinel_hosts': config.redis.sentinel_hosts,
            'sentinel_service_name': config.redis.sentinel_service_name
        },
        'selenium_grid': {
            'hub_url': config.selenium_grid.hub_url,
            'max_sessions': config.selenium_grid.max_sessions,
            'browser_timeout': config.selenium_grid.browser_timeout,
            'node_max_instances': config.selenium_grid.node_max_instances,
            'node_max_sessions': config.selenium_grid.node_max_sessions
        },
        'worker': {
            'max_workers': config.worker.max_workers,
            'task_timeout': config.worker.task_timeout,
            'heartbeat_interval': config.worker.heartbeat_interval,
            'max_retry_attempts': config.worker.max_retry_attempts
        },
        'scheduler': {
            'max_workers': config.scheduler.max_workers,
            'task_distribution_interval': config.scheduler.task_distribution_interval,
            'load_balance_strategy': config.scheduler.load_balance_strategy,
            'max_retry_attempts': config.scheduler.max_retry_attempts
        },
        'gateway': {
            'port': config.gateway.port,
            'host': config.gateway.host,
            'rate_limit_per_minute': config.gateway.rate_limit_per_minute,
            'worker_nodes': config.gateway.worker_nodes
        },
        'monitoring': {
            'port': config.monitoring.port,
            'host': config.monitoring.host,
            'metrics_interval': config.monitoring.metrics_interval,
            'alert_enabled': config.monitoring.alert_enabled,
            'alert_thresholds': config.monitoring.alert_thresholds
        },
        'security': {
            'api_key_enabled': config.security.api_key_enabled,
            'jwt_enabled': config.security.jwt_enabled,
            'ip_whitelist_enabled': config.security.ip_whitelist_enabled,
            'allowed_ips': config.security.allowed_ips
        },
        'deployment_mode': config.deployment_mode,
        'cluster_name': config.cluster_name,
        'log_level': config.log_level
    }
    
    os.makedirs(os.path.dirname(config_path), exist_ok=True)
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)

# 全局配置实例
_distributed_config = None

def get_distributed_config() -> DistributedConfig:
    """获取全局分布式配置实例"""
    global _distributed_config
    if _distributed_config is None:
        _distributed_config = load_distributed_config()
    return _distributed_config