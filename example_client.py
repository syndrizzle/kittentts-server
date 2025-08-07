#!/usr/bin/env python3
"""
Example client for testing the KittenTTS Server
"""

import requests
import time
import argparse
from pathlib import Path

class KittenTTSClient:
    """Simple client for KittenTTS Server API"""
    
    def __init__(self, base_url="http://localhost:8001"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
    
    def health_check(self):
        """Check server health"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Health check failed: {e}")
            return None
    
    def list_models(self):
        """List available models"""
        try:
            response = self.session.get(f"{self.base_url}/v1/models", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to list models: {e}")
            return None
    
    def list_voices(self):
        """List available voices"""
        try:
            response = self.session.get(f"{self.base_url}/v1/audio/voices", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            print(f"Failed to list voices: {e}")
            return None
    
    def generate_speech(self, text, voice="alloy", model="tts-1-hd", 
                       response_format="wav", speed=1.0, output_file=None):
        """Generate speech from text"""
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": response_format,
            "speed": speed
        }
        
        try:
            print(f"Generating speech for: '{text[:50]}{'...' if len(text) > 50 else ''}'")
            print(f"Voice: {voice}, Speed: {speed}, Format: {response_format}")
            
            response = self.session.post(
                f"{self.base_url}/v1/audio/speech",
                json=payload,
                timeout=60  # TTS can take a while
            )
            response.raise_for_status()
            
            if output_file:
                output_path = Path(output_file)
                output_path.write_bytes(response.content)
                print(f"Audio saved to: {output_path.absolute()}")
                print(f"File size: {len(response.content)} bytes")
            
            return response.content
            
        except requests.RequestException as e:
            print(f"Speech generation failed: {e}")
            if hasattr(e.response, 'text'):
                print(f"Server response: {e.response.text}")
            return None

def main():
    parser = argparse.ArgumentParser(description="KittenTTS Server Test Client")
    parser.add_argument("--url", default="http://localhost:8001", 
                       help="Server URL (default: http://localhost:8001)")
    parser.add_argument("--text", "-t", default="Hello, this is a test of the KittenTTS server!",
                       help="Text to synthesize")
    parser.add_argument("--voice", "-v", default="alloy",
                       choices=["alloy", "echo", "fable", "onyx", "nova", "shimmer"],
                       help="Voice to use")
    parser.add_argument("--speed", "-s", type=float, default=1.0,
                       help="Speech speed (0.25 to 4.0)")
    parser.add_argument("--format", "-f", default="wav",
                       choices=["wav", "mp3"],
                       help="Output format")
    parser.add_argument("--output", "-o", 
                       help="Output file (default: auto-generated)")
    parser.add_argument("--health", action="store_true",
                       help="Check server health only")
    parser.add_argument("--list-voices", action="store_true",
                       help="List available voices")
    parser.add_argument("--list-models", action="store_true", 
                       help="List available models")
    
    args = parser.parse_args()
    
    client = KittenTTSClient(args.url)
    
    print(f"🐱 KittenTTS Server Test Client")
    print(f"Server: {args.url}")
    print("-" * 50)
    
    # Health check
    if args.health or not any([args.list_voices, args.list_models, args.text]):
        print("Checking server health...")
        health = client.health_check()
        if health:
            print(f"✅ Server is {health.get('status', 'unknown')}")
            print(f"   Model loaded: {health.get('model_loaded', 'unknown')}")
            print(f"   Version: {health.get('server_version', 'unknown')}")
        else:
            print("❌ Server health check failed")
            return 1
        
        if args.health:
            return 0
    
    # List models
    if args.list_models:
        print("\nAvailable models:")
        models = client.list_models()
        if models:
            for model in models.get('data', []):
                print(f"  - {model['id']} (owned by {model['owned_by']})")
        else:
            print("  Failed to retrieve models")
    
    # List voices  
    if args.list_voices:
        print("\nAvailable voices:")
        voices = client.list_voices()
        if voices:
            data = voices.get('data', {})
            openai_voices = data.get('openai_compatible', [])
            voice_mapping = data.get('voice_mapping', {})
            
            print("  OpenAI Compatible Voices:")
            for voice in openai_voices:
                kitten_voice = voice_mapping.get(voice, 'unknown')
                print(f"    - {voice} -> {kitten_voice}")
        else:
            print("  Failed to retrieve voices")
    
    # Generate speech
    if args.text and not args.list_voices and not args.list_models:
        print(f"\nGenerating speech...")
        
        # Auto-generate output filename if not provided
        output_file = args.output
        if not output_file:
            timestamp = int(time.time())
            output_file = f"speech_{args.voice}_{timestamp}.{args.format}"
        
        audio_data = client.generate_speech(
            text=args.text,
            voice=args.voice,
            speed=args.speed,
            response_format=args.format,
            output_file=output_file
        )
        
        if audio_data:
            print("✅ Speech generation successful!")
        else:
            print("❌ Speech generation failed")
            return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
