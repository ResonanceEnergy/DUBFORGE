"""
DUBFORGE — Evolution Engine  (Session 124)

Track parameter changes across sessions. Identify which phi-tunings
produce highest-rated output. Maintains an evolution log with scoring.

5 tracker types × 4 presets = 20 presets.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from engine.phi_core import SAMPLE_RATE

PHI = 1.6180339887


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class EvolutionEntry:
    """A single generation in the evolution log."""
    generation: int
    params: dict = field(default_factory=dict)
    score: float = 0.0
    notes: str = ""


@dataclass
class EvolutionLog:
    """Full evolution history."""
    name: str
    entries: list[EvolutionEntry] = field(default_factory=list)

    def best_entry(self) -> EvolutionEntry | None:
        if not self.entries:
            return None
        return max(self.entries, key=lambda e: e.score)

    def trend(self) -> list[float]:
        return [e.score for e in self.entries]


@dataclass
class EvolutionPreset:
    name: str
    tracker_type: str  # param_drift | phi_convergence | score_climb
                       # | diversity | stability
    generations: int = 10
    mutation_rate: float = 0.1
    phi_weight: float = 0.618
    elitism: float = 0.2
    population_size: int = 8


@dataclass
class EvolutionBank:
    name: str
    presets: list[EvolutionPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# TRACKER FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _score_signal(signal: np.ndarray) -> float:
    """Simple quality score: RMS × spectral flatness proxy."""
    rms = float(np.sqrt(np.mean(signal ** 2)))
    spectrum = np.abs(np.fft.rfft(signal[:min(len(signal), 4096)]))
    geo_mean = np.exp(np.mean(np.log(spectrum + 1e-12)))
    arith_mean = np.mean(spectrum) + 1e-12
    flatness = geo_mean / arith_mean
    return min(rms * flatness * 5.0, 1.0)


def _generate_test_signal(freq: float = 432.0, dur: float = 0.5,
                          harmonics: int = 5) -> np.ndarray:
    t = np.linspace(0, dur, int(SAMPLE_RATE * dur), endpoint=False)
    sig = np.zeros_like(t)
    for h in range(1, harmonics + 1):
        sig += np.sin(2 * np.pi * freq * h * t) / (h ** PHI)
    return sig / (np.max(np.abs(sig)) + 1e-12)


def track_param_drift(preset: EvolutionPreset) -> EvolutionLog:
    """Track how parameters drift over generations."""
    log = EvolutionLog(name=f"drift_{preset.name}")
    freq = 432.0
    harmonics = 5

    for gen in range(preset.generations):
        sig = _generate_test_signal(freq, 0.3, harmonics)
        score = _score_signal(sig)
        log.entries.append(EvolutionEntry(
            generation=gen,
            params={"freq": round(float(freq), 2), "harmonics": harmonics},
            score=round(score, 4),
        ))
        # Drift parameters by phi-weighted mutation
        freq *= (1 + preset.mutation_rate * (np.random.random() - 0.5) * PHI)
        freq = np.clip(freq, 50, 2000)
        harmonics = int(max(2, min(16, harmonics + np.random.choice([-1, 0, 1]))))

    return log


def track_phi_convergence(preset: EvolutionPreset) -> EvolutionLog:
    """Track convergence towards phi-ratio harmonics."""
    log = EvolutionLog(name=f"phi_conv_{preset.name}")
    ratio = 1.0  # start away from phi

    for gen in range(preset.generations):
        t = np.linspace(0, 0.3, int(SAMPLE_RATE * 0.3), endpoint=False)
        sig = np.sin(2 * np.pi * 432 * t) + 0.5 * np.sin(2 * np.pi * 432 * ratio * t)
        sig /= np.max(np.abs(sig)) + 1e-12
        score = _score_signal(sig)
        # Bonus for being close to phi
        phi_bonus = max(0, 1 - abs(ratio - PHI) / PHI)
        final_score = score * 0.5 + phi_bonus * 0.5

        log.entries.append(EvolutionEntry(
            generation=gen,
            params={"ratio": round(ratio, 4)},
            score=round(final_score, 4),
        ))
        # Move ratio towards phi
        ratio += (PHI - ratio) * preset.phi_weight * 0.2
        ratio += preset.mutation_rate * (np.random.random() - 0.5)
        ratio = max(0.5, min(3.0, ratio))

    return log


def track_score_climb(preset: EvolutionPreset) -> EvolutionLog:
    """Hill-climbing: keep best params, mutate, keep if better."""
    log = EvolutionLog(name=f"climb_{preset.name}")
    best_freq = 432.0
    best_harmonics = 5
    best_score = 0.0

    for gen in range(preset.generations):
        # Mutate from best
        freq = best_freq * (1 + preset.mutation_rate * (np.random.random() - 0.5))
        freq = np.clip(freq, 50, 2000)
        harmonics = int(max(2, min(16, best_harmonics + np.random.choice([-1, 0, 1]))))

        sig = _generate_test_signal(freq, 0.3, harmonics)
        score = _score_signal(sig)

        if score > best_score:
            best_freq, best_harmonics, best_score = freq, harmonics, score

        log.entries.append(EvolutionEntry(
            generation=gen,
            params={"freq": round(float(best_freq), 2), "harmonics": int(best_harmonics)},
            score=round(best_score, 4),
        ))

    return log


def track_diversity(preset: EvolutionPreset) -> EvolutionLog:
    """Track population diversity across generations."""
    log = EvolutionLog(name=f"diversity_{preset.name}")
    population = [432.0 + i * 50 for i in range(preset.population_size)]

    for gen in range(preset.generations):
        scores = []
        for freq in population:
            sig = _generate_test_signal(freq, 0.2, 4)
            scores.append(_score_signal(sig))

        mean_score = float(np.mean(scores))
        diversity = float(np.std(population) / (np.mean(population) + 1e-12))

        log.entries.append(EvolutionEntry(
            generation=gen,
            params={"pop_size": len(population), "diversity": round(diversity, 4)},
            score=round(mean_score, 4),
        ))

        # Breed: keep top performers, mutate
        sorted_pop = [p for _, p in sorted(zip(scores, population), reverse=True)]
        elite = sorted_pop[:max(1, int(len(sorted_pop) * preset.elitism))]
        new_pop = list(elite)
        while len(new_pop) < preset.population_size:
            parent = elite[np.random.randint(len(elite))]
            child = parent * (1 + preset.mutation_rate * (np.random.random() - 0.5) * PHI)
            new_pop.append(np.clip(child, 50, 4000))
        population = new_pop

    return log


def track_stability(preset: EvolutionPreset) -> EvolutionLog:
    """Track how stable the score remains across generations."""
    log = EvolutionLog(name=f"stability_{preset.name}")
    freq = 432.0
    prev_score = 0.0

    for gen in range(preset.generations):
        sig = _generate_test_signal(freq, 0.3, 5)
        score = _score_signal(sig)
        stability = 1.0 - abs(score - prev_score)

        log.entries.append(EvolutionEntry(
            generation=gen,
            params={"freq": round(freq, 2), "stability": round(stability, 4)},
            score=round(score, 4),
        ))

        prev_score = score
        # Small perturbation
        freq *= (1 + 0.02 * (np.random.random() - 0.5))

    return log


# Router
TRACKER_FUNCTIONS: dict[str, callable] = {
    "param_drift": track_param_drift,
    "phi_convergence": track_phi_convergence,
    "score_climb": track_score_climb,
    "diversity": track_diversity,
    "stability": track_stability,
}


def run_evolution(preset: EvolutionPreset) -> EvolutionLog:
    fn = TRACKER_FUNCTIONS.get(preset.tracker_type)
    if fn is None:
        raise ValueError(f"Unknown tracker: {preset.tracker_type}")
    return fn(preset)


# ═══════════════════════════════════════════════════════════════════════════
# BANKS  (5 × 4 = 20)
# ═══════════════════════════════════════════════════════════════════════════

def param_drift_bank() -> EvolutionBank:
    return EvolutionBank("param_drift", [
        EvolutionPreset("drift_slow", "param_drift", generations=8, mutation_rate=0.05),
        EvolutionPreset("drift_fast", "param_drift", generations=12, mutation_rate=0.2),
        EvolutionPreset("drift_phi", "param_drift", generations=10, mutation_rate=0.1, phi_weight=0.8),
        EvolutionPreset("drift_wild", "param_drift", generations=15, mutation_rate=0.4),
    ])


def phi_convergence_bank() -> EvolutionBank:
    return EvolutionBank("phi_convergence", [
        EvolutionPreset("conv_slow", "phi_convergence", generations=10, phi_weight=0.3),
        EvolutionPreset("conv_fast", "phi_convergence", generations=8, phi_weight=0.8),
        EvolutionPreset("conv_exact", "phi_convergence", generations=15, phi_weight=0.618, mutation_rate=0.02),
        EvolutionPreset("conv_noisy", "phi_convergence", generations=12, phi_weight=0.5, mutation_rate=0.3),
    ])


def score_climb_bank() -> EvolutionBank:
    return EvolutionBank("score_climb", [
        EvolutionPreset("climb_gentle", "score_climb", generations=10, mutation_rate=0.05),
        EvolutionPreset("climb_steep", "score_climb", generations=8, mutation_rate=0.3),
        EvolutionPreset("climb_long", "score_climb", generations=20, mutation_rate=0.1),
        EvolutionPreset("climb_phi", "score_climb", generations=12, mutation_rate=0.1, phi_weight=0.618),
    ])


def diversity_bank() -> EvolutionBank:
    return EvolutionBank("diversity", [
        EvolutionPreset("div_small", "diversity", population_size=4, generations=8),
        EvolutionPreset("div_large", "diversity", population_size=12, generations=10),
        EvolutionPreset("div_elite", "diversity", population_size=8, elitism=0.5),
        EvolutionPreset("div_open", "diversity", population_size=8, elitism=0.1, mutation_rate=0.3),
    ])


def stability_bank() -> EvolutionBank:
    return EvolutionBank("stability", [
        EvolutionPreset("stable_base", "stability", generations=10),
        EvolutionPreset("stable_long", "stability", generations=20),
        EvolutionPreset("stable_tight", "stability", generations=10, mutation_rate=0.02),
        EvolutionPreset("stable_loose", "stability", generations=10, mutation_rate=0.2),
    ])


ALL_EVOLUTION_BANKS: dict[str, callable] = {
    "param_drift": param_drift_bank,
    "phi_convergence": phi_convergence_bank,
    "score_climb": score_climb_bank,
    "diversity": diversity_bank,
    "stability": stability_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def export_evolution_logs(output_dir: str = "output") -> list[str]:
    """Run all evolution trackers and export logs as JSON."""
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    for bank_name, gen_fn in ALL_EVOLUTION_BANKS.items():
        bank = gen_fn()
        for preset in bank.presets:
            log = run_evolution(preset)
            data = {
                "name": log.name,
                "entries": [
                    {"generation": e.generation, "params": e.params,
                     "score": e.score, "notes": e.notes}
                    for e in log.entries
                ],
                "best_score": log.best_entry().score if log.best_entry() else 0,
                "trend": log.trend(),
            }
            fpath = out / f"evolution_{log.name}.json"
            with open(fpath, "w") as f:
                json.dump(data, f, indent=2)
            paths.append(str(fpath))

    return paths


def write_evolution_manifest(output_dir: str = "output") -> dict:
    out = Path(output_dir) / "analysis"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"module": "evolution_engine", "banks": {}}
    for name, gen_fn in ALL_EVOLUTION_BANKS.items():
        bank = gen_fn()
        manifest["banks"][name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "evolution_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_evolution_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    logs = export_evolution_logs()
    print(f"Evolution Engine: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(logs)} evolution logs")


if __name__ == "__main__":
    main()
