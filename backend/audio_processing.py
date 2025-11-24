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

class AudioProcessor:
    def __init__(self):
        self.api_keys = Config.GROQ_API_KEYS
        self.current_key_index = 0
    
    def _get_client(self):
        if not self.api_keys:
            raise ValueError("No Groq API keys found in environment variables.")
        
        key = self.api_keys[self.current_key_index]
        self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
        return Groq(api_key=key)

audio_processor = AudioProcessor()

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
    max_retries = len(audio_processor.api_keys)
    last_error = None
    
    for attempt in range(max_retries):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(audio_file.filename)[1]) as tmp_file:
                await audio_file.seek(0)
                content = await audio_file.read()
                tmp_file.write(content)
                tmp_path = tmp_file.name
            
            await audio_file.seek(0)
            
            groq_client = audio_processor._get_client()
            logger.info(f"Transcribing with Whisper (attempt {attempt + 1}/{max_retries})")
            
            with open(tmp_path, "rb") as audio:
                transcription = groq_client.audio.transcriptions.create(
                    file=(audio_file.filename, audio.read()),
                    model="whisper-large-v3",
                    language="en"
                )
            
            os.unlink(tmp_path)
            
            return transcription.text.strip()
            
        except Exception as e:
            last_error = e
            logger.warning(f"Whisper transcription failed (attempt {attempt + 1}/{max_retries}): {e}")
            
            if 'tmp_path' in locals() and os.path.exists(tmp_path):
                os.unlink(tmp_path)
            
            if attempt < max_retries - 1:
                logger.info(f"Retrying with next API key...")
    
    logger.error(f"All Whisper API keys failed. Last error: {last_error}")
    raise Exception(f"Whisper transcription failed after {max_retries} attempts: {last_error}")


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

