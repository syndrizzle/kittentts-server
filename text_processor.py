"""
Text processing utilities for KittenTTS Server
Handles text chunking for large inputs to improve TTS processing.
"""

import re
from typing import List, Optional
import logging

logger = logging.getLogger(__name__)

class TextChunker:
    """
    Intelligent text chunker that splits large text into manageable chunks
    while preserving sentence boundaries and natural speech flow.
    """
    
    def __init__(self, max_chunk_size: int = 1200):
        """
        Initialize the text chunker.
        
        Args:
            max_chunk_size: Maximum characters per chunk
        """
        self.max_chunk_size = max_chunk_size
        
        # Sentence boundary patterns (improved for various cases)
        self.sentence_endings = re.compile(r'[.!?]+\s+')
        self.paragraph_breaks = re.compile(r'\n\s*\n')
        
        # Patterns for preserving context
        self.dialogue_pattern = re.compile(r'"[^"]*"')
        self.list_item_pattern = re.compile(r'^\s*[-*•]\s+', re.MULTILINE)
        
    def chunk_text(self, text: str) -> List[str]:
        """
        Split text into chunks while preserving natural boundaries.
        
        Args:
            text: Input text to chunk
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
            
        text = text.strip()
        
        # If text is already small enough, return as single chunk
        if len(text) <= self.max_chunk_size:
            return [text]
            
        logger.info(f"Chunking text of {len(text)} characters into chunks of max {self.max_chunk_size}")
        
        chunks = []
        
        # First, try to split by paragraphs
        paragraphs = self.paragraph_breaks.split(text)
        
        current_chunk = ""
        
        for paragraph in paragraphs:
            paragraph = paragraph.strip()
            if not paragraph:
                continue
                
            # If the paragraph itself is too long, split it first
            if len(paragraph) > self.max_chunk_size:
                para_chunks = self._split_paragraph(paragraph)
                for p in para_chunks:
                    if current_chunk and len(current_chunk) + len(p) + 2 > self.max_chunk_size:
                        chunks.append(current_chunk.strip())
                        current_chunk = p
                    else:
                        if current_chunk:
                            current_chunk += "\n\n" + p
                        else:
                            current_chunk = p
                continue

            # Try to append paragraph to current chunk
            if current_chunk and len(current_chunk) + len(paragraph) + 2 > self.max_chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n" + paragraph
                else:
                    current_chunk = paragraph
        # Add final chunk if any
        if current_chunk:
            chunks.append(current_chunk.strip())
            
        # Validate chunks
        chunks = [chunk for chunk in chunks if chunk.strip()]
        
        logger.info(f"Split into {len(chunks)} chunks")
        return chunks
    
    def _split_paragraph(self, paragraph: str) -> List[str]:
        """
        Split a long paragraph into smaller chunks by sentences.
        
        Args:
            paragraph: Paragraph text to split
            
        Returns:
            List of paragraph chunks
        """
        # Split by sentences
        sentences = self.sentence_endings.split(paragraph)
        
        # Reconstruct sentences with their endings
        reconstructed_sentences = []
        sentence_parts = self.sentence_endings.findall(paragraph)
        
        for i, sentence in enumerate(sentences[:-1]):  # All but last
            if sentence.strip():
                ending = sentence_parts[i] if i < len(sentence_parts) else ". "
                reconstructed_sentences.append(sentence.strip() + ending.rstrip())
        
        # Add the last sentence (no ending to add)
        if sentences[-1].strip():
            reconstructed_sentences.append(sentences[-1].strip())
        
        # Group sentences into chunks
        chunks = []
        current_chunk = ""
        
        for sentence in reconstructed_sentences:
            # If adding this sentence would exceed chunk size
            if current_chunk and len(current_chunk) + len(sentence) + 1 > self.max_chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        # If we still have chunks that are too long, split them more aggressively
        final_chunks = []
        for chunk in chunks:
            if len(chunk) <= self.max_chunk_size:
                final_chunks.append(chunk)
            else:
                # Last resort: split by character limit with word boundaries
                final_chunks.extend(self._split_by_words(chunk))
        
        return final_chunks
    
    def _split_by_words(self, text: str) -> List[str]:
        """
        Split text by word boundaries when sentence splitting isn't enough.
        
        Args:
            text: Text to split
            
        Returns:
            List of word-boundary chunks
        """
        words = text.split()
        chunks = []
        current_chunk = ""
        
        for word in words:
            # Hard-split tokens longer than the max size
            if len(word) > self.max_chunk_size:
                if current_chunk:
                    chunks.append(current_chunk.strip())
                    current_chunk = ""
                for i in range(0, len(word), self.max_chunk_size):
                    chunks.append(word[i : i + self.max_chunk_size])
                continue

            # If adding this word would exceed chunk size
            if current_chunk and len(current_chunk) + len(word) + 1 > self.max_chunk_size:
                chunks.append(current_chunk.strip())
                current_chunk = word
            else:
                if current_chunk:
                    current_chunk += " " + word
                else:
                    current_chunk = word
        # Add final chunk
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def estimate_processing_time(self, text: str) -> float:
        """
        Estimate processing time based on text length.
        
        Args:
            text: Input text
            
        Returns:
            Estimated processing time in seconds
        """
        # Rough estimate: ~100 characters per second for TTS
        base_time = len(text) / 100
        
        # Add overhead for chunking
        chunks = self.chunk_text(text)
        chunk_overhead = len(chunks) * 0.5  # 0.5 seconds per chunk overhead
        
        return base_time + chunk_overhead


def validate_text_input(text: str, max_total_chars: int) -> tuple[bool, Optional[str]]:
    """
    Validate text input against size limits.
    
    Args:
        text: Input text to validate
        max_total_chars: Maximum allowed characters
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not text or not text.strip():
        return False, "Input text cannot be empty"
    
    if len(text) > max_total_chars:
        return False, f"Input text too long. Maximum length is {max_total_chars} characters, got {len(text)}"
    
    # Check for potentially problematic content
    if len(text.strip()) < 3:
        return False, "Input text too short. Minimum length is 3 characters"
    
    return True, None
