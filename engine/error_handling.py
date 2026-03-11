"""
DUBFORGE — Error Handling & Validation  (Session 135)

Input validation decorators, graceful failure wrappers,
and retry logic for all public functions.
"""

import functools
import time
from pathlib import Path
from typing import TypeVar

import numpy as np

F = TypeVar("F")

from engine.config_loader import PHI
class DubforgeError(Exception):
    """Base exception for DUBFORGE errors."""


class InvalidSignalError(DubforgeError):
    """Signal is invalid (empty, NaN, etc)."""


class InvalidPresetError(DubforgeError):
    """Preset configuration is invalid."""


class RenderError(DubforgeError):
    """Rendering failed."""


class ExportError(DubforgeError):
    """Export to file failed."""


# ═══════════════════════════════════════════════════════════════════════════
# VALIDATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def validate_signal(signal: np.ndarray, name: str = "signal") -> np.ndarray:
    """Validate a numpy signal array. Returns cleaned signal."""
    if signal is None:
        raise InvalidSignalError(f"{name}: signal is None")
    if not isinstance(signal, np.ndarray):
        raise InvalidSignalError(f"{name}: expected numpy array, got {type(signal)}")
    if signal.size == 0:
        raise InvalidSignalError(f"{name}: signal is empty")
    if np.any(np.isnan(signal)):
        signal = np.nan_to_num(signal, nan=0.0)
    if np.any(np.isinf(signal)):
        signal = np.clip(signal, -1e6, 1e6)
    return signal


def validate_frequency(freq: float, name: str = "frequency") -> float:
    """Validate a frequency value."""
    if not isinstance(freq, (int, float)):
        raise InvalidPresetError(f"{name}: expected number, got {type(freq)}")
    if freq <= 0:
        raise InvalidPresetError(f"{name}: must be positive, got {freq}")
    if freq > 22050:
        raise InvalidPresetError(f"{name}: exceeds Nyquist ({freq} > 22050)")
    return float(freq)


def validate_duration(dur: float, name: str = "duration") -> float:
    """Validate a duration value."""
    if dur <= 0:
        raise InvalidPresetError(f"{name}: must be positive, got {dur}")
    if dur > 300:
        raise InvalidPresetError(f"{name}: unreasonably long ({dur}s)")
    return float(dur)


def validate_output_dir(path: str) -> Path:
    """Validate and create output directory."""
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p


# ═══════════════════════════════════════════════════════════════════════════
# DECORATORS
# ═══════════════════════════════════════════════════════════════════════════

def safe_render(func):
    """Decorator that catches render errors and returns a silent signal."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception:
            # Return 1 second of silence
            from engine.phi_core import SAMPLE_RATE
            return np.zeros(SAMPLE_RATE)
    return wrapper


def retry(max_attempts: int = 3, backoff_factor: float = PHI):
    """Retry decorator with phi-ratio backoff."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_error = None
            for attempt in range(max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_error = e
                    if attempt < max_attempts - 1:
                        wait = backoff_factor ** attempt * 0.1
                        time.sleep(wait)
            raise RenderError(f"Failed after {max_attempts} attempts: {last_error}")
        return wrapper
    return decorator


def validate_inputs(**validators):
    """Decorator to validate function inputs.

    Usage:
        @validate_inputs(freq=validate_frequency, dur=validate_duration)
        def make_tone(freq, dur): ...
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            import inspect
            sig = inspect.signature(func)
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()
            for param_name, validator_fn in validators.items():
                if param_name in bound.arguments:
                    bound.arguments[param_name] = validator_fn(
                        bound.arguments[param_name], param_name
                    )
            return func(*bound.args, **bound.kwargs)
        return wrapper
    return decorator


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT
# ═══════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("Error Handling: validators, decorators, and error classes ready.")
    print(f"  Exceptions: {', '.join(c.__name__ for c in [DubforgeError, InvalidSignalError, InvalidPresetError, RenderError, ExportError])}")
    print("  Validators: validate_signal, validate_frequency, validate_duration")
    print("  Decorators: safe_render, retry, validate_inputs")


if __name__ == "__main__":
    main()
