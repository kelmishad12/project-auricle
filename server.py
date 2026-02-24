from fastapi import FastAPI, Depends, HTTPException
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Dict, Any

from src.core.graph import AuricleGraph
from src.adapters.config import get_providers

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("🚀 Project Auricle Server starting...")
    yield
    print("🛑 Project Auricle Server shutting down...")

app = FastAPI(title="Project Auricle Server", description="Agentic API for Contextual Briefings", lifespan=lifespan)

class BriefingRequest(BaseModel):
    user_email: str
    env: str = "dev"
    
@app.post("/api/v1/briefings/generate")
async def generate_briefing(req: BriefingRequest):
    println("Generating briefing for user: ", req.user_email)
    providers = get_providers(env=req.env)
    
    # Initialize Graph with injected dependencies
    graph = AuricleGraph(
        mail_provider=providers["mail_provider"], 
        cal_provider=providers["cal_provider"]
    )
    
    initial_state = {
        "messages": [],
        "email_summaries": [],
        "calendar_events": [],
        "briefing": "",
        "safety_check_passed": False
    }
    
    # Invoke LangGraph asynchronously
    final_state = await graph.ainvoke(initial_state)
    
    return {
        "status": "success",
        "briefing": final_state.get("briefing"),
        "safety_passed": final_state.get("safety_check_passed")
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
