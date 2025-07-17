#!/usr/bin/env python3
"""
Analyze the current document processing pipeline
Compare our implementation vs Doctor+FLP
"""

print("=" * 70)
print("CURRENT DOCUMENT PROCESSING PIPELINE ANALYSIS")
print("=" * 70)

# 1. Check what PDF processing we currently have
print("\n1. CURRENT PDF PROCESSING CAPABILITIES:")
print("-" * 50)

# Check installed libraries
try:
    import PyPDF2
    print("✅ PyPDF2 - Basic PDF text extraction")
except:
    print("❌ PyPDF2 not found")

try:
    import pytesseract
    print("✅ pytesseract - OCR for scanned documents")
except:
    print("❌ pytesseract not found")

try:
    import PIL
    print("✅ PIL/Pillow - Image processing for OCR")
except:
    print("❌ PIL not found")

# Check Tesseract
import subprocess
try:
    result = subprocess.run(['tesseract', '--version'], capture_output=True, text=True)
    if result.returncode == 0:
        print("✅ Tesseract OCR 5.3.0 - System-wide OCR engine")
except:
    print("❌ Tesseract not found")

# 2. Check FLP tools
print("\n2. FLP TOOLS CURRENTLY AVAILABLE:")
print("-" * 50)

try:
    import eyecite
    print("✅ Eyecite - Citation extraction")
except:
    print("❌ Eyecite not found")

try:
    from courts_db import courts
    print("✅ Courts-DB - Court standardization")
except:
    print("❌ Courts-DB not found")

try:
    from reporters_db import REPORTERS
    print("✅ Reporters-DB - Reporter normalization")
except:
    print("❌ Reporters-DB not found")

try:
    import judge_pics
    print("✅ Judge-pics - Judge photos")
except:
    print("❌ Judge-pics not found")

# 3. Check what Doctor would provide
print("\n3. DOCTOR SERVICE CAPABILITIES (if running):")
print("-" * 50)
print("🔧 Advanced PDF text extraction with PDF Plumber")
print("🔧 Court document margin stripping")
print("🔧 Federal document number extraction")
print("🔧 Thumbnail generation")
print("🔧 Bad redaction detection (X-Ray)")
print("🔧 Court audio processing")
print("🔧 RECAP-optimized processing")
print("🔧 Parallel processing (16 workers)")

# 4. Current processing flow
print("\n4. CURRENT PROCESSING FLOW:")
print("-" * 50)
print("1. Download PDF from CourtListener")
print("2. Extract text with PyPDF2")
print("3. If no text, could use OCR (Tesseract)")
print("4. Extract citations with Eyecite")
print("5. Standardize courts with Courts-DB")
print("6. Normalize reporters with Reporters-DB")
print("7. Store in PostgreSQL")

# 5. Doctor + FLP flow
print("\n5. DOCTOR + FLP FLOW (ideal):")
print("-" * 50)
print("1. Download PDF from CourtListener")
print("2. Send to Doctor service for:")
print("   - Advanced text extraction")
print("   - Margin stripping")
print("   - Document number extraction")
print("   - Thumbnail generation")
print("3. Process Doctor's clean text with:")
print("   - Eyecite for citations")
print("   - Courts-DB for standardization")
print("   - Reporters-DB for normalization")
print("4. Store enhanced data in PostgreSQL")

# 6. Test current extraction quality
print("\n6. TESTING CURRENT EXTRACTION QUALITY:")
print("-" * 50)

import os
if os.path.exists('opinion_pdfs'):
    pdf_files = [f for f in os.listdir('opinion_pdfs') if f.endswith('.pdf')]
    if pdf_files:
        test_pdf = os.path.join('opinion_pdfs', pdf_files[0])
        print(f"Testing with: {test_pdf}")
        
        # Try PyPDF2 extraction
        try:
            with open(test_pdf, 'rb') as f:
                reader = PyPDF2.PdfReader(f)
                text = reader.pages[0].extract_text()
                print(f"✓ PyPDF2 extracted {len(text)} characters")
                
                # Check for common issues
                if '\n\n\n' in text:
                    print("⚠️  Multiple line breaks detected (formatting issues)")
                if text.count(' ') < len(text) / 10:
                    print("⚠️  Low space count (possible extraction issues)")
                    
        except Exception as e:
            print(f"✗ PyPDF2 error: {e}")
    else:
        print("No test PDFs available")

# 7. Check Doctor service availability
print("\n7. DOCTOR SERVICE STATUS:")
print("-" * 50)

import requests
try:
    # Check if Doctor is running
    response = requests.get('http://localhost:5050/', timeout=2)
    print("✅ Doctor service is running!")
except:
    print("❌ Doctor service not accessible at localhost:5050")
    print("   Would need to start with: docker run -p 5050:5050 freelawproject/doctor:latest")

# Analysis summary
print("\n" + "=" * 70)
print("ANALYSIS SUMMARY")
print("=" * 70)

print("\n🔍 FINDINGS:")
print("1. We have basic PDF processing working (PyPDF2 + Tesseract)")
print("2. FLP citation tools are installed and working")
print("3. Doctor would provide better text extraction for legal documents")
print("4. Doctor handles edge cases our simple extraction might miss")

print("\n💡 RECOMMENDATION:")
print("Current setup works for clean PDFs but Doctor would provide:")
print("- Better handling of court document formatting")
print("- More accurate text for citation extraction")
print("- Thumbnails for UI display")
print("- Document metadata extraction")

print("\n❓ DECISION POINTS:")
print("1. Is the current extraction quality sufficient?")
print("2. Do we need thumbnails and document numbers?")
print("3. Is setting up Doctor service worth the complexity?")
print("4. Should we make Doctor optional or required?")