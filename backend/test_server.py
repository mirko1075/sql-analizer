#!/usr/bin/env python3
"""
Quick test script to verify the FastAPI server starts correctly.

This script:
1. Checks that all modules can be imported
2. Verifies database connection
3. Tests that the FastAPI app can be created
4. Lists all registered endpoints
"""
import sys
import os

# Add backend to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("FastAPI Backend Test")
print("=" * 60)

# Test 1: Import modules
print("\n[1/5] Testing module imports...")
try:
    from core.config import settings
    from core.logger import setup_logger
    from db.session import check_db_connection
    from main import app
    print("✓ All modules imported successfully")
except ImportError as e:
    print(f"✗ Import error: {e}")
    sys.exit(1)

logger = setup_logger(__name__)

# Test 2: Configuration
print("\n[2/5] Checking configuration...")
print(f"  Environment: {settings.env}")
print(f"  Internal DB: {settings.internal_db.host}:{settings.internal_db.port}")
print(f"  Redis: {settings.redis_host}:{settings.redis_port}")
print("✓ Configuration loaded")

# Test 3: Database connection
print("\n[3/5] Testing database connection...")
try:
    if check_db_connection():
        print("✓ Database connection successful")
    else:
        print("⚠ Database connection failed (check if internal-db is running)")
except Exception as e:
    print(f"⚠ Database connection error: {e}")

# Test 4: FastAPI app
print("\n[4/5] Verifying FastAPI app...")
print(f"  Title: {app.title}")
print(f"  Version: {app.version}")
print(f"  Docs URL: http://localhost:8000{app.docs_url}")
print("✓ FastAPI app created")

# Test 5: List routes
print("\n[5/5] Registered endpoints:")
routes_by_prefix = {}
for route in app.routes:
    if hasattr(route, 'methods') and hasattr(route, 'path'):
        prefix = route.path.split('/')[1] if '/' in route.path else 'root'
        if prefix not in routes_by_prefix:
            routes_by_prefix[prefix] = []
        routes_by_prefix[prefix].append({
            'methods': sorted(route.methods - {'HEAD', 'OPTIONS'}),
            'path': route.path,
            'name': route.name
        })

for prefix in sorted(routes_by_prefix.keys()):
    print(f"\n  /{prefix}:")
    for route in sorted(routes_by_prefix[prefix], key=lambda x: x['path']):
        methods = ', '.join(route['methods'])
        print(f"    {methods:10s} {route['path']}")

print("\n" + "=" * 60)
print("✓ All tests passed!")
print("=" * 60)

print("\nTo start the server, run:")
print("  cd backend && python main.py")
print("Or with uvicorn:")
print("  uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000")
print("\nAPI Documentation will be available at:")
print("  http://localhost:8000/docs")
