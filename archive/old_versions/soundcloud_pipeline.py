"""
DUBFORGE Engine — SoundCloud Likes Pipeline

Downloads tracks from a SoundCloud user's likes page,
separates stems using HT-Demucs, runs per-stem analysis,
and builds taste prototypes.

Workflow:
    1. Scrape SoundCloud likes URL via yt-dlp
    2. Download audio files
    3. Separate stems via HT-Demucs (torch)
    4. Run DUBFORGE feature extraction per stem
    5. Generate Serum blueprints per stem
    6. Build averaged taste prototypes
    7. Export everything to output/taste/

Dependencies (all optional — pipeline degrades gracefully):
    yt-dlp         — SoundCloud download
    demucs         — stem separation
    librosa        — feature extraction
    numpy          — vector operations
    soundfile      — audio I/O
    joblib         — parallel processing (optional)

Outputs:
    output/taste/downloads/          — raw audio files
    output/taste/stems/<track>/      — separated stems
    output/taste/stem_analysis.json  — per-track analysis
    output/taste/prototypes.json     — averaged taste vectors
    output/taste/serum_blueprints/   — Serum 2 preset blueprints
    output/taste/taste_report.md     — human-readable report
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from engine.config_loader import get_config_value
from engine.log import get_logger
from engine.turboquant import (
    CompressedAudioBuffer,
    TurboQuantConfig,
    compress_audio_buffer,
    phi_optimal_bits,
)

_log = get_logger("dubforge.soundcloud_pipeline")

# ═══════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

OUTPUT_ROOT = Path(__file__).parent.parent / "output" / "taste"
DOWNLOADS_DIR = OUTPUT_ROOT / "downloads"
STEMS_DIR = OUTPUT_ROOT / "stems"
BLUEPRINTS_DIR = OUTPUT_ROOT / "serum_blueprints"

# Demucs model — HT-Demucs is the best for electronic music
DEMUCS_MODEL = "htdemucs"

# yt-dlp safe defaults
YTDLP_FORMAT = "bestaudio/best"
YTDLP_MAX_FILESIZE = "100M"

# Browsers yt-dlp can extract cookies from
SUPPORTED_BROWSERS = ("chrome", "firefox", "edge", "safari", "opera", "brave", "chromium")


# ═══════════════════════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════════════════════

def _normalize_sc_url(url: str) -> str:
    """
    Normalize a SoundCloud URL before scraping.

    - Bare artist profile   → /tracks playlist
      e.g. soundcloud.com/substandardbassmusic  → .../tracks
    - /you/likes            → left unchanged (requires auth cookies)
    - /username/likes       → left unchanged
    - /username/sets/...    → left unchanged
    """
    from urllib.parse import urlparse
    parsed = urlparse(url.strip())
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    # Only a username — no sub-path → scrape /tracks
    if len(path_parts) == 1:
        return url.rstrip("/") + "/tracks"
    return url


def _resolve_likes_url(url: str, cookies_file: Optional[str] = None) -> str:
    """Resolve ``/you/likes`` to the real username likes URL.

    SoundCloud's ``/you/likes`` is a browser-side route — yt-dlp can't handle
    it because the SoundCloud resolve API returns 404 for the virtual ``you``
    user.  This helper queries ``api-v2.soundcloud.com/me`` with the oauth
    token extracted from the cookies to get the real permalink, then rewrites
    the URL.

    Returns the original URL unchanged if it doesn't match ``/you/``.
    """
    from urllib.parse import urlparse
    parsed = urlparse(url.strip())
    path_parts = [p for p in parsed.path.strip("/").split("/") if p]
    if not path_parts or path_parts[0].lower() != "you":
        return url

    # Need oauth_token from cookies
    token = None
    if cookies_file:
        try:
            import http.cookiejar
            cj = http.cookiejar.MozillaCookieJar(cookies_file)
            cj.load(ignore_discard=True, ignore_expires=True)
            for c in cj:
                if c.name == "oauth_token":
                    token = c.value
                    break
        except Exception as e:
            _log.warning(f"Could not read cookies file for /you/ resolution: {e}")

    if not token:
        _log.warning("Cannot resolve /you/ URL without oauth_token in cookies")
        return url

    try:
        import urllib.request
        req = urllib.request.Request(
            f"https://api-v2.soundcloud.com/me?oauth_token={token}",
            headers={"User-Agent": "Mozilla/5.0"},
        )
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        permalink = data.get("permalink", "")
        if permalink:
            # Rebuild: /you/likes → /permalink/likes
            new_parts = [permalink] + path_parts[1:]
            new_url = f"https://soundcloud.com/{'/'.join(new_parts)}"
            _log.info(f"Resolved /you/ URL: {url} → {new_url}")
            return new_url
    except Exception as e:
        _log.warning(f"Failed to resolve /you/ URL via API: {e}")

    return url


# ═══════════════════════════════════════════════════════════════════════════
# DATA MODELS
# ═══════════════════════════════════════════════════════════════════════════

@dataclass
class DownloadedTrack:
    """Metadata for a downloaded track."""
    title: str = ""
    url: str = ""
    filepath: str = ""
    duration_s: float = 0.0
    artist: str = ""
    downloaded: bool = False
    error: str = ""


@dataclass
class PipelineResult:
    """Full pipeline result for a batch of tracks."""
    source_url: str = ""
    tracks_found: int = 0
    tracks_downloaded: int = 0
    tracks_analyzed: int = 0
    tracks: list[DownloadedTrack] = field(default_factory=list)
    analyses: list = field(default_factory=list)      # list[TrackAnalysis]
    blueprints: dict = field(default_factory=dict)     # dict[track → dict[stem → SerumBlueprint]]
    prototype_path: str = ""
    report_path: str = ""
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "tracks_found": self.tracks_found,
            "tracks_downloaded": self.tracks_downloaded,
            "tracks_analyzed": self.tracks_analyzed,
            "prototype_path": self.prototype_path,
            "report_path": self.report_path,
            "errors": self.errors,
            "tracks": [
                {"title": t.title, "url": t.url, "downloaded": t.downloaded,
                 "error": t.error}
                for t in self.tracks
            ],
        }


# ═══════════════════════════════════════════════════════════════════════════
# STEP 1: DOWNLOAD — yt-dlp SoundCloud scraping
# ═══════════════════════════════════════════════════════════════════════════

def _check_ytdlp() -> bool:
    """Check if yt-dlp is available."""
    return shutil.which("yt-dlp") is not None


def download_soundcloud_likes(likes_url: str,
                               output_dir: Optional[Path] = None,
                               max_tracks: int = 50,
                               cookies_from_browser: Optional[str] = None,
                               cookies_file: Optional[str] = None) -> list[DownloadedTrack]:
    """
    Download tracks from a SoundCloud URL.

    Args:
        likes_url: SoundCloud URL — likes page, artist profile, or playlist.
            /you/likes requires ``cookies_from_browser`` or ``cookies_file`` for auth.
            Bare artist URLs (soundcloud.com/artist) are auto-normalised to /tracks.
        output_dir: Directory to save audio files.
        max_tracks: Maximum number of tracks to download.
        cookies_from_browser: Browser name to extract cookies from for auth
            ("chrome", "firefox", "edge", "safari", "brave", "chromium").
            Required for private likes pages (soundcloud.com/you/likes).
        cookies_file: Path to a Netscape-format cookies.txt file.
            Alternative to cookies_from_browser when browser DB is locked.

    Returns:
        List of DownloadedTrack with file paths.
    """
    out_dir = output_dir or DOWNLOADS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    if not _check_ytdlp():
        raise RuntimeError(
            "yt-dlp not found. Install with: pip install yt-dlp"
        )

    url = _normalize_sc_url(likes_url)
    if url != likes_url:
        _log.info(f"Normalised URL: {likes_url} → {url}")

    # Resolve /you/likes → /username/likes (yt-dlp can't handle /you/)
    resolved = _resolve_likes_url(url, cookies_file=cookies_file)
    if resolved != url:
        url = resolved

    if cookies_from_browser and cookies_from_browser.lower() not in SUPPORTED_BROWSERS:
        raise ValueError(
            f"Unsupported browser '{cookies_from_browser}'. "
            f"Choose from: {', '.join(SUPPORTED_BROWSERS)}"
        )

    auth_msg = ""
    if cookies_file:
        auth_msg = f", cookies file {cookies_file}"
    elif cookies_from_browser:
        auth_msg = f", cookies from {cookies_from_browser}"

    _log.info(f"Downloading: {url} (max={max_tracks}{auth_msg})")

    # First: get metadata (no download)
    tracks = _get_track_list(url, max_tracks,
                             cookies_from_browser=cookies_from_browser,
                             cookies_file=cookies_file)

    # Then: download audio
    for track in tracks:
        if track.error:
            continue
        try:
            _download_single(track, out_dir,
                             cookies_from_browser=cookies_from_browser,
                             cookies_file=cookies_file)
        except Exception as e:
            track.error = str(e)
            _log.warning(f"Download failed: {track.title} — {e}")

    downloaded = sum(1 for t in tracks if t.downloaded)
    _log.info(f"Downloaded {downloaded}/{len(tracks)} tracks")

    return tracks


def _get_track_list(likes_url: str, max_tracks: int,
                    cookies_from_browser: Optional[str] = None,
                    cookies_file: Optional[str] = None) -> list[DownloadedTrack]:
    """Get list of tracks from SoundCloud URL via yt-dlp metadata.

    Raises
    ------
    RuntimeError
        If yt-dlp exits with a non-zero code (e.g. cookie DB locked,
        network error, auth failure).
    """
    cmd = [
        "yt-dlp",
        "--flat-playlist",
        "--dump-json",
        "--playlist-items", f"1:{max_tracks}",
        "--no-warnings",
    ]
    if cookies_file:
        cmd += ["--cookies", cookies_file]
    elif cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    cmd.append(likes_url)

    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=120,
    )

    if result.returncode != 0:
        stderr = result.stderr.strip()
        _log.error(f"yt-dlp failed (exit {result.returncode}): {stderr}")
        raise RuntimeError(
            f"yt-dlp failed (exit {result.returncode}): {stderr}"
        )

    tracks = []
    for line in result.stdout.strip().split("\n"):
        if not line.strip():
            continue
        try:
            info = json.loads(line)
            tracks.append(DownloadedTrack(
                title=info.get("title", "Unknown"),
                url=info.get("url", info.get("webpage_url", "")),
                duration_s=float(info.get("duration", 0) or 0),
                artist=info.get("uploader", ""),
            ))
        except json.JSONDecodeError:
            continue

    _log.info(f"Found {len(tracks)} tracks in likes")
    return tracks


def _download_single(track: DownloadedTrack, output_dir: Path,
                     cookies_from_browser: Optional[str] = None,
                     cookies_file: Optional[str] = None) -> None:
    """Download a single track's audio."""
    safe_title = "".join(c if c.isalnum() or c in "-_ " else "_" for c in track.title)[:80]
    output_template = str(output_dir / f"{safe_title}.%(ext)s")

    cmd = [
        "yt-dlp",
        "--format", YTDLP_FORMAT,
        "--extract-audio",
        "--audio-format", "wav",
        "--audio-quality", "0",
        "--max-filesize", YTDLP_MAX_FILESIZE,
        "--output", output_template,
        "--no-playlist",
        "--no-warnings",
    ]
    if cookies_file:
        cmd += ["--cookies", cookies_file]
    elif cookies_from_browser:
        cmd += ["--cookies-from-browser", cookies_from_browser]
    cmd.append(track.url)

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)

    if result.returncode != 0:
        track.error = result.stderr[:200] if result.stderr else "Download failed"
        return

    # Find the output file
    wav_path = output_dir / f"{safe_title}.wav"
    if wav_path.exists():
        track.filepath = str(wav_path)
        track.downloaded = True
    else:
        # Try other extensions
        for ext in (".opus", ".m4a", ".mp3", ".ogg", ".webm"):
            alt = output_dir / f"{safe_title}{ext}"
            if alt.exists():
                track.filepath = str(alt)
                track.downloaded = True
                break

    if not track.downloaded:
        track.error = "File not found after download"


