"""Tests for engine.genetic_evolver — Session 172."""
import pytest
from engine.genetic_evolver import (
    PatchEvolver, Patch, Gene, EvolutionConfig,
    create_default_patch, random_patch,
)


class TestGeneticEvolver:
    def test_create_default(self):
        p = create_default_patch()
        assert isinstance(p, Patch)
        assert len(p.genes) > 0

    def test_random_patch(self):
        p = random_patch()
        assert isinstance(p, Patch)

    def test_evolver(self):
        config = EvolutionConfig(population_size=10, max_generations=3)
        evolver = PatchEvolver(config)
        evolver.initialize()

        def fitness(patch):
            return sum(g.value for g in patch.genes) / len(patch.genes)

        evolver.evaluate(fitness)
        best = evolver.evolve(2, fitness)
        assert isinstance(best, Patch)

    def test_crossover(self):
        config = EvolutionConfig()
        evolver = PatchEvolver(config)
        a = create_default_patch(seed=1)
        b = create_default_patch(seed=2)
        child = evolver.crossover(a, b)
        assert isinstance(child, Patch)

    def test_mutate(self):
        config = EvolutionConfig(mutation_rate=1.0)
        evolver = PatchEvolver(config)
        p = create_default_patch()
        m = evolver.mutate(p)
        assert isinstance(m, Patch)
