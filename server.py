#!/usr/bin/env python3
"""
KittenTTS FastAPI Server for Open WebUI Integration
Provides OpenAI-compatible TTS API endpoints.
"""

import io
import os
import tempfile
import logging
from typing import Literal, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from contextlib import asynccontextmanager
from pydantic import BaseModel
import soundfile as sf
import uvicorn

from config import Config

# Configure logging
logging.basicConfig(level=getattr(logging, Config.LOG_LEVEL.upper()))
logger = logging.getLogger(__name__)

# Global TTS model instance
tts_model = None

def init_model():
    """Initialize the KittenTTS model with GPU acceleration"""
    global tts_model
    if tts_model is None:
        try:
            logger.info("Loading KittenTTS model with GPU acceleration...")
            
            # Try to use our GPU-accelerated version first
            try:
                from gpu_kitten_tts import GPUKittenTTS
                tts_model = GPUKittenTTS()
                
                # Log performance info
                perf_info = tts_model.get_performance_info()
                logger.info(f"GPU-accelerated KittenTTS loaded successfully!")
                logger.info(f"Execution providers: {perf_info['providers']}")
                logger.info(f"GPU enabled: {perf_info['gpu_enabled']}")
                logger.info(f"Available voices: {perf_info['voices_count']}")
                
            except Exception as gpu_error:
                logger.warning(f"Failed to load GPU-accelerated version: {gpu_error}")
                logger.info("Falling back to standard KittenTTS...")
                
                # Fallback to standard KittenTTS
                import kittentts
                tts_model = kittentts.KittenTTS()
                logger.info("Standard KittenTTS model loaded successfully!")
                
        except ImportError as e:
            logger.error("KittenTTS not found. Please install KittenTTS first.")
            raise ImportError("KittenTTS package not found. Please install it first.") from e
        except Exception as e:
            logger.error(f"Failed to load KittenTTS model: {e}")
            raise

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handle application lifespan events"""
    # Startup
    try:
        init_model()
        logger.info("Application startup completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("Application shutdown")

app = FastAPI(
    title="KittenTTS API Server", 
    version="1.0.0", 
    description="OpenAI-compatible TTS API server using KittenTTS",
    lifespan=lifespan
)

class TTSRequest(BaseModel):
    model: str = "tts-1-hd"  # OpenAI compatible model name
    input: str  # Text to synthesize
    voice: str = "alloy"  # Voice selection
    response_format: Optional[Literal["mp3", "opus", "aac", "flac", "wav", "pcm"]] = "mp3"
    speed: Optional[float] = 1.0  # Speed of speech (0.25 to 4.0)

    class Config:
        schema_extra = {
            "example": {
                "model": "tts-1-hd",
                "input": "Hello, this is a test of the KittenTTS server!",
                "voice": "alloy",
                "response_format": "mp3",
                "speed": 1.0
            }
        }

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log incoming requests"""
    logger.info(f"{request.method} {request.url.path} - {request.client.host}")
    response = await call_next(request)
    return response

@app.get("/")
async def root():
    """Root endpoint with server information"""
    return {
        "message": "KittenTTS API Server",
        "status": "running",
        "version": "1.0.0",
        "endpoints": {
            "speech": "/v1/audio/speech",
            "models": "/v1/models", 
            "voices": "/v1/audio/voices",
            "health": "/health"
        }
    }

@app.get("/v1/models")
async def list_models():
    """List available TTS models (OpenAI compatible)"""
    return {
        "object": "list",
        "data": [
            {
                "id": "tts-1",
                "object": "model",
                "created": 1677610602,
                "owned_by": "kittentts"
            },
            {
                "id": "tts-1-hd",
                "object": "model", 
                "created": 1677610602,
                "owned_by": "kittentts"
            }
        ]
    }

@app.post("/v1/audio/speech")
async def create_speech(request: TTSRequest):
    """
    Generate speech from text using KittenTTS
    Compatible with OpenAI TTS API format
    """
    try:
        # Validate input
        if not request.input.strip():
            raise HTTPException(status_code=400, detail="Input text cannot be empty")
        
        if len(request.input) > Config.MAX_TEXT_LENGTH:
            raise HTTPException(
                status_code=400, 
                detail=f"Input text too long. Maximum length is {Config.MAX_TEXT_LENGTH} characters"
            )
        
        # Initialize model if not already done
        if tts_model is None:
            logger.info("Model not initialized, initializing now...")
            init_model()
        
        # Map voice and validate speed
        kitten_voice = Config.VOICE_MAPPING.get(request.voice, "expr-voice-5-m")
        # Clamp speed to acceptable range
        speed = max(0.25, min(4.0, request.speed))
        
        logger.info(
            f"Generating speech - Text: '{request.input[:50]}...', "
            f"Voice: {kitten_voice}, Speed: {speed}, Format: {request.response_format}"
        )
        
        # Generate speech
        audio_data = tts_model.generate(request.input, voice=kitten_voice, speed=speed)
        
        # Determine content type and filename based on format
        content_types = {
            "wav": "audio/wav",
            "mp3": "audio/mpeg",
            "opus": "audio/opus",
            "aac": "audio/aac", 
            "flac": "audio/flac",
            "pcm": "audio/pcm"
        }
        
        format_ext = request.response_format or "wav"
        content_type = content_types.get(format_ext, "audio/wav")
        filename = f"speech.{format_ext}"
        
        # Convert audio data to bytes
        if format_ext in ["wav", "mp3", None]:
            # Create temporary file for WAV format
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                # Assuming audio_data is numpy array with sample rate info
                sample_rate = getattr(audio_data, 'sample_rate', 22050)
                sf.write(tmp_file.name, audio_data, sample_rate)
                
                # Read the audio file data
                with open(tmp_file.name, "rb") as f:
                    audio_bytes = f.read()
                
                # Clean up temporary file
                os.unlink(tmp_file.name)
        else:
            # For other formats, return WAV for now
            # TODO: Add proper format conversion
            logger.warning(f"Format '{format_ext}' not fully supported, returning WAV")
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                sample_rate = getattr(audio_data, 'sample_rate', 22050)
                sf.write(tmp_file.name, audio_data, sample_rate)
                
                with open(tmp_file.name, "rb") as f:
                    audio_bytes = f.read()
                
                os.unlink(tmp_file.name)
        
        logger.info(f"Successfully generated {len(audio_bytes)} bytes of audio")
        
        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(audio_bytes))
            }
        )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except ImportError as e:
        logger.error(f"KittenTTS import error: {e}")
        raise HTTPException(
            status_code=500, 
            detail="KittenTTS not properly installed. Please check the installation."
        )
    except Exception as e:
        logger.error(f"Error generating speech: {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail=f"Speech generation failed: {str(e)}"
        )