# ═══════════════════════════════════════════════════════════════════════════
# STEP 2: STEM SEPARATION — HT-Demucs
# ═══════════════════════════════════════════════════════════════════════════

def _check_demucs() -> bool:
    """Check if demucs is available."""
    try:
        import demucs  # type: ignore[import-not-found]
        return True
    except ImportError:
        return False


def separate_stems(audio_path: str,
                   output_dir: Optional[Path] = None,
                   model: str = DEMUCS_MODEL) -> Optional[Path]:
    """
    Separate an audio file into stems using HT-Demucs.

    Returns the directory containing separated stems, or None on failure.
    Demucs outputs: bass.wav, drums.wav, other.wav, vocals.wav
    """
    out_dir = output_dir or STEMS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)

    track_name = Path(audio_path).stem
    # Demucs outputs to out_dir/<model>/<track_name>/  — check that path for cache
    stem_output = out_dir / model / track_name

    if stem_output.exists():
        existing = list(stem_output.glob("*.wav"))
        if len(existing) >= 4:
            _log.info(f"Stems already exist: {stem_output}")
            return stem_output
        # Dir exists but incomplete (e.g. prior run was killed) — wipe it so
        # demucs doesn't silently skip the track
        _log.info(f"Stale stem dir found (only {len(existing)} WAVs), clearing: {stem_output}")
        shutil.rmtree(stem_output)

    _log.info(f"Separating stems: {audio_path}")

    # Try Python API first, fall back to CLI on any error
    try:
        return _separate_python(audio_path, out_dir, model)
    except Exception as e:
        _log.warning(f"Demucs Python API failed ({e}), trying CLI...")
        return _separate_cli(audio_path, out_dir, model)


