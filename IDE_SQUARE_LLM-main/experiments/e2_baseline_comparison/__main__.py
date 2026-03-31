"""
CLI entry point for E2 experiment.

Usage:
    python -m experiments.e2_baseline_comparison
"""

import asyncio
from .main import main

if __name__ == "__main__":
    asyncio.run(main())
