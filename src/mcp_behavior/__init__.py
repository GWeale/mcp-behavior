"""MCP Behavior public package."""

from .core import record, record_async, verify, verify_async
from .models import (
    CallReport,
    Difference,
    EffectReport,
    ScenarioReport,
    Verdict,
    VerificationReport,
)

__all__ = [
    "CallReport",
    "Difference",
    "EffectReport",
    "ScenarioReport",
    "Verdict",
    "VerificationReport",
    "record",
    "record_async",
    "verify",
    "verify_async",
]

__version__ = "0.1.0"
