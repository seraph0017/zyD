```
# 智能验证码自动识别系统 (zyD)

基于火山引擎AI和Selenium的智能验证码自动识别解决方案，支持
分布式部署和高并发处理。

## 🌟 功能特性

- 🤖 **AI驱动识别** - 集成火山引擎豆包大模型进行验证码视觉
识别
- 🚀 **Docker容器化部署** - 支持一键部署，环境隔离
- 🕷️ **Selenium Grid分布式** - 支持多节点并发处理
- 📊 **任务队列管理** - Redis队列支持异步任务处理和调度
- 🔄 **智能重试机制** - 指数退避重试和错误恢复
- 📈 **实时监控** - 完整的日志记录和任务状态跟踪
- ⚙️ **灵活配置** - 支持JSON配置文件和环境变量
- 🔌 **RESTful API** - 提供HTTP接口便于系统集成
- 📱 **多模态支持** - 支持文本和视觉模型的组合使用

## 🏗️ 系统架构

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   API Server    │    │  Task Scheduler │    │   Redis Queue   │
│   (Flask)       │◄──►│   (Python)      │◄──►│   (Message)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
│                       │                       │
▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│ Selenium Hub    │    │  Chrome Node 1  │    │  Chrome Node 2  │
│   (Grid)        │◄──►│   (Browser)     │    │   (Browser)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
│
▼
┌─────────────────┐
│ VolcEngine AI   │
│ (Vision Model)  │
└─────────────────┘

```

## 📋 环境要求

- **Python**: 3.9+
- **Docker**: 20.10+
- **Docker Compose**: 2.0+
- **内存**: 建议4GB+
- **磁盘**: 建议2GB+可用空间
- **火山引擎API**: 需要有效的API Key

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <repository-url>
cd zyD
```
### 2. 配置环境
```
# 复制配置文件模板
cp src/config/config.example.json config/config.
json

# 编辑配置文件，填入您的API Key和目标URL
vim config/config.json
```
重要配置项：

- ai.api_key : 火山引擎API密钥
- web.base_url : 目标验证码页面URL
- web.code_input_id : 验证码输入框ID
- web.submit_button_selector : 提交按钮选择器
### 3. 启动服务 Docker部署（推荐）
```
# 启动所有服务
docker-compose up -d

# 查看服务状态
docker-compose ps

# 查看日志
docker-compose logs -f
``` 本地开发
```
# 使用Conda环境
conda env create -f environment.yml
conda activate captcha-solver

# 或使用pip
pip install -r requirements.txt

# 运行主程序
python main.py
```
### 4. 验证部署
```
# 测试API接口
curl http://localhost:8000/health

# 访问Selenium Grid控制台
open http://localhost:4444

# 提交测试任务
curl -X POST http://localhost:8000/submit_task \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com/captcha"}'
```
## 🔧 使用方式
### 单次执行模式
```
# 直接运行验证码识别
python main.py
```
### API服务模式
```
# 启动API服务器
python -m src.api.server

# 启动任务调度器
python -m src.core.scheduler
```
### API接口 提交任务
```
POST /submit_task
Content-Type: application/json

{
  "url": "https://target-site.com/captcha",
  "priority": "high"
}
``` 查询任务状态
```
GET /task_status/{task_id}
``` 健康检查
```
GET /health
```
## ⚙️ 配置说明
### 主要配置文件
- config/config.json - 主配置文件
- docker-compose.yml - Docker服务编排
- environment.yml - Conda环境配置
### 关键配置项
配置项 说明 默认值 browser.headless 无头模式 true ai.vision_model 视觉识别模型 doubao-1.5-vision-lite-250315 retry.max_attempts 最大重试次数 5 web.success_check_timeout 成功检查超时 10

## 📊 监控和日志
### 日志查看
```
# Docker环境
docker-compose logs -f captcha-solver

# 本地环境
tail -f logs/app.log
```
### Redis队列监控
```
# 连接Redis查看队列状态
docker-compose exec redis redis-cli

# 查看队列长度
LLEN captcha_tasks

# 查看任务结果
HGETALL task_results
```
## 🔍 故障排除
### 常见问题
1. 验证码识别失败
   
   - 检查AI API密钥是否正确
   - 确认图片质量和清晰度
   - 调整识别提示词
2. 浏览器启动失败
   
   - 检查Chrome选项配置
   - 确认Selenium Grid连接
   - 查看Docker容器状态
3. 任务队列阻塞
   
   - 检查Redis连接
   - 重启调度器服务
   - 清理异常任务
### 清理命令
```
# 清理Docker资源
docker-compose down -v
docker system prune -f

# 清理Redis队列
docker-compose exec redis redis-cli FLUSHDB
```
## 🛠️ 开发指南
### 项目结构
```
src/
├── ai/                 # AI模型集成
│   └── volcengine_ai.py
├── api/                # REST API服务
│   └── server.py
├── config/             # 配置管理
│   ├── config.py
│   └── config.example.json
├── core/               # 核心功能
│   ├── browser_driver.py
│   └── scheduler.py
├── utils/              # 工具函数
│   └── logger.py
└── main.py            # 主入口
```
### 扩展开发
1. 添加新的AI模型
   
   - 在 src/ai/ 目录下创建新的模型类
   - 实现统一的接口规范
2. 自定义验证码处理逻辑
   
   - 修改 src/main.py 中的处理流程
   - 添加特定网站的适配代码
3. 扩展API接口
   
   - 在 src/api/server.py 中添加新的路由
   - 实现相应的业务逻辑
## 📄 许可证
本项目采用 MIT 许可证 - 查看 LICENSE 文件了解详情。

## 🤝 贡献
欢迎提交 Issue 和 Pull Request！

## 📞 支持
如有问题，请通过以下方式联系：

- 提交 GitHub Issue
- 发送邮件至项目维护者
注意 : 请确保遵守目标网站的使用条款和相关法律法规。本工具仅供学习和研究使用。

```

主要更新内容：

1. **项目名称和定位更准确** - 基于实际代码分析，这是一个专
门的验证码识别系统
2. **技术栈描述更精确** - 突出火山引擎AI的核心作用
3. **架构图更符合实际** - 反映了真实的系统组件关系
4. **配置说明更详细** - 基于实际的配置文件结构
5. **使用方式更清晰** - 区分了单次执行和服务模式
6. **API文档更完整** - 基于实际的API实现
7. **故障排除更实用** - 针对常见问题提供解决方案
8. **开发指南更具体** - 基于真实的项目结构
```