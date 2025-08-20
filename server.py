#!/usr/bin/env python3
"""
KittenTTS FastAPI Server for Open WebUI Integration
Provides OpenAI-compatible TTS API endpoints.
"""

import io
import os
import tempfile
import logging
import numpy as np
from typing import Literal, Optional, Any, Tuple
from dataclasses import dataclass
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import Response
from contextlib import asynccontextmanager
from pydantic import BaseModel
import soundfile as sf
import uvicorn

from config import Config
from text_processor import TextChunker, validate_text_input

@dataclass
class AudioData:
    array: Any
    sample_rate: int
    dtype: Any
    shape: Tuple[int, ...]
    
    def __array__(self):
        return self.array

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
    Generate speech from text using KittenTTS with intelligent chunking
    Compatible with OpenAI TTS API format
    """
    try:
        # Enhanced input validation
        is_valid, error_msg = validate_text_input(request.input, Config.MAX_TOTAL_CHARS)
        if not is_valid:
            if "too long" in error_msg.lower() and len(request.input) > Config.MAX_TOTAL_CHARS:
                # Return 413 for absurdly large requests
                raise HTTPException(
                    status_code=413, 
                    detail=f"Request entity too large. {error_msg}. Consider breaking your text into smaller requests."
                )
            else:
                raise HTTPException(status_code=400, detail=error_msg)
        
        # Initialize model if not already done
        if tts_model is None:
            logger.info("Model not initialized, initializing now...")
            init_model()
        
        # Map voice and validate speed
        kitten_voice = Config.VOICE_MAPPING.get(request.voice, "expr-voice-5-m")
        speed = Config.clamp_speed(request.speed)
        
        # Determine if chunking is needed
        text_length = len(request.input)
        needs_chunking = Config.ENABLE_CHUNKING and text_length > Config.MAX_CHARS_PER_CHUNK
        
        logger.info(
            f"Processing text - Length: {text_length}, Voice: {kitten_voice}, "
            f"Speed: {speed}, Format: {request.response_format}, Chunking: {needs_chunking}"
        )
        
        if needs_chunking:
            # Use chunking for large texts
            chunker = TextChunker(max_chunk_size=Config.MAX_CHARS_PER_CHUNK)
            chunks = chunker.chunk_text(request.input)
            
            logger.info(f"Split text into {len(chunks)} chunks for processing")
            
            # Generate audio for each chunk
            audio_segments = []
            sample_rate = None
            
            for i, chunk in enumerate(chunks):
                logger.debug(f"Processing chunk {i+1}/{len(chunks)}: '{chunk[:50]}...'")
                
                try:
                    chunk_audio = tts_model.generate(chunk, voice=kitten_voice, speed=speed)
                    
                    # Store sample rate from first chunk
                    if sample_rate is None:
                        sample_rate = getattr(chunk_audio, 'sample_rate', 22050)
                    
                    # Convert to numpy array if needed
                    if hasattr(chunk_audio, 'numpy'):
                        chunk_audio = chunk_audio.numpy()
                    elif not isinstance(chunk_audio, np.ndarray):
                        chunk_audio = np.array(chunk_audio)
                    
                    audio_segments.append(chunk_audio)
                    
                except Exception as chunk_error:
                    logger.error(f"Failed to process chunk {i+1}: {chunk_error}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Failed to process text chunk {i+1}/{len(chunks)}: {str(chunk_error)}"
                    )
            
            # Concatenate all audio segments
            if audio_segments:
                # Add small silence between chunks (0.1 seconds)
                silence_samples = int(sample_rate * 0.1)
                silence = np.zeros(silence_samples, dtype=audio_segments[0].dtype)
                
                # Interleave audio segments with silence
                final_audio_parts = []
                for i, segment in enumerate(audio_segments):
                    final_audio_parts.append(segment)
                    if i < len(audio_segments) - 1:  # Don't add silence after last segment
                        final_audio_parts.append(silence)
                
                audio_data = np.concatenate(final_audio_parts)
                
                # Set sample rate attribute for compatibility
                audio_data = AudioData(
                    array=audio_data,
                    sample_rate=sample_rate,
                    dtype=audio_data.dtype,
                    shape=audio_data.shape
                )
                
                logger.info(f"Successfully concatenated {len(chunks)} chunks into final audio")
            else:
                raise HTTPException(status_code=500, detail="No audio segments were generated")
                
        else:
            # Process as single chunk (original behavior)
            logger.info(f"Processing as single chunk: '{request.input[:50]}...'")
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
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
            try:
                # Get sample rate
                sample_rate = getattr(audio_data, 'sample_rate', 22050)
                
                # Convert to numpy array if needed
                if hasattr(audio_data, '__array__'):
                    audio_array = audio_data.__array__()
                elif hasattr(audio_data, 'numpy'):
                    audio_array = audio_data.numpy()
                else:
                    audio_array = np.array(audio_data)
                
                # Write audio file
                sf.write(tmp_file.name, audio_array, sample_rate)
                
                # Read the audio file data
                with open(tmp_file.name, "rb") as f:
                    audio_bytes = f.read()
                    
            finally:
                # Clean up temporary file
                if os.path.exists(tmp_file.name):
                    os.unlink(tmp_file.name)
        
        # Log success with chunking info
        chunk_info = f" ({len(chunks)} chunks)" if needs_chunking else ""
        logger.info(f"Successfully generated {len(audio_bytes)} bytes of audio{chunk_info}")
        
        return Response(
            content=audio_bytes,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(audio_bytes)),
                "X-Chunks-Processed": str(len(chunks) if needs_chunking and 'chunks' in locals() else 1),
                "X-Text-Length": str(text_length)
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
                "max_total_chars": Config.MAX_TOTAL_CHARS,
                "max_chars_per_chunk": Config.MAX_CHARS_PER_CHUNK,
                "chunking_enabled": Config.ENABLE_CHUNKING,
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
