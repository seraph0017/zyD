#!/bin/bash

# 检查是否存在config.json
if [ ! -f "config.json" ]; then
    echo "创建配置文件..."
    cp config.example.json config.json
    echo "请编辑 config.json 文件，填入您的实际配置信息："
    echo "1. 设置 ai.api_key 为您的实际API密钥"
    echo "2. 设置 web.base_url 为目标网站URL"
    echo "3. 根据需要调整其他配置项"
else
    echo "config.json 已存在，跳过创建"
fi

# 创建必要的目录
mkdir -p logs screenshots config

echo "配置初始化完成！"