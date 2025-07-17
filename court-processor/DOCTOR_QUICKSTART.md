# Doctor Service Quick Start Guide

## 1. Start Doctor Service (1 minute)

```bash
# From the project root directory
docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml up -d doctor
```

## 2. Verify Doctor is Running

```bash
# Check service health
curl http://localhost:5050/
# Should return: "Heartbeat detected."

# Check logs
docker logs doctor-judicial
```

## 3. That's It!

The court processor will automatically use Doctor for PDF processing when available. No code changes needed.

## What Doctor Provides

- **Better PDF text extraction** than PyPDF2
- **Handles scanned documents** with OCR
- **Optimized for legal documents**
- **Processes complex PDFs** that PyPDF2 struggles with

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│ Court Processor │────▶│    Doctor    │────▶│   Eyecite   │
│                 │     │   (PDF→Text)  │     │ (Citations) │
└─────────────────┘     └──────────────┘     └─────────────┘
         │                                            │
         │                                            ▼
         │                                    ┌─────────────┐
         └───────────────────────────────────▶│  PostgreSQL │
                                              └─────────────┘
```

## Troubleshooting

**Doctor not accessible?**
```bash
# Ensure on same network
docker network inspect aletheia_backend | grep doctor
```

**High memory usage?**
```bash
# Doctor is limited to 2GB RAM
docker stats doctor-judicial
```

**Need to stop Doctor?**
```bash
docker-compose -f docker-compose.yml -f n8n/docker-compose.doctor.yml down doctor
```

## Next Steps

- Doctor runs automatically when PDFs are processed
- No configuration needed - it's already integrated
- Monitor performance: `docker logs -f doctor-judicial`