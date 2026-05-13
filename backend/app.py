"""
Trinethra Supervisor Feedback Analyzer - Backend
Version: 2.1 (Production Ready)
Features: Persistence, Streaming, History, PDF Export, Enhanced Error Handling
"""

import os
import json
import logging
import asyncio
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, AsyncGenerator
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks, Response, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from pydantic import BaseModel, Field, field_validator
import httpx
import csv
import io
try:
    from fpdf import FPDF
except ImportError:
    # Fallback for different fpdf versions
    try:
        from fpdf2 import FPDF
    except ImportError:
        FPDF = None

# Local imports
from prompts import (
    EVIDENCE_EXTRACTION_PROMPT,
    SCORING_PROMPT,
    KPI_MAPPING_PROMPT,
    GAP_ANALYSIS_PROMPT,
    FOLLOWUP_QUESTIONS_PROMPT,
    SYSTEM_CONTEXT
)
from utils import (
    extract_json_from_response,
    validate_evidence,
    validate_score,
    safe_json_response
)
from database import init_db, save_analysis, get_history, get_analysis_by_id, delete_analysis

# Configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2")
MOCK_MODE = os.getenv("MOCK_MODE", "true").lower() == "true" # Default to true for easy demo
MAX_RETRIES = 3
TIMEOUT = 90  # Seconds
EXPORTS_DIR = Path(__file__).parent / "exports"
EXPORTS_DIR.mkdir(exist_ok=True)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Initialize FastAPI and Database
app = FastAPI(
    title="Trinethra Analyzer",
    version="2.1.0",
    description="Professional AI-powered supervisor feedback analyzer"
)

init_db()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Models
class TranscriptRequest(BaseModel):
    transcript: str = Field(..., min_length=50, max_length=15000)
    model: Optional[str] = Field("llama3.2")
    
    @field_validator('transcript')
    def validate_transcript(cls, v):
        if len(v) < 50:
            raise ValueError('Transcript must be at least 50 characters')
        return v

class UpdateRequest(BaseModel):
    results: Dict[str, Any]

# --- Helper Functions ---

async def query_ollama(prompt: str, model: str, temperature: float = 0.3) -> str:
    """Sends a request to Ollama with retry logic."""
    url = f"{OLLAMA_BASE_URL}/api/generate"
    
    for attempt in range(MAX_RETRIES + 1):
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as client:
                response = await client.post(
                    url,
                    json={
                        "model": model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": temperature,
                            "num_predict": 2000,
                        }
                    }
                )
                response.raise_for_status()
                return response.json().get("response", "")
        except Exception as e:
            if attempt == MAX_RETRIES:
                logger.error(f"Ollama final failure: {str(e)}")
                raise HTTPException(status_code=500, detail=f"Ollama error: {str(e)}")
            wait_time = 2 ** attempt
            logger.warning(f"Ollama attempt {attempt+1} failed, retrying in {wait_time}s...")
            await asyncio.sleep(wait_time)
    return ""

async def process_step(step_name: str, prompt: str, model: str, validator_func=None):
    """Processes a single analysis step."""
    logger.info(f"Running step: {step_name}")
    response_text = await query_ollama(prompt, model)
    data = extract_json_from_response(response_text)
    
    if validator_func and data:
        if not validator_func(data):
            logger.warning(f"Step {step_name} validation failed")
            return {"error": f"Validation failed", "raw": response_text[:100]}
    
    return data if data else {"error": "Parsing failed", "raw": response_text[:100]}

# --- Endpoints ---