def _separate_python(audio_path: str, output_dir: Path, model: str) -> Path:
    """Separate using demucs Python API."""
    import demucs.separate  # type: ignore[import-not-found]

    track_name = Path(audio_path).stem

    # Demucs uses its own arg parsing
    args = [
        "--two-stems", "vocals",  # or use all 4 stems
        "-n", model,
        "--out", str(output_dir),
        audio_path,
    ]

    # Actually, for 4-stem separation don't use --two-stems
    args = [
        "-n", model,
        "--out", str(output_dir),
        audio_path,
    ]

    demucs.separate.main(args)

    # Demucs outputs to: output_dir/model_name/track_name/
    stem_dir = output_dir / model / track_name
    if not stem_dir.exists():
        # Try flat structure
        stem_dir = output_dir / track_name

    return stem_dir


def _separate_cli(audio_path: str, output_dir: Path, model: str) -> Optional[Path]:
    """Fall back to demucs CLI."""
    if not shutil.which("demucs"):
        raise ImportError("demucs not found. Install with: pip install demucs")

    track_name = Path(audio_path).stem

    cmd = [
        sys.executable, "-m", "demucs",
        "-n", model,
        "--out", str(output_dir),
        audio_path,
    ]

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)

    if result.returncode != 0:
        _log.error(f"Demucs CLI failed: {result.stderr[:300]}")
        return None

    stem_dir = output_dir / model / track_name
    if stem_dir.exists():
        return stem_dir

    stem_dir = output_dir / track_name
    return stem_dir if stem_dir.exists() else None


