"""Compatibility shim for JSONL signature I/O.

Historical name: jsonl_validation.py
New modules:
  - ptc_model.py (dataclasses)
  - ptc_jsonl.py  (JSONL I/O)

Keeping this file avoids breaking imports in older code/tests.
"""

from __future__ import annotations

from ptc_jsonl import dump_signature_jsonl, load_signature_jsonl
from ptc_model import ClockRec, PTCSig, utc_now_iso

# Backward-compat alias (prime_tower_clocks.py expects this name)
_utc_now_iso = utc_now_iso

__all__ = [
    "ClockRec",
    "PTCSig",
    "dump_signature_jsonl",
    "load_signature_jsonl",
    "utc_now_iso",
    "_utc_now_iso",
]
