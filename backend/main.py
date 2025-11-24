from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional
import uvicorn
from scoring import ScoringEngine
from logs import logger
from config import Config
from audio_processing import router as audio_router

app = FastAPI(title="Nirmaan AI Scoring Tool")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

engine = ScoringEngine()

app.include_router(audio_router)

class ScoreRequest(BaseModel):
    transcript: str
    duration: Optional[int] = None

@app.get("/")
def read_root():
    return {"message": "Nirmaan AI Scoring API is running"}

@app.post("/score")
def score_transcript_endpoint(request: ScoreRequest):
    if not request.transcript:
        raise HTTPException(status_code=400, detail="Transcript is required")
    
    try:
        logger.info(f"Scoring transcript of length {len(request.transcript)}")
        result = engine.score_transcript(request.transcript, request.duration)
        return result
    except Exception as e:
        logger.error(f"Error scoring transcript: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8001)
