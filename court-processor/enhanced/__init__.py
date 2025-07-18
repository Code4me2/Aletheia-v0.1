"""
Enhanced Unified Court Document Processing Pipeline

This module provides enhanced versions of the court document processing
components, building on the existing UnifiedDocumentProcessor foundation
with improved features, error handling, and performance optimizations.
"""

__version__ = "1.0.0"
__author__ = "Aletheia Legal Intelligence"

from .enhanced_unified_processor import EnhancedUnifiedDocumentProcessor

__all__ = [
    "EnhancedUnifiedDocumentProcessor",
]