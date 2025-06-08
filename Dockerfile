FROM python:3.9-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖和Chrome
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    unzip \
    curl \
    xvfb \
    # 添加Google Chrome的官方GPG密钥和源
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" > /etc/apt/sources.list.d/google-chrome.list \
    # 更新包列表并安装Chrome
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    # 清理APT缓存
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/screenshots /app/logs /app/config

# 设置环境变量
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV DISPLAY=:99

# 暴露端口
EXPOSE 8000

# 默认命令
CMD ["python", "run.py"]