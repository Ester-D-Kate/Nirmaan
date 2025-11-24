import tempfile
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, UploadFile, File
from groq import Groq
from config import Config
from logs import logger
from scoring import ScoringEngine

router = APIRouter(prefix="/audio", tags=["Audio Processing"])

engine = ScoringEngine()
groq_client = Groq(api_key=Config.GROQ_API_KEYS[0] if Config.GROQ_API_KEYS else None)

@router.post("/score")
async def score_audio_endpoint(
    audio_file: UploadFile = File(...),
    duration: Optional[int] = None
):

    if not audio_file:
        raise HTTPException(status_code=400, detail="Audio file is required")
    
    try:
        logger.info(f"Processing audio file: {audio_file.filename}")
        
        transcription = await transcribe_with_whisper(audio_file)
        
        if not transcription.strip():
            raise HTTPException(status_code=400, detail="Could not transcribe audio")
        
        logger.info(f"Transcribed: {transcription[:100]}...")
        
        if duration is None:
            duration = await extract_audio_duration(audio_file)
        
        logger.info(f"Audio duration: {duration}s")
        
        result = engine.score_transcript(transcription, duration)
        
        result["transcription"] = transcription
        
        return result
        
    except Exception as e:
        logger.error(f"Audio processing failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

async def transcribe_with_whisper(audio_file: UploadFile) -> str:
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as tmp_file:
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        await audio_file.seek(0)
        
        with open(tmp_path, "rb") as audio:
            transcription = groq_client.audio.transcriptions.create(
                file=(audio_file.filename, audio.read()),
                model="whisper-large-v3",
                language="en"
            )
        
        os.unlink(tmp_path)
        
        return transcription.text.strip()
        
    except Exception as e:
        logger.error(f"Whisper transcription failed: {e}")
        raise

async def extract_audio_duration(audio_file: UploadFile) -> Optional[int]:
    try:
        import wave
        import contextlib
        
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as tmp_file:
            await audio_file.seek(0)
            content = await audio_file.read()
            tmp_file.write(content)
            tmp_path = tmp_file.name
        
        await audio_file.seek(0)
        
        with contextlib.closing(wave.open(tmp_path, 'r')) as f:
            frames = f.getnframes()
            rate = f.getframerate()
            duration = int(frames / float(rate))
        
        os.unlink(tmp_path)
        
        return duration
        
    except Exception as e:
        logger.warning(f"Could not extract audio duration: {e}")
        return None

