#!/usr/bin/env python3
"""
Test script for KittenTTS server chunking functionality
Tests various text sizes and chunking scenarios
"""

import requests
import time
import sys
from typing import Dict, Any

# Test server configuration
SERVER_URL = "http://localhost:8001"
SPEECH_ENDPOINT = f"{SERVER_URL}/v1/audio/speech"
HEALTH_ENDPOINT = f"{SERVER_URL}/health"

def test_server_health() -> bool:
    """Test if server is running and healthy"""
    try:
        response = requests.get(HEALTH_ENDPOINT, timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Server is healthy: {data.get('status')}")
            config = data.get('config', {})
            print(f"   Max total chars: {config.get('max_total_chars')}")
            print(f"   Max chars per chunk: {config.get('max_chars_per_chunk')}")
            print(f"   Chunking enabled: {config.get('chunking_enabled')}")
            return True
        else:
            print(f"❌ Server health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Cannot connect to server: {e}")
        return False

def test_speech_generation(text: str, test_name: str, expected_chunks: int = None) -> Dict[str, Any]:
    """Test speech generation with given text"""
    print(f"\n🧪 Testing: {test_name}")
    print(f"   Text length: {len(text)} characters")
    print(f"   Text preview: '{text[:100]}{'...' if len(text) > 100 else ''}'")
    
    payload = {
        "model": "tts-1-hd",
        "input": text,
        "voice": "alloy",
        "response_format": "wav"
    }
    
    start_time = time.time()
    
    try:
        response = requests.post(SPEECH_ENDPOINT, json=payload, timeout=30)
        end_time = time.time()
        
        result = {
            "success": response.status_code == 200,
            "status_code": response.status_code,
            "processing_time": end_time - start_time,
            "audio_size": len(response.content) if response.status_code == 200 else 0,
            "chunks_processed": response.headers.get("X-Chunks-Processed", "1"),
            "text_length_header": response.headers.get("X-Text-Length", str(len(text))),
            "error": None
        }
        
        if response.status_code == 200:
            print(f"   ✅ Success! Generated {result['audio_size']} bytes of audio")
            print(f"   ⏱️  Processing time: {result['processing_time']:.2f} seconds")
            print(f"   📦 Chunks processed: {result['chunks_processed']}")
            
            if expected_chunks and int(result['chunks_processed']) != expected_chunks:
                print(f"   ⚠️  Expected {expected_chunks} chunks, got {result['chunks_processed']}")
        else:
            try:
                error_data = response.json()
                result["error"] = error_data.get("detail", "Unknown error")
            except:
                result["error"] = response.text
            
            print(f"   ❌ Failed with status {response.status_code}: {result['error']}")
        
        return result
        
    except requests.exceptions.Timeout:
        print(f"   ❌ Request timed out after 30 seconds")
        return {"success": False, "error": "Timeout", "processing_time": 30}
    except requests.exceptions.RequestException as e:
        print(f"   ❌ Request failed: {e}")
        return {"success": False, "error": str(e), "processing_time": 0}

def run_chunking_tests():
    """Run comprehensive chunking tests"""
    print("🚀 Starting KittenTTS Chunking Tests")
    print("=" * 50)
    
    # Check server health first
    if not test_server_health():
        print("\n❌ Server is not available. Please start the server first.")
        return False
    
    # Test cases
    test_cases = [
        {
            "name": "Small text (no chunking expected)",
            "text": "Hello, this is a short test message.",
            "expected_chunks": 1
        },
        {
            "name": "Medium text (single chunk)",
            "text": "This is a medium-length text that should still fit within a single chunk. " * 10,
            "expected_chunks": 1
        },
        {
            "name": "Large text (multiple chunks expected)",
            "text": "This is a longer text that should be split into multiple chunks for processing. " * 20,
            "expected_chunks": 2  # Approximate
        },
        {
            "name": "Very large text (many chunks)",
            "text": "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 50,
            "expected_chunks": 3  # Approximate
        },
        {
            "name": "Text with paragraphs",
            "text": """This is the first paragraph with some content that should be processed.

This is the second paragraph that continues the story and adds more content to test paragraph-based chunking.

This is the third paragraph that concludes our test with even more content to ensure proper chunking behavior.""" * 5,
            "expected_chunks": 2  # Approximate
        },
        {
            "name": "Empty text (should fail)",
            "text": "",
            "expected_chunks": None
        },
        {
            "name": "Very short text (should fail)",
            "text": "Hi",
            "expected_chunks": None
        }
    ]
    
    # Run tests
    results = []
    for test_case in test_cases:
        result = test_speech_generation(
            test_case["text"], 
            test_case["name"], 
            test_case["expected_chunks"]
        )
        result["test_name"] = test_case["name"]
        results.append(result)
    
    # Test oversized text (should return 413)
    print(f"\n🧪 Testing: Oversized text (should return 413)")
    oversized_text = "This text is way too long and should be rejected. " * 2000  # ~100k chars
    print(f"   Text length: {len(oversized_text)} characters")
    
    oversized_result = test_speech_generation(oversized_text, "Oversized text (413 expected)")
    if oversized_result["status_code"] == 413:
        print(f"   ✅ Correctly rejected with 413 status")
    else:
        print(f"   ❌ Expected 413, got {oversized_result['status_code']}")
    
    results.append(oversized_result)
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Summary")
    print("=" * 50)
    
    successful_tests = sum(1 for r in results if r["success"])
    total_tests = len(results)
    
    print(f"Total tests: {total_tests}")
    print(f"Successful: {successful_tests}")
    print(f"Failed: {total_tests - successful_tests}")
    
    if successful_tests == total_tests - 2:  # Expect 2 failures (empty text and oversized)
        print("✅ All expected tests passed!")
        return True
    else:
        print("❌ Some tests failed unexpectedly")
        return False

if __name__ == "__main__":
    success = run_chunking_tests()
    sys.exit(0 if success else 1)
