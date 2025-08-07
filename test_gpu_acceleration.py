#!/usr/bin/env python3
"""
Test script to verify GPU acceleration is working
"""

import time
import sys
import os
import requests
from pathlib import Path

# Add current directory to Python path
sys.path.insert(0, str(Path(__file__).parent))

def test_standard_kittentts():
    """Test standard KittenTTS performance"""
    print("🧪 Testing Standard KittenTTS...")
    
    try:
        import kittentts
        tts = kittentts.KittenTTS()
        
        test_text = "Hello, this is a performance test of the KittenTTS engine."
        
        # Warm up
        tts.generate(test_text, voice="expr-voice-5-m", speed=1.0)
        
        # Time the generation
        start_time = time.time()
        audio_data = tts.generate(test_text, voice="expr-voice-5-m", speed=1.0)
        end_time = time.time()
        
        duration = end_time - start_time
        audio_length = len(audio_data) if audio_data is not None else 0
        
        print(f"  ✅ Standard KittenTTS: {duration:.3f}s (audio: {audio_length:,} samples)")
        return duration, audio_length
        
    except Exception as e:
        print(f"  ❌ Standard KittenTTS failed: {e}")
        return None, None

def test_gpu_kittentts():
    """Test GPU-accelerated KittenTTS performance"""
    print("🚀 Testing GPU-Accelerated KittenTTS...")
    
    try:
        from gpu_kitten_tts import GPUKittenTTS
        tts = GPUKittenTTS()
        
        # Show performance info
        perf_info = tts.get_performance_info()
        print(f"  📊 GPU Enabled: {perf_info['gpu_enabled']}")
        print(f"  📊 Providers: {perf_info['providers']}")
        print(f"  📊 GPU Provider: {perf_info['gpu_provider']}")
        
        test_text = "Hello, this is a performance test of the GPU-accelerated KittenTTS engine."
        
        # Warm up
        tts.generate(test_text, voice="expr-voice-5-m", speed=1.0)
        
        # Time the generation
        start_time = time.time()
        audio_data = tts.generate(test_text, voice="expr-voice-5-m", speed=1.0)
        end_time = time.time()
        
        duration = end_time - start_time
        audio_length = len(audio_data) if audio_data is not None else 0
        
        print(f"  ✅ GPU KittenTTS: {duration:.3f}s (audio: {audio_length:,} samples)")
        return duration, audio_length, perf_info
        
    except Exception as e:
        print(f"  ❌ GPU KittenTTS failed: {e}")
        return None, None, None

def test_server_endpoint():
    """Test server GPU acceleration via API"""
    print("🌐 Testing Server API...")
    
    try:
        # Check if server is running
        health_response = requests.get("http://localhost:8001/health", timeout=5)
        if health_response.status_code != 200:
            print("  ❌ Server not responding")
            return None
        
        health_data = health_response.json()
        print(f"  📊 Server Status: {health_data.get('status', 'unknown')}")
        
        # Check GPU status
        gpu_response = requests.get("http://localhost:8001/gpu/status", timeout=5)
        if gpu_response.status_code == 200:
            gpu_data = gpu_response.json()
            gpu_info = gpu_data.get('gpu_acceleration', {})
            print(f"  📊 GPU Acceleration: {gpu_info.get('enabled', False)}")
            print(f"  📊 Active Providers: {gpu_info.get('active_providers', [])}")
        
        # Test speech generation
        test_text = "Hello, this is a test of the server API with GPU acceleration."
        
        payload = {
            "model": "tts-1-hd",
            "input": test_text,
            "voice": "alloy",
            "speed": 1.0,
            "response_format": "wav"
        }
        
        start_time = time.time()
        response = requests.post(
            "http://localhost:8001/v1/audio/speech",
            json=payload,
            timeout=30
        )
        end_time = time.time()
        
        if response.status_code == 200:
            duration = end_time - start_time
            audio_length = len(response.content)
            print(f"  ✅ Server API: {duration:.3f}s (audio: {audio_length:,} bytes)")
            return duration, audio_length
        else:
            print(f"  ❌ Server API failed: {response.status_code} - {response.text}")
            return None, None
            
    except requests.RequestException as e:
        print(f"  ❌ Server API failed: {e}")
        print("     Make sure the server is running: python server.py")
        return None, None

def main():
    print("🐱 KittenTTS GPU Acceleration Test")
    print("=" * 50)
    
    # Test configurations
    print("\n🔧 Environment Configuration:")
    print(f"  KITTENTTS_USE_GPU: {os.getenv('KITTENTTS_USE_GPU', 'not set')}")
    print(f"  KITTENTTS_GPU_PROVIDER: {os.getenv('KITTENTTS_GPU_PROVIDER', 'not set')}")
    print(f"  KITTENTTS_ONNX_THREADS: {os.getenv('KITTENTTS_ONNX_THREADS', 'not set')}")
    
    # Test ONNX Runtime providers
    try:
        import onnxruntime as ort
        print(f"\n🔧 ONNX Runtime:")
        print(f"  Version: {ort.__version__}")
        print(f"  Available Providers: {ort.get_available_providers()}")
    except ImportError:
        print("  ❌ ONNX Runtime not available")
    
    print("\n" + "=" * 50)
    
    # Run performance tests
    results = {}
    
    # Test 1: Standard KittenTTS
    std_duration, std_length = test_standard_kittentts()
    if std_duration is not None:
        results['standard'] = (std_duration, std_length)
    
    print()
    
    # Test 2: GPU-accelerated KittenTTS
    gpu_duration, gpu_length, gpu_info = test_gpu_kittentts()
    if gpu_duration is not None:
        results['gpu'] = (gpu_duration, gpu_length)
    
    print()
    
    # Test 3: Server API
    server_duration, server_length = test_server_endpoint()
    if server_duration is not None:
        results['server'] = (server_duration, server_length)
    
    # Performance comparison
    print("\n" + "=" * 50)
    print("📊 Performance Summary:")
    
    if 'standard' in results and 'gpu' in results:
        std_time, _ = results['standard']
        gpu_time, _ = results['gpu']
        
        if gpu_time < std_time:
            speedup = std_time / gpu_time
            print(f"  🚀 GPU Acceleration: {speedup:.2f}x faster!")
        else:
            slowdown = gpu_time / std_time
            print(f"  ⚠️  GPU Acceleration: {slowdown:.2f}x slower (check configuration)")
    
    for test_name, (duration, length) in results.items():
        print(f"  {test_name.title()}: {duration:.3f}s")
    
    print("\n✅ Test completed!")
    
    if 'gpu' in results and gpu_info:
        if gpu_info['gpu_enabled'] and 'CoreMLExecutionProvider' in gpu_info['providers']:
            print("🎉 GPU acceleration is working with Apple Silicon!")
        elif gpu_info['gpu_enabled'] and 'CUDAExecutionProvider' in gpu_info['providers']:
            print("🎉 GPU acceleration is working with CUDA!")
        else:
            print("ℹ️  GPU acceleration may not be optimal. Check your configuration.")

if __name__ == "__main__":
    main()
