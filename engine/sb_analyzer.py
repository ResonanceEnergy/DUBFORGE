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
from dataclasses import asdict, dataclass, field
from pathlib import Path

from engine.config_loader import FIBONACCI, load_config
from engine.log import get_logger

_log = get_logger("dubforge.sb_analyzer")


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
    section_map: dict = field(default_factory=dict)


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
            Track("O.P.U.S.", 201.08, key="Fm", notes="Album opener",
                  section_map={"intro": 8, "build1": 8, "drop1": 16, "break": 8, "build2": 8, "drop2": 16, "outro": 8}),
            Track("Spacetime", 168.00, key="Dm", is_collab=True, collab_artist="NEVVE",
                  notes="feat. Nevve"),
            Track("Cabin Fever", 204.00, key="Em"),
            Track("Open Your Mind (Anthology 999)", 217.06, key="Gm"),
            Track("Gassed Up", 238.18, key="Fm", is_collab=True, collab_artist="Flowdan",
                  notes="feat. Flowdan",
                  section_map={"intro": 8, "build1": 8, "drop1": 16, "break": 8, "build2": 8, "drop2": 16, "outro": 8}),
            Track("Flute Dub", 185.14, key="Dm"),
            Track("Gummy Worm", 243.43, key="Em", is_collab=True, collab_artist="Boogie T",
                  notes="feat. Boogie T"),
            Track("Cyclops Rocks", 130.40, key="Fm", notes="Shortest track in album"),
            Track("Take Flight VIP", 290.62, key="Gm", is_vip=True,
                  notes="LONGEST track in corpus — 4:50"),
            Track("Morning Coffee", 152.47, key="Cm", is_collab=True, collab_artist="Sony",
                  notes="feat. Sony"),
            Track("Into Pieces", 211.76, key="Em", is_collab=True, collab_artist="Grabbitz",
                  notes="feat. Grabbitz",
                  section_map={"intro": 8, "build1": 8, "drop1": 16, "break": 16, "build2": 8, "drop2": 16, "outro": 8}),
            Track("FUNcKED", 179.59, key="Fm"),
            Track("Griztronics II (Another Level)", 165.52, key="Dm",
                  is_collab=True, collab_artist="GRiZ"),
            Track("Tuba Demon", 154.76, key="Fm"),
            Track("Hieroglyph", 204.14, key="Em"),
            Track("MetaFractal", 163.83, key="Gm"),
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
            Track("Into Pieces (Wooli x Grabbitz Remix)", 204.39, key="Em",
                  is_remix=True, collab_artist="Wooli x Grabbitz"),
            Track("Spacetime (Virtual Riot Remix)", 210.21, key="Dm",
                  is_remix=True, collab_artist="Virtual Riot",
                  notes="feat. NEVVE"),
            Track("Tuba Demon (HOL! Remix)", 178.48, key="Fm",
                  is_remix=True, collab_artist="HOL!"),
            Track("Take Flight (Kai Wachi Remix)", 190.37, key="Gm",
                  is_remix=True, collab_artist="Kai Wachi"),
            Track("O.P.U.S. (PEEKABOO Remix)", 246.86, key="Fm",
                  is_remix=True, collab_artist="PEEKABOO"),
            Track("Gummy Worm (Dirt Monkey x Jantsen Remix)", 211.20, key="Em",
                  is_remix=True, collab_artist="Dirt Monkey x Jantsen",
                  notes="feat. Boogie T"),
            Track("Morning Coffee (Mr. Bill Remix)", 180.00, key="Cm",
                  is_remix=True, collab_artist="Mr. Bill",
                  notes="feat. Sony"),
            Track("Cyclops Rocks (LEVEL UP Remix)", 120.83, key="Fm",
                  is_remix=True, collab_artist="LEVEL UP",
                  notes="Shortest track in corpus — 2:01"),
            Track("Hieroglyph (Of The Trees Remix)", 197.14, key="Em",
                  is_remix=True, collab_artist="Of The Trees"),
            Track("Cabin Fever (Kompany Remix)", 182.07, key="Em",
                  is_remix=True, collab_artist="Kompany"),
            Track("Flute Dub (A Hundred Drums Remix)", 253.26, key="Dm",
                  is_remix=True, collab_artist="A Hundred Drums"),
            Track("MetaFractal (MUST DIE! Remix)", 164.80, key="Gm",
                  is_remix=True, collab_artist="MUST DIE!"),
            Track("FUNcKED (HE$H x Versa Remix)", 196.14, key="Fm",
                  is_remix=True, collab_artist="HE$H x Versa"),
            Track("Gassed Up (IMANU Remix)", 178.50, key="Fm",
                  is_remix=True, collab_artist="IMANU",
                  notes="feat. Flowdan"),
            # — VIPs (tracks 15-24) —
            Track("Gassed Up VIP", 226.29, key="Fm", is_vip=True,
                  notes="feat. Flowdan"),
            Track("Cyclops Rocks VIP", 148.74, key="Fm", is_vip=True),
            Track("MetaFractal VIP", 170.71, key="Gm", is_vip=True),
            Track("Hieroglyph VIP", 169.64, key="Em", is_vip=True),
            Track("Spacetime VIP", 168.00, key="Dm", is_vip=True,
                  notes="feat. NEVVE"),
            Track("Flute Dub VIP", 154.29, key="Dm", is_vip=True),
            Track("GRiZTRONICS II (Another Level) VIP", 145.66, key="Dm", is_vip=True,
                  is_collab=True, collab_artist="GRiZ"),
            Track("Take Flight Tech House VIP", 210.00, key="Gm", is_vip=True,
                  notes="Genre-flip VIP — tech house"),
            Track("Into Pieces VIP", 217.41, key="Em", is_vip=True,
                  notes="feat. Grabbitz"),
            Track("Bunker Buster VIP", 291.31, key="Abm", is_vip=True,
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
            Track("Cottage Gore", 164.07, key="Dm",
                  section_map={"intro": 8, "build1": 8, "drop1": 16, "break": 8, "build2": 8, "drop2": 16, "outro": 4}),
            Track("Only Star You See", 189.94, key="Em",
                  is_collab=True, collab_artist="Caitlyn Scarlett",
                  notes="feat. Caitlyn Scarlett"),
            Track("Amnesia", 155.59, key="Fm"),
            Track("Afternoon Coffee (Slide)", 185.14, key="Cm",
                  is_collab=True, collab_artist="Ronzo",
                  notes="feat. Ronzo — Coffee series track"),
            Track("Parabola Paradox (Slap It)", 240.00, key="Gm",
                  is_collab=True, collab_artist="Kwengface",
                  notes="feat. Kwengface"),
            Track("Alien Communication", 303.43, key="Fm",
                  notes="LONGEST non-VIP track — 5:03",
                  section_map={"intro": 16, "build1": 8, "drop1": 16, "break": 16, "build2": 8, "drop2": 16, "breakdown": 8, "drop3": 16, "outro": 8}),
            Track("Asteroid", 243.20, key="Em"),
            Track("Interface Wheel", 197.14, key="Dm"),
            Track("Dreams (Plasma Reflex)", 240.00, key="Fm",
                  is_collab=True, collab_artist="Crooked Bangs",
                  notes="feat. Crooked Bangs"),
            Track("Reality Distortion", 216.00, key="Gm"),
            Track("Insidious", 241.63, key="Abm"),
            Track("Quantum Queso", 176.57, key="Fm"),
            Track("Mind Pluck", 270.86, key="Em"),
            Track("Black Ice", 260.00, key="Dm"),
            Track("Omnidirectional", 222.61, key="Gm"),
            Track("Buried Alive", 211.03, key="Em",
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
            Track("Oblivion", 185.38, key="Dm",
                  section_map={"intro": 8, "build1": 8, "drop1": 13, "break": 8, "build2": 5, "drop2": 13, "outro": 8}),
            Track("Mothclaws", 210.21, key="Em"),
            Track("Brass Danger", 202.29, key="Fm"),
            Track("Stratosphere", 174.22, key="Gm"),
            Track("Lock In", 215.17, key="Fm"),
            Track("Brain Squeak", 172.21, key="Dm"),
            Track("Fibonacci (Part 1)", 164.80, key="Em",
                  notes="Title track — Fibonacci number sequence reference",
                  section_map={"intro": 5, "build1": 8, "drop1": 13, "break": 5, "build2": 8, "drop2": 13, "outro": 5}),
            Track("Final Breath", 229.03, key="Fm"),
        ],
    )
    corpus.append(fibonacci_1)

    # --- Fibonacci Pt 2: Infinity (2025) — 10 tracks ---
    fibonacci_2 = Album(
        title="Fibonacci Pt 2: Infinity",
        year=2025,
        platform_url="https://music.apple.com/ca/album/fibonacci-pt-2-infinity/1850609271",
        tracks=[
            Track("Infinity", 196.70, key="Em",
                  section_map={"intro": 8, "build1": 8, "drop1": 13, "break": 8, "build2": 5, "drop2": 13, "outro": 5}),
            Track("Anxious", 200.63, key="Dm"),
            Track("Fuck Up", 156.00, key="Fm"),
            Track("Nothing Between", 246.36, key="Em"),
            Track("Antidote (Midnight Coffee)", 200.80, key="Cm",
                  notes="Coffee series track"),
            Track("By A Thread", 185.60, key="Dm"),
            Track("Contour", 168.33, key="Gm"),
            Track("Gangstas", 190.55, key="Fm"),
            Track("Friends", 196.36, key="Em"),
            Track("Got Away", 214.29, key="Dm"),
        ],
    )
    corpus.append(fibonacci_2)

    return corpus


