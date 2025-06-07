#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from browser_driver import BrowserDriver
from volcengine_ai import VolcEngineAI
from config import get_config
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# 获取配置
config = get_config()

# 配置日志
logging.basicConfig(
    level=getattr(logging, config.log.level),
    format=config.log.format
)
logger = logging.getLogger(__name__)

def validate_code(code):
    """验证识别出的验证码是否有效"""
    if not code:
        return False
    # 可以添加更多验证逻辑，例如长度检查、格式检查等
    return True

def check_success_page(driver):
    """检查是否成功跳转到目标页面"""
    try:
        # 检查是否出现成功页面的标志元素
        WebDriverWait(driver.driver, config.web.success_check_timeout).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, config.web.success_page_selector))
        )
        
        # 检查页面URL是否发生变化
        current_url = driver.driver.current_url
        for keyword in config.web.success_url_keywords:
            if keyword in current_url.lower():
                return True
                
        # 检查页面是否包含成功相关的文本
        page_text = driver.driver.page_source
        for keyword in config.web.success_keywords:
            if keyword in page_text.lower():
                return True
                
        return False
    except (TimeoutException, NoSuchElementException):
        return False

def process_captcha_and_submit(driver, ai):
    """处理验证码识别和提交的完整流程"""
    try:
        # 获取截图
        logger.info("正在截取页面图片...")
        screenshot_path = driver.get_screenshot()
        logger.info(f"截图已保存至: {screenshot_path}")
        
        # 确认文件存在
        if not os.path.exists(screenshot_path):
            logger.error(f"错误：截图文件不存在: {screenshot_path}")
            return False
        
        # 使用视觉模型分析图片
        logger.info("正在分析图片...")
        
        # 使用vision_chat_completion方法处理图片
        result = ai.vision_chat_completion(
            text_prompt=config.ai.captcha_prompt,
            image_path=screenshot_path,
            image_format=config.file.screenshot_format,
            model=config.ai.vision_model
        )
        
        # 处理结果
        if result and hasattr(result, 'choices') and len(result.choices) > 0:
            code = result.choices[0].message.content.strip()
            logger.info(f"识别到的验证码: {code}")
            
            # 验证识别结果
            if not validate_code(code):
                logger.warning("验证码识别结果可能不正确，但仍将尝试提交")
            
            # 输入验证码并提交
            logger.info("正在输入验证码并提交...")
            driver.enter_code_and_submit(code)
            
            # 等待页面响应
            time.sleep(2)
            
            return True
        else:
            logger.error("未能获取有效的分析结果")
            return False
            
    except Exception as e:
        logger.exception(f"处理验证码过程中出现错误: {e}")
        return False

def main():
    driver = None
    start_time = time.time()
    try:
        # 初始化浏览器驱动
        logger.info("正在初始化浏览器驱动...")
        driver = BrowserDriver(headless=config.browser.headless)
        
        # 访问目标页面
        logger.info(f"正在访问页面: {config.web.base_url}")
        driver.get_page(config.web.base_url)
        
        # 初始化火山引擎AI
        logger.info("正在初始化AI模型...")
        ai = VolcEngineAI(api_key=config.ai.api_key)
        
        # 重试循环
        for attempt in range(1, config.retry.max_attempts + 1):
            logger.info(f"第 {attempt} 次尝试验证码识别和提交")
            
            # 处理验证码识别和提交
            if process_captcha_and_submit(driver, ai):
                # 检查是否成功跳转
                logger.info("正在检查页面跳转结果...")
                
                if check_success_page(driver):
                    logger.info("✅ 验证码验证成功，已跳转到目标页面！")
                    
                    # 验证成功后，将浏览器设置为全屏
                    logger.info("正在设置浏览器全屏模式...")
                    driver.fullscreen()
                    
                    try:
                        result_message = driver.driver.find_element(By.CSS_SELECTOR, config.web.success_page_selector).text
                        logger.info(f"页面内容: {result_message}")
                    except:
                        logger.info("已成功跳转，但无法获取具体页面内容")
                    break
                else:
                    logger.warning(f"❌ 第 {attempt} 次尝试失败，未能跳转到成功页面")
                    
                    if attempt < config.retry.max_attempts:
                        wait_time = config.retry.wait_time
                        if config.retry.exponential_backoff:
                            wait_time = min(wait_time * (config.retry.backoff_multiplier ** (attempt - 1)), config.retry.max_wait_time)
                        
                        logger.info(f"等待 {wait_time} 秒后进行第 {attempt + 1} 次重试...")
                        time.sleep(wait_time)
                        
                        # 刷新页面，准备下一次尝试
                        try:
                            driver.driver.refresh()
                            WebDriverWait(driver.driver, config.web.element_wait_timeout).until(
                                EC.presence_of_element_located((By.ID, config.web.code_input_id))
                            )
                        except TimeoutException:
                            logger.error("页面刷新后无法找到验证码输入框")
                            break
                    else:
                        logger.error(f"已达到最大重试次数 ({config.retry.max_attempts})，验证码验证失败")
            else:
                logger.error(f"第 {attempt} 次验证码处理失败")
                if attempt < config.retry.max_attempts:
                    logger.info(f"等待 {config.retry.wait_time} 秒后重试...")
                    time.sleep(config.retry.wait_time)
                else:
                    logger.error(f"已达到最大重试次数 ({config.retry.max_attempts})，程序终止")
                    
    except Exception as e:
        logger.exception(f"执行过程中出现错误: {e}")
    finally:
        # 确保浏览器资源被释放
        if driver:
            time.sleep(10)
            logger.info("正在关闭浏览器...")
            driver.close()
        
        # 输出总执行时间
        elapsed_time = time.time() - start_time
        logger.info(f"总执行时间: {elapsed_time:.2f}秒")

if __name__ == "__main__":
    main()