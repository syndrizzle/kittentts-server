# KittenTTS Server API Documentation

This document provides detailed information about the KittenTTS Server API endpoints.

## Base URL

```
http://localhost:8001
```

## Authentication

Currently, no authentication is required for the API endpoints.

## Endpoints

### 1. Root Endpoint

**GET /** 

Returns basic server information and available endpoints.

**Response:**
```json
{
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
```

### 2. Health Check

**GET /health**

Returns server health status and model information.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "server_version": "1.0.0",
  "model_info": {
    "voices_available": 6,
    "model_type": "KittenTTS"
  },
  "supported_formats": ["wav", "mp3"],
  "config": {
    "max_text_length": 4000,
    "available_voices": 6
  }
}
```

### 3. List Models (OpenAI Compatible)

**GET /v1/models**

Returns available TTS models in OpenAI-compatible format.

**Response:**
```json
{
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
```

### 4. List Voices

**GET /v1/audio/voices**

Returns available voices and voice mapping information.

**Response:**
```json
{
  "object": "list",
  "data": {
    "openai_compatible": [
      "alloy", "echo", "fable", "onyx", "nova", "shimmer"
    ],
    "kitten_native": [
      "expr-voice-5-m", "expr-voice-2-m", "expr-voice-3-f", 
      "expr-voice-4-m", "expr-voice-5-f", "expr-voice-2-f"
    ],
    "voice_mapping": {
      "alloy": "expr-voice-5-m",
      "echo": "expr-voice-2-m",
      "fable": "expr-voice-3-f",
      "onyx": "expr-voice-4-m",
      "nova": "expr-voice-5-f",
      "shimmer": "expr-voice-2-f"
    },
    "total_voices": 6
  }
}
```

### 5. Generate Speech (OpenAI Compatible)

**POST /v1/audio/speech**

Generates audio from text input using KittenTTS.

**Request Body:**
```json
{
  "model": "tts-1-hd",
  "input": "Hello, world! This is a test of the KittenTTS server.",
  "voice": "alloy",
  "response_format": "mp3",
  "speed": 1.0
}
```

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| model | string | Yes | - | TTS model to use ("tts-1" or "tts-1-hd") |
| input | string | Yes | - | Text to convert to speech (max 4000 chars) |
| voice | string | No | "alloy" | Voice to use for synthesis |
| response_format | string | No | "mp3" | Audio format ("wav", "mp3") |
| speed | float | No | 1.0 | Speech speed (0.25 to 4.0) |

**Available Voices:**
- `alloy` - Male voice (expr-voice-5-m)
- `echo` - Male voice (expr-voice-2-m)
- `fable` - Female voice (expr-voice-3-f)
- `onyx` - Male voice (expr-voice-4-m) 
- `nova` - Female voice (expr-voice-5-f)
- `shimmer` - Female voice (expr-voice-2-f)

**Response:**
Returns audio data as binary content with appropriate Content-Type header.

**Response Headers:**
- `Content-Type`: `audio/wav` or `audio/mpeg`
- `Content-Disposition`: `attachment; filename=speech.wav`
- `Content-Length`: Size of audio data in bytes

## Error Responses

All endpoints return appropriate HTTP status codes and error messages:

### 400 Bad Request
```json
{
  "detail": "Input text cannot be empty"
}
```

### 500 Internal Server Error
```json
{
  "detail": "Speech generation failed: [error details]"
}
```

## Rate Limiting

Currently, no rate limiting is implemented. Consider implementing rate limiting in production environments.

## Examples

### Generate Speech with curl

```bash
curl -X POST "http://localhost:8001/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "Hello, this is a test of the KittenTTS server!",
    "voice": "nova",
    "response_format": "wav",
    "speed": 1.2
  }' \
  --output speech.wav
```

### Check Server Health

```bash
curl "http://localhost:8001/health"
```

### List Available Voices

```bash
curl "http://localhost:8001/v1/audio/voices"
```

### Python Client Example

```python
import requests

# Generate speech
response = requests.post(
    "http://localhost:8001/v1/audio/speech",
    json={
        "model": "tts-1-hd",
        "input": "Hello from Python!",
        "voice": "alloy",
        "speed": 1.0
    }
)

if response.status_code == 200:
    with open("output.wav", "wb") as f:
        f.write(response.content)
    print("Audio saved to output.wav")
else:
    print(f"Error: {response.status_code} - {response.text}")
```

## OpenAI Compatibility

The `/v1/audio/speech` endpoint is designed to be compatible with OpenAI's TTS API, allowing easy integration with existing applications that use OpenAI's text-to-speech service.

### Differences from OpenAI API

1. **Authentication**: No API key required
2. **Models**: Uses KittenTTS models instead of OpenAI models
3. **Voices**: Maps OpenAI voice names to KittenTTS voices
4. **Formats**: Currently supports WAV and MP3 (limited MP3 support)
5. **Additional Endpoints**: Provides extra endpoints like `/health` and `/v1/audio/voices`