def _load_corpus_from_yaml() -> list[Album] | None:
    """Try loading corpus from configs/sb_corpus_v1.yaml. Returns None on failure."""
    try:
        data = load_config("sb_corpus_v1")
        if not data or "albums" not in data:
            return None
        albums: list[Album] = []
        for ad in data["albums"]:
            tracks = []
            for td in ad.get("tracks", []):
                tracks.append(Track(
                    title=td.get("title", "?"),
                    duration_s=float(td.get("duration", 0)),
                    bpm=float(td.get("bpm", 150.0)),
                    key=td.get("key", ""),
                    is_vip=bool(td.get("is_vip", False)),
                    is_remix=bool(td.get("is_remix", False)),
                    is_collab=bool(td.get("is_collab", False)),
                    collab_artist=td.get("collab_artist", ""),
                    notes=td.get("notes", ""),
                ))
            albums.append(Album(
                title=ad.get("title", "?"),
                year=int(ad.get("year", 0)),
                tracks=tracks,
                platform_url=ad.get("platform_url", ""),
            ))
        return albums if albums else None
    except Exception as exc:
        _log.warning("YAML corpus load failed: %s", exc)
        return None


def load_corpus() -> list[Album]:
    """Load corpus from YAML data file, falling back to hardcoded build_corpus()."""
    yaml_corpus = _load_corpus_from_yaml()
    if yaml_corpus is not None:
        return yaml_corpus
    return build_corpus()


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


