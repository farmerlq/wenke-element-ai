#!/bin/bash

echo "正在启动AI聊天后端服务..."

# 检查Docker是否安装
if ! command -v docker &> /dev/null; then
    echo "错误: Docker未安装，请先安装Docker"
    exit 1
fi

# 检查Docker Compose是否安装
if ! command -v docker-compose &> /dev/null; then
    echo "错误: Docker Compose未安装，请先安装Docker Compose"
    exit 1
fi

echo "构建并启动服务..."
docker-compose up --build -d

echo "服务启动完成!"
echo "应用地址: http://localhost:8000"
echo "健康检查: http://localhost:8000/health"
echo "MySQL端口: 3306"
echo "Redis端口: 6379"