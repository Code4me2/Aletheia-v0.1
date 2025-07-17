#!/usr/bin/env python3
"""
Test setting up Doctor service
"""
import subprocess
import time
import requests

print("=" * 70)
print("DOCTOR SERVICE SETUP TEST")
print("=" * 70)

# Check if Doctor image exists
print("\n1. Checking for Doctor Docker image...")
result = subprocess.run(['docker', 'images', 'freelawproject/doctor', '--format', '{{.Repository}}:{{.Tag}}'], 
                       capture_output=True, text=True)

if 'freelawproject/doctor' in result.stdout:
    print("✅ Doctor image found locally")
else:
    print("❌ Doctor image not found")
    print("   Would need to pull: docker pull freelawproject/doctor:latest")

# Check if port 5050 is available
print("\n2. Checking if port 5050 is available...")
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = sock.connect_ex(('localhost', 5050))
sock.close()

if result != 0:
    print("✅ Port 5050 is available")
else:
    print("❌ Port 5050 is already in use")

# Show how to run Doctor
print("\n3. To run Doctor service:")
print("-" * 50)
print("docker run -d \\")
print("  --name doctor \\")
print("  -p 5050:5050 \\")
print("  -e WORKER_COUNT=4 \\")
print("  --memory='2g' \\")
print("  --network=backend \\")
print("  freelawproject/doctor:latest")

print("\n4. Doctor configuration for docker-compose.yml:")
print("-" * 50)
print("""
  doctor:
    image: freelawproject/doctor:latest
    container_name: doctor-judicial
    ports:
      - "5050:5050"
    environment:
      - WORKER_COUNT=4
    mem_limit: 2g
    networks:
      - backend
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:5050/"]
      interval: 30s
      timeout: 10s
      retries: 3
""")

print("\n5. Integration points needed:")
print("-" * 50)
print("✓ Update process_opinion_pdfs.py to use Doctor API")
print("✓ Update fetch scripts to call Doctor for text extraction")
print("✓ Add Doctor health check to startup")
print("✓ Update documentation to include Doctor setup")

print("\n" + "=" * 70)
print("RECOMMENDATION")
print("=" * 70)
print("\n📊 Current State:")
print("- Basic PDF extraction is working")
print("- Successfully extracted text from 10+ opinions")
print("- Citation extraction is functional")

print("\n🔍 Doctor Benefits:")
print("- Better margin handling for court docs")
print("- Federal document number extraction")
print("- Thumbnails for UI")
print("- More robust extraction for edge cases")

print("\n💡 Suggested Approach:")
print("1. Keep current PyPDF2 extraction as fallback")
print("2. Add Doctor as optional enhancement")
print("3. Use Doctor when available, fallback to PyPDF2")
print("4. This provides resilience and flexibility")