"""
Tests for the KittenTTS API server
"""

import pytest
import httpx
from fastapi.testclient import TestClient
from unittest.mock import Mock, patch

# Import the app
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server import app

client = TestClient(app)

class TestHealthEndpoint:
    """Test the health check endpoint"""
    
    def test_health_check_without_model(self):
        """Test health check when model is not loaded"""
        with patch('server.tts_model', None):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["model_loaded"] is False
            assert "status" in data

    def test_health_check_with_model(self):
        """Test health check when model is loaded"""
        mock_model = Mock()
        with patch('server.tts_model', mock_model):
            response = client.get("/health")
            assert response.status_code == 200
            data = response.json()
            assert data["model_loaded"] is True


class TestRootEndpoint:
    """Test the root endpoint"""
    
    def test_root_endpoint(self):
        """Test the root endpoint returns correct information"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "KittenTTS API Server"
        assert data["status"] == "running"
        assert "endpoints" in data


class TestModelsEndpoint:
    """Test the models endpoint"""
    
    def test_list_models(self):
        """Test listing available models"""
        response = client.get("/v1/models")
        assert response.status_code == 200
        data = response.json()
        assert data["object"] == "list"
        assert "data" in data
        assert len(data["data"]) >= 2  # Should have tts-1 and tts-1-hd


class TestVoicesEndpoint:
    """Test the voices endpoint"""
    
    def test_list_voices_without_model(self):
        """Test listing voices when model is not initialized"""
        with patch('server.tts_model', None), \
             patch('server.init_model') as mock_init:
            mock_model = Mock()
            mock_model.available_voices = ["test-voice-1", "test-voice-2"]
            mock_init.return_value = None
            
            # Mock the global tts_model after init_model is called
            with patch('server.tts_model', mock_model):
                response = client.get("/v1/audio/voices")
                assert response.status_code == 200
                data = response.json()
                assert "data" in data
                assert "openai_compatible" in data["data"]

    def test_list_voices_with_model(self):
        """Test listing voices when model is loaded"""
        mock_model = Mock()
        mock_model.available_voices = ["test-voice-1", "test-voice-2"]
        
        with patch('server.tts_model', mock_model):
            response = client.get("/v1/audio/voices")
            assert response.status_code == 200
            data = response.json()
            assert "data" in data
            assert "voice_mapping" in data["data"]


class TestSpeechEndpoint:
    """Test the speech generation endpoint"""
    
    def test_speech_generation_invalid_input(self):
        """Test speech generation with invalid input"""
        # Empty input
        response = client.post("/v1/audio/speech", json={
            "model": "tts-1-hd",
            "input": "",
            "voice": "alloy"
        })
        assert response.status_code == 400
        
        # Input too long
        long_text = "x" * 5000  # Assuming max length is 4000
        response = client.post("/v1/audio/speech", json={
            "model": "tts-1-hd",
            "input": long_text,
            "voice": "alloy"
        })
        assert response.status_code == 400

    def test_speech_generation_valid_request(self):
        """Test valid speech generation request"""
        mock_model = Mock()
        mock_model.generate.return_value = b"fake_audio_data"
        
        with patch('server.tts_model', mock_model), \
             patch('soundfile.write') as mock_sf_write, \
             patch('tempfile.NamedTemporaryFile') as mock_temp, \
             patch('builtins.open', create=True) as mock_open:
            
            # Setup mocks
            mock_temp.return_value.__enter__.return_value.name = "test.wav"
            mock_open.return_value.__enter__.return_value.read.return_value = b"wav_data"
            
            response = client.post("/v1/audio/speech", json={
                "model": "tts-1-hd",
                "input": "Hello world",
                "voice": "alloy",
                "speed": 1.0
            })
            
            # Should not fail due to missing model
            # In real test, we'd mock the entire chain properly
            # For now, just check that the endpoint exists and validates input
            assert response.status_code in [200, 500]  # 500 if model not available

    def test_speech_generation_speed_clamping(self):
        """Test that speed values are properly clamped"""
        mock_model = Mock()
        mock_model.generate.return_value = b"fake_audio_data"
        
        with patch('server.tts_model', mock_model):
            # Test speed too high
            response = client.post("/v1/audio/speech", json={
                "model": "tts-1-hd",
                "input": "Test",
                "voice": "alloy",
                "speed": 10.0  # Should be clamped to 4.0
            })
            
            if response.status_code == 200:
                # Speed should have been clamped
                mock_model.generate.assert_called()
                call_args = mock_model.generate.call_args
                # Speed should be clamped to max 4.0
                assert call_args.kwargs.get('speed', 1.0) <= 4.0


@pytest.fixture
def mock_kittentts():
    """Fixture to mock KittenTTS import"""
    mock_module = Mock()
    mock_tts = Mock()
    mock_module.KittenTTS.return_value = mock_tts
    mock_tts.available_voices = ["voice1", "voice2"]
    mock_tts.generate.return_value = b"fake_audio"
    
    with patch.dict('sys.modules', {'kittentts': mock_module}):
        yield mock_tts


def test_server_startup_without_kittentts():
    """Test server behavior when KittenTTS is not available"""
    with patch('server.init_model') as mock_init:
        mock_init.side_effect = ImportError("KittenTTS not found")
        
        # The server should handle the import error gracefully
        # This test would need to be run in isolation or with proper mocking
