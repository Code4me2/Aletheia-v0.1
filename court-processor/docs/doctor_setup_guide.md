# Doctor Service Setup Guide

## Complexity Level: **Low-Medium** ⭐⭐⭐☆☆

The Docker setup for Doctor is relatively straightforward. Here's what's involved:

## 1. Basic Setup (5 minutes)

### Option A: Add to existing docker-compose.yml
```yaml
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
```

### Option B: Standalone Docker run
```bash
docker run -d \
  --name doctor \
  -p 5050:5050 \
  -e WORKER_COUNT=4 \
  --memory="2g" \
  --network=backend \
  freelawproject/doctor:latest
```

## 2. Requirements

- **Memory**: 2GB recommended (for OCR operations)
- **Port**: 5050 (usually available)
- **Network**: Must be on same network as court-processor
- **Disk**: ~500MB for the Docker image

## 3. Integration Steps

### Minimal Changes Needed:

1. **Add health check to court-processor** (optional):
```python
def check_doctor_available():
    try:
        response = requests.get('http://doctor:5050/', timeout=2)
        return response.status_code == 200
    except:
        return False
```

2. **Update PDF processing function**:
```python
async def extract_text(pdf_path):
    if check_doctor_available():
        # Use Doctor
        with open(pdf_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(
                'http://doctor:5050/extract/doc/text/',
                files=files,
                data={'strip_margin': True}
            )
            if response.status_code == 200:
                return response.json()['text']
    
    # Fallback to PyPDF2
    return extract_with_pypdf2(pdf_path)
```

## 4. No Code Changes Required

Since we're already using PyPDF2 as fallback, you can:
1. **Keep all existing code unchanged**
2. **Doctor becomes an optional performance enhancement**
3. **System continues working without Doctor**

## 5. Testing Doctor (Optional)

```bash
# Start Doctor
docker-compose up -d doctor

# Test extraction
curl -X POST -F "file=@test.pdf" http://localhost:5050/extract/doc/text/

# Check logs
docker logs doctor-judicial
```

## Complexity Breakdown

✅ **Simple**:
- Single Docker container
- No database changes
- No code changes required
- Works alongside existing setup

⚠️ **Slightly Complex**:
- Needs 2GB memory allocation
- Another service to monitor
- Network configuration (if not using docker-compose)

❌ **Not Complex**:
- No authentication setup
- No persistent storage needed
- No complex configuration
- No dependencies on other services

## Recommendation

The Docker setup is **quite simple** - just adding one service to docker-compose.yml. The real complexity is whether you want to:

1. **Just add it**: 5 minutes, improves PDF extraction quality
2. **Fully integrate**: 1-2 hours, add health checks and monitoring
3. **Skip for now**: Current PyPDF2 solution is working fine

Since your current PDF extraction is functional, adding Doctor is a **nice-to-have optimization**, not a requirement.