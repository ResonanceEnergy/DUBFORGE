"""Tests for engine.template_generator — Template Generator (Phase 4)."""

import json
from pathlib import Path

from engine.template_generator import (
    ALL_TEMPLATE_BANKS,
    TemplateBank,
    TemplateConfig,
    TemplatePreset,
    export_templates,
    generate_template,
    write_template_manifest,
)

# ── dataclass tests ──────────────────────────────────────────────────────

def test_template_config_defaults():
    c = TemplateConfig(name="t", genre="dubstep", energy=0.5)
    assert c.bpm == 150
    assert c.key == "F"
    assert c.scale == "minor"


def test_template_config_to_dict():
    c = TemplateConfig(name="t", genre="dubstep", energy=0.7)
    d = c.to_dict()
    assert isinstance(d, dict)
    assert d["name"] == "t"
    assert d["genre"] == "dubstep"
    assert "sections" in d
    assert "fx_chain" in d


def test_template_config_sections_default():
    c = TemplateConfig(name="t", genre="dubstep", energy=0.5)
    assert len(c.sections) >= 3
    assert "intro" in c.sections


def test_template_config_fx_chain_default():
    c = TemplateConfig(name="t", genre="dubstep", energy=0.5)
    assert len(c.fx_chain) >= 1


def test_template_preset_defaults():
    p = TemplatePreset(name="t", generator_type="dubstep")
    assert p.energy_profile == "standard"
    assert p.complexity == 0.5


def test_template_bank_dataclass():
    b = TemplateBank(name="test_bank", presets=[
        TemplatePreset(name="a", generator_type="dubstep"),
    ])
    assert len(b.presets) == 1
    assert b.name == "test_bank"


# ── generate_template per genre ─────────────────────────────────────────

def test_generate_dubstep():
    p = TemplatePreset(name="t", generator_type="dubstep", bpm_range=(145, 155))
    cfg = generate_template(p)
    assert isinstance(cfg, TemplateConfig)
    assert cfg.genre == "dubstep"
    assert 145 <= cfg.bpm <= 155


def test_generate_riddim():
    p = TemplatePreset(name="t", generator_type="riddim", bpm_range=(140, 150))
    cfg = generate_template(p)
    assert cfg.genre == "riddim"
    assert 140 <= cfg.bpm <= 150


def test_generate_melodic():
    p = TemplatePreset(name="t", generator_type="melodic", bpm_range=(130, 145))
    cfg = generate_template(p)
    assert cfg.genre == "melodic"
    assert 130 <= cfg.bpm <= 145


def test_generate_hybrid():
    p = TemplatePreset(name="t", generator_type="hybrid", bpm_range=(145, 155))
    cfg = generate_template(p)
    assert cfg.genre == "hybrid"


def test_generate_ambient():
    p = TemplatePreset(name="t", generator_type="ambient", bpm_range=(60, 90))
    cfg = generate_template(p)
    assert cfg.genre == "ambient"
    assert 60 <= cfg.bpm <= 90


def test_generate_template_sections_populated():
    p = TemplatePreset(name="t", generator_type="dubstep")
    cfg = generate_template(p)
    assert len(cfg.sections) >= 3


def test_generate_template_fx_chain_populated():
    p = TemplatePreset(name="t", generator_type="dubstep")
    cfg = generate_template(p)
    assert len(cfg.fx_chain) >= 1


def test_generate_template_high_complexity_adds_fx():
    p = TemplatePreset(name="t", generator_type="dubstep", complexity=0.9)
    cfg = generate_template(p)
    assert "multiband_compression" in cfg.fx_chain


def test_generate_template_to_dict_round_trip():
    p = TemplatePreset(name="t", generator_type="melodic")
    cfg = generate_template(p)
    d = cfg.to_dict()
    assert isinstance(d["bpm"], int)
    assert isinstance(d["sections"], list)


# ── banks ────────────────────────────────────────────────────────────────

def test_all_banks_registered():
    assert len(ALL_TEMPLATE_BANKS) == 5


def test_total_presets_is_20():
    total = sum(len(fn().presets) for fn in ALL_TEMPLATE_BANKS.values())
    assert total == 20


def test_each_bank_has_4_presets():
    for name, gen_fn in ALL_TEMPLATE_BANKS.items():
        bank = gen_fn()
        assert len(bank.presets) == 4, f"Bank {name} has {len(bank.presets)} presets"


# ── manifest + export ───────────────────────────────────────────────────

def test_write_manifest(tmp_path):
    manifest = write_template_manifest(str(tmp_path))
    assert "banks" in manifest
    assert len(manifest["banks"]) == 5
    json_path = tmp_path / "templates" / "template_manifest.json"
    assert json_path.exists()


def test_export_templates_creates_files(tmp_path):
    paths = export_templates(str(tmp_path))
    assert isinstance(paths, list)
    assert len(paths) == 20
    for p in paths:
        assert Path(p).exists()
        with open(p) as f:
            data = json.load(f)
        assert "genre" in data
        assert "bpm" in data
        assert "sections" in data
