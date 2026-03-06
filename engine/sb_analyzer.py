"""
DUBFORGE Engine — Subtronics Analyzer (SB Analyzer)

Metadata-based analysis engine for Subtronics discography.
Analyzes album structure, duration patterns, BPM, and
extracts structural invariants for engine calibration.

When audio files are available, can be extended with
spectral analysis (FFT, MFCC, spectral centroid, etc.)

Outputs:
    output/analysis/sb_corpus.json
    output/analysis/sb_signature_vector.json
"""

import json
import math
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Optional

PHI = 1.6180339887498948482
FIBONACCI = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89, 144, 233]


# --- Data Models ----------------------------------------------------------

@dataclass
class Track:
    """Single track metadata."""
    title: str
    duration_s: float
    bpm: float = 150.0
    key: str = ""
    is_vip: bool = False
    is_remix: bool = False
    is_collab: bool = False
    collab_artist: str = ""
    notes: str = ""


@dataclass
class Album:
    """Album metadata + tracks."""
    title: str
    year: int
    tracks: list = field(default_factory=list)
    platform_url: str = ""

    @property
    def track_count(self) -> int:
        return len(self.tracks)

    @property
    def avg_duration_s(self) -> float:
        if not self.tracks:
            return 0.0
        return sum(t.duration_s for t in self.tracks) / len(self.tracks)

    @property
    def avg_bpm(self) -> float:
        if not self.tracks:
            return 0.0
        return sum(t.bpm for t in self.tracks) / len(self.tracks)

    @property
    def total_duration_s(self) -> float:
        return sum(t.duration_s for t in self.tracks)


@dataclass
class SignatureVector:
    """
    The SB10 Baseline Signature Vector — a set of invariants
    extracted from the Subtronics corpus that define the
    "Subtronics sound" for engine calibration.
    """
    avg_bpm: float = 150.0
    bpm_range: tuple = (140, 155)
    avg_duration_s: float = 220.0
    drop_bars_mode: int = 16
    drop_energy_peak: float = 0.95
    drop_energy_floor: float = 0.75
    build_bars_mode: int = 8
    build_curve: str = "phi"
    break_energy_ceiling: float = 0.35
    sub_treatment: str = "clean_mono_sine"
    mid_treatment: str = "fm_wavetable_heavy"
    stereo_strategy: str = "mono_sub_wide_mid_high"
    key_centers: list = field(default_factory=lambda: ["F", "E", "D", "G"])
    fm_index_trend: str = "increasing_per_album"
    fractal_alignment_score: float = 0.0  # 0-1, computed

    def compute_fractal_alignment(self, drop_bars: int) -> float:
        """
        How close is the drop bar count to a Fibonacci number?
        Returns 0-1 where 1 = exact Fibonacci match.
        """
        min_dist = min(abs(drop_bars - f) for f in FIBONACCI if f > 0)
        self.fractal_alignment_score = max(0, 1.0 - (min_dist / 5.0))
        return self.fractal_alignment_score


# --- Corpus: Subtronics Discography Metadata -----------------------------
# Durations sourced from actual Apple Music .m4p file metadata (mdls)
# Path: ~/Music/Music/Media.localized/Apple Music/Subtronics/

