"""Tests for engine.rco — Rollercoaster Optimizer energy curves."""

from engine.rco import (
    RCOProfile,
    exponential_curve,
    fibonacci_step_curve,
    generate_energy_curve,
    linear_curve,
    phi_curve,
    subtronics_emotive_preset,
    subtronics_hybrid_preset,
    subtronics_weapon_preset,
)


class TestCurveGenerators:
    def test_phi_curve_length(self):
        curve = phi_curve(0.0, 1.0, 100)
        assert len(curve) == 100

    def test_phi_curve_values_bounded(self):
        curve = phi_curve(0.0, 1.0, 50)
        assert all(0.0 - 0.01 <= v <= 1.0 + 0.01 for v in curve)

    def test_linear_curve_endpoints(self):
        curve = linear_curve(0.0, 1.0, 100)
        assert abs(curve[0]) < 0.02
        assert abs(curve[-1] - 1.0) < 0.02

    def test_fibonacci_step_curve_monotonic(self):
        curve = fibonacci_step_curve(0.0, 1.0, 100)
        for i in range(1, len(curve)):
            assert curve[i] >= curve[i - 1] - 0.01

    def test_exponential_curve_length(self):
        curve = exponential_curve(0.0, 1.0, 64)
        assert len(curve) == 64


class TestPresets:
    def test_weapon_preset_valid(self):
        p = subtronics_weapon_preset()
        assert isinstance(p, RCOProfile)
        assert len(p.sections) > 0

    def test_emotive_preset_valid(self):
        p = subtronics_emotive_preset()
        assert isinstance(p, RCOProfile)

    def test_hybrid_preset_valid(self):
        p = subtronics_hybrid_preset()
        assert isinstance(p, RCOProfile)


class TestGenerateEnergyCurve:
    def test_generates_dict(self):
        preset = subtronics_weapon_preset()
        result = generate_energy_curve(preset)
        assert isinstance(result, dict)
        assert "energy" in result

    def test_energy_values_bounded(self):
        preset = subtronics_emotive_preset()
        result = generate_energy_curve(preset)
        energy = result["energy"]
        assert all(0.0 <= v <= 1.0 + 0.05 for v in energy)
