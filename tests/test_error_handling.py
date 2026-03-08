"""Tests for engine.error_handling — exceptions, validators, decorators."""

import numpy as np
import pytest

from engine.error_handling import (
    DubforgeError,
    ExportError,
    InvalidPresetError,
    InvalidSignalError,
    RenderError,
    main,
    retry,
    safe_render,
    validate_duration,
    validate_frequency,
    validate_inputs,
    validate_output_dir,
    validate_signal,
)

# ── Exception classes ────────────────────────────────────────────────────

class TestExceptions:
    def test_dubforge_error_is_exception(self):
        assert issubclass(DubforgeError, Exception)

    def test_invalid_signal_error_hierarchy(self):
        assert issubclass(InvalidSignalError, DubforgeError)

    def test_invalid_preset_error_hierarchy(self):
        assert issubclass(InvalidPresetError, DubforgeError)

    def test_render_error_hierarchy(self):
        assert issubclass(RenderError, DubforgeError)

    def test_export_error_hierarchy(self):
        assert issubclass(ExportError, DubforgeError)

    def test_raise_dubforge_error(self):
        with pytest.raises(DubforgeError):
            raise DubforgeError("test")

    def test_raise_invalid_signal_caught_as_dubforge(self):
        with pytest.raises(DubforgeError):
            raise InvalidSignalError("bad signal")


# ── validate_signal ──────────────────────────────────────────────────────

class TestValidateSignal:
    def test_valid_signal_passthrough(self):
        sig = np.array([0.1, 0.2, 0.3])
        result = validate_signal(sig)
        np.testing.assert_array_equal(result, sig)

    def test_none_raises(self):
        with pytest.raises(InvalidSignalError):
            validate_signal(None)

    def test_non_array_raises(self):
        with pytest.raises(InvalidSignalError):
            validate_signal([1, 2, 3])

    def test_empty_array_raises(self):
        with pytest.raises(InvalidSignalError):
            validate_signal(np.array([]))

    def test_nan_replaced_with_zero(self):
        sig = np.array([1.0, np.nan, 0.5])
        result = validate_signal(sig)
        assert not np.any(np.isnan(result))

    def test_inf_clipped(self):
        sig = np.array([np.inf, -np.inf, 0.5])
        result = validate_signal(sig)
        assert not np.any(np.isinf(result))

    def test_custom_name_in_error(self):
        with pytest.raises(InvalidSignalError, match="my_sig"):
            validate_signal(None, "my_sig")


# ── validate_frequency ───────────────────────────────────────────────────

class TestValidateFrequency:
    def test_valid_freq(self):
        assert validate_frequency(440.0) == 440.0

    def test_int_freq_returns_float(self):
        assert isinstance(validate_frequency(100), float)

    def test_zero_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_frequency(0)

    def test_negative_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_frequency(-100.0)

    def test_above_nyquist_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_frequency(22051)

    def test_string_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_frequency("440")

    def test_boundary_22050_ok(self):
        assert validate_frequency(22050) == 22050.0


# ── validate_duration ────────────────────────────────────────────────────

class TestValidateDuration:
    def test_valid_duration(self):
        assert validate_duration(2.0) == 2.0

    def test_zero_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_duration(0)

    def test_negative_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_duration(-1.0)

    def test_too_long_raises(self):
        with pytest.raises(InvalidPresetError):
            validate_duration(301)

    def test_boundary_300_ok(self):
        assert validate_duration(300) == 300.0


# ── validate_output_dir ──────────────────────────────────────────────────

class TestValidateOutputDir:
    def test_creates_dir(self, tmp_path):
        target = tmp_path / "new_dir"
        validate_output_dir(str(target))
        assert target.exists()

    def test_returns_path(self, tmp_path):
        from pathlib import Path
        result = validate_output_dir(str(tmp_path / "out"))
        assert isinstance(result, Path)


# ── safe_render decorator ────────────────────────────────────────────────

class TestSafeRender:
    def test_success_passthrough(self):
        @safe_render
        def ok():
            return np.array([1.0, 2.0])
        result = ok()
        np.testing.assert_array_equal(result, np.array([1.0, 2.0]))

    def test_error_returns_zeros(self):
        @safe_render
        def broken():
            raise ValueError("boom")
        result = broken()
        assert isinstance(result, np.ndarray)
        assert np.all(result == 0.0)

    def test_error_returns_sample_rate_length(self):
        @safe_render
        def broken():
            raise RuntimeError("fail")
        result = broken()
        from engine.phi_core import SAMPLE_RATE
        assert len(result) == SAMPLE_RATE


# ── retry decorator ──────────────────────────────────────────────────────

class TestRetry:
    def test_success_no_retry_needed(self):
        @retry(max_attempts=3)
        def ok():
            return "done"
        assert ok() == "done"

    def test_fails_all_raises_render_error(self):
        @retry(max_attempts=2, backoff_factor=1.0)
        def broken():
            raise ValueError("always fails")
        with pytest.raises(RenderError, match="Failed after 2 attempts"):
            broken()

    def test_succeeds_on_second_try(self):
        counter = {"n": 0}
        @retry(max_attempts=3, backoff_factor=1.0)
        def flaky():
            counter["n"] += 1
            if counter["n"] < 2:
                raise ValueError("not yet")
            return "ok"
        assert flaky() == "ok"


# ── validate_inputs decorator ────────────────────────────────────────────

class TestValidateInputs:
    def test_valid_inputs_pass(self):
        @validate_inputs(freq=validate_frequency, dur=validate_duration)
        def make_tone(freq, dur):
            return freq * dur
        assert make_tone(440.0, 1.0) == 440.0

    def test_invalid_freq_raises(self):
        @validate_inputs(freq=validate_frequency)
        def make_tone(freq):
            return freq
        with pytest.raises(InvalidPresetError):
            make_tone(-100)


# ── main ─────────────────────────────────────────────────────────────────

class TestMain:
    def test_main_runs(self, capsys):
        main()
        captured = capsys.readouterr()
        assert "Error Handling" in captured.out
