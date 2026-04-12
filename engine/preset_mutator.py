"""
DUBFORGE — Preset Mutator  (Session 125)

Take a patch config, apply phi-weighted random mutations,
breed new patches via genetic algorithm.

5 mutation types × 4 presets = 20 presets.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

import numpy as np

from engine.config_loader import PHI
from engine.turboquant import SpectralVectorIndex, TurboQuantConfig

PHI_INV = 1.0 / PHI


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class PatchGene:
    """A single mutable parameter in a patch."""
    name: str
    value: float
    min_val: float = 0.0
    max_val: float = 1.0


@dataclass
class Patch:
    """A collection of genes representing a sound patch."""
    name: str
    genes: list[PatchGene] = field(default_factory=list)
    fitness: float = 0.0

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "fitness": round(self.fitness, 4),
            "genes": {g.name: round(g.value, 4) for g in self.genes},
        }

    def copy(self, new_name: str = "") -> "Patch":
        return Patch(
            name=new_name or self.name,
            genes=[PatchGene(g.name, g.value, g.min_val, g.max_val) for g in self.genes],
            fitness=self.fitness,
        )

    def to_vector(self) -> list[float]:
        """Extract gene values as a float vector for TQ indexing."""
        return [g.value for g in self.genes]


@dataclass
class MutatorPreset:
    name: str
    mutation_type: str  # gaussian | phi_scaled | uniform | swap | crossover
    mutation_rate: float = 0.2
    mutation_strength: float = 0.1
    population_size: int = 8
    generations: int = 10
    elitism_ratio: float = 0.25
    crossover_rate: float = 0.5


@dataclass
class MutatorBank:
    name: str
    presets: list[MutatorPreset] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════
# DEFAULT PATCH TEMPLATE
# ═══════════════════════════════════════════════════════════════════════════

def create_default_patch(name: str = "init") -> Patch:
    """Create a default synthesis patch with standard gene parameters."""
    genes = [
        PatchGene("osc1_level", 0.8, 0.0, 1.0),
        PatchGene("osc2_level", 0.5, 0.0, 1.0),
        PatchGene("osc2_detune", 0.1, 0.0, 1.0),
        PatchGene("filter_cutoff", 0.7, 0.0, 1.0),
        PatchGene("filter_resonance", 0.3, 0.0, 1.0),
        PatchGene("env_attack", 0.01, 0.0, 1.0),
        PatchGene("env_decay", 0.3, 0.0, 1.0),
        PatchGene("env_sustain", 0.6, 0.0, 1.0),
        PatchGene("env_release", 0.4, 0.0, 1.0),
        PatchGene("lfo_rate", 0.2, 0.0, 1.0),
        PatchGene("lfo_depth", 0.3, 0.0, 1.0),
        PatchGene("distortion", 0.0, 0.0, 1.0),
        PatchGene("reverb_mix", 0.2, 0.0, 1.0),
        PatchGene("delay_mix", 0.1, 0.0, 1.0),
        PatchGene("stereo_width", 0.5, 0.0, 1.0),
    ]
    return Patch(name=name, genes=genes)


# ═══════════════════════════════════════════════════════════════════════════
# MUTATION FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════

def _fitness_function(patch: Patch) -> float:
    """Evaluate patch fitness. Rewards phi-ratio relationships between params."""
    vals = [g.value for g in patch.genes]
    if len(vals) < 2:
        return 0.0

    # Base: signal-like score from parameter variety
    variety = float(np.std(vals))

    # Phi bonus: count parameter pairs near phi ratio
    phi_hits = 0
    pairs = 0
    for i in range(len(vals)):
        for j in range(i + 1, len(vals)):
            if vals[j] > 0.01 and vals[i] > 0.01:
                ratio = max(vals[i], vals[j]) / min(vals[i], vals[j])
                if abs(ratio - PHI) / PHI < 0.1:
                    phi_hits += 1
                pairs += 1

    phi_bonus = phi_hits / max(pairs, 1)
    return min(variety * 2 + phi_bonus * 0.5, 1.0)


def mutate_gaussian(patch: Patch, preset: MutatorPreset) -> Patch:
    """Gaussian mutation — add noise scaled by mutation_strength."""
    child = patch.copy(f"{patch.name}_gauss")
    for gene in child.genes:
        if np.random.random() < preset.mutation_rate:
            noise = np.random.normal(0, preset.mutation_strength)
            gene.value = float(np.clip(gene.value + noise, gene.min_val, gene.max_val))
    child.fitness = _fitness_function(child)
    return child


def mutate_phi_scaled(patch: Patch, preset: MutatorPreset) -> Patch:
    """Phi-scaled mutation — mutations scale by 1/phi for each successive gene."""
    child = patch.copy(f"{patch.name}_phi")
    for i, gene in enumerate(child.genes):
        if np.random.random() < preset.mutation_rate:
            scale = PHI_INV ** i
            noise = np.random.normal(0, preset.mutation_strength * scale)
            gene.value = float(np.clip(gene.value + noise, gene.min_val, gene.max_val))
    child.fitness = _fitness_function(child)
    return child


def mutate_uniform(patch: Patch, preset: MutatorPreset) -> Patch:
    """Uniform mutation — random value within range."""
    child = patch.copy(f"{patch.name}_uni")
    for gene in child.genes:
        if np.random.random() < preset.mutation_rate:
            gene.value = float(np.random.uniform(gene.min_val, gene.max_val))
    child.fitness = _fitness_function(child)
    return child


def mutate_swap(patch: Patch, preset: MutatorPreset) -> Patch:
    """Swap mutation — exchange values between random gene pairs."""
    child = patch.copy(f"{patch.name}_swap")
    genes = child.genes
    for _ in range(max(1, int(len(genes) * preset.mutation_rate))):
        i, j = np.random.choice(len(genes), 2, replace=False)
        genes[i].value, genes[j].value = genes[j].value, genes[i].value
    child.fitness = _fitness_function(child)
    return child


def mutate_crossover(parent_a: Patch, parent_b: Patch, preset: MutatorPreset) -> Patch:
    """Crossover mutation — blend two parents at a random split point."""
    child = parent_a.copy(f"{parent_a.name}_x_{parent_b.name}")
    split = np.random.randint(1, len(child.genes))
    for i in range(split, len(child.genes)):
        if i < len(parent_b.genes):
            alpha = preset.crossover_rate
            child.genes[i].value = float(
                alpha * parent_b.genes[i].value + (1 - alpha) * parent_a.genes[i].value
            )
            child.genes[i].value = float(np.clip(child.genes[i].value,
                                                  child.genes[i].min_val,
                                                  child.genes[i].max_val))
    child.fitness = _fitness_function(child)
    return child


MUTATOR_FUNCTIONS: dict[str, Callable[..., Any]] = {
    "gaussian": mutate_gaussian,
    "phi_scaled": mutate_phi_scaled,
    "uniform": mutate_uniform,
    "swap": mutate_swap,
    "crossover": mutate_crossover,
}


# ═══════════════════════════════════════════════════════════════════════════
# GENETIC ALGORITHM
# ═══════════════════════════════════════════════════════════════════════════

def evolve_population(seed_patch: Patch, preset: MutatorPreset) -> list[Patch]:
    """Run a genetic algorithm and return final population sorted by fitness."""
    mutate_fn = MUTATOR_FUNCTIONS.get(preset.mutation_type)
    if mutate_fn is None:
        raise ValueError(f"Unknown mutation type: {preset.mutation_type}")

    # Initialize population from seed
    population: list[Patch] = []
    for i in range(preset.population_size):
        p = seed_patch.copy(f"gen0_{i}")
        if i > 0:  # mutate all except first (keep original)
            if preset.mutation_type == "crossover":
                p = mutate_crossover(seed_patch, p, preset)
            else:
                p = mutate_fn(p, preset)
        else:
            p.fitness = _fitness_function(p)
        population.append(p)

    for gen in range(preset.generations):
        # Sort by fitness
        population.sort(key=lambda x: x.fitness, reverse=True)

        # Elite selection
        n_elite = max(1, int(preset.population_size * preset.elitism_ratio))
        next_gen = [p.copy(f"gen{gen + 1}_e{i}") for i, p in enumerate(population[:n_elite])]

        # Breed rest
        while len(next_gen) < preset.population_size:
            parent = population[np.random.randint(n_elite)]
            if preset.mutation_type == "crossover":
                other = population[np.random.randint(len(population))]
                child = mutate_crossover(parent, other, preset)
            else:
                child = mutate_fn(parent, preset)
            child.name = f"gen{gen + 1}_{len(next_gen)}"
            next_gen.append(child)

        population = next_gen

    population.sort(key=lambda x: x.fitness, reverse=True)
    return population


# ═══════════════════════════════════════════════════════════════════════════
# BANKS
# ═══════════════════════════════════════════════════════════════════════════

def gaussian_bank() -> MutatorBank:
    return MutatorBank("gaussian", [
        MutatorPreset("gauss_gentle", "gaussian", mutation_rate=0.1, mutation_strength=0.05),
        MutatorPreset("gauss_moderate", "gaussian", mutation_rate=0.3, mutation_strength=0.1),
        MutatorPreset("gauss_aggressive", "gaussian", mutation_rate=0.5, mutation_strength=0.2),
        MutatorPreset("gauss_phi", "gaussian", mutation_rate=0.2, mutation_strength=0.1),
    ])


def phi_scaled_bank() -> MutatorBank:
    return MutatorBank("phi_scaled", [
        MutatorPreset("phi_gentle", "phi_scaled", mutation_rate=0.2, mutation_strength=0.05),
        MutatorPreset("phi_moderate", "phi_scaled", mutation_rate=0.3, mutation_strength=0.1),
        MutatorPreset("phi_deep", "phi_scaled", mutation_rate=0.5, mutation_strength=0.15),
        MutatorPreset("phi_max", "phi_scaled", mutation_rate=0.6, mutation_strength=0.2),
    ])


def uniform_bank() -> MutatorBank:
    return MutatorBank("uniform", [
        MutatorPreset("uni_sparse", "uniform", mutation_rate=0.1),
        MutatorPreset("uni_moderate", "uniform", mutation_rate=0.3),
        MutatorPreset("uni_dense", "uniform", mutation_rate=0.5),
        MutatorPreset("uni_random", "uniform", mutation_rate=0.8),
    ])


def swap_bank() -> MutatorBank:
    return MutatorBank("swap", [
        MutatorPreset("swap_single", "swap", mutation_rate=0.1),
        MutatorPreset("swap_double", "swap", mutation_rate=0.2),
        MutatorPreset("swap_heavy", "swap", mutation_rate=0.4),
        MutatorPreset("swap_max", "swap", mutation_rate=0.6),
    ])


def crossover_bank() -> MutatorBank:
    return MutatorBank("crossover", [
        MutatorPreset("cross_balanced", "crossover", crossover_rate=0.5),
        MutatorPreset("cross_parent_a", "crossover", crossover_rate=0.3),
        MutatorPreset("cross_parent_b", "crossover", crossover_rate=0.7),
        MutatorPreset("cross_phi", "crossover", crossover_rate=PHI_INV),
    ])


ALL_MUTATOR_BANKS: dict[str, Callable[..., Any]] = {
    "gaussian": gaussian_bank,
    "phi_scaled": phi_scaled_bank,
    "uniform": uniform_bank,
    "swap": swap_bank,
    "crossover": crossover_bank,
}


# ═══════════════════════════════════════════════════════════════════════════
# EXPORT + MANIFEST
# ═══════════════════════════════════════════════════════════════════════════

def export_mutated_patches(output_dir: str = "output") -> list[str]:
    """Evolve patches and export best results as JSON."""
    out = Path(output_dir) / "presets"
    out.mkdir(parents=True, exist_ok=True)
    paths: list[str] = []

    seed = create_default_patch("seed")
    for bank_name, gen_fn in ALL_MUTATOR_BANKS.items():
        bank = gen_fn()
        for preset in bank.presets:
            population = evolve_population(seed, preset)
            best = population[0]
            fpath = out / f"mutated_{preset.name}.json"
            with open(fpath, "w") as f:
                json.dump(best.to_dict(), f, indent=2)
            paths.append(str(fpath))

    return paths


def write_mutator_manifest(output_dir: str = "output") -> dict:
    out = Path(output_dir) / "presets"
    out.mkdir(parents=True, exist_ok=True)

    manifest: dict = {"module": "preset_mutator", "banks": {}}
    for name, gen_fn in ALL_MUTATOR_BANKS.items():
        bank = gen_fn()
        manifest["banks"][name] = {
            "name": bank.name,
            "preset_count": len(bank.presets),
            "presets": [p.name for p in bank.presets],
        }

    path = out / "mutator_manifest.json"
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2)
    return manifest


def main() -> None:
    manifest = write_mutator_manifest()
    total = sum(b["preset_count"] for b in manifest["banks"].values())
    patches = export_mutated_patches()
    print(f"Preset Mutator: {len(manifest['banks'])} banks, {total} presets, "
          f"{len(patches)} mutated patches")


if __name__ == "__main__":
    main()
