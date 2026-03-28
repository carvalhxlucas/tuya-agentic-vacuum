from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from agent import create_agent, execute_agent
from agent.tools import get_device_state

LIFESPAN = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global LIFESPAN
    LIFESPAN = create_agent()
    yield
    LIFESPAN = None


app = FastAPI(
    title="AI Vacuum Robot API",
    description="API for controlling the vacuum robot via natural language",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str


class ActionPayload(BaseModel):
    action: str
    parameters: Optional[dict[str, Any]] = None
    executedAt: str


class ChatResponse(BaseModel):
    message: str
    actionPayload: Optional[ActionPayload] = None


class RobotStateResponse(BaseModel):
    status: str
    batteryLevel: int


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/robot/state", response_model=RobotStateResponse)
async def robot_state():
    state = get_device_state()
    if state is None:
        return RobotStateResponse(status="idle", batteryLevel=0)
    return RobotStateResponse(**state)


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    if LIFESPAN is None:
        raise HTTPException(status_code=503, detail="Agent not initialized")
    try:
        response_message, action_name, action_params = execute_agent(LIFESPAN, request.message.strip())
        action_payload = None
        if action_name:
            action_payload = ActionPayload(
                action=action_name,
                parameters=action_params,
                executedAt=datetime.utcnow().isoformat() + "Z",
            )
        return ChatResponse(message=response_message, actionPayload=action_payload)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
