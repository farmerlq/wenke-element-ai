# Docker 部署指南

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+

## 快速开始

### Linux/Mac
```bash
# 启动服务
./start.sh

# 停止服务
./stop.sh
```

### Windows
```bash
# 启动服务
start.bat

# 停止服务
stop.bat
```

## 手动部署

```bash
# 构建并启动所有服务
docker-compose up --build -d

# 仅启动服务（不重新构建）
docker-compose up -d

# 停止服务
docker-compose down

# 查看服务状态
docker-compose ps

# 查看应用日志
docker-compose logs app
```

## 服务说明

### 容器服务
- **app**: 主应用服务，运行在端口 8000
- **mysql**: MySQL数据库，运行在端口 3306
- **redis**: Redis缓存，运行在端口 6379

### 网络配置
所有服务都连接到 `ai-network` 网络，容器间可以通过服务名互相访问。

## 环境变量配置

应用支持以下环境变量（在 `docker-compose.yml` 中配置）：

### 数据库配置
- `DB_HOST`: 数据库主机（默认: mysql）
- `DB_PORT`: 数据库端口（默认: 3306）
- `DB_USER`: 数据库用户（默认: root）
- `DB_PASSWORD`: 数据库密码
- `DB_NAME`: 数据库名称（默认: ai_chat）
- `DB_CHARSET`: 数据库字符集（默认: utf8mb4）

### Redis配置
- `REDIS_HOST`: Redis主机（默认: redis）
- `REDIS_PORT`: Redis端口（默认: 6379）
- `REDIS_DB`: Redis数据库编号（默认: 0）

### 应用配置
- `APP_HOST`: 应用绑定地址（默认: 0.0.0.0）
- `APP_PORT`: 应用端口（默认: 8000）
- `DEBUG`: 调试模式（默认: False）

## 数据持久化

MySQL数据存储在名为 `mysql_data` 的Docker卷中，确保数据在容器重启后不会丢失。

## 健康检查

应用启动后，可以通过以下端点检查服务状态：

```bash
curl http://localhost:8000/health
```

## 故障排除

### 端口冲突
如果出现端口冲突，可以修改 `docker-compose.yml` 中的端口映射配置。

### 构建失败
确保Docker有足够的磁盘空间和内存资源。

### 数据库连接问题
检查MySQL容器是否正常启动，以及环境变量配置是否正确。