@app.get("/health")
async def health():
    """Checks service health and Ollama connectivity."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(f"{OLLAMA_BASE_URL}/api/tags")
            ollama_status = "connected" if resp.status_code == 200 else "error"
            models = [m["name"] for m in resp.json().get("models", [])] if resp.status_code == 200 else []
    except:
        ollama_status = "disconnected"
        models = []
        
    return {
        "status": "healthy",
        "ollama": ollama_status,
        "models_available": models,
        "current_model": OLLAMA_MODEL
    }

@app.post("/analyze")
async def analyze_transcript(request: TranscriptRequest):
    """Full sequential analysis endpoint."""
    if MOCK_MODE:
        res = await get_mock_results(request.transcript)
        # Try to extract fellow name even in mock mode for realism
        import re
        match = re.search(r"Fellow,?\s+([A-Z][a-z]+)", request.transcript)
        res["fellow_name"] = match.group(1) if match else "Unknown Fellow"
        return res
    
    start_time = time.time()
    transcript = request.transcript
    model = request.model or OLLAMA_MODEL
    
    # 1. Evidence
    evidence_data = await process_step(
        "evidence", 
        EVIDENCE_EXTRACTION_PROMPT.format(context=SYSTEM_CONTEXT, transcript=transcript),
        model, 
        validate_evidence
    )
    evidence_str = json.dumps(evidence_data) if "error" not in evidence_data else "No evidence"
    
    # 2. Scoring
    score_data = await process_step(
        "scoring",
        SCORING_PROMPT.format(context=SYSTEM_CONTEXT, evidence=evidence_str),
        model,
        validate_score
    )
    
    # 3. KPI Mapping
    kpi_data = await process_step(
        "kpis",
        KPI_MAPPING_PROMPT.format(context=SYSTEM_CONTEXT, evidence=evidence_str, transcript=transcript),
        model
    )
    
    # 4. Gaps
    gap_data = await process_step(
        "gaps",
        GAP_ANALYSIS_PROMPT.format(context=SYSTEM_CONTEXT, evidence=evidence_str),
        model
    )
    gap_str = json.dumps(gap_data) if "error" not in gap_data else "No gaps"
    
    # 5. Follow-up
    questions_data = await process_step(
        "questions",
        FOLLOWUP_QUESTIONS_PROMPT.format(context=SYSTEM_CONTEXT, gaps=gap_str),
        model
    )
    
    elapsed = time.time() - start_time
    
    results = {
        "evidence": evidence_data,
        "scoring": score_data,
        "kpi_mapping": kpi_data,
        "gap_analysis": gap_data,
        "followup_questions": questions_data
    }
    
    # Save to database
    score = score_data.get("score", 0) if isinstance(score_data, dict) else 0
    confidence = score_data.get("confidence", "unknown") if isinstance(score_data, dict) else "unknown"
    
    analysis_id = save_analysis(
        transcript=transcript,
        model=model,
        score=score,
        confidence=confidence,
        results=results,
        metadata={"processing_time": elapsed}
    )
    
    return {
        "id": analysis_id,
        **results,
        "metadata": {
            "processing_time_seconds": round(elapsed, 2),
            "model_used": model,
            "timestamp": datetime.now().isoformat()
        }
    }

@app.get("/history")
async def history(limit: int = Query(20, le=100)):
    """Returns analysis history."""
    return get_history(limit)

@app.delete("/analysis/{analysis_id}")
async def delete_record(analysis_id: int):
    """Deletes an analysis record."""
    delete_analysis(analysis_id)
    return {"status": "deleted"}

@app.get("/stats")
async def get_dashboard_stats():
    """Returns overview statistics for the dashboard."""
    history = get_history(500) # Get a larger sample for stats
    if not history:
        return {"total": 0, "avg_score": 0, "top_kpi": "N/A"}
    
    total = len(history)
    avg_score = sum(item['score'] for item in history) / total
    
    # Simple top KPI logic
    kpi_counts = {}
    for item in history:
        for kpi_item in item['results'].get('kpi_mapping', {}).get('kpi_mappings', []):
            name = kpi_item.get('kpi', 'Unknown')
            kpi_counts[name] = kpi_counts.get(name, 0) + 1
    
    top_kpi = max(kpi_counts, key=kpi_counts.get) if kpi_counts else "N/A"
    
    return {
        "total": total,
        "avg_score": round(avg_score, 1),
        "top_kpi": top_kpi
    }

@app.get("/export/csv")
async def export_all_csv():
    """Exports all analysis history to a CSV file."""
    history = get_history(1000)
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Timestamp", "Score", "Confidence", "Transcript Snippet"])
    
    for item in history:
        writer.writerow([
            item['id'],
            item['timestamp'],
            item['score'],
            item['confidence'],
            item['transcript'][:100].replace("\n", " ") + "..."
        ])
    
    output.seek(0)
    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=trinethra_export.csv"}
    )

@app.get("/export/{analysis_id}")
async def export_pdf(analysis_id: int):
    """Generates and returns a PDF report for an analysis."""
    data = get_analysis_by_id(analysis_id)
    if not data:
        raise HTTPException(status_code=404, detail="Analysis not found")
    
    results = data['results']
    pdf = FPDF()
    pdf.add_page()
    
    # Header
    pdf.set_font("Helvetica", "B", 20)
    pdf.cell(0, 10, "Trinethra Analysis Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 10, f"Date: {data['timestamp']} | ID: {analysis_id}", ln=True, align="C")
    pdf.ln(5)
    
    # Score Section
    pdf.set_font("Helvetica", "B", 16)
    pdf.set_fill_color(240, 240, 240)
    pdf.cell(0, 10, " Overall Performance Score", ln=True, fill=True)
    pdf.set_font("Helvetica", "B", 40)
    pdf.cell(0, 25, f"{data['score']}/10", ln=True, align="C")
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 10, f"Level: {results['scoring'].get('level_description', 'N/A')}", ln=True, align="C")
    pdf.ln(5)
    
    # Justification
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "Justification:", ln=True)
    pdf.set_font("Helvetica", "", 10)
    pdf.multi_cell(0, 6, results['scoring'].get('justification', 'No justification provided.'))
    pdf.ln(5)
    
    # Evidence
    pdf.set_font("Helvetica", "B", 14)
    pdf.cell(0, 10, " Behavioral Evidence", ln=True, fill=True)
    pdf.set_font("Helvetica", "", 9)
    for item in results['evidence'].get('evidence', []):
        sentiment = item.get('sentiment', '').upper()
        pdf.set_font("Helvetica", "B", 9)
        pdf.write(5, f"[{sentiment}] ")
        pdf.set_font("Helvetica", "I", 9)
        pdf.write(5, f"\"{item.get('quote', '')}\"\n")
        pdf.set_font("Helvetica", "", 9)
        pdf.write(5, f"Dimension: {item.get('dimension', '')} | {item.get('explanation', '')}\n\n")
    
    pdf_path = EXPORTS_DIR / f"report_{analysis_id}.pdf"
    pdf.output(str(pdf_path))
    
    return FileResponse(
        path=pdf_path, 
        filename=f"Trinethra_Report_{analysis_id}.pdf",
        media_type="application/pdf"
    )

@app.post("/analyze/stream")
async def analyze_stream(request: TranscriptRequest):
    """Streaming analysis for real-time UI updates."""
    
    async def event_generator():
        if MOCK_MODE:
            # Fake streaming for demo
            yield json.dumps({"type": "progress", "step": "evidence", "message": "MOCK: Extracting evidence...", "progress": 20}) + "\n"
            await asyncio.sleep(1)
            yield json.dumps({"type": "progress", "step": "scoring", "message": "MOCK: Scoring...", "progress": 50}) + "\n"
            await asyncio.sleep(1)
            mock_res = await get_mock_results(request.transcript)
            yield json.dumps({"type": "complete", "id": mock_res["id"], "data": mock_res}) + "\n"
            return

        transcript = request.transcript
        model = request.model or OLLAMA_MODEL
        start_time = time.time()
        
        # Step 1: Evidence
        yield json.dumps({"type": "progress", "step": "evidence", "message": "Extracting behavioral evidence...", "progress": 20}) + "\n"
        evidence_data = await process_step(
            "evidence", 
            EVIDENCE_EXTRACTION_PROMPT.format(context=SYSTEM_CONTEXT, transcript=transcript),
            model, 
            validate_evidence
        )
        evidence_str = json.dumps(evidence_data) if "error" not in evidence_data else "No evidence"
        
        # Step 2: Scoring
        yield json.dumps({"type": "progress", "step": "scoring", "message": "Calculating rubric score...", "progress": 40}) + "\n"
        score_data = await process_step(
            "scoring",
            SCORING_PROMPT.format(context=SYSTEM_CONTEXT, evidence=evidence_str),
            model,
            validate_score
        )
        
        # Step 3: KPIs
        yield json.dumps({"type": "progress", "step": "kpi", "message": "Mapping business KPIs...", "progress": 60}) + "\n"
        kpi_data = await process_step(
            "kpis",
            KPI_MAPPING_PROMPT.format(context=SYSTEM_CONTEXT, evidence=evidence_str, transcript=transcript),
            model
        )
        
        # Step 4: Gaps
        yield json.dumps({"type": "progress", "step": "gaps", "message": "Identifying assessment gaps...", "progress": 80}) + "\n"
        gap_data = await process_step(
            "gaps",
            GAP_ANALYSIS_PROMPT.format(context=SYSTEM_CONTEXT, evidence=evidence_str),
            model
        )
        gap_str = json.dumps(gap_data) if "error" not in gap_data else "No gaps"
        
        # Step 5: Questions
        yield json.dumps({"type": "progress", "step": "questions", "message": "Generating follow-up questions...", "progress": 95}) + "\n"
        questions_data = await process_step(
            "questions",
            FOLLOWUP_QUESTIONS_PROMPT.format(context=SYSTEM_CONTEXT, gaps=gap_str),
            model
        )
        
        results = {
            "evidence": evidence_data,
            "scoring": score_data,
            "kpi_mapping": kpi_data,
            "gap_analysis": gap_data,
            "followup_questions": questions_data
        }
        
        # Save to DB
        score = score_data.get("score", 0) if isinstance(score_data, dict) else 0
        confidence = score_data.get("confidence", "unknown") if isinstance(score_data, dict) else "unknown"
        elapsed = time.time() - start_time
        
        analysis_id = save_analysis(transcript, model, score, confidence, results, {"processing_time": elapsed})
        
        yield json.dumps({
            "type": "complete",
            "id": analysis_id,
            "data": results,
            "metadata": {"processing_time_seconds": round(elapsed, 2)}
        }) + "\n"

    return StreamingResponse(event_generator(), media_type="application/x-ndjson")

async def get_mock_results(transcript: str):
    """Returns static mock results for demonstration."""
    await asyncio.sleep(2) # Simulate work
    results = {
        "fellow_name": "Rahul",
        "sentiment_stats": {"positive": 70, "negative": 20, "neutral": 10},
        "evidence": {
            "evidence": [
                {"quote": "Rahul is very consistent.", "dimension": "Reliability", "sentiment": "positive", "explanation": "Supervisor explicitly mentions consistency."},
                {"quote": "He sometimes gets too caught up in data.", "dimension": "Operational Awareness", "sentiment": "negative", "explanation": "Identifies a gap in floor coordination."}
            ]
        },
        "scoring": {
            "score": 8,
            "confidence": "high",
            "level_description": "Advanced Performer",
            "justification": "The fellow shows strong technical results and consistency, with minor gaps in cross-departmental coordination."
        },
        "kpi_mapping": {
            "kpi_mappings": [
                {"kpi": "Operational Efficiency", "evidence": "Reduced breakdown time by 20%"},
                {"kpi": "Technical Proficiency", "evidence": "Built digital maintenance log"}
            ]
        },
        "gap_analysis": {"gaps": ["Floor check frequency", "Inter-departmental coordination"]},
        "followup_questions": {"questions": ["How can Rahul improve his floor-check routine?", "What steps can he take to coordinate with the purchase department?"]}
    }
    return {
        "id": 999,
        **results,
        "metadata": {"processing_time_seconds": 2.0, "model_used": "mock-mode", "timestamp": datetime.now().isoformat()}
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8005)
