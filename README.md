# KittenTTS Server

A FastAPI-based TTS (Text-to-Speech) server that provides OpenAI-compatible API endpoints using [KittenTTS](https://github.com/KittenML/KittenTTS). This server can be easily integrated with Open WebUI and other applications that support OpenAI's TTS API format.

**note: you will need to have KittenTTS separately installed on your system**

## Features

- 🔌 OpenAI-compatible TTS API endpoints
- 🗣️ Multiple voice options with voice mapping
- ⚡ Fast and efficient speech synthesis using KittenTTS
- 🎛️ Configurable speech speed (0.25x to 4.0x)
- 📊 Health check and model status endpoints
- 🔧 Easy integration with Open WebUI

## Quick Start

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/drivenfast/kitten-tts-server
   cd kittentts-server
   ```

2. **Create and activate a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install KittenTTS**
   ```bash
   # Follow KittenTTS installation instructions from their repository
   # This typically involves installing from source or using their provided wheels
   ```

5. **Start the server**
   ```bash
   python server.py
   ```

   Or use the startup script:
   ```bash
   chmod +x start_server.sh
   ./start_server.sh
   ```

The server will be available at `http://localhost:8001`

## API Endpoints

### Generate Speech
```bash
POST /v1/audio/speech
```

**Request Body:**
```json
{
  "model": "tts-1-hd",
  "input": "Hello, this is a test of the KittenTTS server!",
  "voice": "alloy",
  "response_format": "mp3",
  "speed": 2.0
}
```

**Example using curl:**
```bash
curl -X POST "http://localhost:8001/v1/audio/speech" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "tts-1-hd",
    "input": "Hello world!",
    "voice": "alloy",
    "speed": 1.0
  }' \
  --output speech.wav
```

### List Models
```bash
GET /v1/models
```

### List Voices
```bash
GET /v1/audio/voices
```

### Health Check
```bash
GET /health
```

## Voice Mapping

The server maps OpenAI-compatible voice names to KittenTTS voices:

| OpenAI Voice | KittenTTS Voice | Description |
|--------------|-----------------|-------------|
| alloy        | expr-voice-5-m  | Male voice  |
| echo         | expr-voice-2-m  | Male voice  |
| fable        | expr-voice-3-f  | Female voice|
| onyx         | expr-voice-4-m  | Male voice  |
| nova         | expr-voice-5-f  | Female voice|
| shimmer      | expr-voice-2-f  | Female voice|

## Integration with Open WebUI

1. **Start the KittenTTS server:**
   ```bash
   python server.py
   ```

2. **Configure Open WebUI:**
   - Go to Settings → Audio
   - Set TTS Engine to "OpenAI"
   - Set API Base URL to: `http://localhost:8001/v1`
   - Leave API Key empty (not required)
   - Input one of the voices mapped to OpenAI Voice (e.g. shimmer) in the TTS Voice Field
   - Leave TTS model field as tts-1-hd

3. **Test the integration:**
   - Try using TTS in Open WebUI chat
   - The server logs will show generation requests

## Configuration

### Environment Variables

- `KITTENTTS_HOST`: Server host (default: "0.0.0.0")
- `KITTENTTS_PORT`: Server port (default: 8001)
- `KITTENTTS_LOG_LEVEL`: Logging level (default: "info")
- `KITTENTTS_USE_GPU`: Enable GPU acceleration (default: "true")
- `KITTENTTS_GPU_PROVIDER`: GPU provider preference (default: "auto")
- `KITTENTTS_ONNX_THREADS`: ONNX Runtime threads (default: 0 = auto)

### GPU Acceleration

The server automatically detects and uses GPU acceleration when available:

**Apple Silicon (M1/M2/M3/M4):**
- Uses CoreML execution provider for GPU/Neural Engine acceleration
- Automatically enabled on macOS with Apple Silicon

**NVIDIA CUDA:**
- Uses CUDA execution provider when CUDA is available
- Requires CUDA runtime and ONNX Runtime GPU package

**Intel/AMD Systems:**
- Falls back to CPU execution with optimized threading
- Can use OpenVINO if available

**Configuration Options:**
```bash
# Enable/disable GPU acceleration
export KITTENTTS_USE_GPU=true

# Force specific provider (auto, coreml, cuda, cpu)
export KITTENTTS_GPU_PROVIDER=auto

# Set number of CPU threads (0 = auto-detect)
export KITTENTTS_ONNX_THREADS=4
```

**Check GPU Status:**
```bash
curl http://localhost:8001/gpu/status
```

### Custom Configuration

You can modify the voice mapping and other settings by editing the `config.py` file.

## Docker Support

### Build and Run with Docker

```bash
# Build the Docker image
docker build -t kittentts-server .

# Run the container
docker run -p 8001:8001 kittentts-server
```

### Using Docker Compose

```bash
docker-compose up -d
```

## Development

### Project Structure

```
kittentts-server/
├── server.py              # Main FastAPI server
├── config.py              # Configuration settings
├── requirements.txt       # Python dependencies
├── start_server.sh        # Startup script
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── tests/                 # Test files
│   ├── test_api.py
│   └── test_integration.py
└── docs/                  # Additional documentation
    ├── api.md
    └── deployment.md
```

### Running Tests

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run with coverage
pytest tests/ --cov=. --cov-report=html
```

### Code Formatting

```bash
# Format code with black
black .

# Sort imports
isort .

# Lint with flake8
flake8 .
```

## Troubleshooting

### Common Issues

1. **KittenTTS not found:**
   - Ensure KittenTTS is properly installed in your environment
   - Check that all dependencies are installed

2. **Audio format issues:**
   - The server currently supports WAV and MP3 formats
   - MP3 support may require additional audio codecs

3. **Port already in use:**
   - Change the port in `config.py` or set the `KITTENTTS_PORT` environment variable

### Logs

Server logs are output to the console. For production deployments, consider using a proper logging configuration.

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Acknowledgments

- [KittenTTS](https://github.com/KittenML/KittenTTS) for the excellent TTS engine
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Open WebUI](https://github.com/open-webui/open-webui) for TTS integration support

---

**Note:** This server requires KittenTTS to be installed separately. Please refer to the KittenTTS documentation for installation instructions specific to your system.
