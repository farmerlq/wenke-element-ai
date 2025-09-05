@echo off
echo 正在启动AI聊天后端服务...

REM 检查Docker是否安装
docker --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker未安装，请先安装Docker
    pause
    exit /b 1
)

REM 检查Docker Compose是否安装
docker-compose --version >nul 2>&1
if errorlevel 1 (
    echo 错误: Docker Compose未安装，请先安装Docker Compose
    pause
    exit /b 1
)

echo 构建并启动服务...
docker-compose up --build -d

echo 服务启动完成!
echo 应用地址: http://localhost:8000
echo 健康检查: http://localhost:8000/health
echo MySQL端口: 3306
echo Redis端口: 6379

pause