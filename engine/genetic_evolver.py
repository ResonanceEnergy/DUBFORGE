"""
DUBFORGE — Genetic Patch Evolver Engine  (Session 172)

Evolves synth parameter patches using genetic algorithms
with PHI-weighted fitness, crossover, and mutation.
"""

import math
import random
from dataclasses import dataclass, field
from typing import Any

PHI = 1.6180339887


@dataclass
class Gene:
    """A single parameter in a patch."""
    name: str
    value: float
    min_val: float = 0.0
    max_val: float = 1.0

    def clamp(self) -> 'Gene':
        self.value = max(self.min_val, min(self.max_val, self.value))
        return self


@dataclass
class Patch:
    """A synth patch (chromosome)."""
    genes: list[Gene] = field(default_factory=list)
    fitness: float = 0.0
    generation: int = 0
    uid: str = ""

    def to_dict(self) -> dict[str, float]:
        return {g.name: g.value for g in self.genes}

    def copy(self) -> 'Patch':
        return Patch(
            genes=[Gene(g.name, g.value, g.min_val, g.max_val) for g in self.genes],
            fitness=self.fitness,
            generation=self.generation,
        )


# Default gene templates for dubstep patches
GENE_TEMPLATES: list[dict[str, Any]] = [
    {"name": "frequency", "min": 20.0, "max": 2000.0, "default": 80.0},
    {"name": "drive", "min": 0.0, "max": 1.0, "default": 0.5},
    {"name": "cutoff", "min": 100.0, "max": 8000.0, "default": 1000.0},
    {"name": "resonance", "min": 0.0, "max": 1.0, "default": 0.3},
    {"name": "attack", "min": 0.001, "max": 0.5, "default": 0.01},
    {"name": "decay", "min": 0.01, "max": 2.0, "default": 0.3},
    {"name": "sustain", "min": 0.0, "max": 1.0, "default": 0.7},
    {"name": "release", "min": 0.01, "max": 2.0, "default": 0.2},
    {"name": "lfo_rate", "min": 0.1, "max": 20.0, "default": 4.0},
    {"name": "lfo_depth", "min": 0.0, "max": 1.0, "default": 0.5},
    {"name": "mix", "min": 0.0, "max": 1.0, "default": 0.8},
    {"name": "detune", "min": 0.0, "max": 50.0, "default": 5.0},
    {"name": "distortion", "min": 0.0, "max": 1.0, "default": 0.3},
    {"name": "reverb", "min": 0.0, "max": 1.0, "default": 0.2},
    {"name": "delay", "min": 0.0, "max": 1.0, "default": 0.15},
    {"name": "width", "min": 0.0, "max": 1.0, "default": 0.6},
]


def create_default_patch(seed: int | None = None) -> Patch:
    """Create a patch with default genes."""
    rng = random.Random(seed)
    genes = []
    for t in GENE_TEMPLATES:
        val = t["default"] + rng.gauss(0, 0.1) * (t["max"] - t["min"])
        g = Gene(t["name"], val, t["min"], t["max"]).clamp()
        genes.append(g)
    return Patch(genes=genes)


def random_patch(seed: int | None = None) -> Patch:
    """Create a fully random patch."""
    rng = random.Random(seed)
    genes = []
    for t in GENE_TEMPLATES:
        val = rng.uniform(t["min"], t["max"])
        genes.append(Gene(t["name"], val, t["min"], t["max"]))
    return Patch(genes=genes)


@dataclass
class EvolutionConfig:
    """Configuration for evolution process."""
    population_size: int = 16
    elite_count: int = 2
    mutation_rate: float = 0.15
    mutation_strength: float = 0.2
    crossover_rate: float = 0.7
    phi_weight: bool = True
    max_generations: int = 50


