"""Tests for engine.preset_mutator — Preset Mutator (Phase 4)."""

import json
from pathlib import Path

import pytest

from engine.preset_mutator import (
    ALL_MUTATOR_BANKS,
    MutatorPreset,
    Patch,
    PatchGene,
    create_default_patch,
    evolve_population,
    export_mutated_patches,
    mutate_crossover,
    mutate_gaussian,
    mutate_phi_scaled,
    mutate_swap,
    mutate_uniform,
    write_mutator_manifest,
)

# ── dataclass tests ──────────────────────────────────────────────────────

def test_patch_gene_defaults():
    g = PatchGene(name="vol", value=0.5)
    assert g.min_val == 0.0
    assert g.max_val == 1.0


def test_patch_to_dict():
    p = Patch(name="test", genes=[PatchGene("a", 0.5), PatchGene("b", 0.3)],
              fitness=0.7)
    d = p.to_dict()
    assert d["name"] == "test"
    assert "a" in d["genes"]
    assert d["fitness"] == 0.7


def test_patch_copy():
    p = create_default_patch("orig")
    c = p.copy("clone")
    assert c.name == "clone"
    assert len(c.genes) == len(p.genes)
    # Verify deep copy — mutating clone doesn't affect original
    c.genes[0].value = 999.0
    assert p.genes[0].value != 999.0


def test_patch_copy_default_name():
    p = create_default_patch("orig")
    c = p.copy()
    assert c.name == "orig"


def test_default_patch_has_genes():
    p = create_default_patch()
    assert len(p.genes) == 15


def test_default_patch_gene_names():
    p = create_default_patch()
    names = {g.name for g in p.genes}
    assert "osc1_level" in names
    assert "filter_cutoff" in names
    assert "reverb_mix" in names


def test_preset_defaults():
    p = MutatorPreset(name="t", mutation_type="gaussian")
    assert p.mutation_rate == 0.2
    assert p.population_size == 8
    assert p.generations == 10


# ── mutation function tests ─────────────────────────────────────────────

def test_mutate_gaussian_returns_patch():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="gaussian",
                           mutation_rate=1.0, mutation_strength=0.1)
    child = mutate_gaussian(seed, preset)
    assert isinstance(child, Patch)
    assert child.fitness >= 0.0


def test_mutate_phi_scaled_returns_patch():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="phi_scaled",
                           mutation_rate=1.0, mutation_strength=0.1)
    child = mutate_phi_scaled(seed, preset)
    assert isinstance(child, Patch)


def test_mutate_uniform_returns_patch():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="uniform", mutation_rate=1.0)
    child = mutate_uniform(seed, preset)
    assert isinstance(child, Patch)
    for g in child.genes:
        assert g.min_val <= g.value <= g.max_val


def test_mutate_swap_returns_patch():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="swap", mutation_rate=0.5)
    child = mutate_swap(seed, preset)
    assert isinstance(child, Patch)


def test_mutate_crossover_returns_patch():
    a = create_default_patch("a")
    b = create_default_patch("b")
    preset = MutatorPreset(name="t", mutation_type="crossover", crossover_rate=0.5)
    child = mutate_crossover(a, b, preset)
    assert isinstance(child, Patch)
    assert len(child.genes) == len(a.genes)


# ── genetic algorithm ───────────────────────────────────────────────────

def test_evolve_population_returns_sorted():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="gaussian",
                           population_size=6, generations=3)
    pop = evolve_population(seed, preset)
    assert len(pop) == 6
    # Should be sorted by fitness descending
    for i in range(len(pop) - 1):
        assert pop[i].fitness >= pop[i + 1].fitness


def test_evolve_population_crossover():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="crossover",
                           population_size=4, generations=2)
    pop = evolve_population(seed, preset)
    assert len(pop) == 4


def test_evolve_population_unknown_type():
    seed = create_default_patch("seed")
    preset = MutatorPreset(name="t", mutation_type="nonexistent")
    with pytest.raises(ValueError):
        evolve_population(seed, preset)


# ── banks ────────────────────────────────────────────────────────────────

def test_all_banks_registered():
    assert len(ALL_MUTATOR_BANKS) == 5


def test_total_presets_is_20():
    total = sum(len(fn().presets) for fn in ALL_MUTATOR_BANKS.values())
    assert total == 20


# ── manifest + export ───────────────────────────────────────────────────

def test_write_manifest(tmp_path):
    manifest = write_mutator_manifest(str(tmp_path))
    assert "banks" in manifest
    assert len(manifest["banks"]) == 5
    json_path = tmp_path / "presets" / "mutator_manifest.json"
    assert json_path.exists()


def test_export_mutated_patches_creates_files(tmp_path):
    paths = export_mutated_patches(str(tmp_path))
    assert isinstance(paths, list)
    assert len(paths) == 20
    for p in paths:
        assert Path(p).exists()
        with open(p) as f:
            data = json.load(f)
        assert "name" in data
        assert "genes" in data


def test_each_bank_has_4_presets():
    for name, gen_fn in ALL_MUTATOR_BANKS.items():
        bank = gen_fn()
        assert len(bank.presets) == 4, f"Bank {name} has {len(bank.presets)} presets"
