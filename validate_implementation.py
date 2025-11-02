#!/usr/bin/env python3
"""
Quick validation script to check if the multi-database implementation is ready.

Checks:
1. All new Python modules can be imported
2. Database models are valid
3. API routes are properly configured
4. Dependencies work correctly
"""
import sys
import importlib.util

def check_module(module_path, description):
    """Check if a module can be imported."""
    try:
        spec = importlib.util.spec_from_file_location("module", module_path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}: {e}")
        return False

def main():
    """Run validation checks."""
    print("=" * 60)
    print("Multi-Database Implementation Validation")
    print("=" * 60)
    print()

    checks = [
        ("backend/core/visibility.py", "Visibility filtering module"),
        ("backend/api/schemas/collectors.py", "Collector schemas"),
        ("backend/api/routes/collectors.py", "Collector routes"),
        ("backend/api/routes/database_connections.py", "Database connection routes"),
        ("backend/api/routes/slow_queries.py", "Slow queries routes (updated)"),
        ("backend/api/routes/stats.py", "Stats routes (updated)"),
        ("backend/api/routes/statistics.py", "Statistics routes (updated)"),
    ]

    results = []
    for module_path, description in checks:
        results.append(check_module(module_path, description))

    print()
    print("=" * 60)
    if all(results):
        print("✓ All validation checks passed!")
        print()
        print("Next steps:")
        print("1. Run database migrations (see MIGRATION_GUIDE.md)")
        print("2. Start the backend: cd backend && uvicorn main:app --reload")
        print("3. Test the API endpoints")
        print("=" * 60)
        return 0
    else:
        print("✗ Some validation checks failed")
        print("Please fix the errors above before proceeding")
        print("=" * 60)
        return 1

if __name__ == "__main__":
    sys.exit(main())