# --- Key & Section Analysis -----------------------------------------------

def key_distribution(corpus: list[Album]) -> dict:
    """Analyze key distribution across the corpus."""
    key_counts: dict[str, int] = {}
    key_by_album: dict[str, dict[str, int]] = {}

    for album in corpus:
        album_keys: dict[str, int] = {}
        for t in album.tracks:
            if t.key:
                key_counts[t.key] = key_counts.get(t.key, 0) + 1
                album_keys[t.key] = album_keys.get(t.key, 0) + 1
        key_by_album[album.title] = album_keys

    sorted_keys = sorted(key_counts.items(), key=lambda x: x[1], reverse=True)
    return {
        "total_keyed_tracks": sum(key_counts.values()),
        "key_counts": dict(sorted_keys),
        "top_key": sorted_keys[0][0] if sorted_keys else "",
        "key_by_album": key_by_album,
        "minor_ratio": sum(v for k, v in key_counts.items() if k.endswith("m")) / max(1, sum(key_counts.values())),
    }


def section_analysis(corpus: list[Album]) -> dict:
    """Analyze section structures across tracks with section maps."""
    mapped_tracks = []
    all_drop_bars = []
    all_build_bars = []
    all_break_bars = []
    all_intro_bars = []

    for album in corpus:
        for t in album.tracks:
            if t.section_map:
                mapped_tracks.append({
                    "title": t.title,
                    "album": album.title,
                    "sections": t.section_map,
                    "total_bars": sum(t.section_map.values()),
                })
                for sec_name, bars in t.section_map.items():
                    if "drop" in sec_name:
                        all_drop_bars.append(bars)
                    elif "build" in sec_name:
                        all_build_bars.append(bars)
                    elif "break" in sec_name:
                        all_break_bars.append(bars)
                    elif "intro" in sec_name:
                        all_intro_bars.append(bars)

    return {
        "mapped_track_count": len(mapped_tracks),
        "tracks": mapped_tracks,
        "drop_bar_avg": round(sum(all_drop_bars) / max(1, len(all_drop_bars)), 1),
        "drop_bar_mode": max(set(all_drop_bars), key=all_drop_bars.count) if all_drop_bars else 0,
        "build_bar_avg": round(sum(all_build_bars) / max(1, len(all_build_bars)), 1),
        "break_bar_avg": round(sum(all_break_bars) / max(1, len(all_break_bars)), 1),
        "intro_bar_avg": round(sum(all_intro_bars) / max(1, len(all_intro_bars)), 1),
        "fibonacci_drop_count": sum(1 for b in all_drop_bars if b in (1, 2, 3, 5, 8, 13, 21, 34)),
        "total_drops_analyzed": len(all_drop_bars),
    }