# ═══════════════════════════════════════════════════════════════════════════
# STEP 3: FULL PIPELINE — download → separate → analyze → blueprint
# ═══════════════════════════════════════════════════════════════════════════

def run_pipeline(likes_url: str,
                 max_tracks: int = 20,
                 separate: bool = True,
                 generate_blueprints: bool = True,
                 extract_embeddings: bool = False,
                 cookies_from_browser: Optional[str] = None,
                 output_dir: Optional[Path] = None) -> PipelineResult:
    """
    Run the full SoundCloud likes → taste profile pipeline.

    Args:
        likes_url: SoundCloud likes page URL
        max_tracks: Maximum tracks to process
        separate: Whether to run stem separation (requires demucs)
        generate_blueprints: Whether to generate Serum 2 blueprints
        extract_embeddings: Whether to compute OpenL3 embeddings (slow)
        output_dir: Override output directory

    Returns:
        PipelineResult with all analyses and exports.
    """
    # Lazy imports to avoid circular deps
    from engine.dubstep_taste_analyzer import (
        TrackAnalysis,
        analyze_track,
        build_prototypes,
        export_analysis,
        export_prototypes,
        export_taste_report,
    )
    from engine.serum_blueprint import (
        export_all_blueprints,
        generate_blueprints_from_analysis,
    )

    out = output_dir or OUTPUT_ROOT
    out.mkdir(parents=True, exist_ok=True)

    result = PipelineResult(source_url=likes_url)

    # --- Step 1: Download ---
    _log.info("=" * 60)
    _log.info("STEP 1: Downloading SoundCloud likes")
    _log.info("=" * 60)

    try:
        tracks = download_soundcloud_likes(
            likes_url, output_dir=out / "downloads", max_tracks=max_tracks,
            cookies_from_browser=cookies_from_browser,
        )
        result.tracks = tracks
        result.tracks_found = len(tracks)
        result.tracks_downloaded = sum(1 for t in tracks if t.downloaded)
    except Exception as e:
        result.errors.append(f"Download step failed: {e}")
        _log.error(f"Download step failed: {e}")
        return result

    # --- Step 2: Stem separation ---
    stem_dirs: dict[str, Optional[Path]] = {}

    if separate:
        _log.info("=" * 60)
        _log.info("STEP 2: Separating stems (HT-Demucs)")
        _log.info("=" * 60)

        for track in tracks:
            if not track.downloaded:
                continue
            try:
                stem_dir = separate_stems(
                    track.filepath, output_dir=out / "stems",
                )
                stem_dirs[track.title] = stem_dir
            except Exception as e:
                result.errors.append(f"Stem separation failed ({track.title}): {e}")
                _log.warning(f"Stem separation failed: {track.title} — {e}")
                stem_dirs[track.title] = None

    # --- Step 3: Analyze ---
    _log.info("=" * 60)
    _log.info("STEP 3: Analyzing features per stem")
    _log.info("=" * 60)

    analyses: list[TrackAnalysis] = []

    for track in tracks:
        if not track.downloaded:
            continue
        try:
            stem_dir = stem_dirs.get(track.title)
            analysis = analyze_track(
                audio_path=track.filepath,
                stem_dir=str(stem_dir) if stem_dir else None,
                track_name=track.title,
                source_url=track.url,
                extract_embeddings=extract_embeddings,
            )
            analyses.append(analysis)
            export_analysis(analysis, output_dir=out)
        except Exception as e:
            result.errors.append(f"Analysis failed ({track.title}): {e}")
            _log.warning(f"Analysis failed: {track.title} — {e}")

    result.analyses = analyses
    result.tracks_analyzed = len(analyses)

    # --- Step 4: Serum blueprints ---
    if generate_blueprints and analyses:
        _log.info("=" * 60)
        _log.info("STEP 4: Generating Serum 2 blueprints")
        _log.info("=" * 60)

        for analysis in analyses:
            try:
                bps = generate_blueprints_from_analysis(
                    stems=analysis.stems,
                    track_name=analysis.track_name,
                    bpm=analysis.overall_bpm,
                )
                result.blueprints[analysis.track_name] = bps
                export_all_blueprints(bps, output_dir=out / "serum_blueprints")
            except Exception as e:
                result.errors.append(f"Blueprint generation failed ({analysis.track_name}): {e}")

    # --- Step 5: Build prototypes ---
    if analyses:
        _log.info("=" * 60)
        _log.info("STEP 5: Building taste prototypes")
        _log.info("=" * 60)

        try:
            profile = build_prototypes(analyses)
            proto_path = export_prototypes(profile, output_dir=out)
            result.prototype_path = str(proto_path)
        except Exception as e:
            result.errors.append(f"Prototype building failed: {e}")

        # --- Taste report ---
        try:
            profile = build_prototypes(analyses)
            report_path = export_taste_report(analyses, profile, output_dir=out)
            result.report_path = str(report_path)
        except Exception as e:
            result.errors.append(f"Report generation failed: {e}")

    # --- Summary ---
    _log.info("=" * 60)
    _log.info(f"Pipeline complete: {result.tracks_analyzed}/{result.tracks_found} "
              f"tracks analyzed, {len(result.errors)} errors")
    _log.info("=" * 60)

    # Export pipeline result
    result_path = out / "pipeline_result.json"
    result_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# LOCAL FILE ANALYSIS — for pre-existing audio files