class PatchEvolver:
    """Genetic algorithm engine for evolving synth patches."""

    def __init__(self, config: EvolutionConfig | None = None,
                 seed: int = 42):
        self.config = config or EvolutionConfig()
        self.rng = random.Random(seed)
        self.population: list[Patch] = []
        self.generation = 0
        self.best_ever: Patch | None = None
        self.history: list[dict] = []

    def initialize(self, seed_patches: list[Patch] | None = None) -> None:
        """Initialize population."""
        self.population = []
        if seed_patches:
            for p in seed_patches[:self.config.population_size]:
                self.population.append(p.copy())

        while len(self.population) < self.config.population_size:
            self.population.append(random_patch(self.rng.randint(0, 99999)))

        self.generation = 0

    def evaluate(self, fitness_fn: Any = None) -> None:
        """Evaluate fitness of all patches."""
        for patch in self.population:
            if fitness_fn:
                patch.fitness = fitness_fn(patch)
            else:
                patch.fitness = self._default_fitness(patch)

        self.population.sort(key=lambda p: p.fitness, reverse=True)

        if (self.best_ever is None or
                self.population[0].fitness > self.best_ever.fitness):
            self.best_ever = self.population[0].copy()

    def _default_fitness(self, patch: Patch) -> float:
        """Default fitness: penalize extremes, reward PHI ratios."""
        score = 0.0
        params = patch.to_dict()

        # Reward moderate values
        for gene in patch.genes:
            normalized = (gene.value - gene.min_val) / max(
                gene.max_val - gene.min_val, 1e-10)
            # Gaussian around 0.5 but PHI-shifted
            center = 1.0 / PHI  # ~0.618
            score += math.exp(-((normalized - center) ** 2) * 4)

        # Reward if attack < decay
        if "attack" in params and "decay" in params:
            if params["attack"] < params["decay"]:
                score += 1.0

        # Reward if frequency in dubstep range
        if "frequency" in params:
            freq = params["frequency"]
            if 40 <= freq <= 200:
                score += PHI

        # Reward moderate drive + distortion
        drive = params.get("drive", 0)
        dist = params.get("distortion", 0)
        if 0.2 < drive + dist < 1.2:
            score += 1.0

        return score

    def select_parents(self) -> tuple[Patch, Patch]:
        """Tournament selection with PHI sizing."""
        k = max(2, int(len(self.population) / PHI))
        t1 = self.rng.sample(self.population, min(k, len(self.population)))
        t2 = self.rng.sample(self.population, min(k, len(self.population)))
        p1 = max(t1, key=lambda p: p.fitness)
        p2 = max(t2, key=lambda p: p.fitness)
        return p1, p2

    def crossover(self, p1: Patch, p2: Patch) -> Patch:
        """PHI-point crossover."""
        if self.rng.random() > self.config.crossover_rate:
            return p1.copy()

        child = Patch()
        n = len(p1.genes)
        # PHI crossover point
        cross_pt = int(n / PHI)

        for i in range(n):
            g1 = p1.genes[i]
            g2 = p2.genes[i] if i < len(p2.genes) else g1

            if i < cross_pt:
                val = g1.value
            else:
                # Blend with PHI ratio
                alpha = 1.0 / PHI
                val = alpha * g1.value + (1.0 - alpha) * g2.value

            child.genes.append(Gene(g1.name, val, g1.min_val, g1.max_val).clamp())

        return child

    def mutate(self, patch: Patch) -> Patch:
        """Mutate genes with PHI-scaled perturbation."""
        for gene in patch.genes:
            if self.rng.random() < self.config.mutation_rate:
                range_size = gene.max_val - gene.min_val
                perturbation = self.rng.gauss(0, 1) * self.config.mutation_strength * range_size
                if self.config.phi_weight:
                    perturbation *= (1.0 / PHI)
                gene.value += perturbation
                gene.clamp()
        return patch

    def evolve_step(self, fitness_fn: Any = None) -> dict:
        """Run one generation of evolution."""
        self.evaluate(fitness_fn)

        # Record history
        stats = {
            "generation": self.generation,
            "best_fitness": self.population[0].fitness,
            "avg_fitness": sum(p.fitness for p in self.population) / len(self.population),
            "worst_fitness": self.population[-1].fitness,
        }
        self.history.append(stats)

        # Elite preservation
        new_pop: list[Patch] = []
        for i in range(min(self.config.elite_count, len(self.population))):
            elite = self.population[i].copy()
            elite.generation = self.generation + 1
            new_pop.append(elite)

        # Breed new population
        while len(new_pop) < self.config.population_size:
            p1, p2 = self.select_parents()
            child = self.crossover(p1, p2)
            child = self.mutate(child)
            child.generation = self.generation + 1
            new_pop.append(child)

        self.population = new_pop
        self.generation += 1
        return stats

    def evolve(self, n_generations: int | None = None,
               fitness_fn: Any = None) -> Patch:
        """Run full evolution."""
        gens = n_generations or self.config.max_generations

        for _ in range(gens):
            self.evolve_step(fitness_fn)

        self.evaluate(fitness_fn)
        return self.population[0]

    def get_summary(self) -> dict:
        """Get evolution summary."""
        return {
            "generation": self.generation,
            "population_size": len(self.population),
            "best_patch": self.best_ever.to_dict() if self.best_ever else {},
            "best_fitness": self.best_ever.fitness if self.best_ever else 0.0,
            "history_length": len(self.history),
        }


def main() -> None:
    print("Genetic Patch Evolver Engine")

    evolver = PatchEvolver(seed=42)
    evolver.initialize()
    print(f"  Population: {len(evolver.population)} patches")

    best = evolver.evolve(20)
    print(f"  Evolved {evolver.generation} generations")
    print(f"  Best fitness: {best.fitness:.3f}")
    print("  Best patch:")
    for name, val in best.to_dict().items():
        print(f"    {name}: {val:.3f}")

    summary = evolver.get_summary()
    print(f"  Summary: {summary['history_length']} history entries")
    print("Done.")


if __name__ == "__main__":
    main()
