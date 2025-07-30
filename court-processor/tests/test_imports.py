#!/usr/bin/env python3
"""Test script to check import paths and dependencies"""
import sys
import os

print("Python version:", sys.version)
print("\nPython path:")
for path in sys.path:
    print(f"  - {path}")

print("\nCurrent working directory:", os.getcwd())
print("\nChecking if we're in Docker:", os.path.exists('/app'))

# Try importing various modules
modules_to_test = [
    "aiohttp",
    "psycopg2",
    "courts_db",
    "eyecite",
    "reporters_db",
    "services.database",
    "eleven_stage_pipeline_robust_complete",
    "fastapi",
    "uvicorn"
]

print("\nTesting imports:")
for module in modules_to_test:
    try:
        if module == "services.database":
            # Need to add path for services
            sys.path.append(os.path.dirname(os.path.abspath(__file__)))
        __import__(module)
        print(f"✓ {module}")
    except ImportError as e:
        print(f"✗ {module}: {e}")
    except Exception as e:
        print(f"✗ {module}: {type(e).__name__}: {e}")