@app.get("/v1/audio/voices")
async def list_voices():
    """List available voices (extension to OpenAI API)"""
    try:
        if tts_model is None:
            init_model()
        
        # Get available voices from KittenTTS
        try:
            kitten_voices = tts_model.available_voices
        except AttributeError:
            # Fallback if available_voices is not implemented
            kitten_voices = list(Config.VOICE_MAPPING.values())
        
        openai_voices = list(Config.VOICE_MAPPING.keys())
        
        return {
            "object": "list",
            "data": {
                "openai_compatible": openai_voices,
                "kitten_native": kitten_voices,
                "voice_mapping": Config.VOICE_MAPPING,
                "total_voices": len(openai_voices)
            }
        }
    except Exception as e:
        logger.error(f"Error listing voices: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list voices: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        model_status = tts_model is not None
        
        # Try to get model info if available
        model_info = {}
        if model_status:
            try:
                model_info = {
                    "voices_available": len(getattr(tts_model, 'available_voices', [])),
                    "model_type": str(type(tts_model).__name__)
                }
                
                # Add GPU performance info if available
                if hasattr(tts_model, 'get_performance_info'):
                    perf_info = tts_model.get_performance_info()
                    model_info.update({
                        "gpu_acceleration": perf_info.get('gpu_enabled', False),
                        "execution_providers": perf_info.get('providers', []),
                        "gpu_provider": perf_info.get('gpu_provider', 'none')
                    })
                
            except Exception as e:
                logger.warning(f"Could not get model info: {e}")
        
        return {
            "status": "healthy" if model_status else "model_not_loaded",
            "model_loaded": model_status,
            "server_version": "1.0.0",
            "model_info": model_info,
            "supported_formats": ["wav", "mp3"],
            "config": {
                "max_text_length": Config.MAX_TEXT_LENGTH,
                "available_voices": len(Config.VOICE_MAPPING),
                "gpu_acceleration_enabled": Config.USE_GPU
            }
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return {
            "status": "unhealthy",
            "error": str(e),
            "model_loaded": False
        }

@app.get("/gpu/status")
async def gpu_status():
    """Get detailed GPU acceleration status"""
    try:
        if tts_model is None:
            init_model()
        
        # Get performance info if available
        if hasattr(tts_model, 'get_performance_info'):
            perf_info = tts_model.get_performance_info()
            return {
                "gpu_acceleration": {
                    "enabled": perf_info.get('gpu_enabled', False),
                    "provider": perf_info.get('gpu_provider', 'auto'),
                    "active_providers": perf_info.get('providers', []),
                    "onnx_threads": perf_info.get('onnx_threads', 'auto')
                },
                "model_info": {
                    "type": str(type(tts_model).__name__),
                    "model_path": perf_info.get('model_path', 'unknown'),
                    "voices_count": perf_info.get('voices_count', 0)
                },
                "system_info": {
                    "available_providers": [],  # Will be populated below
                }
            }
        else:
            return {
                "gpu_acceleration": {
                    "enabled": False,
                    "provider": "standard_kittentts",
                    "active_providers": ["CPUExecutionProvider"],
                    "note": "Using standard KittenTTS without GPU acceleration"
                },
                "model_info": {
                    "type": str(type(tts_model).__name__),
                    "voices_count": len(getattr(tts_model, 'available_voices', []))
                }
            }
            
    except Exception as e:
        logger.error(f"GPU status check failed: {e}")
        return {
            "error": str(e),
            "gpu_acceleration": {"enabled": False}
        }

if __name__ == "__main__":
    print("🐱 Starting KittenTTS API Server...")
    print("=" * 50)
    print(f"📡 Server will be available at: http://{Config.HOST}:{Config.PORT}")
    print(f"🎯 OpenAI-compatible endpoint: http://{Config.HOST}:{Config.PORT}/v1/audio/speech")
    print(f"📋 API documentation: http://{Config.HOST}:{Config.PORT}/docs")
    print(f"🔍 Health check: http://{Config.HOST}:{Config.PORT}/health")
    print("=" * 50)
    print("Use Ctrl+C to stop the server")
    print("")
    
    try:
        uvicorn.run(
            app, 
            host=Config.HOST, 
            port=Config.PORT,
            log_level=Config.LOG_LEVEL.lower()
        )
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except Exception as e:
        logger.error(f"Server failed to start: {e}")
        raise