# ═══════════════════════════════════════════════════════════════════════════

def analyze_local_files(audio_dir: str,
                        separate: bool = True,
                        generate_blueprints: bool = True,
                        output_dir: Optional[Path] = None) -> PipelineResult:
    """
    Run the analysis pipeline on local audio files (skip download step).

    Args:
        audio_dir: Directory containing audio files (WAV, FLAC, MP3)
        separate: Whether to run stem separation
        generate_blueprints: Whether to generate Serum 2 blueprints
        output_dir: Override output directory

    Returns:
        PipelineResult
    """
    from engine.dubstep_taste_analyzer import (
        analyze_track,
        build_prototypes,
        export_analysis,
        export_prototypes,
        export_taste_report,
    )
    from engine.serum_blueprint import (
        export_all_blueprints,
        generate_blueprints_from_analysis,
    )

    audio_path = Path(audio_dir)
    out = output_dir or OUTPUT_ROOT
    out.mkdir(parents=True, exist_ok=True)

    result = PipelineResult(source_url=f"local:{audio_dir}")

    # Find audio files
    extensions = {".wav", ".flac", ".mp3", ".ogg", ".opus", ".m4a", ".aiff"}
    audio_files = sorted(
        f for f in audio_path.iterdir()
        if f.suffix.lower() in extensions
    )

    result.tracks_found = len(audio_files)
    _log.info(f"Found {len(audio_files)} audio files in {audio_dir}")

    # Build tracks
    tracks = []
    for f in audio_files:
        tracks.append(DownloadedTrack(
            title=f.stem,
            filepath=str(f),
            downloaded=True,
        ))
    result.tracks = tracks
    result.tracks_downloaded = len(tracks)

    # Stem separation
    stem_dirs: dict[str, Optional[Path]] = {}
    if separate:
        for track in tracks:
            try:
                stem_dir = separate_stems(track.filepath, output_dir=out / "stems")
                stem_dirs[track.title] = stem_dir
            except Exception as e:
                result.errors.append(f"Stem separation failed ({track.title}): {e}")
                stem_dirs[track.title] = None

    # Analysis
    analyses = []
    for track in tracks:
        try:
            stem_dir = stem_dirs.get(track.title)
            analysis = analyze_track(
                audio_path=track.filepath,
                stem_dir=str(stem_dir) if stem_dir else None,
                track_name=track.title,
            )
            analyses.append(analysis)
            export_analysis(analysis, output_dir=out)
        except Exception as e:
            result.errors.append(f"Analysis failed ({track.title}): {e}")

    result.analyses = analyses
    result.tracks_analyzed = len(analyses)

    # Blueprints
    if generate_blueprints and analyses:
        for analysis in analyses:
            try:
                bps = generate_blueprints_from_analysis(
                    stems=analysis.stems,
                    track_name=analysis.track_name,
                    bpm=analysis.overall_bpm,
                )
                result.blueprints[analysis.track_name] = bps
                export_all_blueprints(bps, output_dir=out / "serum_blueprints")
            except Exception as e:
                result.errors.append(f"Blueprint failed ({analysis.track_name}): {e}")

    # Prototypes + report
    if analyses:
        try:
            profile = build_prototypes(analyses)
            proto_path = export_prototypes(profile, output_dir=out)
            result.prototype_path = str(proto_path)
            report_path = export_taste_report(analyses, profile, output_dir=out)
            result.report_path = str(report_path)
        except Exception as e:
            result.errors.append(f"Prototype/report failed: {e}")

    result_path = out / "pipeline_result.json"
    result_path.write_text(json.dumps(result.to_dict(), indent=2), encoding="utf-8")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# FEEDBACK LOOP — thumbs up/down for taste refinement
