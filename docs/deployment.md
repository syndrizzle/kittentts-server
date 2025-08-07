# KittenTTS Server Deployment Guide

This guide covers various deployment options for the KittenTTS Server.

## Prerequisites

- Python 3.8 or higher
- KittenTTS library installed
- Sufficient system resources (RAM depends on model size)

## Local Development

### Quick Start

1. Clone the repository and navigate to the directory
2. Create a virtual environment: `python -m venv venv`
3. Activate it: `source venv/bin/activate` (Linux/Mac) or `venv\Scripts\activate` (Windows)
4. Install dependencies: `pip install -r requirements.txt`
5. Install KittenTTS according to their documentation
6. Start the server: `python server.py` or `./start_server.sh`

## Production Deployment

### Option 1: Systemd Service (Linux)

1. **Create a systemd service file:**

```bash
sudo nano /etc/systemd/system/kittentts-server.service
```

```ini
[Unit]
Description=KittenTTS API Server
After=network.target

[Service]
Type=simple
User=www-data
WorkingDirectory=/opt/kittentts-server
Environment=PATH=/opt/kittentts-server/venv/bin
Environment=KITTENTTS_HOST=0.0.0.0
Environment=KITTENTTS_PORT=8001
Environment=KITTENTTS_LOG_LEVEL=INFO
ExecStart=/opt/kittentts-server/venv/bin/python server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

2. **Enable and start the service:**

```bash
sudo systemctl daemon-reload
sudo systemctl enable kittentts-server
sudo systemctl start kittentts-server
sudo systemctl status kittentts-server
```

### Option 2: Docker Deployment

#### Build and Run Locally

```bash
# Build the image
docker build -t kittentts-server .

# Run the container
docker run -d \
  --name kittentts-server \
  -p 8001:8001 \
  -e KITTENTTS_LOG_LEVEL=INFO \
  --restart unless-stopped \
  kittentts-server
```

#### Using Docker Compose

```bash
# Start the service
docker-compose up -d

# View logs
docker-compose logs -f

# Stop the service  
docker-compose down
```

#### Docker with Volume Mounts

For persistent logs or configuration:

```bash
docker run -d \
  --name kittentts-server \
  -p 8001:8001 \
  -v $(pwd)/logs:/app/logs \
  -v $(pwd)/config.py:/app/config.py:ro \
  -e KITTENTTS_LOG_LEVEL=INFO \
  --restart unless-stopped \
  kittentts-server
```

### Option 3: Gunicorn + Nginx

For high-traffic production environments:

1. **Install Gunicorn:**

```bash
pip install gunicorn
```

2. **Create Gunicorn configuration (`gunicorn.conf.py`):**

```python
bind = "127.0.0.1:8001"
workers = 2
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50
preload_app = True
timeout = 120
keepalive = 5
```

3. **Start with Gunicorn:**

```bash
gunicorn -c gunicorn.conf.py server:app
```

4. **Nginx configuration:**

```nginx
upstream kittentts_backend {
    server 127.0.0.1:8001;
}

server {
    listen 80;
    server_name your-domain.com;
    
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://kittentts_backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
    }
    
    location /health {
        proxy_pass http://kittentts_backend/health;
        access_log off;
    }
}
```

## Cloud Deployment

### AWS EC2

1. **Launch EC2 instance** (recommend t3.medium or larger)
2. **Install dependencies:**

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv nginx
```

3. **Deploy application** using one of the methods above
4. **Configure security groups** to allow traffic on port 80/443
5. **Optional: Set up SSL** with Let's Encrypt

### Google Cloud Platform

1. **Create Compute Engine instance**
2. **Use startup script:**

```bash
#!/bin/bash
apt-get update
apt-get install -y python3 python3-pip git
git clone https://github.com/your-username/kittentts-server.git
cd kittentts-server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
# Install KittenTTS here
python server.py
```

3. **Configure firewall rules** for port 8001

### DigitalOcean Droplet

Similar to AWS EC2, but using DigitalOcean's interface.

### Docker on Cloud Platforms

Most cloud providers support Docker deployment:

- **AWS ECS/Fargate**
- **Google Cloud Run**  
- **Azure Container Instances**
- **DigitalOcean App Platform**

Example for Google Cloud Run:

```bash
# Build and push to Container Registry
docker build -t gcr.io/PROJECT_ID/kittentts-server .
docker push gcr.io/PROJECT_ID/kittentts-server

# Deploy to Cloud Run
gcloud run deploy kittentts-server \
  --image gcr.io/PROJECT_ID/kittentts-server \
  --platform managed \
  --region us-central1 \
  --port 8001 \
  --memory 2Gi \
  --timeout 300
```

## Environment Configuration

### Environment Variables

Set these environment variables for production:

```bash
export KITTENTTS_HOST=0.0.0.0
export KITTENTTS_PORT=8001
export KITTENTTS_LOG_LEVEL=INFO
export KITTENTTS_MAX_TEXT_LENGTH=4000
```

### Configuration File

Alternatively, modify `config.py` directly:

```python
class Config:
    HOST = "0.0.0.0"
    PORT = 8001
    LOG_LEVEL = "INFO"
    MAX_TEXT_LENGTH = 4000
    # ... other settings
```

## Performance Tuning

### System Requirements

- **Minimum**: 2GB RAM, 1 CPU core
- **Recommended**: 4GB+ RAM, 2+ CPU cores
- **Storage**: 1GB+ for application and models

### Optimization Tips

1. **Use SSD storage** for faster model loading
2. **Increase worker processes** based on CPU cores
3. **Implement caching** for frequently requested audio
4. **Use load balancer** for multiple instances
5. **Monitor memory usage** - TTS models can be memory-intensive

### Caching Strategy

Consider implementing Redis caching for generated audio:

```python
import redis
import hashlib

redis_client = redis.Redis(host='localhost', port=6379, db=0)

def get_cache_key(text, voice, speed):
    return hashlib.md5(f"{text}{voice}{speed}".encode()).hexdigest()

def get_cached_audio(key):
    return redis_client.get(key)

def cache_audio(key, audio_data, ttl=3600):
    redis_client.setex(key, ttl, audio_data)
```

## Monitoring and Logging

### Health Checks

Set up monitoring on the `/health` endpoint:

```bash
# Simple health check
curl -f http://localhost:8001/health || exit 1
```

### Log Management

Configure proper logging in production:

```python
import logging
from logging.handlers import RotatingFileHandler

# In config.py or server.py
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('logs/kittentts.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
```

### Metrics Collection

Consider using tools like:
- **Prometheus** + Grafana for metrics
- **ELK Stack** for log analysis
- **New Relic** or **DataDog** for APM

## Security Considerations

### Network Security

1. **Use HTTPS** in production (SSL/TLS)
2. **Firewall configuration** - only expose necessary ports
3. **VPC/Private networks** when possible
4. **Rate limiting** to prevent abuse

### Application Security

1. **Input validation** - already implemented for text length
2. **CORS configuration** if needed
3. **Authentication/Authorization** for API access
4. **Regular updates** of dependencies

### Example rate limiting with slowapi:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/v1/audio/speech")
@limiter.limit("10/minute")
async def create_speech(request: Request, tts_request: TTSRequest):
    # ... existing code
```

## Troubleshooting

### Common Issues

1. **KittenTTS not found**
   - Ensure KittenTTS is installed in the correct environment
   - Check Python path and virtual environment activation

2. **Memory issues**
   - Monitor RAM usage during model loading
   - Consider using swap space or larger instance

3. **Permission errors**
   - Check file permissions for the application directory
   - Ensure the service user has necessary permissions

4. **Port already in use**
   - Check if another service is using the port
   - Use `lsof -i :8001` to find the process

5. **Audio generation failures**
   - Check KittenTTS model installation
   - Verify audio dependencies (libsndfile, etc.)

### Debug Mode

Enable debug logging for troubleshooting:

```bash
export KITTENTTS_LOG_LEVEL=DEBUG
python server.py
```

## Backup and Recovery

### Important Files to Backup

- Application code
- Configuration files
- Trained models (if custom)
- SSL certificates
- Log files (if needed for analysis)

### Backup Script Example

```bash
#!/bin/bash
BACKUP_DIR="/backup/kittentts-$(date +%Y%m%d)"
mkdir -p $BACKUP_DIR

# Backup application
tar -czf $BACKUP_DIR/app.tar.gz /opt/kittentts-server/

# Backup logs
cp -r /opt/kittentts-server/logs $BACKUP_DIR/

# Backup systemd service file
cp /etc/systemd/system/kittentts-server.service $BACKUP_DIR/
```