def build_corpus() -> list[Album]:
    """
    Build the Subtronics discography corpus from REAL file metadata.
    Durations are exact values extracted from the user's Apple Music library.
    """
    corpus = []

    # --- FRACTALS (2022) — 16 tracks ---
    fractals = Album(
        title="FRACTALS",
        year=2022,
        platform_url="https://music.apple.com/ca/album/fractals/1600129103",
        tracks=[
            Track("O.P.U.S.", 201.08, notes="Album opener"),
            Track("Spacetime", 168.00, is_collab=True, collab_artist="NEVVE",
                  notes="feat. Nevve"),
            Track("Cabin Fever", 204.00),
            Track("Open Your Mind (Anthology 999)", 217.06),
            Track("Gassed Up", 238.18, is_collab=True, collab_artist="Flowdan",
                  notes="feat. Flowdan"),
            Track("Flute Dub", 185.14),
            Track("Gummy Worm", 243.43, is_collab=True, collab_artist="Boogie T",
                  notes="feat. Boogie T"),
            Track("Cyclops Rocks", 130.40, notes="Shortest track in album"),
            Track("Take Flight VIP", 290.62, is_vip=True,
                  notes="LONGEST track in corpus — 4:50"),
            Track("Morning Coffee", 152.47, is_collab=True, collab_artist="Sony",
                  notes="feat. Sony"),
            Track("Into Pieces", 211.76, is_collab=True, collab_artist="Grabbitz",
                  notes="feat. Grabbitz"),
            Track("FUNcKED", 179.59),
            Track("Griztronics II (Another Level)", 165.52,
                  is_collab=True, collab_artist="GRiZ"),
            Track("Tuba Demon", 154.76),
            Track("Hieroglyph", 204.14),
            Track("MetaFractal", 163.83),
        ],
    )
    corpus.append(fractals)

    # --- Antifractals (2022) — 24 tracks (14 remixes + 10 VIPs) ---
    antifractals = Album(
        title="Antifractals",
        year=2022,
        platform_url="https://music.apple.com/ca/album/antifractals/1655750333",
        tracks=[
            # — Remixes (tracks 1-14) —
            Track("Into Pieces (Wooli x Grabbitz Remix)", 204.39,
                  is_remix=True, collab_artist="Wooli x Grabbitz"),
            Track("Spacetime (Virtual Riot Remix)", 210.21,
                  is_remix=True, collab_artist="Virtual Riot",
                  notes="feat. NEVVE"),
            Track("Tuba Demon (HOL! Remix)", 178.48,
                  is_remix=True, collab_artist="HOL!"),
            Track("Take Flight (Kai Wachi Remix)", 190.37,
                  is_remix=True, collab_artist="Kai Wachi"),
            Track("O.P.U.S. (PEEKABOO Remix)", 246.86,
                  is_remix=True, collab_artist="PEEKABOO"),
            Track("Gummy Worm (Dirt Monkey x Jantsen Remix)", 211.20,
                  is_remix=True, collab_artist="Dirt Monkey x Jantsen",
                  notes="feat. Boogie T"),
            Track("Morning Coffee (Mr. Bill Remix)", 180.00,
                  is_remix=True, collab_artist="Mr. Bill",
                  notes="feat. Sony"),
            Track("Cyclops Rocks (LEVEL UP Remix)", 120.83,
                  is_remix=True, collab_artist="LEVEL UP",
                  notes="Shortest track in corpus — 2:01"),
            Track("Hieroglyph (Of The Trees Remix)", 197.14,
                  is_remix=True, collab_artist="Of The Trees"),
            Track("Cabin Fever (Kompany Remix)", 182.07,
                  is_remix=True, collab_artist="Kompany"),
            Track("Flute Dub (A Hundred Drums Remix)", 253.26,
                  is_remix=True, collab_artist="A Hundred Drums"),
            Track("MetaFractal (MUST DIE! Remix)", 164.80,
                  is_remix=True, collab_artist="MUST DIE!"),
            Track("FUNcKED (HE$H x Versa Remix)", 196.14,
                  is_remix=True, collab_artist="HE$H x Versa"),
            Track("Gassed Up (IMANU Remix)", 178.50,
                  is_remix=True, collab_artist="IMANU",
                  notes="feat. Flowdan"),
            # — VIPs (tracks 15-24) —
            Track("Gassed Up VIP", 226.29, is_vip=True,
                  notes="feat. Flowdan"),
            Track("Cyclops Rocks VIP", 148.74, is_vip=True),
            Track("MetaFractal VIP", 170.71, is_vip=True),
            Track("Hieroglyph VIP", 169.64, is_vip=True),
            Track("Spacetime VIP", 168.00, is_vip=True,
                  notes="feat. NEVVE"),
            Track("Flute Dub VIP", 154.29, is_vip=True),
            Track("GRiZTRONICS II (Another Level) VIP", 145.66, is_vip=True,
                  is_collab=True, collab_artist="GRiZ"),
            Track("Take Flight Tech House VIP", 210.00, is_vip=True,
                  notes="Genre-flip VIP — tech house"),
            Track("Into Pieces VIP", 217.41, is_vip=True,
                  notes="feat. Grabbitz"),
            Track("Bunker Buster VIP", 291.31, is_vip=True,
                  notes="Second longest track in corpus — 4:51"),
        ],
    )
    corpus.append(antifractals)

    # --- Tesseract (2023) — 16 tracks ---
    tesseract = Album(
        title="Tesseract",
        year=2023,
        platform_url="https://music.apple.com/ca/album/tesseract/1727874942",
        tracks=[
            Track("Cottage Gore", 164.07),
            Track("Only Star You See", 189.94,
                  is_collab=True, collab_artist="Caitlyn Scarlett",
                  notes="feat. Caitlyn Scarlett"),
            Track("Amnesia", 155.59),
            Track("Afternoon Coffee (Slide)", 185.14,
                  is_collab=True, collab_artist="Ronzo",
                  notes="feat. Ronzo — Coffee series track"),
            Track("Parabola Paradox (Slap It)", 240.00,
                  is_collab=True, collab_artist="Kwengface",
                  notes="feat. Kwengface"),
            Track("Alien Communication", 303.43,
                  notes="LONGEST non-VIP track — 5:03"),
            Track("Asteroid", 243.20),
            Track("Interface Wheel", 197.14),
            Track("Dreams (Plasma Reflex)", 240.00,
                  is_collab=True, collab_artist="Crooked Bangs",
                  notes="feat. Crooked Bangs"),
            Track("Reality Distortion", 216.00),
            Track("Insidious", 241.63),
            Track("Quantum Queso", 176.57),
            Track("Mind Pluck", 270.86),
            Track("Black Ice", 260.00),
            Track("Omnidirectional", 222.61),
            Track("Buried Alive", 211.03,
                  is_collab=True, collab_artist="Jem Cooke",
                  notes="feat. Jem Cooke"),
        ],
    )
    corpus.append(tesseract)

    # --- Fibonacci Pt 1: Oblivion (2025) — 8 tracks ---
    fibonacci_1 = Album(
        title="Fibonacci Pt 1: Oblivion",
        year=2025,
        platform_url="https://music.apple.com/ca/album/fibonacci/1850610250",
        tracks=[
            Track("Oblivion", 185.38),
            Track("Mothclaws", 210.21),
            Track("Brass Danger", 202.29),
            Track("Stratosphere", 174.22),
            Track("Lock In", 215.17),
            Track("Brain Squeak", 172.21),
            Track("Fibonacci (Part 1)", 164.80,
                  notes="Title track — Fibonacci number sequence reference"),
            Track("Final Breath", 229.03),
        ],
    )
    corpus.append(fibonacci_1)

    # --- Fibonacci Pt 2: Infinity (2025) — 10 tracks ---
    fibonacci_2 = Album(
        title="Fibonacci Pt 2: Infinity",
        year=2025,
        platform_url="https://music.apple.com/ca/album/fibonacci-pt-2-infinity/1850609271",
        tracks=[
            Track("Infinity", 196.70),
            Track("Anxious", 200.63),
            Track("Fuck Up", 156.00),
            Track("Nothing Between", 246.36),
            Track("Antidote (Midnight Coffee)", 200.80,
                  notes="Coffee series track"),
            Track("By A Thread", 185.60),
            Track("Contour", 168.33),
            Track("Gangstas", 190.55),
            Track("Friends", 196.36),
            Track("Got Away", 214.29),
        ],
    )
    corpus.append(fibonacci_2)

    return corpus