# ═══════════════════════════════════════════════════════════════════════════

def apply_feedback(analyses_path: str,
                   track_name: str,
                   thumbs: str) -> None:
    """
    Apply thumbs up/down feedback to a track analysis.

    This updates the stored analysis JSON so prototype rebuilding
    can filter by user preference.

    Args:
        analyses_path: Directory containing analysis JSONs
        track_name: Name of the track to update
        thumbs: "up" or "down"
    """
    if thumbs not in ("up", "down"):
        raise ValueError(f"thumbs must be 'up' or 'down', got '{thumbs}'")

    analyses_dir = Path(analyses_path)
    safe_name = "".join(c if c.isalnum() or c in "-_ " else "_" for c in track_name)

    for json_file in analyses_dir.glob("*_analysis.json"):
        if safe_name.lower() in json_file.stem.lower():
            data = json.loads(json_file.read_text(encoding="utf-8"))
            data["thumbs"] = thumbs
            json_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
            _log.info(f"Applied thumbs {thumbs} to: {track_name}")
            return

    _log.warning(f"Track not found for feedback: {track_name}")


# ═══════════════════════════════════════════════════════════════════════════
# MULTI-SOURCE PIPELINE — combine multiple SoundCloud URLs
# ═══════════════════════════════════════════════════════════════════════════

