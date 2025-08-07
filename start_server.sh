#!/bin/bash
# KittenTTS Server Startup Script

set -e  # Exit on error

echo "🐱 Starting KittenTTS API Server for Open WebUI..."
echo "=================================================="

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check if Python is available
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    print_error "Python is not installed or not in PATH"
    exit 1
fi

# Use python3 if available, otherwise python
PYTHON_CMD="python3"
if ! command -v python3 &> /dev/null; then
    PYTHON_CMD="python"
fi

print_status "Using Python: $(command -v $PYTHON_CMD)"

# Check if virtual environment exists
if [ -d "venv" ]; then
    print_status "Activating virtual environment..."
    source venv/bin/activate
    print_success "Virtual environment activated"
elif [ -d "../kittentts-env-312" ]; then
    print_status "Found existing virtual environment, activating..."
    source ../kittentts-env-312/bin/activate
    print_success "Virtual environment activated"
else
    print_warning "No virtual environment found. Creating one..."
    $PYTHON_CMD -m venv venv
    source venv/bin/activate
    print_success "Virtual environment created and activated"
    
    print_status "Installing dependencies..."
    pip install --upgrade pip
    pip install -r requirements.txt
    print_success "Dependencies installed"
fi

# Verify KittenTTS installation
print_status "Checking KittenTTS installation..."
if $PYTHON_CMD -c "import kittentts; print('KittenTTS version:', getattr(kittentts, '__version__', 'unknown'))" 2>/dev/null; then
    print_success "KittenTTS is properly installed"
else
    print_error "KittenTTS is not installed or not working properly"
    print_warning "Please install KittenTTS manually:"
    echo "  1. Follow the installation instructions from the KittenTTS repository"
    echo "  2. Make sure it's installed in the activated virtual environment"
    exit 1
fi

# Check if the server script exists
if [ ! -f "server.py" ]; then
    print_error "server.py not found in current directory"
    exit 1
fi

# Set default environment variables if not set
export KITTENTTS_HOST=${KITTENTTS_HOST:-"0.0.0.0"}
export KITTENTTS_PORT=${KITTENTTS_PORT:-"8001"}
export KITTENTTS_LOG_LEVEL=${KITTENTTS_LOG_LEVEL:-"INFO"}

print_status "Server configuration:"
echo "  Host: $KITTENTTS_HOST"
echo "  Port: $KITTENTTS_PORT"
echo "  Log Level: $KITTENTTS_LOG_LEVEL"

print_success "Starting server..."
echo "=================================================="
echo "Server will be available at: http://$KITTENTTS_HOST:$KITTENTTS_PORT"
echo "API documentation: http://$KITTENTTS_HOST:$KITTENTTS_PORT/docs"
echo "Health check: http://$KITTENTTS_HOST:$KITTENTTS_PORT/health"
echo ""
echo "Use Ctrl+C to stop the server"
echo "=================================================="
echo ""

# Start the server
$PYTHON_CMD server.py
