from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.api import agents, sessions, chat
from app.db.database import engine
from app.models import agent, message, session

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)

# 创建数据库表
agent.Base.metadata.create_all(bind=engine)
message.Base.metadata.create_all(bind=engine)
session.Base.metadata.create_all(bind=engine)

app = FastAPI(title="WenKe AI Backend", version="1.0.0")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["sessions"])
app.include_router(chat.router, prefix="/api/chat", tags=["chat"])

@app.get("/")
async def root():
    return {"message": "WenKe AI Backend is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)