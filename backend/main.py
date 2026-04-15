"""
Neo Eco Cleaning — Lead Generator API
=======================================
FastAPI backend that orchestrates the Google Maps scraping pipeline
and serves progress/results to the frontend.

v2.1 — Added /api/filters endpoint, filter passthrough to engine,
       and dual export (xlsx / csv) support.
"""

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from typing import Dict, List

from models import SearchRequest, Lead, ScrapeProgress
from scraper.engine import (
    LeadScraperEngine,
    export_to_excel,
    export_to_csv,
    AVAILABLE_BUSINESS_TYPES,
    AVAILABLE_LOCATIONS,
)

app = FastAPI(
    title="Neo Eco Cleaning — Lead Generator API",
    version="2.1",
    description="Google Maps lead scraper for property management firms and estate agents in London.",
)

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
export_paths: Dict[str, str] = {}
export_formats: Dict[str, str] = {}


@app.get("/api/filters")
async def get_filters():
    """Return the available filter options for the frontend.

    This powers the business-type chips and location selector.
    """
    return {
        "business_types": AVAILABLE_BUSINESS_TYPES,
        "locations": AVAILABLE_LOCATIONS,
    }


@app.post("/api/start")
async def start_scraping(request: SearchRequest, background_tasks: BackgroundTasks):
    """Trigger a new scraping run.

    Returns a session_id that can be used to poll progress and fetch results.
    """
    session_id = f"neo_eco_{len(active_sessions)}"

    active_sessions[session_id] = ScrapeProgress(
        status="starting",
        leads_found=0,
        current_action="Initialising Playwright browser\u2026",
    )
    scraped_leads[session_id] = []
    export_formats[session_id] = request.export_format or "xlsx"

    # Start the scraping task in the background
    background_tasks.add_task(run_scraper_task, session_id, request)
    return {"session_id": session_id}


async def run_scraper_task(session_id: str, request: SearchRequest):
    """Background task: run the full scraping pipeline."""
    engine = LeadScraperEngine(
        on_progress=lambda p: update_progress(session_id, p),
        on_lead=lambda lead: add_lead(session_id, lead),
    )
    try:
        await engine.run(request)
        active_sessions[session_id].status = "completed"
        active_sessions[session_id].current_action = "Scraping finished. Export ready."

        # Store the export path for the download endpoint
        if engine.all_leads:
            try:
                fmt = export_formats.get(session_id, "xlsx")
                if fmt == "csv":
                    path = export_to_csv(engine.all_leads)
                else:
                    path = export_to_excel(engine.all_leads)
                export_paths[session_id] = path
            except Exception as exc:
                print(f"[api] Export failed: {exc}")

    except Exception as e:
        active_sessions[session_id].status = "failed"
        active_sessions[session_id].current_action = f"Error: {str(e)}"


def update_progress(session_id: str, progress: ScrapeProgress):
    active_sessions[session_id] = progress


def add_lead(session_id: str, lead: Lead):
    scraped_leads[session_id].append(lead)


@app.get("/api/progress/{session_id}")
async def get_progress(session_id: str):
    """Poll the current status of a scraping session."""
    if session_id not in active_sessions:
        raise HTTPException(status_code=404, detail="Session not found")
    return active_sessions[session_id]


@app.get("/api/results/{session_id}")
async def get_results(session_id: str):
    """Fetch all leads discovered in a scraping session."""
    if session_id not in scraped_leads:
        raise HTTPException(status_code=404, detail="Session not found")
    return scraped_leads[session_id]


@app.get("/api/export/{session_id}")
async def download_export(session_id: str):
    """Download the export file (xlsx or csv) for a completed session."""
    if session_id not in export_paths:
        raise HTTPException(status_code=404, detail="No export available for this session")

    filepath = export_paths[session_id]
    fmt = export_formats.get(session_id, "xlsx")

    if fmt == "csv":
        return FileResponse(
            path=filepath,
            media_type="text/csv",
            filename=filepath.split("/")[-1],
        )
    else:
        return FileResponse(
            path=filepath,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            filename=filepath.split("/")[-1],
        )
