"""
Service configuration for Docker environment
"""
import os

# Service URLs - Docker service names (all services run in Docker)
HAYSTACK_URL = "http://haystack-judicial:8000"
DOCTOR_URL = "http://doctor-judicial:5050"
UNSTRUCTURED_URL = "http://unstructured-service:8880"  # If/when deployed
DATABASE_HOST = "db"

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', f'postgresql://aletheia:aletheia123@{DATABASE_HOST}:5432/aletheia')

# API Keys
COURTLISTENER_API_TOKEN = os.getenv('COURTLISTENER_API_TOKEN', '')
FLP_API_KEY = os.getenv('FLP_API_KEY', '')

# Service endpoints
SERVICES = {
    'haystack': {
        'url': HAYSTACK_URL,
        'endpoints': {
            'documents': f"{HAYSTACK_URL}/documents",
            'search': f"{HAYSTACK_URL}/search",
            'health': f"{HAYSTACK_URL}/health"
        }
    },
    'doctor': {
        'url': DOCTOR_URL,
        'endpoints': {
            'extract': f"{DOCTOR_URL}/extract",
            'thumbnail': f"{DOCTOR_URL}/thumbnail"
        }
    }
}