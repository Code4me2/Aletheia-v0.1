FROM python:3.13-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Get tesseract dependencies
RUN apt-get update
RUN apt-get install libtesseract-dev libleptonica-dev liblept5 -y
RUN apt-get install tesseract-ocr -y
RUN apt-get install python3-pil -y
RUN apt-get install tesseract-ocr-eng -y
RUN apt-get install tesseract-ocr-script-latn -y
RUN apt-get install ffmpeg libsm6 libxext6  -y


# Copy only requirements first for better caching
COPY n8n/unstructured-service/requirements.txt .
RUN pip install -r requirements.txt


# Copy application code
#COPY . .

COPY n8n/unstructured-service/unstructured_service.py .


# Run the application
CMD ["uvicorn", "unstructured_service:app", "--host", "0.0.0.0", "--port", "8880", "--reload"]