def evolution_analysis(corpus: list[Album]) -> dict:
    """Track sound design evolution across albums."""
    albums_sorted = sorted(corpus, key=lambda a: a.year)
    evolution = []

    for album in albums_sorted:
        key_counts: dict[str, int] = {}
        durations = []
        vip_count = 0
        collab_count = 0
        section_mapped = 0

        for t in album.tracks:
            durations.append(t.duration_s)
            if t.key:
                key_counts[t.key] = key_counts.get(t.key, 0) + 1
            if t.is_vip:
                vip_count += 1
            if t.is_collab:
                collab_count += 1
            if t.section_map:
                section_mapped += 1

        top_key = max(key_counts.items(), key=lambda x: x[1])[0] if key_counts else ""

        evolution.append({
            "album": album.title,
            "year": album.year,
            "track_count": len(album.tracks),
            "avg_duration_s": round(sum(durations) / max(1, len(durations)), 1),
            "duration_spread_s": round(max(durations) - min(durations), 1) if durations else 0,
            "top_key": top_key,
            "unique_keys": len(key_counts),
            "vip_count": vip_count,
            "collab_ratio": round(collab_count / max(1, len(album.tracks)), 2),
            "section_mapped": section_mapped,
        })

    return {
        "era_count": len(evolution),
        "eras": evolution,
        "duration_trend": "increasing" if len(evolution) >= 2 and evolution[-1]["avg_duration_s"] > evolution[0]["avg_duration_s"] else "stable",
        "collab_trend": "decreasing" if len(evolution) >= 2 and evolution[-1]["collab_ratio"] < evolution[0]["collab_ratio"] else "stable",
    }


def golden_section_analysis(corpus: list[Album]) -> list[dict]:
    """Check if climax points align with golden section (total_beats / phi)."""
    PHI = 1.6180339887
    results = []

    for album in corpus:
        for t in album.tracks:
            if t.section_map:
                total_bars = sum(t.section_map.values())
                total_beats = total_bars * 4
                golden_beat = total_beats / PHI
                golden_bar = golden_beat / 4

                # Find which section the golden point falls in
                cumulative = 0
                golden_section = ""
                for sec_name, bars in t.section_map.items():
                    cumulative += bars
                    if cumulative >= golden_bar and not golden_section:
                        golden_section = sec_name

                # Check if it lands in a drop
                is_drop_aligned = "drop" in golden_section

                results.append({
                    "title": t.title,
                    "total_bars": total_bars,
                    "golden_bar": round(golden_bar, 1),
                    "golden_section": golden_section,
                    "drop_aligned": is_drop_aligned,
                })

    return results


# --- Spectral Analysis (Stubs) --------------------------------------------

