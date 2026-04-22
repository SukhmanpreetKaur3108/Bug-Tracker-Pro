"""
modules/priority.py  —  C Priority Engine Bridge
=================================================
Loads the compiled C shared library and exposes a clean Python interface
via ctypes.  If the library is absent (e.g. on a CI machine without a
C compiler), the module falls back to a pure-Python function that mirrors
the C formula exactly so the application remains fully functional.

Compile the library first:
    Windows (MinGW-w64):
        gcc -shared -o priority_engine.dll priority_engine.c -lm

    Linux / macOS:
        gcc -shared -fPIC -o priority_engine.so priority_engine.c -lm

ctypes type annotations
-----------------------
    argtypes: [c_int, c_int, c_int]   ← severity, age_days, related_count
    restype : c_double                ← score in [0.0, 100.0]
"""

import ctypes
import logging
import os
import sys

logger = logging.getLogger(__name__)

# Resolve absolute path to the shared library
_ROOT = os.path.dirname(os.path.dirname(__file__))
_LIB_NAME = "priority_engine.dll" if sys.platform == "win32" else "priority_engine.so"
_LIB_PATH = os.path.join(_ROOT, _LIB_NAME)

# Attempt to load the compiled library
_lib: ctypes.CDLL | None = None
try:
    _lib = ctypes.CDLL(_LIB_PATH)
    # Declare exact argument and return types to ensure correct marshalling
    _lib.calculate_priority.argtypes = [ctypes.c_int, ctypes.c_int, ctypes.c_int]
    _lib.calculate_priority.restype  = ctypes.c_double
    logger.info("C priority engine loaded: %s", _LIB_PATH)
except OSError:
    logger.warning(
        "C library not found at '%s' — using Python fallback. "
        "Compile priority_engine.c to enable the C engine.",
        _LIB_PATH,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def score_bug(severity: int, age_days: int, related_count: int) -> float:
    """
    Compute a weighted priority score for a bug.

    Delegates to the C shared library when available; otherwise falls back
    to the pure-Python implementation with identical logic.

    :param severity:      Severity level: 1 (Low), 2 (Medium), 3 (High), 4 (Critical).
    :param age_days:      Days since the bug was reported (must be >= 0).
    :param related_count: Number of related/duplicate bugs (must be >= 0).
    :return:              A float in [0.0, 100.0].  Higher = more urgent.
    """
    if _lib is not None:
        return _lib.calculate_priority(
            ctypes.c_int(severity),
            ctypes.c_int(age_days),
            ctypes.c_int(related_count),
        )
    return _python_fallback(severity, age_days, related_count)


def using_c_engine() -> bool:
    """Return True if the C shared library was loaded successfully."""
    return _lib is not None


# ---------------------------------------------------------------------------
# Pure-Python fallback (identical logic to the C function)
# ---------------------------------------------------------------------------

def _python_fallback(severity: int, age_days: int, related_count: int) -> float:
    """
    Mirror of calculate_priority() written in pure Python.

    Used automatically when the C library is unavailable.
    """
    if severity < 1 or severity > 4 or age_days < 0 or related_count < 0:
        return 0.0

    severity_weight = severity / 4.0
    age_factor      = min(age_days / 30.0, 1.0)
    freq_factor     = min(related_count / 5.0, 1.0)

    return (severity_weight * 40.0) + (age_factor * 35.0) + (freq_factor * 25.0)
