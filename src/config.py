"""Central configuration for AIProductBench CN V1.

This module holds only project-wide constants: paths, versions, the frozen
domain set, the rubric shape, and request policy. Model-specific facts live in
the configurable model pool (data/models_v1.json) and are handled by
src/models.py. Pricing and currency rules live in src/pricing.py.

Credentials are read from environment variables only. This project never reads
API keys, tokens, or provider settings from Codex configuration files, shell
history, or any other file on disk.
"""

from __future__ import annotations

from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
MODEL_POOL_FILE = DATA_DIR / "models_v1.json"
DEFAULT_CASES_FILE = DATA_DIR / "fixtures" / "synthetic_v1_cases.json"
PRODUCTION_CASES_FILE = DATA_DIR / "cases_v1.json"  # Phase 3B deliverable, authored domain by domain
RESULTS_DIR = PROJECT_ROOT / "results"
SAMPLE_RESULTS_FILE = PROJECT_ROOT / "sample_results.json"
LEADERBOARD_FILE = PROJECT_ROOT / "leaderboard.html"

# --------------------------------------------------------------------------
# Versions
# --------------------------------------------------------------------------

BENCHMARK_NAME = "AIProductBench CN"
BENCHMARK_VERSION = "1.0.0-dev"
JUDGE_PROMPT_VERSION = "1.0"

# --------------------------------------------------------------------------
# Frozen V1 domain set — see docs/METHODOLOGY_V1.md
# --------------------------------------------------------------------------

DOMAINS = (
    "instruction_constraint_following",
    "structured_information_analysis",
    "product_reasoning_decision",
    "chinese_business_communication",
    "agent_workflow_planning",
)

DOMAIN_SHORT_LABELS = {
    "instruction_constraint_following": "Instruction",
    "structured_information_analysis": "Structured",
    "product_reasoning_decision": "Product",
    "chinese_business_communication": "Chinese comms",
    "agent_workflow_planning": "Agent planning",
}

DIFFICULTIES = ("easy", "medium", "hard")
LANGUAGES = ("zh", "en", "mixed")

# --------------------------------------------------------------------------
# Rubric
# --------------------------------------------------------------------------

RUBRIC_DIMENSIONS = (
    "task_completion",
    "reasoning_quality",
    "instruction_following",
)

SCORE_MIN = 1
SCORE_MAX = 5

# --------------------------------------------------------------------------
# Currency
# --------------------------------------------------------------------------

DISPLAY_CURRENCY = "CNY"

# Production FX snapshot. Currency conversion requires an explicit, dated
# snapshot with a named source. This project never hard-codes a permanent
# conversion rate and never converts silently: while the rate is null, USD
# prices simply have no CNY-normalized value.
FX_SNAPSHOT = {
    "status": "unverified",
    "fx_pair": "USD/CNY",
    "fx_rate": None,
    "fx_snapshot_date": None,
    "source": None,
}

# Synthetic FX snapshot used only by --dry-run so the CNY normalization path is
# exercised offline. Every dry-run artifact is flagged synthetic and this rate
# must never reach a real result.
SYNTHETIC_FX_SNAPSHOT = {
    "status": "synthetic",
    "synthetic": True,
    "fx_pair": "USD/CNY",
    "fx_rate": 7.20,
    "fx_snapshot_date": "2026-09-11",
    "source": "synthetic dry-run fixture — not a real exchange rate",
}

# --------------------------------------------------------------------------
# Request policy
# --------------------------------------------------------------------------

REQUEST_TIMEOUT_SECONDS = 120
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 2.0

# --------------------------------------------------------------------------
# Planning targets (documentation only, not enforced as hard limits)
# --------------------------------------------------------------------------

TARGET_CANDIDATE_MODELS = 10
TARGET_DOMAINS = 5
TARGET_CASES = 50
JUDGES_PER_RESPONSE = 2
