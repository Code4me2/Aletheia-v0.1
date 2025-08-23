#!/usr/bin/env python3
"""Convert PDF to text using court-processor's PDF processor"""
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'court-processor'))

from pdf_processor import PDFProcessor

# Initialize the PDF processor
processor = PDFProcessor(ocr_enabled=True)

# PDF file to convert
pdf_file = "Human levitation.pdf"
output_dir = "n8n/local-files/uploads/test"
output_file = os.path.join(output_dir, "Human_levitation.txt")

# Extract text from PDF
print(f"Converting {pdf_file} to text...")
text, metadata = processor.extract_text_from_pdf(pdf_file)

# Save the text to file
with open(output_file, 'w', encoding='utf-8') as f:
    f.write(f"Extracted from: {pdf_file}\n")
    f.write(f"Pages: {metadata.get('pages', 'Unknown')}\n")
    f.write(f"Title: {metadata.get('title', 'Unknown')}\n")
    f.write(f"Author: {metadata.get('author', 'Unknown')}\n")
    f.write(f"Creation Date: {metadata.get('creation_date', 'Unknown')}\n")
    f.write("="*50 + "\n\n")
    f.write(text)

print(f"Text saved to: {output_file}")
print(f"Total pages: {metadata.get('pages', 'Unknown')}")