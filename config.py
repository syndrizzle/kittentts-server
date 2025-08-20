"""
Configuration settings for KittenTTS Server
"""

import os

class Config:
    """Server configuration class"""
    
    # Server settings
    HOST = os.getenv("KITTENTTS_HOST", "0.0.0.0")
    PORT = int(os.getenv("KITTENTTS_PORT", 8001))
    LOG_LEVEL = os.getenv("KITTENTTS_LOG_LEVEL", "INFO")
    
    # Text processing limits
    MAX_TEXT_LENGTH = int(os.getenv("KITTENTTS_MAX_TEXT_LENGTH", 4000))  # Legacy limit for backward compatibility
    MAX_TOTAL_CHARS = int(os.getenv("KITTENTTS_MAX_TOTAL_CHARS", 50000))  # Absolute maximum to prevent abuse
    MAX_CHARS_PER_CHUNK = int(os.getenv("KITTENTTS_MAX_CHARS_PER_CHUNK", 1200))  # Optimal chunk size for TTS
    ENABLE_CHUNKING = os.getenv("KITTENTTS_ENABLE_CHUNKING", "true").lower() in ("true", "1", "yes", "on")
    
    # GPU acceleration settings
    USE_GPU = os.getenv("KITTENTTS_USE_GPU", "true").lower() in ("true", "1", "yes", "on")
    GPU_PROVIDER = os.getenv("KITTENTTS_GPU_PROVIDER", "auto")  # auto, coreml, cuda, cpu
    ONNX_THREADS = int(os.getenv("KITTENTTS_ONNX_THREADS", 0))  # 0 = auto
    
    # Voice mapping from OpenAI names to KittenTTS voices
    VOICE_MAPPING = {
        "alloy": "expr-voice-5-m",      # Male voice
        "echo": "expr-voice-2-m",       # Male voice  
        "fable": "expr-voice-3-f",      # Female voice
        "onyx": "expr-voice-4-m",       # Male voice
        "nova": "expr-voice-5-f",       # Female voice
        "shimmer": "expr-voice-2-f"     # Female voice
    }
    
    # Default audio settings
    DEFAULT_SAMPLE_RATE = 44100
    DEFAULT_SPEED = 1.0
    MIN_SPEED = 0.25
    MAX_SPEED = 4.0
    
    # Supported audio formats
    SUPPORTED_FORMATS = ["wav", "mp3", "opus", "aac", "flac", "pcm"]
    
    @classmethod
    def get_kitten_voice(cls, openai_voice: str) -> str:
        """Get KittenTTS voice name from OpenAI voice name"""
        return cls.VOICE_MAPPING.get(openai_voice, "expr-voice-5-m")
    
    @classmethod
    def clamp_speed(cls, speed: float) -> float:
        """Ensure speed is within acceptable range"""
        return max(cls.MIN_SPEED, min(cls.MAX_SPEED, speed))
