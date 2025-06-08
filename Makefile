# Docker调试和管理命令

.PHONY: debug restart clean build logs status help

# 默认目标
help:
	@echo "Docker调试命令:"
	@echo "  make debug    - 完全重建并启动 (无缓存)"
	@echo "  make restart  - 快速重启服务"
	@echo "  make clean    - 深度清理Docker资源"
	@echo "  make build    - 重新构建镜像"
	@echo "  make logs     - 查看实时日志"
	@echo "  make status   - 查看服务状态"
	@echo "  make stop     - 停止所有服务"
	@echo "  make start    - 启动所有服务"

# 调试模式 - 完全重建
debug:
	@echo "🔧 启动调试模式..."
	docker-compose down -v --remove-orphans
	docker system prune -f
	docker-compose build --no-cache --pull
	docker-compose up -d
	@echo "✅ 调试环境已启动"
	make status

# 快速重启
restart:
	@echo "⚡ 快速重启服务..."
	docker-compose down
	docker-compose up -d
	make status

# 深度清理
clean:
	@echo "🧹 深度清理Docker资源..."
	docker-compose down -v --remove-orphans
	docker system prune -a -f
	docker volume prune -f
	@echo "✅ 清理完成"

# 重新构建
build:
	@echo "🔨 重新构建镜像..."
	docker-compose build --no-cache

# 查看日志
logs:
	@echo "📋 实时日志 (Ctrl+C 退出):"
	docker-compose logs -f

# 查看状态
status:
	@echo "📊 服务状态:"
	docker-compose ps
	@echo ""
	@echo "🌐 访问地址:"
	@echo "  API服务: http://localhost:8000"
	@echo "  Selenium Grid: http://localhost:4444"

# 停止服务
stop:
	@echo "⏹️  停止所有服务..."
	docker-compose down

# 启动服务
start:
	@echo "🚀 启动所有服务..."
	docker-compose up -d
	make status

# 单独重启某个服务
restart-api:
	docker-compose restart captcha-solver
	docker-compose logs -f captcha-solver

restart-scheduler:
	docker-compose restart task-scheduler
	docker-compose logs -f task-scheduler

restart-selenium:
	docker-compose restart selenium-hub chrome
	docker-compose logs -f selenium-hub