"""
DUBFORGE Engine — Marketplace Metadata Generator

Generate standardized metadata for sample pack distribution on
Splice, Loopcloud, and other marketplaces.

Outputs:
    - Splice-format tags (genre, instrument, key, BPM, mood)
    - Loopcloud detection headers
    - Standardized ACID/REX metadata in WAV chunks
    - Pack-level metadata.json for distribution
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from engine.config_loader import PHI


# ═══════════════════════════════════════════════════════════════════════════
# TAG TAXONOMY — Splice / Loopcloud compatible
# ═══════════════════════════════════════════════════════════════════════════

GENRE_TAGS = [
    "Dubstep", "Bass Music", "Electronic", "Experimental Bass",
    "Riddim", "Heavy Bass", "Halftime", "Future Bass",
]

INSTRUMENT_TAGS = {
    "drums":  ["Drum", "Kick", "Snare", "Hi-Hat", "Percussion", "Clap"],
    "bass":   ["Bass", "Sub Bass", "Mid Bass", "Wobble Bass", "Growl"],
    "synths": ["Synth", "Lead", "Pad", "Pluck", "Arp"],
    "fx":     ["FX", "Riser", "Impact", "Transition", "Texture", "Noise"],
    "stems":  ["Stem", "Loop", "Full Mix"],
    "vocals": ["Vocal", "Vocal Chop", "Vox FX"],
}

MOOD_TAGS = [
    "Aggressive", "Dark", "Heavy", "Intense", "Energetic",
    "Atmospheric", "Deep", "Gritty", "Hypnotic", "Powerful",
]

KEY_NAMES = [
    "C", "C#", "D", "D#", "E", "F",
    "F#", "G", "G#", "A", "A#", "B",
]


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODEL
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class SampleMetadata:
    """Metadata for a single sample file."""
    filename: str
    category: str
    subcategory: str = ""
    bpm: float = 140.0
    key: str = "F"
    scale: str = "minor"
    duration_s: float = 1.0
    sample_rate: int = 44100
    bit_depth: int = 16
    channels: int = 1
    tags: list[str] = field(default_factory=list)
    instrument_tags: list[str] = field(default_factory=list)
    mood_tags: list[str] = field(default_factory=list)
    one_shot: bool = True
    loopable: bool = False

    def to_splice_dict(self) -> dict:
        """Export as Splice-compatible metadata."""
        return {
            "filename": self.filename,
            "type": "one-shot" if self.one_shot else "loop",
            "bpm": self.bpm if not self.one_shot else None,
            "key": f"{self.key} {self.scale}" if self.key else None,
            "tags": list(set(
                self.tags + self.instrument_tags + self.mood_tags
            )),
            "instrument": self.instrument_tags[0] if self.instrument_tags else self.category,
            "genre": "Dubstep",
        }

    def to_loopcloud_dict(self) -> dict:
        """Export as Loopcloud-compatible metadata."""
        return {
            "file": self.filename,
            "bpm": self.bpm,
            "key": self.key,
            "mode": self.scale,
            "category": self.category.title(),
            "subcategory": self.subcategory or "General",
            "tags": self.tags + self.instrument_tags,
            "one_shot": self.one_shot,
            "sample_rate": self.sample_rate,
            "bit_depth": self.bit_depth,
        }


@dataclass
class PackMetadata:
    """Metadata for an entire sample pack."""
    name: str = "DUBFORGE Pack"
    version: str = "1.0"
    author: str = "DUBFORGE"
    description: str = "Phi-precision dubstep sample pack"
    bpm: float = 140.0
    key: str = "F"
    scale: str = "minor"
    genre: str = "Dubstep"
    tags: list[str] = field(default_factory=list)
    samples: list[SampleMetadata] = field(default_factory=list)
    phi: float = PHI

    def to_dict(self) -> dict:
        return {
            "pack": {
                "name": self.name,
                "version": self.version,
                "author": self.author,
                "description": self.description,
                "genre": self.genre,
                "bpm": self.bpm,
                "key": f"{self.key} {self.scale}",
                "tags": self.tags or GENRE_TAGS[:3],
                "total_samples": len(self.samples),
                "phi_ratio": self.phi,
                "tuning": "A4 = 432 Hz",
            },
            "samples": [s.to_splice_dict() for s in self.samples],
        }


# ═══════════════════════════════════════════════════════════════════════════
# AUTO-TAGGER — infer tags from category/filename
# ═══════════════════════════════════════════════════════════════════════════

def auto_tag_sample(filename: str, category: str,
                    subcategory: str = "",
                    bpm: float = 140.0,
                    key: str = "F") -> SampleMetadata:
    """Automatically generate metadata tags from filename and category."""
    name_lower = filename.lower()

    # Determine if one-shot or loop
    one_shot = True
    loopable = False
    if "loop" in name_lower or "stem" in name_lower:
        one_shot = False
        loopable = True

    # Instrument tags from category
    cat_key = category.lower()
    inst_tags = list(INSTRUMENT_TAGS.get(cat_key, [category.title()]))

    # Refine from subcategory / filename
    if "kick" in name_lower:
        inst_tags = ["Kick", "Drum"]
    elif "snare" in name_lower:
        inst_tags = ["Snare", "Drum"]
    elif "hat" in name_lower:
        inst_tags = ["Hi-Hat", "Drum"]
    elif "clap" in name_lower:
        inst_tags = ["Clap", "Drum"]
    elif "sub" in name_lower and cat_key == "bass":
        inst_tags = ["Sub Bass", "Bass"]
    elif "growl" in name_lower:
        inst_tags = ["Growl", "Bass", "Mid Bass"]
    elif "wobble" in name_lower:
        inst_tags = ["Wobble Bass", "Bass"]
    elif "riser" in name_lower:
        inst_tags = ["Riser", "FX"]
    elif "impact" in name_lower:
        inst_tags = ["Impact", "FX"]
    elif "pad" in name_lower:
        inst_tags = ["Pad", "Synth"]
    elif "lead" in name_lower:
        inst_tags = ["Lead", "Synth"]

    # Mood from category
    mood = ["Heavy", "Dark"]
    if cat_key == "fx":
        mood = ["Intense", "Energetic"]
    elif cat_key in ("synths", "stems") and "pad" in name_lower:
        mood = ["Atmospheric", "Deep"]

    return SampleMetadata(
        filename=filename,
        category=category,
        subcategory=subcategory,
        bpm=bpm,
        key=key,
        tags=GENRE_TAGS[:2],
        instrument_tags=inst_tags,
        mood_tags=mood,
        one_shot=one_shot,
        loopable=loopable,
    )


# ═══════════════════════════════════════════════════════════════════════════
# PACK METADATA BUILDER
# ═══════════════════════════════════════════════════════════════════════════

def build_pack_metadata(pack_dir: str,
                        pack_name: str = "DUBFORGE Dubstep Vol 1",
                        bpm: float = 140.0,
                        key: str = "F") -> PackMetadata:
    """Scan a pack directory and auto-tag all .wav files."""
    pack_path = Path(pack_dir)
    pack = PackMetadata(
        name=pack_name, bpm=bpm, key=key,
        description=f"PHI-precision dubstep sample pack — {pack_name}",
    )

    for wav in sorted(pack_path.rglob("*.wav")):
        # Infer category from parent folder
        rel = wav.relative_to(pack_path)
        parts = rel.parts
        category = parts[0] if len(parts) > 1 else "misc"
        subcategory = parts[1] if len(parts) > 2 else ""

        meta = auto_tag_sample(
            filename=str(rel),
            category=category,
            subcategory=subcategory,
            bpm=bpm,
            key=key,
        )
        pack.samples.append(meta)

    return pack


def export_marketplace_metadata(pack_dir: str,
                                pack_name: str = "DUBFORGE Dubstep Vol 1",
                                output_dir: str = "output") -> dict:
    """Generate marketplace metadata files for a sample pack."""
    pack = build_pack_metadata(pack_dir, pack_name)
    out = Path(output_dir) / "marketplace"
    out.mkdir(parents=True, exist_ok=True)

    # Splice metadata
    splice_data = pack.to_dict()
    with open(out / "splice_metadata.json", "w") as f:
        json.dump(splice_data, f, indent=2)

    # Loopcloud metadata
    loopcloud_data = {
        "pack": pack.name,
        "author": pack.author,
        "genre": pack.genre,
        "samples": [s.to_loopcloud_dict() for s in pack.samples],
    }
    with open(out / "loopcloud_metadata.json", "w") as f:
        json.dump(loopcloud_data, f, indent=2)

    # Summary
    categories: dict[str, int] = {}
    for s in pack.samples:
        categories[s.category] = categories.get(s.category, 0) + 1

    result = {
        "pack": pack_name,
        "total_samples": len(pack.samples),
        "categories": categories,
        "splice_metadata": str(out / "splice_metadata.json"),
        "loopcloud_metadata": str(out / "loopcloud_metadata.json"),
    }

    with open(out / "marketplace_summary.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def main() -> None:
    # Default: scan output/sample_packs
    result = export_marketplace_metadata(
        "output/sample_packs",
        "DUBFORGE Dubstep Vol 1",
    )
    print(f"Marketplace metadata: {result['total_samples']} samples tagged")
    print(f"  Splice:    {result['splice_metadata']}")
    print(f"  Loopcloud: {result['loopcloud_metadata']}")


if __name__ == "__main__":
    main()