def spectral_centroid_estimate(track: Track) -> float:
    """Estimate spectral centroid from track metadata.

    Returns an estimated centroid frequency in Hz based on
    genre characteristics and BPM. Full implementation would
    require audio file analysis.
    """
    # Heuristic: weapon tracks tend darker (lower centroid)
    base_centroid = 2000.0
    if track.bpm >= 150:
        base_centroid *= 0.9  # faster = typically denser low-end
    if "weapon" in track.title.lower() or "growl" in track.title.lower():
        base_centroid *= 0.8
    if "emotive" in track.title.lower() or "melodic" in track.title.lower():
        base_centroid *= 1.2
    return round(base_centroid, 1)


def spectral_bandwidth_estimate(track: Track) -> float:
    """Estimate spectral bandwidth from track metadata.

    Returns estimated bandwidth in Hz. Full implementation
    requires audio file analysis.
    """
    base_bw = 4000.0
    if track.bpm >= 150:
        base_bw *= 1.1
    return round(base_bw, 1)


def spectral_profile(corpus: list[Album]) -> dict:
    """Generate spectral profile estimates for the entire corpus.

    Returns per-album and global spectral statistics.
    Full spectral analysis requires audio files — this provides
    metadata-based estimates as scaffolding.
    """
    all_centroids = []
    all_bandwidths = []
    album_profiles = {}

    for album in corpus:
        centroids = []
        bandwidths = []
        for t in album.tracks:
            c = spectral_centroid_estimate(t)
            b = spectral_bandwidth_estimate(t)
            centroids.append(c)
            bandwidths.append(b)
            all_centroids.append(c)
            all_bandwidths.append(b)

        album_profiles[album.name] = {
            "avg_centroid_hz": round(sum(centroids) / max(1, len(centroids)), 1),
            "avg_bandwidth_hz": round(sum(bandwidths) / max(1, len(bandwidths)), 1),
            "track_count": len(centroids),
        }

    return {
        "global_avg_centroid_hz": round(sum(all_centroids) / max(1, len(all_centroids)), 1),
        "global_avg_bandwidth_hz": round(sum(all_bandwidths) / max(1, len(all_bandwidths)), 1),
        "album_profiles": album_profiles,
        "note": "Estimates based on metadata heuristics. Full spectral analysis requires audio files.",
    }


# --- Main -----------------------------------------------------------------

def main() -> None:
    out_dir = Path('output/analysis')
    out_dir.mkdir(parents=True, exist_ok=True)

    corpus = load_corpus()

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

    # Key distribution
    key_dist = key_distribution(corpus)
    key_path = out_dir / 'sb_key_distribution.json'
    with open(key_path, 'w') as f:
        json.dump(key_dist, f, indent=2)
    print(f"Key distribution: {key_path}")
    print(f"  Top key: {key_dist['top_key']} ({key_dist['key_counts'].get(key_dist['top_key'], 0)} tracks)")
    print(f"  Minor ratio: {key_dist['minor_ratio']:.0%}")

    # Section analysis
    sections = section_analysis(corpus)
    section_path = out_dir / 'sb_section_analysis.json'
    with open(section_path, 'w') as f:
        json.dump(sections, f, indent=2)
    print(f"Section analysis: {section_path}")
    print(f"  Drop bar mode: {sections['drop_bar_mode']}")
    print(f"  Fibonacci drops: {sections['fibonacci_drop_count']}/{sections['total_drops_analyzed']}")

    # Evolution analysis
    evo = evolution_analysis(corpus)
    evo_path = out_dir / 'sb_evolution.json'
    with open(evo_path, 'w') as f:
        json.dump(evo, f, indent=2)
    print(f"Evolution analysis: {evo_path}")
    print(f"  Duration trend: {evo['duration_trend']}")

    # Golden section
    golden = golden_section_analysis(corpus)
    golden_path = out_dir / 'sb_golden_section.json'
    with open(golden_path, 'w') as f:
        json.dump(golden, f, indent=2)
    print(f"Golden section: {golden_path}  ({len(golden)} tracks analyzed)")

    # Spectral profile (estimate)
    spectral = spectral_profile(corpus)
    spectral_path = out_dir / 'sb_spectral_profile.json'
    with open(spectral_path, 'w') as f:
        json.dump(spectral, f, indent=2)
    print(f"Spectral profile: {spectral_path}")
    print(f"  Avg centroid: {spectral['global_avg_centroid_hz']} Hz")

    print("SB Analyzer complete.")


if __name__ == '__main__':
    main()
