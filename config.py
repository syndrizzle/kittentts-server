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
    MAX_TEXT_LENGTH = int(os.getenv("KITTENTTS_MAX_TEXT_LENGTH", 4000))
    
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
    DEFAULT_SAMPLE_RATE = 22050
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
