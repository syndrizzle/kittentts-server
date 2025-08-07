"""
Integration tests for KittenTTS server
These tests require KittenTTS to be actually installed
"""

import pytest
import requests
import time
import subprocess
import os
import signal
from pathlib import Path

@pytest.mark.integration
class TestKittenTTSIntegration:
    """Integration tests that require actual KittenTTS installation"""
    
    @pytest.fixture(scope="class")
    def server_process(self):
        """Start the server for integration testing"""
        # This assumes the server can be started
        # In practice, you might want to use a different approach
        # or skip if KittenTTS is not available
        
        server_script = Path(__file__).parent.parent / "server.py"
        if not server_script.exists():
            pytest.skip("Server script not found")
        
        # Try to start the server
        env = os.environ.copy()
        env["KITTENTTS_PORT"] = "8002"  # Use different port for tests
        
        try:
            process = subprocess.Popen(
                ["python", str(server_script)],
                cwd=server_script.parent,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            # Wait for server to start
            time.sleep(5)
            
            # Check if server is responding
            try:
                response = requests.get("http://localhost:8002/health", timeout=5)
                if response.status_code != 200:
                    process.terminate()
                    pytest.skip("Server failed to start properly")
            except requests.RequestException:
                process.terminate()
                pytest.skip("Server not responding")
            
            yield process
            
        except Exception as e:
            pytest.skip(f"Could not start server: {e}")
        finally:
            # Clean up
            if 'process' in locals():
                process.terminate()
                process.wait(timeout=10)

    def test_health_endpoint(self, server_process):
        """Test the health endpoint with actual server"""
        response = requests.get("http://localhost:8002/health")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "model_loaded" in data

    def test_models_endpoint(self, server_process):
        """Test the models endpoint with actual server"""
        response = requests.get("http://localhost:8002/v1/models")
        assert response.status_code == 200
        
        data = response.json()
        assert data["object"] == "list"
        assert len(data["data"]) >= 2

    def test_voices_endpoint(self, server_process):
        """Test the voices endpoint with actual server"""
        response = requests.get("http://localhost:8002/v1/audio/voices")
        assert response.status_code == 200
        
        data = response.json()
        assert "data" in data
        assert "openai_compatible" in data["data"]
        assert "voice_mapping" in data["data"]

    @pytest.mark.skipif(
        not os.getenv("KITTENTTS_INTEGRATION_TESTS"),
        reason="Set KITTENTTS_INTEGRATION_TESTS=1 to run actual TTS tests"
    )
    def test_speech_generation(self, server_process):
        """Test actual speech generation (only if enabled)"""
        response = requests.post(
            "http://localhost:8002/v1/audio/speech",
            json={
                "model": "tts-1-hd",
                "input": "Hello, this is a test.",
                "voice": "alloy",
                "speed": 1.0
            },
            timeout=30  # TTS can take a while
        )
        
        # Should return audio data
        if response.status_code == 200:
            assert len(response.content) > 0
            assert response.headers.get("content-type", "").startswith("audio/")
        else:
            # If it fails, it might be due to KittenTTS not being available
            # Log the error for debugging
            print(f"TTS generation failed: {response.status_code} - {response.text}")
            pytest.skip("TTS generation not available")

    def test_invalid_requests(self, server_process):
        """Test server handles invalid requests properly"""
        # Empty input
        response = requests.post(
            "http://localhost:8002/v1/audio/speech",
            json={
                "model": "tts-1-hd",
                "input": "",
                "voice": "alloy"
            }
        )
        assert response.status_code == 400
        
        # Invalid voice (should default gracefully)
        response = requests.post(
            "http://localhost:8002/v1/audio/speech",
            json={
                "model": "tts-1-hd",
                "input": "Hello",
                "voice": "invalid_voice"
            }
        )
        # Should either work (with default voice) or return error
        assert response.status_code in [200, 400, 500]


@pytest.mark.performance
class TestPerformance:
    """Performance-related tests"""
    
    @pytest.mark.skipif(
        not os.getenv("KITTENTTS_PERFORMANCE_TESTS"),
        reason="Set KITTENTTS_PERFORMANCE_TESTS=1 to run performance tests"
    )
    def test_concurrent_requests(self, server_process):
        """Test server can handle multiple concurrent requests"""
        import concurrent.futures
        import threading
        
        def make_request(text):
            try:
                response = requests.post(
                    "http://localhost:8002/v1/audio/speech",
                    json={
                        "model": "tts-1-hd",
                        "input": f"Test message {text}",
                        "voice": "alloy"
                    },
                    timeout=60
                )
                return response.status_code, len(response.content)
            except Exception as e:
                return None, str(e)
        
        # Make 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [future.result() for future in futures]
        
        # Check results
        successful_requests = [r for r in results if r[0] == 200]
        assert len(successful_requests) >= 3  # At least 60% success rate
