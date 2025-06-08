#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from src.config.config import get_config
import time
import os

# 获取配置
config = get_config()

class BrowserDriver:
    def __init__(self, headless=None, remote_url=None):
        try:
            # 使用配置文件中的设置，如果没有传入参数
            if headless is None:
                headless = config.browser.headless
            
            # 配置 Chrome 选项
            chrome_options = Options()
            
            if headless:
                chrome_options.add_argument('--headless')
            
            # Docker环境下的必要选项
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--disable-features=VizDisplayCompositor')
            chrome_options.add_argument('--remote-debugging-port=9222')
            
            # 添加配置文件中的选项
            for option in config.browser.chrome_options:
                chrome_options.add_argument(option)
            
            # 设置窗口大小和用户代理
            chrome_options.add_argument(f'--window-size={config.browser.window_width},{config.browser.window_height}')
            chrome_options.add_argument(f'--user-agent={config.browser.user_agent}')
            
            # 性能优化选项
            if config.browser.disable_images:
                prefs = {"profile.managed_default_content_settings.images": 2}
                chrome_options.add_experimental_option("prefs", prefs)
            
            if config.browser.disable_css:
                chrome_options.add_argument('--disable-css')
            
            # 检查是否使用远程WebDriver
            remote_url = remote_url or os.getenv('SELENIUM_HUB_URL')
            
            if remote_url:
                # 使用远程WebDriver连接到Selenium Grid (Selenium 4 语法)
                print(f"连接到远程Selenium Hub: {remote_url}")
                self.driver = webdriver.Remote(
                    command_executor=remote_url,
                    options=chrome_options
                )
            else:
                # 本地WebDriver - 使用webdriver-manager自动管理ChromeDriver
                try:
                    from webdriver_manager.chrome import ChromeDriverManager
                    service = Service(ChromeDriverManager().install())
                    self.driver = webdriver.Chrome(service=service, options=chrome_options)
                except ImportError:
                    print("webdriver-manager未安装，尝试使用系统ChromeDriver")
                    self.driver = webdriver.Chrome(options=chrome_options)
            
            self.driver.implicitly_wait(config.browser.implicit_wait)
            self.driver.set_page_load_timeout(config.browser.page_load_timeout)
            
            print("✅ 浏览器驱动初始化成功")
            
        except Exception as e:
            print(f"❌ 浏览器初始化失败: {e}")
            if "ChromeDriver" in str(e) or "chromedriver" in str(e):
                print("请确保已安装 ChromeDriver 并添加到 PATH 环境变量中")
                print("或者安装 webdriver-manager: pip install webdriver-manager")
            raise e

    def get_page(self, url):
        try:
            self.driver.get(url)
            WebDriverWait(self.driver, config.web.element_wait_timeout).until(
                EC.presence_of_element_located((By.ID, config.web.code_input_id))
            )
        except TimeoutException:
            print("页面加载超时")
            raise
    
    def get_screenshot(self, filename=None):
        """获取页面截图并保存"""
        try:
            # 如果没有提供文件名，则使用时间戳生成
            if filename is None:
                # 确保截图目录存在
                os.makedirs(config.file.screenshot_dir, exist_ok=True)
                filename = f"{config.file.screenshot_dir}/{config.file.screenshot_prefix}_{int(time.time())}.{config.file.screenshot_format}"
            
            # 确保文件名有正确的后缀
            if not filename.endswith(f".{config.file.screenshot_format}"):
                filename += f".{config.file.screenshot_format}"
            
            # 获取完整页面截图
            self.driver.save_screenshot(filename)
            print(f"截图已保存到: {filename}")
            
            # 返回文件的绝对路径
            return os.path.abspath(filename)
        except Exception as e:
            print(f"截图失败: {e}")
            return None

    def enter_code_and_submit(self, code_str):
        try:
            code_field = self.driver.find_element(By.ID, config.web.code_input_id)
            code_field.clear()
            code_field.send_keys(code_str)
            
            self.driver.execute_script(f"$('{config.web.submit_button_selector}').click()")
        except (NoSuchElementException, TimeoutException) as e:
            print(f"操作失败: {e}")
            raise
    
    def maximize_window(self):
        """将浏览器窗口最大化"""
        try:
            self.driver.maximize_window()
            print("浏览器窗口已最大化")
        except Exception as e:
            print(f"窗口最大化失败: {e}")
    
    def fullscreen(self):
        """将浏览器设置为全屏模式"""
        try:
            self.driver.fullscreen_window()
            print("浏览器已进入全屏模式")
        except Exception as e:
            print(f"全屏模式设置失败: {e}")
            # 如果全屏失败，尝试最大化窗口作为备选方案
            self.maximize_window()

    def close(self):
        if hasattr(self, 'driver') and self.driver:
            self.driver.quit()

if __name__ == "__main__":
    driver = BrowserDriver()
    try:
        driver.get_page(config.web.base_url)
        
        # 获取并保存截图
        screenshot_path = driver.get_screenshot()
        print(f"截图保存路径: {screenshot_path}")
        
        driver.enter_code_and_submit("")
        time.sleep(10)
    finally:
        driver.close()
    
