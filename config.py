#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目配置文件
统一管理所有配置项
"""

import os
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class BrowserConfig:
    """浏览器配置"""
    # 基础配置
    headless: bool = True
    window_width: int = 1920
    window_height: int = 1080
    implicit_wait: int = 10
    page_load_timeout: int = 30
    
    # Chrome选项
    chrome_options: List[str] = None
    user_agent: str = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # 性能优化
    disable_images: bool = False
    disable_css: bool = False
    
    def __post_init__(self):
        if self.chrome_options is None:
            self.chrome_options = [
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-gpu',
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]


@dataclass
class AIConfig:
    """AI模型配置"""
    # API配置
    api_key: str = ""
    base_url: str = "https://ark.cn-beijing.volces.com/api/v3"
    
    # 文本模型配置
    text_model: str = "doubao-1.5-pro-32k-250115"
    text_max_tokens: int = 1000
    text_temperature: float = 0.7
    
    # 视觉模型配置
    vision_model: str = "doubao-1.5-vision-lite-250315"
    vision_max_tokens: int = 1000
    vision_temperature: float = 0.7
    
    # 验证码识别提示词
    captcha_prompt: str = "请解析图片中验证码，并仅返回验证码内容，请勿返回其他内容。"
    
    def __post_init__(self):
        # 从环境变量获取API密钥
        if not self.api_key:
            self.api_key = os.environ.get("ARK_API_KEY", "")


@dataclass
class WebConfig:
    """网站配置"""
    # 目标网站
    base_url: str = "https://www.hongkongdisneyland.com/zh-hk/merchstore/duffy/"
    
    # 页面元素选择器
    code_input_id: str = "solution"
    submit_button_selector: str = ".botdetect-button.btn"
    success_page_selector: str = ".cart-button-wrapper"
    
    # 成功页面检测关键词
    success_keywords: List[str] = None
    success_url_keywords: List[str] = None
    
    # 页面等待时间
    element_wait_timeout: int = 10
    success_check_timeout: int = 5
    
    def __post_init__(self):
        if self.success_keywords is None:
            self.success_keywords = ["成功", "success", "添加到购物车", "cart"]
        if self.success_url_keywords is None:
            self.success_url_keywords = ["success", "cart"]


@dataclass
class RetryConfig:
    """重试配置"""
    max_attempts: int = 5
    wait_time: int = 3  # 秒
    exponential_backoff: bool = False
    backoff_multiplier: float = 1.5
    max_wait_time: int = 30


@dataclass
class LogConfig:
    """日志配置"""
    level: str = "INFO"
    format: str = "%(asctime)s - %(levelname)s - %(message)s"
    file_path: str = ""
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    backup_count: int = 5


@dataclass
class FileConfig:
    """文件配置"""
    screenshot_dir: str = "testpng"
    screenshot_prefix: str = "screenshot"
    screenshot_format: str = "png"
    auto_cleanup: bool = False
    max_files: int = 100


class Config:
    """主配置类"""
    
    def __init__(self, config_file: str = None):
        # 初始化各模块配置
        self.browser = BrowserConfig()
        self.ai = AIConfig()
        self.web = WebConfig()
        self.retry = RetryConfig()
        self.log = LogConfig()
        self.file = FileConfig()
        
        # 如果提供了配置文件，则加载
        if config_file and os.path.exists(config_file):
            self.load_from_file(config_file)
    
    def load_from_file(self, config_file: str):
        """从配置文件加载配置"""
        try:
            import json
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # 更新配置
            for section, values in config_data.items():
                if hasattr(self, section):
                    config_obj = getattr(self, section)
                    for key, value in values.items():
                        if hasattr(config_obj, key):
                            setattr(config_obj, key, value)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
    
    def save_to_file(self, config_file: str):
        """保存配置到文件"""
        try:
            import json
            from dataclasses import asdict
            
            config_data = {
                'browser': asdict(self.browser),
                'ai': asdict(self.ai),
                'web': asdict(self.web),
                'retry': asdict(self.retry),
                'log': asdict(self.log),
                'file': asdict(self.file)
            }
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            print(f"配置已保存到: {config_file}")
        except Exception as e:
            print(f"保存配置文件失败: {e}")
    
    def get_env_config(self) -> Dict[str, Any]:
        """获取环境变量配置"""
        return {
            'ARK_API_KEY': os.environ.get('ARK_API_KEY', ''),
            'BROWSER_HEADLESS': os.environ.get('BROWSER_HEADLESS', 'true').lower() == 'true',
            'MAX_RETRY_ATTEMPTS': int(os.environ.get('MAX_RETRY_ATTEMPTS', '5')),
            'RETRY_WAIT_TIME': int(os.environ.get('RETRY_WAIT_TIME', '3')),
            'LOG_LEVEL': os.environ.get('LOG_LEVEL', 'INFO')
        }
    
    def apply_env_config(self):
        """应用环境变量配置"""
        env_config = self.get_env_config()
        
        if env_config['ARK_API_KEY']:
            self.ai.api_key = env_config['ARK_API_KEY']
        
        self.browser.headless = env_config['BROWSER_HEADLESS']
        self.retry.max_attempts = env_config['MAX_RETRY_ATTEMPTS']
        self.retry.wait_time = env_config['RETRY_WAIT_TIME']
        self.log.level = env_config['LOG_LEVEL']


# 全局配置实例
config = Config()

# 应用环境变量配置
config.apply_env_config()


# 便捷访问函数
def get_config() -> Config:
    """获取配置实例"""
    return Config('config.json')


def load_config(config_file: str) -> Config:
    """加载配置文件"""
    return Config(config_file)