# --- Analysis Functions ---------------------------------------------------

def analyze_corpus(corpus: list[Album]) -> dict:
    """Generate full corpus analysis report."""
    report = {
        "total_albums": len(corpus),
        "total_tracks": sum(a.track_count for a in corpus),
        "total_duration_s": round(sum(a.total_duration_s for a in corpus), 1),
        "total_duration_min": round(sum(a.total_duration_s for a in corpus) / 60, 1),
        "albums": [],
    }

    all_durations = []
    all_bpms = []

    for album in corpus:
        album_data = {
            "title": album.title,
            "year": album.year,
            "track_count": album.track_count,
            "avg_duration_s": round(album.avg_duration_s, 1),
            "avg_bpm": round(album.avg_bpm, 1),
            "total_duration_s": round(album.total_duration_s, 1),
            "vip_count": sum(1 for t in album.tracks if t.is_vip),
            "remix_count": sum(1 for t in album.tracks if t.is_remix),
            "collab_count": sum(1 for t in album.tracks if t.is_collab),
            "tracks": [asdict(t) for t in album.tracks],
        }
        report["albums"].append(album_data)
        all_durations.extend(t.duration_s for t in album.tracks)
        all_bpms.extend(t.bpm for t in album.tracks)

    report["global_avg_duration_s"] = round(sum(all_durations) / len(all_durations), 1)
    report["global_avg_bpm"] = round(sum(all_bpms) / len(all_bpms), 1)
    report["bpm_range"] = [min(all_bpms), max(all_bpms)]
    report["duration_range_s"] = [min(all_durations), max(all_durations)]

    return report


def build_signature_vector(corpus: list[Album]) -> SignatureVector:
    """
    Extract the SB10 signature vector from the corpus.
    """
    all_durations = []
    all_bpms = []
    key_counts = {}

    for album in corpus:
        for t in album.tracks:
            all_durations.append(t.duration_s)
            all_bpms.append(t.bpm)
            key_counts[t.key] = key_counts.get(t.key, 0) + 1

    top_keys = sorted(key_counts.keys(), key=lambda k: key_counts[k], reverse=True)[:4]

    sv = SignatureVector(
        avg_bpm=round(sum(all_bpms) / len(all_bpms), 1),
        bpm_range=(min(all_bpms), max(all_bpms)),
        avg_duration_s=round(sum(all_durations) / len(all_durations), 1),
        drop_bars_mode=16,
        key_centers=top_keys,
    )

    # Check Fibonacci alignment for the latest album's bar count
    sv.compute_fractal_alignment(13)  # Fibonacci album uses 13-bar drops

    return sv


