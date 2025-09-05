from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.db.database import engine, Base
from app.api import auth, chat, system
import uvicorn

# 创建数据库表
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AI聊天系统",
    description="基于FastAPI的AI聊天后端服务",
    version="1.0.0"
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(system.router)

@app.get("/")
async def root():
    return {"message": "AI聊天系统API服务已启动"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "ai-chat-backend"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)