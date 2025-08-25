"""
PDF processing module for court opinions
Extracted and simplified from court-scraping-server
"""
import logging
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
import subprocess
import fitz  # PyMuPDF
import re
import tempfile
import os

logger = logging.getLogger(__name__)

class PDFProcessor:
    """Handle PDF to text conversion with OCR fallback"""
    
    def __init__(self, ocr_enabled: bool = True):
        self.ocr_enabled = ocr_enabled
        
    def extract_text_from_pdf(self, pdf_path: str) -> Tuple[str, Dict[str, Any]]:
        """Extract text and metadata from PDF"""
        text = ""
        metadata = {}
        
        try:
            pdf_document = fitz.open(pdf_path)
            
            # Extract metadata
            metadata = {
                'pages': pdf_document.page_count,
                'title': pdf_document.metadata.get('title', ''),
                'author': pdf_document.metadata.get('author', ''),
                'creation_date': str(pdf_document.metadata.get('creationDate', '')),
            }
            
            # Extract text from each page
            for page_num in range(pdf_document.page_count):
                page = pdf_document[page_num]
                page_text = page.get_text()
                
                # Add page separator
                if page_text:
                    text += f"\n\n--- Page {page_num + 1} ---\n\n"
                    text += page_text
                    
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"Error extracting text from {pdf_path}: {e}")
            
        return text, metadata
    
    def ocr_pdf(self, pdf_path: str) -> str:
        """Perform OCR on a PDF file"""
        text = ""
        
        try:
            # Convert PDF to images
            pdf_document = fitz.open(pdf_path)
            
            # Limit pages to prevent excessive processing
            max_pages = min(pdf_document.page_count, 500)
            
            for page_num in range(max_pages):
                # Convert page to image
                page = pdf_document[page_num]
                mat = fitz.Matrix(2, 2)  # 2x zoom for better OCR
                pix = page.get_pixmap(matrix=mat)
                
                # Use temporary file
                with tempfile.NamedTemporaryFile(suffix='.png', delete=True, mode='wb') as tmp_file:
                    # Save image data to temp file
                    img_data = pix.tobytes("png")
                    tmp_file.write(img_data)
                    tmp_file.flush()
                    
                    # Perform OCR with timeout
                    try:
                        result = subprocess.run(
                            ['tesseract', tmp_file.name, 'stdout', '-l', 'eng'],
                            capture_output=True,
                            text=True,
                            timeout=30,  # 30 second timeout per page
                            check=False,
                            env={**os.environ, 'OMP_THREAD_LIMIT': '1'}  # Limit threads
                        )
                        
                        if result.returncode == 0:
                            page_text = result.stdout
                            if page_text:
                                text += f"\n\n--- Page {page_num + 1} (OCR) ---\n\n"
                                text += page_text
                        else:
                            logger.warning(f"OCR failed for page {page_num + 1}: {result.stderr}")
                            
                    except subprocess.TimeoutExpired:
                        logger.warning(f"OCR timeout for page {page_num + 1}")
                        continue
                    
            pdf_document.close()
            
        except Exception as e:
            logger.error(f"OCR error for {pdf_path}: {e}")
            
        return text
    
    def clean_text(self, text: str) -> str:
        """Clean and normalize extracted text"""
        # Remove excessive whitespace
        text = re.sub(r'\n{3,}', '\n\n', text)
        text = re.sub(r' {2,}', ' ', text)
        
        # Fix common OCR errors
        replacements = {
            'ﬁ': 'fi',
            'ﬂ': 'fl',
            'ﬀ': 'ff',
            'ﬃ': 'ffi',
            'ﬄ': 'ffl',
            '—': '--',
            '"': '"',
            '"': '"',
            ''': "'",
            ''': "'",
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
            
        # Remove null bytes and other control characters
        text = text.replace('\x00', '')
        text = re.sub(r'[\x01-\x08\x0b-\x0c\x0e-\x1f\x7f-\x9f]', '', text)
        
        return text.strip()
    
    def extract_judges_from_text(self, text: str, court_code: str) -> Optional[str]:
        """Extract judge names from PDF text based on court-specific patterns"""
        judges = None
        
        # Ninth Circuit and First Circuit pattern: "Before: [judges]"
        if court_code in ['ca9', 'ca1']:
            # Handle both "Before:" with colon and "Before" without, and newlines
            before_match = re.search(r'Before:?\s*\n?\s*([A-Z][A-Za-z\s,\.]+?)(?:Circuit|District)?\s*Judge', text[:3000], re.IGNORECASE | re.DOTALL)
            if before_match:
                judges_text = before_match.group(1)
                # Clean up and extract individual names
                judges_text = re.sub(r'\s+', ' ', judges_text).strip()
                # For now, return the full panel text
                judges = judges_text
        
        # Federal Circuit pattern: Similar to ca9
        elif court_code == 'cafc':
            before_match = re.search(r'Before:\s*([A-Z][A-Za-z\s,\.]+?)(?:Circuit|District)?\s*Judge', text[:3000], re.IGNORECASE)
            if before_match:
                judges = before_match.group(1).strip()
        
        # Tax Court pattern: "Opinion by Judge [Name]"
        elif court_code == 'tax':
            opinion_match = re.search(r'Opinion\s+by\s+(?:Judge\s+)?([A-Z][A-Za-z\s]+?)(?:\.|,|\n)', text[:2000], re.IGNORECASE)
            if opinion_match:
                judges = opinion_match.group(1).strip()
        
        # US Court of Federal Claims: Similar patterns
        elif court_code == 'uscfc':
            # Try "Judge [Name]" pattern
            judge_match = re.search(r'(?:Honorable\s+)?Judge\s+([A-Z][A-Za-z\s\.]+?)(?:\n|,|\.)', text[:1500], re.IGNORECASE)
            if judge_match:
                judges = judge_match.group(1).strip()
        
        return judges
    
    def process_pdf(self, pdf_path: str) -> Tuple[str, Dict[str, Any]]:
        """Main method to process a PDF file"""
        # Try regular text extraction first
        text, metadata = self.extract_text_from_pdf(pdf_path)
        
        # If no text and OCR is enabled, try OCR
        if not text.strip() and self.ocr_enabled:
            logger.info(f"No text extracted, attempting OCR for {pdf_path}")
            text = self.ocr_pdf(pdf_path)
        
        # Clean the text
        if text:
            text = self.clean_text(text)
            
        return text, metadata