# --- VIP Delta Analysis ---------------------------------------------------

def vip_delta_analysis(corpus: list[Album]) -> list[dict]:
    """
    Compare VIP/remix versions against originals.
    Find what changes between album iterations.
    Matches FRACTALS originals → Antifractals VIPs by base title.
    """
    deltas = []

    fractals = next((a for a in corpus if a.title == "FRACTALS"), None)
    antifractals = next((a for a in corpus if a.title == "Antifractals"), None)

    if fractals and antifractals:
        # Manual VIP→Original mapping (real tracklist)
        vip_map = {
            "Gassed Up VIP":                        "Gassed Up",
            "Cyclops Rocks VIP":                    "Cyclops Rocks",
            "MetaFractal VIP":                      "MetaFractal",
            "Hieroglyph VIP":                       "Hieroglyph",
            "Spacetime VIP":                        "Spacetime",
            "Flute Dub VIP":                        "Flute Dub",
            "GRiZTRONICS II (Another Level) VIP":   "Griztronics II (Another Level)",
            "Into Pieces VIP":                      "Into Pieces",
        }

        for af_track in antifractals.tracks:
            if af_track.is_vip:
                # Look up original title
                base_name = vip_map.get(af_track.title)
                if base_name is None:
                    # Fallback: strip " VIP" suffix
                    base_name = af_track.title.replace(" VIP", "")

                original = next(
                    (t for t in fractals.tracks
                     if t.title.lower().startswith(base_name.lower())),
                    None
                )

                delta = {
                    "vip": af_track.title,
                    "vip_duration_s": round(af_track.duration_s, 2),
                    "has_original": original is not None,
                }

                if original:
                    delta["original"] = original.title
                    delta["original_duration_s"] = round(original.duration_s, 2)
                    delta["duration_delta_s"] = round(
                        af_track.duration_s - original.duration_s, 2
                    )
                    delta["longer"] = af_track.duration_s > original.duration_s
                else:
                    delta["original"] = f"(no match for '{base_name}')"
                    delta["notes"] = "No original found — may be Antifractals-exclusive"

                deltas.append(delta)

        # Also capture remix deltas
        for af_track in antifractals.tracks:
            if af_track.is_remix:
                # Try to find original
                base_search = af_track.title.split("(")[0].strip()
                original = next(
                    (t for t in fractals.tracks
                     if t.title.lower().startswith(base_search.lower())),
                    None
                )

                delta = {
                    "remix": af_track.title,
                    "remixer": af_track.collab_artist,
                    "remix_duration_s": round(af_track.duration_s, 2),
                    "has_original": original is not None,
                }

                if original:
                    delta["original"] = original.title
                    delta["original_duration_s"] = round(original.duration_s, 2)
                    delta["duration_delta_s"] = round(
                        af_track.duration_s - original.duration_s, 2
                    )

                deltas.append(delta)

    return deltas


# --- Main -----------------------------------------------------------------

def main():
    out_dir = Path('output/analysis')
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = build_corpus()

    # Full corpus report
    report = analyze_corpus(corpus)
    report_path = out_dir / 'sb_corpus.json'
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    print(f"Corpus analysis: {report_path}")
    print(f"  Albums: {report['total_albums']}")
    print(f"  Tracks: {report['total_tracks']}")
    print(f"  Total duration: {report['total_duration_min']} min")
    print(f"  Avg BPM: {report['global_avg_bpm']}")
    print(f"  Avg duration: {report['global_avg_duration_s']}s")

    # Signature vector
    sv = build_signature_vector(corpus)
    sv_path = out_dir / 'sb_signature_vector.json'
    with open(sv_path, 'w') as f:
        json.dump(asdict(sv), f, indent=2)
    print(f"Signature vector: {sv_path}")
    print(f"  Fractal alignment: {sv.fractal_alignment_score:.2f}")

    # VIP delta
    deltas = vip_delta_analysis(corpus)
    delta_path = out_dir / 'sb_vip_deltas.json'
    with open(delta_path, 'w') as f:
        json.dump(deltas, f, indent=2)
    print(f"VIP deltas: {delta_path}  ({len(deltas)} pairs)")

    print("SB Analyzer complete.")


if __name__ == '__main__':
    main()
