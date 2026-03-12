"""
Centralized configuration defaults for the test harness.

All values can be overridden via environment variables or CLI args.
"""

import os
from pathlib import Path

# Project root
PROJECT_ROOT = Path(__file__).parent.parent

# Test harness root
HARNESS_ROOT = Path(__file__).parent

# Default LLM settings
DEFAULT_BASE_URL = os.environ.get("EVAL_BASE_URL", "http://localhost:11434/v1")
DEFAULT_API_KEY = os.environ.get("EVAL_API_KEY", "ollama")
DEFAULT_MODEL = os.environ.get("EVAL_MODEL", "qwen2.5:14b")

# Paths
TASKS_DIR = HARNESS_ROOT / "tasks"
RESULTS_DIR = HARNESS_ROOT / "results"

# Runner defaults
MAX_TURNS = 50
DEFAULT_TIMEOUT = 300.0  # seconds

# Grading weights
WEIGHT_COVERAGE = 0.25
WEIGHT_ORDER = 0.15
WEIGHT_EFFICIENCY = 0.15
WEIGHT_ERROR_RECOVERY = 0.15
WEIGHT_GEOMETRY = 0.30
