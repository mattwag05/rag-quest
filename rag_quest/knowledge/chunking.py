"""Intelligent text chunking strategies for RAG profiles."""

import re
from typing import List, Tuple


class RAGProfileConfig:
    """Configuration for different RAG profiles."""
    
    PROFILES = {
        "fast": {
            "chunk_size": 4000,
            "chunk_overlap": 200,
            "min_chunk_size": 1000,
            "query_mode": "naive",
            "top_k": 15,
            "chunk_top_k": 10,
            "description": "Fast retrieval, suitable for weak hardware or quick testing"
        },
        "balanced": {
            "chunk_size": 2000,
            "chunk_overlap": 300,
            "min_chunk_size": 500,
            "query_mode": "local",
            "top_k": 30,
            "chunk_top_k": 15,
            "description": "Good balance of quality and speed"
        },
        "deep": {
            "chunk_size": 1000,
            "chunk_overlap": 400,
            "min_chunk_size": 300,
            "query_mode": "hybrid",
            "top_k": 50,
            "chunk_top_k": 25,
            "description": "Best quality, slower, for capable hardware"
        }
    }
    
    def __init__(self, profile: str = "balanced"):
        if profile not in self.PROFILES:
            raise ValueError(f"Unknown profile: {profile}. Must be one of {list(self.PROFILES.keys())}")
        self.profile = profile
        self.config = self.PROFILES[profile]
    
    def get_chunk_size(self) -> int:
        return self.config["chunk_size"]
    
    def get_chunk_overlap(self) -> int:
        return self.config["chunk_overlap"]
    
    def get_min_chunk_size(self) -> int:
        return self.config["min_chunk_size"]
    
    def get_query_mode(self) -> str:
        return self.config["query_mode"]
    
    def get_top_k(self) -> int:
        return self.config["top_k"]
    
    def get_chunk_top_k(self) -> int:
        return self.config["chunk_top_k"]
    
    def get_description(self) -> str:
        return self.config["description"]


class TextChunker:
    """Handles intelligent text chunking based on RAG profile."""
    
    def __init__(self, profile: str = "balanced"):
        self.profile_config = RAGProfileConfig(profile)
    
    def chunk_text(self, text: str) -> List[str]:
        """
        Chunk text intelligently, respecting sentence/paragraph boundaries.
        """
        chunk_size = self.profile_config.get_chunk_size()
        chunk_overlap = self.profile_config.get_chunk_overlap()
        min_chunk_size = self.profile_config.get_min_chunk_size()
        
        # First pass: split by paragraphs
        paragraphs = text.split('\n\n')
        
        # Build chunks that respect paragraph boundaries
        chunks = []
        current_chunk = ""
        
        for paragraph in paragraphs:
            # If adding this paragraph would exceed size, save current chunk
            if current_chunk and len(current_chunk) + len(paragraph) > chunk_size:
                if len(current_chunk) >= min_chunk_size:
                    chunks.append(current_chunk.strip())
                # Start new chunk with overlap
                current_chunk = self._get_overlap(current_chunk, chunk_overlap) + paragraph
            else:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += paragraph
        
        # Add final chunk
        if current_chunk and len(current_chunk) >= min_chunk_size:
            chunks.append(current_chunk.strip())
        
        return chunks
    
    def chunk_by_sections(self, text: str) -> List[Tuple[str, str]]:
        """
        Chunk text by detecting sections/chapters with headings.
        Returns list of (section_title, section_content) tuples.
        """
        # Common heading patterns (markdown, docx-style, etc.)
        heading_pattern = r'^(#{1,6}|\*{1,3}|={3,}|-{3,})\s+(.+)$'
        
        chunks = []
        current_section = ""
        current_title = "Introduction"
        
        for line in text.split('\n'):
            match = re.match(heading_pattern, line, re.MULTILINE)
            
            if match:
                # Save previous section
                if current_section.strip():
                    chunks.append((current_title, current_section.strip()))
                
                current_title = match.group(2).strip()
                current_section = ""
            else:
                current_section += line + '\n'
        
        # Add final section
        if current_section.strip():
            chunks.append((current_title, current_section.strip()))
        
        return chunks
    
    def _get_overlap(self, text: str, overlap_size: int) -> str:
        """Get the last N characters for overlap, respecting word boundaries."""
        if len(text) <= overlap_size:
            return text
        
        # Start from overlap point and find the last complete sentence or paragraph
        start_pos = len(text) - overlap_size
        overlap_text = text[start_pos:]
        
        # Try to find a sentence boundary
        sentence_end = overlap_text.rfind('.')
        if sentence_end > 0:
            return overlap_text[sentence_end + 1:].strip()
        
        # Try to find a paragraph boundary
        para_end = overlap_text.rfind('\n\n')
        if para_end > 0:
            return overlap_text[para_end + 2:].strip()
        
        return overlap_text


def chunk_pdf_text(pdf_text: str, profile: str = "balanced") -> List[str]:
    """
    Chunk text extracted from PDF, preserving page structure when useful.
    """
    chunker = TextChunker(profile)
    
    # Try section-based chunking first
    sections = chunker.chunk_by_sections(pdf_text)
    
    if sections:
        # We found structured sections, chunk each one
        all_chunks = []
        for title, content in sections:
            section_chunks = chunker.chunk_text(content)
            # Prepend section title to first chunk for context
            if section_chunks:
                section_chunks[0] = f"[Section: {title}]\n\n{section_chunks[0]}"
            all_chunks.extend(section_chunks)
        return all_chunks
    else:
        # No clear structure, just chunk the text
        return chunker.chunk_text(pdf_text)
