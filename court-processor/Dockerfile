FROM python:3.11-slim

# Install system dependencies
RUN apt-get update && apt-get install -y \
    # For PDF processing
    poppler-utils \
    # For OCR
    tesseract-ocr \
    tesseract-ocr-eng \
    # For database connection
    libpq-dev \
    gcc \
    # For cron
    cron \
    # Cleanup
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Copy application code
COPY --chown=appuser:appuser . .

# Create directories for data with proper ownership
RUN mkdir -p /data/pdfs /data/logs && \
    chown -R appuser:appuser /data /app

# Copy cron job file (cron needs root to run)
COPY scripts/court-schedule /etc/cron.d/court-schedule
RUN chmod 0644 /etc/cron.d/court-schedule && \
    crontab /etc/cron.d/court-schedule

# Add Python3 symlink for compatibility
RUN ln -s /usr/bin/python3 /usr/bin/python || true

# Note: This service requires root for cron, but runs tasks as appuser
# The entrypoint script should handle privilege dropping

# Entrypoint script is copied with application code
ENTRYPOINT ["/app/entrypoint.sh"]