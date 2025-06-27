#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from src.core.browser_driver import BrowserDriver
from src.ai.volcengine_ai import VolcEngineAI
from src.config.config import get_config
from src.utils.logger import setup_logger
import os
import time
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import urllib.parse
import datetime

def extract_queue_url(driver, logger=None):
    """提取QueueIT参数并构建URL"""
    try:
        base_url = driver.driver.current_url
        e = ''
        q = ''
        ts = ''
        h = ''
        
        # 提取QueueIT参数
        for cookie in driver.driver.get_cookies():
            if 'QueueIT' in cookie['name']:
                decoded_value = urllib.parse.unquote(cookie['value'])
                params = decoded_value.split('&')
                
                for param in params:
                    if '=' in param:
                        key, value = param.split('=', 1)
                        if key == 'EventId':
                            e = value
                        elif key == 'QueueId':
                            q = value
                        elif key == 'IssueTime':
                            ts = value
                        elif key == 'Hash':
                            h = value
        
        # 构建最终URL
        if e and q and ts and h:
            f_url = base_url + "?queueittoken=e_{e}~q_{q}~ts_{ts}~ce_true~rt_queue~h_{h}".format(e=e, q=q, ts=ts, h=h)
            return f_url
        else:
            return None
            
    except Exception as e:
        if logger:
            logger.error(f"提取URL时出错: {e}")
        else:
            print(f"提取URL时出错: {e}")
        return None

def save_urls_to_file(urls, logger=None):
    """将URL列表保存到txt文件"""
    try:
        # 创建文件名，包含时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"queue_urls_{timestamp}.txt"
        
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"总共获取到 {len(urls)} 个URL\n")
            f.write("-" * 50 + "\n")
            
            for i, url in enumerate(urls, 1):
                f.write(f"{i}. {url}\n")
        
        if logger:
            logger.info(f"URL已保存到文件: {filepath}")
        else:
            print(f"URL已保存到文件: {filepath}")
        return filepath
        
    except Exception as e:
        if logger:
            logger.error(f"保存URL到文件时出错: {e}")
        else:
            print(f"保存URL到文件时出错: {e}")
        return None

def append_url_to_file(url, filepath, index, logger=None):
    """将单个URL追加到文件"""
    try:
        with open(filepath, 'a', encoding='utf-8') as f:
            f.write(f"{index}. {url}\n")
        
        if logger:
            logger.info(f"URL已追加到文件: {url}")
        return True
        
    except Exception as e:
        if logger:
            logger.error(f"追加URL到文件时出错: {e}")
        else:
            print(f"追加URL到文件时出错: {e}")
        return False

def create_url_file(logger=None):
    """创建URL文件并返回文件路径"""
    try:
        # 创建文件名，包含时间戳
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"queue_urls_{timestamp}.txt"
        
        # 确保data目录存在
        os.makedirs("data", exist_ok=True)
        filepath = os.path.join("data", filename)
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"生成时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"循环获取URL结果:\n")
            f.write("-" * 50 + "\n")
        
        if logger:
            logger.info(f"创建URL文件: {filepath}")
        return filepath
        
    except Exception as e:
        if logger:
            logger.error(f"创建URL文件时出错: {e}")
        else:
            print(f"创建URL文件时出错: {e}")
        return None

def main():
    """主函数"""
    # 获取配置
    config = get_config()
    logger = setup_logger(__name__)

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
        
        # 验证成功后，循环获取多个URL
        if driver:
            logger.info(f"开始循环获取多个URL，总共{config.crawler.loop_count}次...")
            
            # 创建URL文件
            url_file_path = create_url_file(logger)
            if not url_file_path:
                logger.error("创建URL文件失败，程序终止")
                return
            
            success_count = 0
            
            # 循环获取多个URL，每次都重新创建浏览器
            for i in range(config.crawler.loop_count):
                try:
                    # 第一次使用现有的driver，后续创建新的
                    current_driver = driver if i == 0 else None
                    
                    if i > 0:
                        logger.info(f"第{i+1}次尝试：创建新的浏览器实例...")
                        current_driver = BrowserDriver(headless=config.browser.headless)
                        
                        # 访问目标页面并重新进行验证流程
                        current_driver.get_page(config.web.base_url)
                        
                        # 重新进行验证码识别和提交流程
                        if process_captcha_and_submit(current_driver, ai):
                            if check_success_page(current_driver):
                                logger.info(f"第{i+1}次验证成功")
                                # 根据配置决定是否全屏
                                if config.crawler.enable_fullscreen:
                                    current_driver.fullscreen()
                            else:
                                logger.warning(f"第{i+1}次验证失败")
                                current_driver.close()
                                continue
                        else:
                            logger.warning(f"第{i+1}次验证码处理失败")
                            current_driver.close()
                            continue
                    
                    # 获取URL
                    url = extract_queue_url(current_driver, logger)
                    if url:
                        success_count += 1
                        logger.info(f"第{i+1}次获取URL成功: {url}")
                        # 立即将URL追加到文件
                        append_url_to_file(url, url_file_path, success_count, logger)
                    else:
                        logger.warning(f"第{i+1}次获取URL失败")
                    
                    # 关闭当前浏览器实例
                    if current_driver:
                        logger.info(f"关闭第{i+1}次的浏览器实例")
                        current_driver.close()
                    
                    # 根据配置决定是否等待
                    if config.crawler.loop_interval > 0 and i < config.crawler.loop_count - 1:
                        logger.info(f"等待{config.crawler.loop_interval}秒后进行第{i+2}次尝试...")
                        time.sleep(config.crawler.loop_interval)
                        
                except Exception as e:
                    logger.error(f"第{i+1}次获取URL时出错: {e}")
                    if 'current_driver' in locals() and current_driver:
                        current_driver.close()
            
            logger.info(f"循环完成，总共成功获取{success_count}个URL，已保存到文件: {url_file_path}")
            
            # 设置driver为None，避免在finally中重复关闭
            driver = None
                    
    except Exception as e:
        logger.exception(f"执行过程中出现错误: {e}")
    finally:
        # 确保浏览器资源被释放
        if driver:
            logger.info("正在关闭浏览器...")
            driver.close()
        
        # 输出总执行时间
        elapsed_time = time.time() - start_time
        logger.info(f"总执行时间: {elapsed_time:.2f}秒")

if __name__ == "__main__":
    main()