def run_multi_pipeline(
    source_urls: list[str],
    max_tracks: int = 20,
    separate: bool = True,
    generate_blueprints: bool = True,
    extract_embeddings: bool = False,
    cookies_from_browser: Optional[str] = None,
    output_dir: Optional[Path] = None,
) -> dict:
    """
    Run the taste pipeline against multiple SoundCloud source URLs and
    merge all analyses into a single combined taste profile.

    Useful for combining:
        - Your own likes  (soundcloud.com/you/likes  — needs cookies)
        - An artist page  (soundcloud.com/substandardbassmusic)
        - A playlist / set

    Args:
        source_urls: List of SoundCloud URLs to process.
        max_tracks: Max tracks per source.
        separate: Run HT-Demucs stem separation.
        generate_blueprints: Generate Serum 2 blueprints.
        extract_embeddings: Compute OpenL3 embeddings (slow).
        cookies_from_browser: Browser for cookie auth (needed for /you/likes).
        output_dir: Override output root.

    Returns:
        dict with keys:
            ``results``        — {url: PipelineResult} per source
            ``merged_report``  — path to combined taste_report.md
            ``total_found``    — total tracks found across all sources
            ``total_downloaded``
            ``total_analyzed``
            ``errors``         — all errors across all sources
    """
    from engine.dubstep_taste_analyzer import (
        build_prototypes,
        export_prototypes,
        export_taste_report,
    )

    out = output_dir or OUTPUT_ROOT
    out.mkdir(parents=True, exist_ok=True)

    results: dict[str, PipelineResult] = {}
    all_analyses = []
    all_errors: list[str] = []

    for url in source_urls:
        url = url.strip()
        if not url:
            continue
        _log.info("=" * 60)
        _log.info(f"SOURCE: {url}")
        _log.info("=" * 60)

        # Per-source sub-directory so downloads don't collide
        from urllib.parse import urlparse
        slug = urlparse(url).path.strip("/").replace("/", "_")[:40]
        src_out = out / "sources" / slug

        result = run_pipeline(
            likes_url=url,
            max_tracks=max_tracks,
            separate=separate,
            generate_blueprints=generate_blueprints,
            extract_embeddings=extract_embeddings,
            cookies_from_browser=cookies_from_browser,
            output_dir=src_out,
        )
        results[url] = result
        all_analyses.extend(result.analyses)
        all_errors.extend(result.errors)

    # Merged taste profile across all sources
    merged_report_path = ""
    if all_analyses:
        _log.info("=" * 60)
        _log.info(f"MERGED PROFILE: {len(all_analyses)} total tracks")
        _log.info("=" * 60)
        try:
            merged_profile = build_prototypes(all_analyses)
            export_prototypes(merged_profile, output_dir=out)
            report_path = export_taste_report(all_analyses, merged_profile, output_dir=out)
            merged_report_path = str(report_path)
        except Exception as e:
            all_errors.append(f"Merged profile build failed: {e}")
            _log.error(f"Merged profile build failed: {e}")

    totals = {
        "results": results,
        "merged_report": merged_report_path,
        "total_found": sum(r.tracks_found for r in results.values()),
        "total_downloaded": sum(r.tracks_downloaded for r in results.values()),
        "total_analyzed": sum(r.tracks_analyzed for r in results.values()),
        "errors": all_errors,
    }

    _log.info(
        f"Multi-pipeline complete: {totals['total_analyzed']} analyzed "
        f"across {len(results)} sources, {len(all_errors)} errors"
    )

    # Persist summary
    summary_path = out / "multi_pipeline_result.json"
    summary_data = {
        "sources": list(results.keys()),
        "merged_report": merged_report_path,
        "total_found": totals["total_found"],
        "total_downloaded": totals["total_downloaded"],
        "total_analyzed": totals["total_analyzed"],
        "errors": all_errors,
        "per_source": {
            url: r.to_dict() for url, r in results.items()
        },
    }
    summary_path.write_text(json.dumps(summary_data, indent=2), encoding="utf-8")
    _log.info(f"Summary saved: {summary_path}")

    return totals
