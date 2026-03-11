"""
DUBFORGE — v4.0 Full Integration  (Session 142)

One-command full pipeline: renders a complete EP with all modules.
Validates cross-module interop at production scale.
"""

import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from engine.config_loader import PHI
SAMPLE_RATE = 48000


@dataclass
class IntegrationResult:
    """Result of a full integration run."""
    modules_tested: int = 0
    modules_passed: int = 0
    modules_failed: int = 0
    failures: list[str] = field(default_factory=list)
    elapsed_s: float = 0.0
    outputs: dict[str, str] = field(default_factory=dict)

    @property
    def success(self) -> bool:
        return self.modules_failed == 0


def _try_module(name: str, fn, result: IntegrationResult) -> bool:
    """Try running a module's main(), track result."""
    result.modules_tested += 1
    try:
        fn()
        result.modules_passed += 1
        result.outputs[name] = "ok"
        return True
    except Exception as e:
        result.modules_failed += 1
        result.failures.append(f"{name}: {e}")
        result.outputs[name] = f"FAIL: {e}"
        return False


def run_full_integration() -> IntegrationResult:
    """Run all DUBFORGE modules in dependency order."""
    result = IntegrationResult()
    t0 = time.time()

    # Phase 1 — Core synth engines
    core_synths = [
        ("sub_bass", "engine.sub_bass"),
        ("wobble_bass", "engine.wobble_bass"),
        ("lead_synth", "engine.lead_synth"),
        ("pad_synth", "engine.pad_synth"),
        ("chord_pad", "engine.chord_pad"),
        ("arp_synth", "engine.arp_synth"),
        ("pluck_synth", "engine.pluck_synth"),
        ("drone_synth", "engine.drone_synth"),
        ("formant_synth", "engine.formant_synth"),
    ]

    for name, mod_path in core_synths:
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            _try_module(name, mod.main, result)
        except Exception as e:
            result.modules_tested += 1
            result.modules_failed += 1
            result.failures.append(f"{name}: import error: {e}")

    # Phase 2 — FX & DSP
    fx_modules = [
        ("multiband_distortion", "engine.multiband_distortion"),
        ("sidechain", "engine.sidechain"),
        ("stereo_imager", "engine.stereo_imager"),
        ("reverb_delay", "engine.reverb_delay"),
        ("noise_generator", "engine.noise_generator"),
        ("glitch_engine", "engine.glitch_engine"),
    ]

    for name, mod_path in fx_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            _try_module(name, mod.main, result)
        except Exception as e:
            result.modules_tested += 1
            result.modules_failed += 1
            result.failures.append(f"{name}: import error: {e}")

    # Phase 3 — Pipeline & Export
    pipeline_modules = [
        ("drum_generator", "engine.drum_generator"),
        ("midi_export", "engine.midi_export"),
        ("fxp_writer", "engine.fxp_writer"),
        ("mastering_chain", "engine.mastering_chain"),
    ]

    for name, mod_path in pipeline_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            _try_module(name, mod.main, result)
        except Exception as e:
            result.modules_tested += 1
            result.modules_failed += 1
            result.failures.append(f"{name}: import error: {e}")

    # Phase 4 — Intelligence
    intel_modules = [
        ("phi_analyzer", "engine.phi_analyzer"),
        ("evolution_engine", "engine.evolution_engine"),
        ("preset_mutator", "engine.preset_mutator"),
        ("sound_palette", "engine.sound_palette"),
    ]

    for name, mod_path in intel_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            _try_module(name, mod.main, result)
        except Exception as e:
            result.modules_tested += 1
            result.modules_failed += 1
            result.failures.append(f"{name}: import error: {e}")

    # Phase 5 — Polish
    polish_modules = [
        ("error_handling", "engine.error_handling"),
        ("plugin_scaffold", "engine.plugin_scaffold"),
        ("tutorials", "engine.tutorials"),
        ("realtime_monitor", "engine.realtime_monitor"),
    ]

    for name, mod_path in polish_modules:
        try:
            import importlib
            mod = importlib.import_module(mod_path)
            _try_module(name, mod.main, result)
        except Exception as e:
            result.modules_tested += 1
            result.modules_failed += 1
            result.failures.append(f"{name}: import error: {e}")

    result.elapsed_s = round(time.time() - t0, 3)
    return result


def export_integration_report(result: IntegrationResult,
                              output_dir: str = "output/analysis") -> str:
    """Write integration report as JSON."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    path = str(Path(output_dir) / "integration_report.json")

    data = {
        "modules_tested": result.modules_tested,
        "modules_passed": result.modules_passed,
        "modules_failed": result.modules_failed,
        "success": result.success,
        "elapsed_s": result.elapsed_s,
        "failures": result.failures,
        "outputs": result.outputs,
    }

    with open(path, "w") as f:
        json.dump(data, f, indent=2)
    return path


def main() -> None:
    result = run_full_integration()
    print(f"v4.0 Full Integration: {result.modules_passed}/{result.modules_tested} passed "
          f"in {result.elapsed_s}s")
    if result.failures:
        for f in result.failures:
            print(f"  FAIL: {f}")
    else:
        print("  All modules OK")
    export_integration_report(result)


if __name__ == "__main__":
    main()
