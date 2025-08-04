# OCR Pipeline Reference Documentation

**NOTE**: This is a reference implementation guide. The court processor currently uses a simpler OCR implementation. See [OCR_STATUS_CURRENT.md](./OCR_STATUS_CURRENT.md) for the actual implementation status.

## Table of Contents
1. [Project Structure](#project-structure)
2. [Requirements](#requirements)
3. [Architecture Overview](#architecture-overview)
4. [Implementation Details](#implementation-details)
5. [Code Implementation](#code-implementation)
6. [Configuration](#configuration)
7. [Usage Examples](#usage-examples)
8. [Performance Optimization](#performance-optimization)

## Project Structure

```
legal-ocr-pipeline/
├── src/
│   ├── __init__.py
│   ├── pipeline/
│   │   ├── __init__.py
│   │   ├── ingestion.py          # Document input handling
│   │   ├── preprocessing.py      # Image enhancement
│   │   ├── layout_analysis.py    # Document structure detection
│   │   ├── ocr_engines.py        # OCR implementation
│   │   ├── specialized.py        # Signature/stamp handling
│   │   ├── postprocessing.py     # Text correction & validation
│   │   ├── output_generator.py   # Structured output creation
│   │   └── orchestrator.py       # Main pipeline controller
│   ├── models/
│   │   └── __init__.py
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── image_utils.py
│   │   └── text_utils.py
│   └── config/
│       ├── __init__.py
│       └── settings.py
├── models/                        # Trained models storage
├── dictionaries/                  # Legal term dictionaries
├── templates/                     # Form templates
├── tests/
├── requirements.txt
├── setup.py
└── README.md
```

## Requirements

### requirements.txt
```txt
# Core dependencies
numpy==1.24.3
opencv-python==4.8.1.78
Pillow==10.1.0
scikit-image==0.22.0

# PDF handling
PyPDF2==3.0.1
pdf2image==1.16.3
pdfplumber==0.10.3

# OCR engines
pytesseract==0.3.10
easyocr==1.7.1
paddlepaddle==2.5.2
paddleocr==2.7.0.3

# Layout analysis
layoutparser==0.3.4
detectron2==0.6
torch==2.1.0
torchvision==0.16.0

# Table extraction
camelot-py[cv]==0.11.0
tabula-py==2.8.2

# NLP and text processing
spacy==3.7.2
nltk==3.8.1
transformers==4.35.2
rapidfuzz==3.5.2

# Document understanding models
timm==0.9.12
sentencepiece==0.1.99

# Data handling
pandas==2.1.3
pydantic==2.5.0
jsonschema==4.20.0

# Task queue and orchestration
celery==5.3.4
redis==5.0.1
flower==2.0.1

# API and utilities
fastapi==0.104.1
uvicorn==0.24.0
python-multipart==0.0.6
tqdm==4.66.1
pyyaml==6.0.1

# Image processing utilities
imutils==0.5.4
scikit-learn==1.3.2

# Logging and monitoring
loguru==0.7.2
python-json-logger==2.0.7
```

### System Requirements
```bash
# Install system dependencies (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-eng \
    tesseract-ocr-fra \
    tesseract-ocr-deu \
    tesseract-ocr-spa \
    libtesseract-dev \
    poppler-utils \
    ghostscript \
    python3-opencv \
    libgl1-mesa-glx
```

## Architecture Overview

The pipeline follows a modular architecture with the following stages:

1. **Ingestion**: Accepts PDFs, images, and scanned documents
2. **Preprocessing**: Enhances image quality for better OCR
3. **Layout Analysis**: Identifies document structure and regions
4. **OCR Processing**: Applies appropriate OCR engine per region
5. **Specialized Handling**: Processes signatures, stamps, checkboxes
6. **Post-processing**: Validates and corrects extracted text
7. **Output Generation**: Creates structured JSON output

## Implementation Details

### Stage 1: Document Ingestion

```python
# src/pipeline/ingestion.py
import os
from typing import List, Union, Tuple
from PIL import Image
import PyPDF2
from pdf2image import convert_from_path
import numpy as np
from pathlib import Path
import tempfile
import logging

logger = logging.getLogger(__name__)

class DocumentIngestion:
    """Handles document input and conversion to processable format"""
    
    def __init__(self, dpi: int = 300, output_format: str = 'PNG'):
        self.dpi = dpi
        self.output_format = output_format
        self.supported_formats = {'.pdf', '.png', '.jpg', '.jpeg', '.tiff', '.tif'}
    
    def load_document(self, file_path: Union[str, Path]) -> List[np.ndarray]:
        """
        Load document and convert to list of numpy arrays (one per page)
        
        Args:
            file_path: Path to input document
            
        Returns:
            List of numpy arrays representing document pages
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"Document not found: {file_path}")
        
        ext = file_path.suffix.lower()
        if ext not in self.supported_formats:
            raise ValueError(f"Unsupported format: {ext}")
        
        if ext == '.pdf':
            return self._process_pdf(file_path)
        else:
            return self._process_image(file_path)
    
    def _process_pdf(self, pdf_path: Path) -> List[np.ndarray]:
        """Convert PDF to images"""
        try:
            # First, try to get page count
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                page_count = len(pdf_reader.pages)
                logger.info(f"PDF has {page_count} pages")
            
            # Convert PDF to images
            images = convert_from_path(
                pdf_path,
                dpi=self.dpi,
                fmt=self.output_format,
                thread_count=4,
                use_pdftocairo=True  # Better quality
            )
            
            # Convert PIL images to numpy arrays
            return [np.array(img) for img in images]
            
        except Exception as e:
            logger.error(f"Error processing PDF: {e}")
            raise
    
    def _process_image(self, image_path: Path) -> List[np.ndarray]:
        """Load single image file"""
        try:
            img = Image.open(image_path)
            
            # Convert to RGB if necessary
            if img.mode != 'RGB':
                img = img.convert('RGB')
            
            return [np.array(img)]
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            raise
    
    def save_images(self, images: List[np.ndarray], output_dir: Path) -> List[Path]:
        """Save processed images to disk"""
        output_dir.mkdir(parents=True, exist_ok=True)
        saved_paths = []
        
        for idx, img_array in enumerate(images):
            img = Image.fromarray(img_array)
            output_path = output_dir / f"page_{idx:04d}.{self.output_format.lower()}"
            img.save(output_path)
            saved_paths.append(output_path)
            
        return saved_paths
```

### Stage 2: Image Preprocessing

```python
# src/pipeline/preprocessing.py
import cv2
import numpy as np
from skimage import filters, morphology, transform
from typing import Tuple, Optional
import logging

logger = logging.getLogger(__name__)

class ImagePreprocessor:
    """Enhance image quality for OCR"""
    
    def __init__(self):
        self.target_dpi = 300
        
    def preprocess(self, image: np.ndarray) -> np.ndarray:
        """
        Apply full preprocessing pipeline
        
        Args:
            image: Input image as numpy array
            
        Returns:
            Preprocessed image
        """
        # Create a copy to avoid modifying original
        img = image.copy()
        
        # Apply preprocessing steps
        img = self.convert_to_grayscale(img)
        img = self.remove_noise(img)
        img = self.correct_skew(img)
        img = self.enhance_contrast(img)
        img = self.binarize(img)
        img = self.remove_borders(img)
        
        return img
    
    def convert_to_grayscale(self, image: np.ndarray) -> np.ndarray:
        """Convert to grayscale if needed"""
        if len(image.shape) == 3:
            return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        return image
    
    def remove_noise(self, image: np.ndarray) -> np.ndarray:
        """Remove noise using morphological operations"""
        # Apply morphological opening to remove small noise
        kernel = np.ones((2, 2), np.uint8)
        denoised = cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)
        
        # Apply median filter for salt-and-pepper noise
        denoised = cv2.medianBlur(denoised, 3)
        
        return denoised
    
    def correct_skew(self, image: np.ndarray, max_angle: float = 5.0) -> np.ndarray:
        """
        Detect and correct document skew
        
        Args:
            image: Grayscale image
            max_angle: Maximum skew angle to correct
            
        Returns:
            Deskewed image
        """
        # Create binary image for line detection
        binary = image > filters.threshold_otsu(image)
        
        # Find lines using Hough transform
        lines = transform.probabilistic_hough_line(
            binary, 
            threshold=30, 
            line_length=100,
            line_gap=5
        )
        
        if not lines:
            return image
        
        # Calculate angles of detected lines
        angles = []
        for line in lines:
            p0, p1 = line
            angle = np.arctan2(p1[1] - p0[1], p1[0] - p0[0]) * 180 / np.pi
            if abs(angle) < max_angle:
                angles.append(angle)
        
        if not angles:
            return image
        
        # Use median angle for rotation
        angle = np.median(angles)
        
        if abs(angle) < 0.1:  # Skip if angle is too small
            return image
        
        # Rotate image
        logger.info(f"Correcting skew: {angle:.2f} degrees")
        rows, cols = image.shape
        M = cv2.getRotationMatrix2D((cols/2, rows/2), angle, 1)
        rotated = cv2.warpAffine(image, M, (cols, rows), 
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
        
        return rotated
    
    def enhance_contrast(self, image: np.ndarray) -> np.ndarray:
        """Enhance contrast using CLAHE"""
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)
        return enhanced
    
    def binarize(self, image: np.ndarray) -> np.ndarray:
        """
        Apply adaptive thresholding for binarization
        Better than simple Otsu for documents with varying lighting
        """
        binary = cv2.adaptiveThreshold(
            image,
            255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY,
            blockSize=11,
            C=2
        )
        return binary
    
    def remove_borders(self, image: np.ndarray, margin: int = 10) -> np.ndarray:
        """Remove black borders that might interfere with OCR"""
        # Find contours
        contours, _ = cv2.findContours(
            255 - image,  # Invert for finding dark regions
            cv2.RETR_EXTERNAL,
            cv2.CHAIN_APPROX_SIMPLE
        )
        
        if not contours:
            return image
        
        # Find largest contour (likely the document)
        largest_contour = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest_contour)
        
        # Add margin and crop
        x = max(0, x - margin)
        y = max(0, y - margin)
        w = min(image.shape[1] - x, w + 2 * margin)
        h = min(image.shape[0] - y, h + 2 * margin)
        
        return image[y:y+h, x:x+w]
```

### Stage 3: Layout Analysis

```python
# src/pipeline/layout_analysis.py
import layoutparser as lp
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import torch
import logging

logger = logging.getLogger(__name__)

class RegionType(Enum):
    """Types of document regions"""
    TITLE = "title"
    PARAGRAPH = "paragraph"
    TABLE = "table"
    FORM_FIELD = "form_field"
    SIGNATURE = "signature"
    STAMP = "stamp"
    CHECKBOX = "checkbox"
    IMAGE = "image"
    HEADER = "header"
    FOOTER = "footer"

@dataclass
class DocumentRegion:
    """Represents a detected region in the document"""
    type: RegionType
    bbox: Tuple[int, int, int, int]  # x1, y1, x2, y2
    confidence: float
    text: Optional[str] = None
    metadata: Optional[Dict] = None
    
    @property
    def area(self) -> int:
        return (self.bbox[2] - self.bbox[0]) * (self.bbox[3] - self.bbox[1])

class LayoutAnalyzer:
    """Analyze document layout and detect regions"""
    
    def __init__(self, device: str = 'cpu'):
        self.device = device
        self._init_models()
        
    def _init_models(self):
        """Initialize layout detection models"""
        # Use Detectron2 model for layout detection
        config_path = "lp://PubLayNet/mask_rcnn_X_101_32x8d_FPN_3x/config"
        self.layout_model = lp.Detectron2LayoutModel(
            config_path,
            extra_config=["MODEL.ROI_HEADS.SCORE_THRESH_TEST", 0.5],
            label_map={
                0: RegionType.PARAGRAPH,
                1: RegionType.TITLE,
                2: RegionType.TABLE,
                3: RegionType.IMAGE,
                4: RegionType.PARAGRAPH  # List items as paragraphs
            }
        )
        
    def analyze_layout(self, image: np.ndarray) -> List[DocumentRegion]:
        """
        Analyze document layout and return detected regions
        
        Args:
            image: Input image (can be grayscale or color)
            
        Returns:
            List of detected document regions
        """
        # Ensure image is in correct format for model
        if len(image.shape) == 2:
            image_rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
        else:
            image_rgb = image
            
        # Detect layout using deep learning model
        layout = self.layout_model.detect(image_rgb)
        
        # Convert to our region format
        regions = []
        for block in layout:
            region = DocumentRegion(
                type=block.type,
                bbox=(block.block.x_1, block.block.y_1, 
                      block.block.x_2, block.block.y_2),
                confidence=block.score
            )
            regions.append(region)
        
        # Add specialized detection for forms and signatures
        regions.extend(self._detect_form_fields(image))
        regions.extend(self._detect_signatures(image))
        regions.extend(self._detect_checkboxes(image))
        
        # Sort regions by reading order (top-to-bottom, left-to-right)
        regions = self._sort_reading_order(regions)
        
        return regions
    
    def _detect_form_fields(self, image: np.ndarray) -> List[DocumentRegion]:
        """Detect form fields using line detection"""
        regions = []
        
        # Convert to grayscale if needed
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
            
        # Detect horizontal and vertical lines
        horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
        vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
        
        # Find lines
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        horizontal_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, horizontal_kernel)
        vertical_lines = cv2.morphologyEx(binary, cv2.MORPH_OPEN, vertical_kernel)
        
        # Combine lines to find intersections (potential form fields)
        combined = cv2.addWeighted(horizontal_lines, 0.5, vertical_lines, 0.5, 0)
        
        # Find contours of potential form fields
        contours, _ = cv2.findContours(combined, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            area = cv2.contourArea(contour)
            if area > 1000:  # Minimum area threshold
                x, y, w, h = cv2.boundingRect(contour)
                if w > 50 and h > 20:  # Reasonable size for form field
                    region = DocumentRegion(
                        type=RegionType.FORM_FIELD,
                        bbox=(x, y, x + w, y + h),
                        confidence=0.8
                    )
                    regions.append(region)
        
        return regions
    
    def _detect_signatures(self, image: np.ndarray) -> List[DocumentRegion]:
        """Detect potential signature regions"""
        regions = []
        
        # Convert to grayscale
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
            
        # Look for regions with high ink density variation (characteristic of signatures)
        # Apply edge detection
        edges = cv2.Canny(gray, 50, 150)
        
        # Find contours
        contours, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Signature heuristics
            aspect_ratio = w / h if h > 0 else 0
            area = w * h
            
            if (2.0 < aspect_ratio < 8.0 and  # Signatures are typically wide
                1000 < area < 50000 and        # Reasonable size
                h > 30 and h < 150):           # Reasonable height
                
                # Check ink density in region
                region_img = gray[y:y+h, x:x+w]
                ink_ratio = np.sum(region_img < 128) / area
                
                if 0.05 < ink_ratio < 0.5:  # Moderate ink density
                    region = DocumentRegion(
                        type=RegionType.SIGNATURE,
                        bbox=(x, y, x + w, y + h),
                        confidence=0.7
                    )
                    regions.append(region)
        
        return regions
    
    def _detect_checkboxes(self, image: np.ndarray) -> List[DocumentRegion]:
        """Detect checkboxes in forms"""
        regions = []
        
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        else:
            gray = image
            
        # Look for small square regions
        _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            
            # Checkbox heuristics
            if (10 < w < 30 and 10 < h < 30 and  # Small size
                0.8 < w/h < 1.2):                 # Square shape
                
                region = DocumentRegion(
                    type=RegionType.CHECKBOX,
                    bbox=(x, y, x + w, y + h),
                    confidence=0.8,
                    metadata={'checked': self._is_checkbox_checked(gray[y:y+h, x:x+w])}
                )
                regions.append(region)
        
        return regions
    
    def _is_checkbox_checked(self, checkbox_img: np.ndarray) -> bool:
        """Determine if a checkbox is checked"""
        # Calculate ink density
        _, binary = cv2.threshold(checkbox_img, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
        ink_ratio = np.sum(binary > 0) / binary.size
        return ink_ratio > 0.3
    
    def _sort_reading_order(self, regions: List[DocumentRegion]) -> List[DocumentRegion]:
        """Sort regions in reading order (top-to-bottom, left-to-right)"""
        def sort_key(region: DocumentRegion):
            # Group by approximate row (y-coordinate with tolerance)
            row = region.bbox[1] // 50
            # Then sort by x-coordinate within row
            return (row, region.bbox[0])
        
        return sorted(regions, key=sort_key)
```

### Stage 4: OCR Processing

```python
# src/pipeline/ocr_engines.py
import pytesseract
import easyocr
from paddleocr import PaddleOCR
from transformers import TrOCRProcessor, VisionEncoderDecoderModel
import cv2
import numpy as np
from typing import Dict, List, Optional, Tuple
from PIL import Image
import torch
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

logger = logging.getLogger(__name__)

class OCREngineManager:
    """Manages multiple OCR engines and selects appropriate one per region"""
    
    def __init__(self, languages: List[str] = ['en'], device: str = 'cpu'):
        self.languages = languages
        self.device = device
        self._init_engines()
        
    def _init_engines(self):
        """Initialize OCR engines"""
        # Tesseract configuration
        self.tesseract_config = r'--oem 3 --psm 6'
        
        # EasyOCR
        self.easyocr_reader = easyocr.Reader(
            self.languages, 
            gpu=(self.device == 'cuda')
        )
        
        # PaddleOCR
        self.paddle_ocr = PaddleOCR(
            use_angle_cls=True,
            lang='en',
            use_gpu=(self.device == 'cuda'),
            show_log=False
        )
        
        # TrOCR for handwriting
        if self.device == 'cuda' and torch.cuda.is_available():
            self.trocr_processor = TrOCRProcessor.from_pretrained(
                'microsoft/trocr-base-handwritten'
            )
            self.trocr_model = VisionEncoderDecoderModel.from_pretrained(
                'microsoft/trocr-base-handwritten'
            ).to(self.device)
        else:
            self.trocr_processor = None
            self.trocr_model = None
            
    def extract_text(self, image: np.ndarray, region_type: str, 
                    confidence_threshold: float = 0.5) -> Dict:
        """
        Extract text from image region using appropriate OCR engine
        
        Args:
            image: Image region to process
            region_type: Type of region (determines OCR engine)
            confidence_threshold: Minimum confidence threshold
            
        Returns:
            Dictionary with text and confidence scores
        """
        if region_type in ['title', 'paragraph', 'header', 'footer']:
            # Use Tesseract for printed text
            return self._tesseract_ocr(image)
        
        elif region_type == 'form_field':
            # Try multiple engines and vote
            return self._multi_engine_ocr(image)
        
        elif region_type == 'table':
            # Use Tesseract with table-specific PSM
            return self._tesseract_table_ocr(image)
        
        elif region_type in ['signature', 'handwritten']:
            # Use TrOCR if available, fallback to EasyOCR
            if self.trocr_model:
                return self._trocr_ocr(image)
            else:
                return self._easyocr_ocr(image)
        
        else:
            # Default to EasyOCR
            return self._easyocr_ocr(image)
    
    def _tesseract_ocr(self, image: np.ndarray) -> Dict:
        """Extract text using Tesseract"""
        try:
            # Get text with confidence scores
            data = pytesseract.image_to_data(
                image, 
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Filter and combine text
            words = []
            confidences = []
            
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:  # Valid detection
                    words.append(data['text'][i])
                    confidences.append(int(data['conf'][i]) / 100.0)
            
            text = ' '.join(words)
            avg_confidence = np.mean(confidences) if confidences else 0.0
            
            return {
                'text': text.strip(),
                'confidence': avg_confidence,
                'word_confidences': list(zip(words, confidences)),
                'engine': 'tesseract'
            }
            
        except Exception as e:
            logger.error(f"Tesseract OCR error: {e}")
            return {'text': '', 'confidence': 0.0, 'engine': 'tesseract'}
    
    def _tesseract_table_ocr(self, image: np.ndarray) -> Dict:
        """Extract text from tables using Tesseract with table-specific settings"""
        try:
            # Use PSM 6 for uniform block of text (good for tables)
            table_config = r'--oem 3 --psm 6 -c preserve_interword_spaces=1'
            
            text = pytesseract.image_to_string(image, config=table_config)
            
            # Also get the structured data for cell detection
            data = pytesseract.image_to_data(
                image, 
                config=table_config,
                output_type=pytesseract.Output.DICT
            )
            
            # Group text by approximate rows
            rows = {}
            for i in range(len(data['text'])):
                if int(data['conf'][i]) > 0:
                    y = data['top'][i]
                    row_key = y // 20  # Group by approximate row
                    if row_key not in rows:
                        rows[row_key] = []
                    rows[row_key].append({
                        'text': data['text'][i],
                        'left': data['left'][i],
                        'conf': data['conf'][i]
                    })
            
            # Sort and structure the table data
            table_data = []
            for row_key in sorted(rows.keys()):
                row_items = sorted(rows[row_key], key=lambda x: x['left'])
                row_text = [item['text'] for item in row_items]
                table_data.append(row_text)
            
            return {
                'text': text.strip(),
                'confidence': 0.8,
                'table_data': table_data,
                'engine': 'tesseract_table'
            }
            
        except Exception as e:
            logger.error(f"Table OCR error: {e}")
            return {'text': '', 'confidence': 0.0, 'engine': 'tesseract_table'}
    
    def _easyocr_ocr(self, image: np.ndarray) -> Dict:
        """Extract text using EasyOCR"""
        try:
            results = self.easyocr_reader.readtext(image)
            
            if not results:
                return {'text': '', 'confidence': 0.0, 'engine': 'easyocr'}
            
            # Combine results
            texts = []
            confidences = []
            
            for (bbox, text, conf) in results:
                texts.append(text)
                confidences.append(conf)
            
            combined_text = ' '.join(texts)
            avg_confidence = np.mean(confidences)
            
            return {
                'text': combined_text.strip(),
                'confidence': avg_confidence,
                'word_confidences': list(zip(texts, confidences)),
                'engine': 'easyocr'
            }
            
        except Exception as e:
            logger.error(f"EasyOCR error: {e}")
            return {'text': '', 'confidence': 0.0, 'engine': 'easyocr'}
    
    def _paddle_ocr(self, image: np.ndarray) -> Dict:
        """Extract text using PaddleOCR"""
        try:
            result = self.paddle_ocr.ocr(image, cls=True)
            
            if not result or not result[0]:
                return {'text': '', 'confidence': 0.0, 'engine': 'paddleocr'}
            
            # Extract text and confidence
            texts = []
            confidences = []
            
            for line in result[0]:
                texts.append(line[1][0])
                confidences.append(line[1][1])
            
            combined_text = ' '.join(texts)
            avg_confidence = np.mean(confidences)
            
            return {
                'text': combined_text.strip(),
                'confidence': avg_confidence,
                'word_confidences': list(zip(texts, confidences)),
                'engine': 'paddleocr'
            }
            
        except Exception as e:
            logger.error(f"PaddleOCR error: {e}")
            return {'text': '', 'confidence': 0.0, 'engine': 'paddleocr'}
    
    def _trocr_ocr(self, image: np.ndarray) -> Dict:
        """Extract handwritten text using TrOCR"""
        try:
            # Convert numpy array to PIL Image
            pil_image = Image.fromarray(image)
            if pil_image.mode != 'RGB':
                pil_image = pil_image.convert('RGB')
            
            # Process with TrOCR
            pixel_values = self.trocr_processor(
                images=pil_image, 
                return_tensors="pt"
            ).pixel_values.to(self.device)
            
            # Generate text
            generated_ids = self.trocr_model.generate(pixel_values)
            generated_text = self.trocr_processor.batch_decode(
                generated_ids, 
                skip_special_tokens=True
            )[0]
            
            return {
                'text': generated_text.strip(),
                'confidence': 0.85,  # TrOCR doesn't provide confidence
                'engine': 'trocr'
            }
            
        except Exception as e:
            logger.error(f"TrOCR error: {e}")
            return {'text': '', 'confidence': 0.0, 'engine': 'trocr'}
    
    def _multi_engine_ocr(self, image: np.ndarray) -> Dict:
        """Use multiple engines and combine results"""
        results = []
        
        # Run OCR engines in parallel
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(self._tesseract_ocr, image): 'tesseract',
                executor.submit(self._easyocr_ocr, image): 'easyocr',
                executor.submit(self._paddle_ocr, image): 'paddle'
            }
            
            for future in as_completed(futures):
                try:
                    result = future.result()
                    if result['text']:
                        results.append(result)
                except Exception as e:
                    logger.error(f"Engine {futures[future]} failed: {e}")
        
        if not results:
            return {'text': '', 'confidence': 0.0, 'engine': 'multi'}
        
        # Vote on best result (highest confidence)
        best_result = max(results, key=lambda x: x['confidence'])
        
        # Check if results agree
        texts = [r['text'].lower().strip() for r in results]
        if len(set(texts)) == 1:
            # All engines agree
            best_result['confidence'] = min(0.95, best_result['confidence'] * 1.1)
        
        best_result['engine'] = 'multi'
        best_result['all_results'] = results
        
        return best_result
```

### Stage 5: Post-Processing

```python
# src/pipeline/postprocessing.py
import re
import spacy
import nltk
from typing import Dict, List, Tuple, Optional
from datetime import datetime
import logging
from rapidfuzz import fuzz, process
import json

logger = logging.getLogger(__name__)

class TextPostProcessor:
    """Post-process and validate extracted text"""
    
    def __init__(self, legal_dictionary_path: Optional[str] = None):
        self.nlp = spacy.load("en_core_web_sm")
        nltk.download('punkt', quiet=True)
        nltk.download('words', quiet=True)
        
        # Load legal dictionary
        self.legal_terms = set()
        if legal_dictionary_path:
            self._load_legal_dictionary(legal_dictionary_path)
        
        # Common legal patterns
        self.patterns = {
            'case_number': re.compile(r'\b\d{2,4}-[A-Z]{2,4}-\d{4,6}\b'),
            'date': re.compile(r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b'),
            'ssn': re.compile(r'\b\d{3}-\d{2}-\d{4}\b'),
            'phone': re.compile(r'\b\d{3}[-.]?\d{3}[-.]?\d{4}\b'),
            'email': re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
            'currency': re.compile(r'\$[\d,]+\.?\d*'),
            'percentage': re.compile(r'\b\d+\.?\d*%'),
            'legal_citation': re.compile(r'\b\d+\s+[A-Z][a-z]+\.?\s+\d+[a-z]?\b')
        }
        
    def _load_legal_dictionary(self, path: str):
        """Load legal terms dictionary"""
        try:
            with open(path, 'r') as f:
                self.legal_terms = set(line.strip().lower() for line in f)
            logger.info(f"Loaded {len(self.legal_terms)} legal terms")
        except Exception as e:
            logger.error(f"Error loading legal dictionary: {e}")
    
    def process_text(self, text: str, region_type: str, 
                    confidence: float) -> Dict:
        """
        Process and enhance extracted text
        
        Args:
            text: Raw OCR text
            region_type: Type of document region
            confidence: OCR confidence score
            
        Returns:
            Processed text with metadata
        """
        if not text:
            return {
                'original': '',
                'processed': '',
                'entities': {},
                'corrections': [],
                'confidence': confidence
            }
        
        # Clean text
        cleaned = self._clean_text(text)
        
        # Correct common OCR errors
        corrected, corrections = self._correct_ocr_errors(cleaned)
        
        # Extract entities
        entities = self._extract_entities(corrected)
        
        # Validate legal terms
        if region_type in ['paragraph', 'title']:
            corrected = self._validate_legal_terms(corrected)
        
        # Format based on region type
        formatted = self._format_text(corrected, region_type)
        
        return {
            'original': text,
            'processed': formatted,
            'entities': entities,
            'corrections': corrections,
            'confidence': confidence
        }
    
    def _clean_text(self, text: str) -> str:
        """Basic text cleaning"""
        # Remove excessive whitespace
        text = ' '.join(text.split())
        
        # Fix common OCR artifacts
        text = text.replace('|', 'I')  # Common OCR error
        text = text.replace('0', 'O')  # In certain contexts
        
        # Remove standalone special characters
        text = re.sub(r'\s+([^\w\s])\s+', r' \1 ', text)
        
        return text.strip()
    
    def _correct_ocr_errors(self, text: str) -> Tuple[str, List[Dict]]:
        """Correct common OCR errors"""
        corrections = []
        
        # Common legal document OCR corrections
        ocr_corrections = {
            'PLAINTIFF': ['PLALNTIFF', 'PLAINTLFF', 'PLAIMTIFF'],
            'DEFENDANT': ['DEFENDAMT', 'DEFENDENT', 'DEFENDNAT'],
            'WHEREAS': ['WHEREAB', 'WHEREAE', 'VHEREAS'],
            'AGREEMENT': ['AGREEMEMT', 'AGREEMEHT', 'AGREERNENT'],
            'CONTRACT': ['COMTRACT', 'CONTRACI', 'CONRACT'],
            'LIABILITY': ['LIABILTY', 'LIABILTIY', 'LLABILITY'],
            'PURSUANT': ['PURSUAMT', 'PURSUAHT', 'FURSUANT'],
            'WITNESS': ['WLTNESS', 'WITNES5', 'VVITNESS'],
            'HEREBY': ['HEREEY', 'MEREBY', 'HBREBY'],
            'COURT': ['COLRT', 'COORT', 'CUURT']
        }
        
        for correct, variants in ocr_corrections.items():
            for variant in variants:
                if variant in text.upper():
                    text = re.sub(
                        re.compile(re.escape(variant), re.IGNORECASE), 
                        correct, 
                        text
                    )
                    corrections.append({
                        'original': variant,
                        'corrected': correct,
                        'type': 'ocr_correction'
                    })
        
        # Fix date formats
        dates = self.patterns['date'].findall(text)
        for date_str in dates:
            try:
                # Normalize date format
                parsed_date = datetime.strptime(date_str, '%m/%d/%Y')
                formatted = parsed_date.strftime('%m/%d/%Y')
                if date_str != formatted:
                    text = text.replace(date_str, formatted)
                    corrections.append({
                        'original': date_str,
                        'corrected': formatted,
                        'type': 'date_normalization'
                    })
            except:
                pass
        
        return text, corrections
    
    def _extract_entities(self, text: str) -> Dict[str, List]:
        """Extract named entities and patterns"""
        entities = {
            'persons': [],
            'organizations': [],
            'locations': [],
            'dates': [],
            'monetary': [],
            'case_numbers': [],
            'emails': [],
            'phones': []
        }
        
        # Use spaCy NER
        doc = self.nlp(text)
        for ent in doc.ents:
            if ent.label_ == 'PERSON':
                entities['persons'].append(ent.text)
            elif ent.label_ == 'ORG':
                entities['organizations'].append(ent.text)
            elif ent.label_ in ['GPE', 'LOC']:
                entities['locations'].append(ent.text)
            elif ent.label_ == 'DATE':
                entities['dates'].append(ent.text)
            elif ent.label_ == 'MONEY':
                entities['monetary'].append(ent.text)
        
        # Extract patterns
        entities['case_numbers'] = self.patterns['case_number'].findall(text)
        entities['emails'] = self.patterns['email'].findall(text)
        entities['phones'] = self.patterns['phone'].findall(text)
        
        # Remove duplicates
        for key in entities:
            entities[key] = list(set(entities[key]))
        
        return entities
    
    def _validate_legal_terms(self, text: str) -> str:
        """Validate and correct legal terminology"""
        if not self.legal_terms:
            return text
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            word_lower = word.lower().strip('.,;:')
            
            # Check if word is in legal dictionary
            if word_lower in self.legal_terms:
                corrected_words.append(word)
            else:
                # Try fuzzy matching for potential corrections
                matches = process.extract(
                    word_lower, 
                    self.legal_terms, 
                    scorer=fuzz.ratio,
                    limit=1
                )
                
                if matches and matches[0][1] > 90:  # High confidence match
                    # Preserve original capitalization
                    if word.isupper():
                        corrected_words.append(matches[0][0].upper())
                    elif word[0].isupper():
                        corrected_words.append(matches[0][0].capitalize())
                    else:
                        corrected_words.append(matches[0][0])
                else:
                    corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _format_text(self, text: str, region_type: str) -> str:
        """Format text based on region type"""
        if region_type == 'title':
            # Title case for titles
            return text.title()
        elif region_type == 'paragraph':
            # Ensure proper sentence capitalization
            sentences = nltk.sent_tokenize(text)
            formatted = []
            for sentence in sentences:
                if sentence:
                    formatted.append(sentence[0].upper() + sentence[1:])
            return ' '.join(formatted)
        else:
            return text
```

### Stage 6: Pipeline Orchestrator

```python
# src/pipeline/orchestrator.py
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime
import traceback
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
import numpy as np
from tqdm import tqdm

from .ingestion import DocumentIngestion
from .preprocessing import ImagePreprocessor
from .layout_analysis import LayoutAnalyzer, DocumentRegion
from .ocr_engines import OCREngineManager
from .postprocessing import TextPostProcessor
from .specialized import SpecializedProcessor
from .output_generator import OutputGenerator

logger = logging.getLogger(__name__)

class OCRPipeline:
    """Main orchestrator for the OCR pipeline"""
    
    def __init__(self, config: Optional[Dict] = None):
        """
        Initialize OCR pipeline
        
        Args:
            config: Configuration dictionary
        """
        self.config = config or self._default_config()
        self._init_components()
        
    def _default_config(self) -> Dict:
        """Default pipeline configuration"""
        return {
            'dpi': 300,
            'languages': ['en'],
            'device': 'cpu',
            'parallel_pages': 4,
            'confidence_threshold': 0.5,
            'output_format': 'json',
            'legal_dictionary_path': None,
            'enable_specialized_processing': True,
            'save_intermediate': False,
            'intermediate_dir': './intermediate'
        }
    
    def _init_components(self):
        """Initialize pipeline components"""
        self.ingestion = DocumentIngestion(dpi=self.config['dpi'])
        self.preprocessor = ImagePreprocessor()
        self.layout_analyzer = LayoutAnalyzer(device=self.config['device'])
        self.ocr_manager = OCREngineManager(
            languages=self.config['languages'],
            device=self.config['device']
        )
        self.postprocessor = TextPostProcessor(
            legal_dictionary_path=self.config.get('legal_dictionary_path')
        )
        self.specialized = SpecializedProcessor()
        self.output_generator = OutputGenerator()
        
    def process_document(self, 
                        input_path: Union[str, Path],
                        output_path: Optional[Union[str, Path]] = None) -> Dict:
        """
        Process a complete document through the OCR pipeline
        
        Args:
            input_path: Path to input document
            output_path: Optional path to save results
            
        Returns:
            Structured extraction results
        """
        start_time = datetime.now()
        input_path = Path(input_path)
        
        logger.info(f"Starting document processing: {input_path}")
        
        try:
            # Stage 1: Ingestion
            logger.info("Stage 1: Document ingestion")
            page_images = self.ingestion.load_document(input_path)
            logger.info(f"Loaded {len(page_images)} pages")
            
            # Process pages (parallel or sequential based on config)
            if self.config['parallel_pages'] > 1 and len(page_images) > 1:
                page_results = self._process_pages_parallel(page_images)
            else:
                page_results = self._process_pages_sequential(page_images)
            
            # Generate final output
            logger.info("Generating final output")
            result = self.output_generator.generate_output(
                page_results,
                metadata={
                    'source_file': str(input_path),
                    'processing_time': (datetime.now() - start_time).total_seconds(),
                    'page_count': len(page_images),
                    'pipeline_version': '1.0.0'
                }
            )
            
            # Save results if output path provided
            if output_path:
                self._save_results(result, output_path)
            
            logger.info(f"Document processing completed in {datetime.now() - start_time}")
            return result
            
        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            logger.error(traceback.format_exc())
            raise
    
    def _process_pages_sequential(self, page_images: List[np.ndarray]) -> List[Dict]:
        """Process pages sequentially"""
        page_results = []
        
        for idx, page_image in enumerate(tqdm(page_images, desc="Processing pages")):
            logger.info(f"Processing page {idx + 1}/{len(page_images)}")
            result = self._process_single_page(page_image, idx)
            page_results.append(result)
            
        return page_results
    
    def _process_pages_parallel(self, page_images: List[np.ndarray]) -> List[Dict]:
        """Process pages in parallel"""
        page_results = [None] * len(page_images)
        
        with ProcessPoolExecutor(max_workers=self.config['parallel_pages']) as executor:
            futures = {
                executor.submit(self._process_single_page, img, idx): idx
                for idx, img in enumerate(page_images)
            }
            
            for future in tqdm(as_completed(futures), 
                             total=len(page_images), 
                             desc="Processing pages"):
                idx = futures[future]
                try:
                    page_results[idx] = future.result()
                except Exception as e:
                    logger.error(f"Error processing page {idx}: {e}")
                    page_results[idx] = {'error': str(e), 'page_number': idx}
        
        return page_results
    
    def _process_single_page(self, page_image: np.ndarray, page_idx: int) -> Dict:
        """Process a single page"""
        page_result = {
            'page_number': page_idx + 1,
            'regions': [],
            'extracted_entities': {},
            'quality_metrics': {}
        }
        
        try:
            # Stage 2: Preprocessing
            preprocessed = self.preprocessor.preprocess(page_image)
            
            # Save intermediate if configured
            if self.config['save_intermediate']:
                self._save_intermediate(preprocessed, f"page_{page_idx}_preprocessed")
            
            # Stage 3: Layout Analysis
            regions = self.layout_analyzer.analyze_layout(preprocessed)
            logger.info(f"Page {page_idx + 1}: Detected {len(regions)} regions")
            
            # Stage 4 & 5: OCR and Post-processing for each region
            all_entities = {}
            for region in regions:
                # Extract region image
                x1, y1, x2, y2 = region.bbox
                region_img = preprocessed[y1:y2, x1:x2]
                
                # OCR extraction
                ocr_result = self.ocr_manager.extract_text(
                    region_img,
                    region.type.value,
                    self.config['confidence_threshold']
                )
                
                # Post-processing
                processed = self.postprocessor.process_text(
                    ocr_result['text'],
                    region.type.value,
                    ocr_result['confidence']
                )
                
                # Update region with results
                region.text = processed['processed']
                region.metadata = {
                    'ocr_engine': ocr_result.get('engine'),
                    'confidence': ocr_result['confidence'],
                    'corrections': processed['corrections']
                }
                
                # Aggregate entities
                for entity_type, values in processed['entities'].items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = []
                    all_entities[entity_type].extend(values)
                
                # Handle specialized regions
                if self.config['enable_specialized_processing']:
                    if region.type.value == 'signature':
                        sig_info = self.specialized.process_signature(region_img)
                        region.metadata.update(sig_info)
                    elif region.type.value == 'checkbox':
                        cb_info = self.specialized.process_checkbox(region_img)
                        region.metadata.update(cb_info)
            
            # Convert regions to dictionaries
            page_result['regions'] = [
                {
                    'type': r.type.value,
                    'bbox': r.bbox,
                    'text': r.text or '',
                    'confidence': r.confidence,
                    'metadata': r.metadata or {}
                }
                for r in regions
            ]
            
            # De-duplicate entities
            page_result['extracted_entities'] = {
                k: list(set(v)) for k, v in all_entities.items()
            }
            
            # Calculate quality metrics
            confidences = [r.confidence for r in regions if r.text]
            page_result['quality_metrics'] = {
                'average_confidence': np.mean(confidences) if confidences else 0.0,
                'min_confidence': min(confidences) if confidences else 0.0,
                'regions_processed': len(regions),
                'regions_with_text': len([r for r in regions if r.text])
            }
            
        except Exception as e:
            logger.error(f"Error processing page {page_idx + 1}: {e}")
            page_result['error'] = str(e)
            
        return page_result
    
    def _save_intermediate(self, image: np.ndarray, name: str):
        """Save intermediate processing results"""
        intermediate_dir = Path(self.config['intermediate_dir'])
        intermediate_dir.mkdir(parents=True, exist_ok=True)
        
        from PIL import Image
        img = Image.fromarray(image)
        img.save(intermediate_dir / f"{name}.png")
    
    def _save_results(self, results: Dict, output_path: Union[str, Path]):
        """Save processing results"""
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        if output_path.suffix == '.json':
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        else:
            # Default to JSON with provided filename
            output_path = output_path.with_suffix('.json')
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Results saved to: {output_path}")
```

### Additional Components

```python
# src/pipeline/specialized.py
import cv2
import numpy as np
from typing import Dict
import hashlib

class SpecializedProcessor:
    """Handle specialized document elements"""
    
    def process_signature(self, signature_img: np.ndarray) -> Dict:
        """Process signature region"""
        # Generate signature hash for comparison
        sig_hash = hashlib.md5(signature_img.tobytes()).hexdigest()
        
        # Calculate signature characteristics
        _, binary = cv2.threshold(signature_img, 127, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        return {
            'signature_hash': sig_hash,
            'stroke_count': len(contours),
            'is_present': len(contours) > 5,  # Heuristic for signature presence
            'requires_verification': True
        }
    
    def process_checkbox(self, checkbox_img: np.ndarray) -> Dict:
        """Determine checkbox state"""
        _, binary = cv2.threshold(checkbox_img, 127, 255, cv2.THRESH_BINARY_INV)
        fill_ratio = np.sum(binary > 0) / binary.size
        
        return {
            'checked': fill_ratio > 0.3,
            'confidence': min(0.95, abs(fill_ratio - 0.5) * 2)
        }

# src/pipeline/output_generator.py
class OutputGenerator:
    """Generate structured output from processing results"""
    
    def generate_output(self, page_results: List[Dict], metadata: Dict) -> Dict:
        """Generate final structured output"""
        # Aggregate all entities across pages
        all_entities = {}
        for page in page_results:
            if 'extracted_entities' in page:
                for entity_type, values in page['extracted_entities'].items():
                    if entity_type not in all_entities:
                        all_entities[entity_type] = []
                    all_entities[entity_type].extend(values)
        
        # De-duplicate
        for entity_type in all_entities:
            all_entities[entity_type] = list(set(all_entities[entity_type]))
        
        # Calculate overall quality metrics
        all_confidences = []
        for page in page_results:
            if 'quality_metrics' in page and 'average_confidence' in page['quality_metrics']:
                all_confidences.append(page['quality_metrics']['average_confidence'])
        
        overall_confidence = np.mean(all_confidences) if all_confidences else 0.0
        
        return {
            'document_metadata': metadata,
            'pages': page_results,
            'extracted_entities': all_entities,
            'quality_score': overall_confidence,
            'validation_flags': self._generate_validation_flags(page_results)
        }
    
    def _generate_validation_flags(self, page_results: List[Dict]) -> List[Dict]:
        """Generate validation flags for review"""
        flags = []
        
        for page in page_results:
            if 'error' in page:
                flags.append({
                    'type': 'processing_error',
                    'page': page['page_number'],
                    'message': page['error']
                })
            
            if 'quality_metrics' in page:
                metrics = page['quality_metrics']
                if metrics.get('average_confidence', 1.0) < 0.7:
                    flags.append({
                        'type': 'low_confidence',
                        'page': page['page_number'],
                        'confidence': metrics['average_confidence']
                    })
        
        return flags
```

## Configuration

Create a configuration file `config/settings.yaml`:

```yaml
pipeline:
  dpi: 300
  languages: ['en']
  device: 'cuda'  # or 'cpu'
  parallel_pages: 4
  confidence_threshold: 0.6
  enable_specialized_processing: true
  save_intermediate: false
  intermediate_dir: './intermediate'

paths:
  legal_dictionary: './dictionaries/legal_terms.txt'
  models_dir: './models'
  temp_dir: '/tmp/ocr_pipeline'

processing:
  max_image_size: [4096, 4096]
  jpeg_quality: 95
  
logging:
  level: 'INFO'
  format: '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
  file: './logs/pipeline.log'
```

## Usage Examples

```python
# example_usage.py
from pathlib import Path
from src.pipeline.orchestrator import OCRPipeline

# Initialize pipeline
pipeline = OCRPipeline({
    'dpi': 300,
    'languages': ['en'],
    'device': 'cuda' if torch.cuda.is_available() else 'cpu',
    'parallel_pages': 4,
    'legal_dictionary_path': './dictionaries/legal_terms.txt'
})

# Process a document
input_file = Path('./samples/legal_contract.pdf')
output_file = Path('./output/contract_extracted.json')

results = pipeline.process_document(input_file, output_file)

# Access results
print(f"Processed {results['document_metadata']['page_count']} pages")
print(f"Overall confidence: {results['quality_score']:.2%}")
print(f"Extracted entities: {list(results['extracted_entities'].keys())}")

# Check for validation flags
if results['validation_flags']:
    print("\nValidation flags:")
    for flag in results['validation_flags']:
        print(f"  - {flag['type']}: {flag.get('message', '')}")
```

## Performance Optimization

1. **GPU Acceleration**: Set device='cuda' for deep learning models
2. **Parallel Processing**: Adjust parallel_pages based on CPU cores
3. **Caching**: Implement Redis caching for repeated documents
4. **Model Optimization**: Use ONNX runtime for faster inference
5. **Batch Processing**: Process multiple documents in queue

## Notes for Implementation

1. **Install Dependencies**: Run `pip install -r requirements.txt` and system dependencies
2. **Download Models**: Some models (spaCy, LayoutParser) need separate downloads
3. **Legal Dictionary**: Create a text file with legal terms (one per line)
4. **Error Handling**: The pipeline includes comprehensive error handling
5. **Logging**: Detailed logging helps debug issues
6. **Scalability**: Use Celery for distributed processing of large batches

This implementation provides a production-ready OCR pipeline specifically optimized for legal documents with high accuracy requirements.
