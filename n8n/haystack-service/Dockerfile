FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for better caching
COPY requirements-rag.txt ./
RUN pip install --no-cache-dir -r requirements-rag.txt

# Install Elasticsearch integration separately
RUN pip install --no-cache-dir "elasticsearch-haystack>=1.0.0" || echo "Elasticsearch integration will be handled differently"

# Create a non-root user
RUN useradd -m -u 1000 -s /bin/bash appuser

# Create a directory for models that can be mounted as a volume
RUN mkdir -p /app/models && chown -R appuser:appuser /app

# Set environment variable for model cache
ENV SENTENCE_TRANSFORMERS_HOME=/app/models

# Copy application code
COPY --chown=appuser:appuser . .

# Switch to non-root user
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=60s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run the application - use RAG-only service
CMD ["uvicorn", "haystack_service_rag:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]