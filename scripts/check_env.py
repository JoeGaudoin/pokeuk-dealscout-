#!/usr/bin/env python3
"""
Environment validation script.
Run this to check if your development environment is properly configured.

Usage:
    python scripts/check_env.py
"""
import os
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(project_root / "backend"))

def check_mark(ok: bool) -> str:
    return "OK" if ok else "MISSING"

def main():
    print("=" * 50)
    print("PokeUK DealScout - Environment Check")
    print("=" * 50)
    print()

    issues = []

    # Check .env file exists
    env_file = project_root / ".env"
    print(f"[{check_mark(env_file.exists())}] .env file")
    if not env_file.exists():
        issues.append("Copy .env.example to .env: cp .env.example .env")

    # Load settings
    try:
        from config import get_settings
        settings = get_settings()
        print("[OK] Settings loaded")
    except Exception as e:
        print(f"[ERROR] Settings: {e}")
        issues.append("Fix settings configuration")
        settings = None

    print()
    print("Database Configuration:")
    print("-" * 30)

    if settings:
        print(f"  PostgreSQL: {settings.database_url[:50]}...")
        print(f"  Redis: {settings.redis_url}")

    # Check Docker
    import subprocess
    try:
        result = subprocess.run(["docker", "--version"], capture_output=True, text=True)
        print(f"\n[OK] Docker: {result.stdout.strip()}")
    except FileNotFoundError:
        print("\n[MISSING] Docker not installed")
        issues.append("Install Docker: https://docs.docker.com/get-docker/")

    # Check if containers are running
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True,
            text=True,
            cwd=project_root
        )
        if "pokeuk_postgres" in result.stdout:
            print("[OK] PostgreSQL container running")
        else:
            print("[STOPPED] PostgreSQL container")
            issues.append("Start containers: make db-up (or docker compose up -d)")

        if "pokeuk_redis" in result.stdout:
            print("[OK] Redis container running")
        else:
            print("[STOPPED] Redis container")
    except Exception:
        pass

    print()
    print("API Credentials:")
    print("-" * 30)

    if settings:
        ebay_ok = settings.ebay_configured
        print(f"  [{check_mark(ebay_ok)}] eBay API")
        if not ebay_ok:
            issues.append("Add eBay API credentials to .env (optional but recommended)")

        pokemon_ok = bool(settings.pokemon_tcg_api_key)
        print(f"  [{check_mark(pokemon_ok)}] Pokemon TCG API")
        if not pokemon_ok:
            print("       (Optional - public API works without key)")

        proxy_ok = settings.proxy_configured
        print(f"  [{check_mark(proxy_ok) if settings.proxy_enabled else 'DISABLED'}] Proxy")

    print()
    print("Enabled Scrapers:")
    print("-" * 30)

    if settings:
        for scraper in settings.get_enabled_scrapers():
            print(f"  - {scraper}")
        if not settings.get_enabled_scrapers():
            print("  (None - configure API keys to enable)")

    print()
    print("=" * 50)

    if issues:
        print("Issues to resolve:")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
        print()
        return 1
    else:
        print("All checks passed! Ready to run.")
        print()
        print("Next steps:")
        print("  1. make db-up       # Start databases")
        print("  2. make db-migrate  # Run migrations")
        print("  3. make api         # Start API server")
        print()
        return 0


if __name__ == "__main__":
    sys.exit(main())
