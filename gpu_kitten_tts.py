"""
GPU-accelerated KittenTTS wrapper with custom ONNX Runtime providers
"""

import os
import json
import logging
import numpy as np
import onnxruntime as ort
from huggingface_hub import hf_hub_download
from kittentts.onnx_model import TextCleaner
import phonemizer

from config import Config

logger = logging.getLogger(__name__)

class GPUKittenTTS:
    """GPU-accelerated KittenTTS with custom execution providers."""
    
    def __init__(self, model_name="KittenML/kitten-tts-nano-0.1", cache_dir=None):
        """Initialize GPU-accelerated KittenTTS.
        
        Args:
            model_name: Hugging Face repository ID or model name
            cache_dir: Directory to cache downloaded files
        """
        self.model_name = model_name
        self.cache_dir = cache_dir
        
        # Download model files
        self.model_path, self.voices_path = self._download_model()
        
        # Load voices data
        self.voices = np.load(self.voices_path)
        
        # Setup execution providers based on configuration
        providers = self._get_execution_providers()
        
        # Create ONNX Runtime session with optimizations
        session_options = ort.SessionOptions()
        
        # Configure threading for optimal performance
        if Config.ONNX_THREADS > 0:
            session_options.intra_op_num_threads = Config.ONNX_THREADS
            session_options.inter_op_num_threads = Config.ONNX_THREADS
        else:
            # Auto-configure based on system
            import platform
            if platform.system() == 'Darwin' and platform.processor() == 'arm':
                # Apple Silicon optimization - use performance cores
                session_options.intra_op_num_threads = 8  # M4 Pro has 10 CPU cores, use 8 for TTS
                session_options.inter_op_num_threads = 4
                logger.info("Using Apple Silicon CPU optimization (8 intra, 4 inter threads)")
            else:
                # Let ONNX Runtime decide for other platforms
                pass
        
        # Enable optimizations
        session_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        session_options.enable_cpu_mem_arena = True
        session_options.enable_mem_pattern = True
        
        logger.info(f"Creating ONNX session with providers: {providers}")
        
        try:
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=session_options,
                providers=providers
            )
            
            # Log which provider was actually selected
            actual_providers = self.session.get_providers()
            logger.info(f"ONNX session created successfully with providers: {actual_providers}")
            
        except Exception as e:
            logger.warning(f"Failed to create session with preferred providers, falling back to CPU: {e}")
            self.session = ort.InferenceSession(
                self.model_path,
                sess_options=session_options,
                providers=['CPUExecutionProvider']
            )
        
        # Initialize phonemizer and text cleaner
        self.phonemizer = phonemizer.backend.EspeakBackend(
            language="en-us", preserve_punctuation=True, with_stress=True
        )
        self.text_cleaner = TextCleaner()
        
        # Available voices
        self.available_voices = [
            'expr-voice-2-m', 'expr-voice-2-f', 'expr-voice-3-m', 'expr-voice-3-f',
            'expr-voice-4-m', 'expr-voice-4-f', 'expr-voice-5-m', 'expr-voice-5-f'
        ]
    
    def _get_execution_providers(self):
        """Determine the best execution providers based on system and configuration."""
        available_providers = ort.get_available_providers()
        logger.info(f"Available ONNX providers: {available_providers}")
        
        if not Config.USE_GPU:
            logger.info("GPU acceleration disabled by configuration")
            return ['CPUExecutionProvider']
        
        providers = []
        
        # Auto-detect or use specified provider
        if Config.GPU_PROVIDER.lower() == "auto":
            # For systems with CUDA support (prioritize CUDA as it works better with TTS models)
            if 'CUDAExecutionProvider' in available_providers:
                providers.append('CUDAExecutionProvider')
                logger.info("Using CUDA GPU acceleration")
                
            # For Apple Silicon - CoreML has issues with dynamic shapes in TTS models
            # Use optimized CPU instead for better performance
            elif 'CoreMLExecutionProvider' in available_providers:
                logger.info("CoreML available but may have compatibility issues with TTS models")
                logger.info("Using optimized CPU execution for better reliability")
                # Don't add CoreML for now due to model compatibility issues
                
            # For Intel/AMD systems with OpenVINO
            elif 'OpenVINOExecutionProvider' in available_providers:
                providers.append('OpenVINOExecutionProvider')
                logger.info("Using OpenVINO acceleration")
                
        elif Config.GPU_PROVIDER.lower() == "coreml":
            if 'CoreMLExecutionProvider' in available_providers:
                providers.append('CoreMLExecutionProvider')
                logger.warning("CoreML requested - may have compatibility issues with this TTS model")
            else:
                logger.warning("CoreML provider requested but not available")
                
        elif Config.GPU_PROVIDER.lower() == "cuda":
            if 'CUDAExecutionProvider' in available_providers:
                providers.append('CUDAExecutionProvider')
            else:
                logger.warning("CUDA provider requested but not available")
        
        # Always add CPU as fallback with optimizations
        providers.append('CPUExecutionProvider')
        
        return providers
    
    def _download_model(self):
        """Download model files from Hugging Face."""
        # Handle different model name formats
        if "/" not in self.model_name:
            repo_id = f"KittenML/{self.model_name}"
        else:
            repo_id = self.model_name
        
        # Download config file first
        config_path = hf_hub_download(
            repo_id=repo_id,
            filename="config.json",
            cache_dir=self.cache_dir
        )
        
        # Load config
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        if config.get("type") != "ONNX1":
            raise ValueError(f"Unsupported model type: {config.get('type')}")
        
        # Download model and voices files
        model_path = hf_hub_download(
            repo_id=repo_id,
            filename=config["model_file"],
            cache_dir=self.cache_dir
        )
        
        voices_path = hf_hub_download(
            repo_id=repo_id,
            filename=config["voices"],
            cache_dir=self.cache_dir
        )
        
        return model_path, voices_path
    
    def _basic_english_tokenize(self, text):
        """Basic English tokenizer that splits on whitespace and punctuation."""
        import re
        tokens = re.findall(r"\w+|[^\w\s]", text)
        return tokens
    
    def _prepare_inputs(self, text: str, voice: str, speed: float = 1.0) -> dict:
        """Prepare ONNX model inputs from text and voice parameters."""
        if voice not in self.available_voices:
            raise ValueError(f"Voice '{voice}' not available. Choose from: {self.available_voices}")
        
        # Phonemize the input text
        phonemes_list = self.phonemizer.phonemize([text])
        
        # Process phonemes to get token IDs
        phonemes = self._basic_english_tokenize(phonemes_list[0])
        phonemes = ' '.join(phonemes)
        tokens = self.text_cleaner(phonemes)
        
        # Add start and end tokens
        tokens.insert(0, 0)
        tokens.append(0)
        
        input_ids = np.array([tokens], dtype=np.int64)
        ref_s = self.voices[voice]
        
        return {
            "input_ids": input_ids,
            "style": ref_s,
            "speed": np.array([speed], dtype=np.float32),
        }
    
    def generate(self, text: str, voice: str = "expr-voice-5-m", speed: float = 1.0) -> np.ndarray:
        """Synthesize speech from text with GPU acceleration.
        
        Args:
            text: Input text to synthesize
            voice: Voice to use for synthesis
            speed: Speech speed (1.0 = normal)
            
        Returns:
            Audio data as numpy array
        """
        try:
            # Prepare inputs
            onnx_inputs = self._prepare_inputs(text, voice, speed)
            
            # Run inference on GPU/accelerated device
            outputs = self.session.run(None, onnx_inputs)
            
            # Trim audio (remove padding)
            audio = outputs[0][5000:-10000]
            
            return audio
            
        except Exception as e:
            logger.error(f"Error during TTS generation: {e}")
            raise
    
    def get_performance_info(self) -> dict:
        """Get information about the current execution setup."""
        return {
            "providers": self.session.get_providers(),
            "model_path": self.model_path,
            "voices_count": len(self.available_voices),
            "gpu_enabled": Config.USE_GPU,
            "gpu_provider": Config.GPU_PROVIDER,
            "onnx_threads": Config.ONNX_THREADS if Config.ONNX_THREADS > 0 else "auto"
        }
