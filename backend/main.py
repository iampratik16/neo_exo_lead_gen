from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict
import asyncio

from models import SearchRequest, Lead, ScrapeProgress
from scraper.engine import LeadScraperEngine

app = FastAPI(title="Bassi Leads API", version="1.0")

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory session tracking for progress
active_sessions: Dict[str, ScrapeProgress] = {}
scraped_leads: Dict[str, List[Lead]] = {}
connected_clients: List[WebSocket] = []

@app.post("/api/start")
async def start_scraping(request: SearchRequest, background_tasks: BackgroundTasks):
    session_id = f"{request.country}_{request.city}_{len(active_sessions)}"
    
    active_sessions[session_id] = ScrapeProgress(
        status="starting",
        leads_found=0,
        current_action="Initializing Playwright browser..."
    )
    scraped_leads[session_id] = []
    
    # Start the scraping task
    background_tasks.add_task(run_scraper_task, session_id, request)
    return {"session_id": session_id}

async def run_scraper_task(session_id: str, request: SearchRequest):
    engine = LeadScraperEngine(
        on_progress=lambda p: update_progress(session_id, p),
        on_lead=lambda l: add_lead(session_id, l)
    )
    try:
        await engine.run(request)
        active_sessions[session_id].status = "completed"
        active_sessions[session_id].current_action = "Scraping finished perfectly."
    except Exception as e:
        active_sessions[session_id].status = "failed"
        active_sessions[session_id].current_action = f"Error: {str(e)}"

def update_progress(session_id: str, progress: ScrapeProgress):
    active_sessions[session_id] = progress
    # In a real app we'd broadcast via websocket here

def add_lead(session_id: str, lead: Lead):
    scraped_leads[session_id].append(lead)

@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    if session_id not in active_sessions:
        return {"error": "Session not found"}
    return active_sessions[session_id]

@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    if session_id not in scraped_leads:
        return {"error": "Session not found"}
    return scraped_leads[session_id]
