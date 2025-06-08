#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from browser_driver import BrowserDriver

def test_webdriver():
    """测试WebDriver是否正常工作"""
    try:
        print("正在测试WebDriver...")
        
        # 测试本地模式
        if not os.getenv('SELENIUM_HUB_URL'):
            print("测试本地WebDriver模式")
            driver = BrowserDriver(headless=True)
        else:
            print(f"测试远程WebDriver模式: {os.getenv('SELENIUM_HUB_URL')}")
            driver = BrowserDriver(headless=True, remote_url=os.getenv('SELENIUM_HUB_URL'))
        
        # 简单测试
        driver.get_page("https://www.google.com")
        print(f"✅ 成功访问页面，标题: {driver.driver.title}")
        
        driver.close()
        print("✅ WebDriver测试成功！")
        
    except Exception as e:
        print(f"❌ WebDriver测试失败: {e}")
        return False
    
    return True

if __name__ == "__main__":
    test_webdriver()