# 爬虫代码重构说明

## 重构内容

### 1. 提取URL拼接逻辑
原来的URL拼接逻辑被提取为独立的函数 `extract_queue_url(driver, logger=None)`：
- 从浏览器cookies中提取QueueIT参数（EventId, QueueId, IssueTime, Hash）
- 构建完整的队列URL
- 支持错误处理和日志记录

### 2. 循环获取多个URL
程序现在会循环获取5个URL（可配置）：
- 每次获取URL后等待30秒
- 刷新页面获取新的参数
- 记录每次获取的结果

### 3. URL保存功能
新增 `save_urls_to_file(urls, logger=None)` 函数：
- 将所有获取到的URL保存到带时间戳的txt文件中
- 文件保存在 `data/` 目录下
- 文件格式：`queue_urls_YYYYMMDD_HHMMSS.txt`
- 包含生成时间、URL数量和详细列表

## 主要改进

### 1. 代码模块化
- 将URL拼接逻辑提取为独立的 `extract_queue_url` 函数
- 新增 `save_urls_to_file` 函数用于批量文件保存操作
- 新增 `append_url_to_file` 函数用于单个URL追加保存
- 新增 `create_url_file` 函数用于创建URL文件
- 提高了代码的可重复使用性和可维护性

### 2. 可配置的爬虫参数
- 新增 `CrawlerConfig` 配置类
- `loop_count`: 循环获取URL的次数（默认30次）
- `enable_fullscreen`: 是否启用浏览器全屏模式（默认True）
- `loop_interval`: 循环间隔时间（默认0秒，即连续执行）
- 支持通过环境变量进行配置

### 3. 实时文件写入
- 每次获取到URL后立即写入文件
- 避免程序异常导致的数据丢失
- 提供实时的进度反馈

### 4. 完善的错误处理
- 在URL提取过程中增加了异常捕获
- 在文件保存过程中增加了错误处理
- 统一使用logger进行日志记录

### 5. 统一日志记录
- 所有新函数都使用传入的logger参数
- 保持了与原有代码风格的一致性
- 便于调试和问题追踪

### 6. 自动文件管理
- 自动生成带时间戳的文件名
- 避免文件名冲突
- 便于文件管理和归档

## 使用方式

运行程序后，它会：
1. 执行原有的验证码识别和提交流程
2. 成功后循环获取5个不同的队列URL
3. 将所有URL保存到 `data/queue_urls_时间戳.txt` 文件中

## 配置选项

### 爬虫配置
- `LOOP_COUNT`: 循环获取URL的次数（默认30次）
- `ENABLE_FULLSCREEN`: 是否启用浏览器全屏模式（默认True）
- `LOOP_INTERVAL`: 循环间隔时间，单位秒（默认0秒，即连续执行）

### 环境变量配置示例
```bash
export LOOP_COUNT=50
export ENABLE_FULLSCREEN=false
export LOOP_INTERVAL=5
```

### 文件输出
程序会自动创建带时间戳的文件名，格式为：`queue_urls_YYYYMMDD_HHMMSS.txt`

每次获取到URL后会立即追加到文件中，文件内容格式：
```
=== Queue URLs Collection Started at 2024-01-01 12:00:00 ===

[1] 2024-01-01 12:00:01 - https://example.com/queue?token=xxx
[2] 2024-01-01 12:00:32 - https://example.com/queue?token=yyy
...
```