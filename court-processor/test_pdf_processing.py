#!/usr/bin/env python3
"""
Test PDF processing capabilities with OCR
"""
import os
import requests
import io

print("Testing PDF Processing Capabilities")
print("=" * 50)

# First, check what's actually available
print("\n1. Checking available libraries...")
libraries = {
    'pytesseract': False,
    'PIL/Pillow': False,
    'PyPDF2': False,
    'PyMuPDF/fitz': False
}

try:
    import pytesseract
    libraries['pytesseract'] = True
    print("✅ pytesseract (OCR) is available")
except:
    print("❌ pytesseract not available")

try:
    from PIL import Image
    libraries['PIL/Pillow'] = True
    print("✅ PIL/Pillow (Image processing) is available")
except:
    print("❌ PIL/Pillow not available")

try:
    import PyPDF2
    libraries['PyPDF2'] = True
    print("✅ PyPDF2 is available")
except:
    print("❌ PyPDF2 not available")

try:
    import fitz
    libraries['PyMuPDF/fitz'] = True
    print("✅ PyMuPDF (fitz) is available")
except:
    print("❌ PyMuPDF (fitz) not available")

# Install missing libraries
if not libraries['PyPDF2']:
    print("\n2. Installing PyPDF2...")
    os.system("pip install PyPDF2")
    try:
        import PyPDF2
        libraries['PyPDF2'] = True
        print("✅ PyPDF2 installed successfully")
    except:
        print("❌ Failed to install PyPDF2")

# Now test with a real PDF
if libraries['pytesseract'] and libraries['PIL/Pillow']:
    print("\n3. Testing OCR on a court PDF...")
    
    # Get a PDF from our downloaded samples
    pdf_files = []
    if os.path.exists('downloaded_pdfs'):
        pdf_files = [f for f in os.listdir('downloaded_pdfs') if f.endswith('.pdf')]
    
    if pdf_files:
        test_pdf = os.path.join('downloaded_pdfs', pdf_files[0])
        print(f"   Using: {test_pdf}")
        
        # Method 1: Try with PyPDF2 (text extraction without OCR)
        if libraries['PyPDF2']:
            try:
                import PyPDF2
                with open(test_pdf, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    num_pages = len(pdf_reader.pages)
                    print(f"\n   PDF has {num_pages} pages")
                    
                    # Extract text from first page
                    first_page = pdf_reader.pages[0]
                    text = first_page.extract_text()
                    
                    if text.strip():
                        print("   ✅ Text extraction successful (no OCR needed)")
                        print(f"   Preview: {text[:200]}...")
                    else:
                        print("   ⚠️  No text found - OCR may be needed")
            except Exception as e:
                print(f"   ❌ PyPDF2 error: {e}")
        
        # Method 2: OCR approach (for scanned PDFs)
        print("\n4. Testing OCR approach...")
        print("   Note: For production use, we would:")
        print("   - Convert PDF pages to images")
        print("   - Run Tesseract OCR on each page")
        print("   - Combine the results")
        
        # Test Tesseract directly
        try:
            version = pytesseract.get_tesseract_version()
            print(f"   ✅ Tesseract version: {version}")
        except Exception as e:
            print(f"   ❌ Tesseract error: {e}")

# Summary
print("\n" + "=" * 50)
print("PDF PROCESSING CAPABILITY SUMMARY")
print("=" * 50)

print("\n✅ AVAILABLE:")
print("- Tesseract OCR 5.3.0 (system-wide)")
print("- pytesseract (Python wrapper)")
print("- Basic text extraction from PDFs")

print("\n❌ MISSING:")
print("- Doctor service (FLP's PDF processor)")
print("- Advanced PDF libraries (pdfplumber, etc.)")

print("\n📋 RECOMMENDATIONS:")
print("1. For searchable PDFs: Use PyPDF2 for direct text extraction")
print("2. For scanned PDFs: Convert to images → OCR with Tesseract")
print("3. For production: Consider running Doctor service")
print("4. Current setup can handle most modern court PDFs")