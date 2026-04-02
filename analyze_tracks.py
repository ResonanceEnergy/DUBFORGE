"""Deep analysis of DUBFORGE rendered tracks vs Subtronics reference spec."""
import glob
import wave
from pathlib import Path

import numpy as np
from numpy.fft import rfft, rfftfreq

SAMPLE_RATE = 48000

# ═══════════════════════════════════════════════════════════════════════════
# SUBTRONICS REFERENCE SPEC (from professional analysis)
# ═══════════════════════════════════════════════════════════════════════════
SUBTRONICS_REF = {
    "bpm_range": (140, 155),
    "duration_range": (180, 300),     # 3-5 minutes
    "lufs_range": (-8, -5),           # -8 to -5 LUFS (loud dubstep masters)
    "peak_db": -0.3,                  # true peak ceiling
    "sections": {
        "intro": (8, 16),             # 8-16 bars
        "buildup1": (8, 16),
        "drop1": (16, 32),            # DROPS ARE 16-32 BARS (the main event)
        "breakdown": (8, 16),
        "buildup2": (4, 8),
        "drop2": (16, 32),            # Usually wilder than drop1
        "outro": (8, 16),
    },
    "spectrum_balance": {
        "sub_20_80": (15, 30),        # Strong sub bass foundation
        "low_80_300": (15, 25),       # Kick body + bass body
        "mid_300_3k": (25, 40),       # Bass harmonics, leads, vocals
        "high_3k_10k": (10, 20),      # Presence, percussion
        "air_10k_plus": (3, 10),      # Cymbals, breath, shimmer
    },
    "stereo_width": (0.3, 0.7),       # Side/Mid ratio (bass mono, highs wide)
    "dynamic_range_db": (3, 8),       # RMS variance in 100ms blocks
    "key_elements": [
        "DISTINCT intro (sparse, mood-setting)",
        "BUILD with riser, drum roll, filter sweep → tension",
        "DROP: massive bass drop with clear rhythm, sidechain pumping",
        "BASS: multiple bass sounds that MODULATE (filter sweeps, LFO motion)",
        "DRUMS: punchy kick (60-80Hz fundamental), snappy snare, crisp hats",
        "ARRANGEMENT: clear contrast between sections (energy, density)",
        "TRANSITION FX: risers, downlifters, impacts, sweeps between sections",
        "SIDECHAIN: kick ducks bass and pad (pumping effect)",
        "STEREO: sub/kick MONO center, mids moderate, highs WIDE",
        "FILLS: drum fills before drops, stutters, glitch edits",
        "SILENCE/SPACE: brief silence before drop hit for impact",
        "VARIATION: drop2 different from drop1 (new bass, higher energy)",
    ],
}


def analyze_wav(filepath):
    """Full analysis of a WAV file."""
    w = wave.open(filepath, "rb")
    sr = w.getframerate()
    ch = w.getnchannels()
    n = w.getnframes()
    dur = n / sr
    raw = w.readframes(n)
    w.close()

    samples = np.frombuffer(raw, dtype=np.int16).astype(np.float64) / 32768.0
    if ch == 2:
        L = samples[0::2]
        R = samples[1::2]
        mono = (L + R) / 2.0
    else:
        L = R = mono = samples

    result = {"file": filepath, "duration": dur, "channels": ch, "sample_rate": sr}

    # Peak / RMS
    peak = np.max(np.abs(samples))
    rms = np.sqrt(np.mean(mono**2))
    result["peak_db"] = 20 * np.log10(max(peak, 1e-10))
    result["rms_db"] = 20 * np.log10(max(rms, 1e-10))

    # Estimated LUFS (simplified K-weighted)
    result["est_lufs"] = result["rms_db"] - 0.7  # rough approximation

    # Spectrum analysis (use drop section if long enough, else whole track)
    if dur > 60:
        # Analyze roughly where the first drop would be (30-50% in)
        drop_start = int(n * 0.3)
        drop_end = int(n * 0.5)
        analysis_seg = mono[drop_start:drop_end]
    else:
        analysis_seg = mono

    fft_data = np.abs(rfft(analysis_seg))
    freqs = rfftfreq(len(analysis_seg), 1 / sr)

    sub = np.mean(fft_data[(freqs >= 20) & (freqs < 80)])
    low = np.mean(fft_data[(freqs >= 80) & (freqs < 300)])
    mid = np.mean(fft_data[(freqs >= 300) & (freqs < 3000)])
    high = np.mean(fft_data[(freqs >= 3000) & (freqs < 10000)])
    air = np.mean(fft_data[(freqs >= 10000)])
    total = sub + low + mid + high + air

    result["spectrum"] = {
        "sub_pct": sub / total * 100,
        "low_pct": low / total * 100,
        "mid_pct": mid / total * 100,
        "high_pct": high / total * 100,
        "air_pct": air / total * 100,
    }

    # Dynamic range (100ms blocks)
    block_sz = int(sr * 0.1)
    num_blocks = len(mono) // block_sz
    if num_blocks > 2:
        rms_blocks = []
        for i in range(num_blocks):
            block = mono[i * block_sz : (i + 1) * block_sz]
            block_rms = np.sqrt(np.mean(block**2))
            rms_blocks.append(20 * np.log10(max(block_rms, 1e-10)))
        result["dynamic_range_db"] = max(rms_blocks) - np.median(rms_blocks)
        result["quietest_block_db"] = min(rms_blocks)
        result["loudest_block_db"] = max(rms_blocks)

        # Check for silence gaps (blocks below -60 dB)
        silence_blocks = sum(1 for r in rms_blocks if r < -60)
        result["silence_blocks"] = silence_blocks
        result["silence_pct"] = silence_blocks / num_blocks * 100
    else:
        result["dynamic_range_db"] = 0

    # Stereo width
    if ch == 2:
        mid_sig = (L + R) / 2
        side_sig = (L - R) / 2
        mid_rms = np.sqrt(np.mean(mid_sig**2))
        side_rms = np.sqrt(np.mean(side_sig**2))
        result["stereo_width"] = side_rms / max(mid_rms, 1e-10)
    else:
        result["stereo_width"] = 0

    # Sidechain detection: look for periodic volume dips in the drop region
    if dur > 30 and num_blocks > 10:
        drop_blocks = rms_blocks[int(num_blocks * 0.3):int(num_blocks * 0.6)]
        if len(drop_blocks) > 4:
            diffs = np.diff(drop_blocks)
            # Count rapid dips (>3 dB drop followed by recovery)
            sidechain_dips = 0
            for j in range(len(diffs) - 1):
                if diffs[j] < -3 and diffs[j + 1] > 2:
                    sidechain_dips += 1
            result["sidechain_pumps_detected"] = sidechain_dips

    # Energy curve: split into 10 segments and measure RMS of each
    seg_size = len(mono) // 10
    energy_curve = []
    for i in range(10):
        seg = mono[i * seg_size : (i + 1) * seg_size]
        seg_rms = np.sqrt(np.mean(seg**2))
        energy_curve.append(20 * np.log10(max(seg_rms, 1e-10)))
    result["energy_curve"] = energy_curve

    # Check if sections have contrast
    if len(energy_curve) >= 7:
        intro_energy = energy_curve[0]
        drop_energy = max(energy_curve[2:5])
        breakdown_energy = min(energy_curve[4:7])
        result["intro_to_drop_db"] = drop_energy - intro_energy
        result["drop_to_breakdown_db"] = drop_energy - breakdown_energy

    return result


def compare_to_subtronics(analysis):
    """Compare analysis results against Subtronics reference spec."""
    issues = []
    ref = SUBTRONICS_REF

    # Duration
    dur = analysis["duration"]
    if dur < ref["duration_range"][0]:
        issues.append(f"TOO SHORT: {dur:.0f}s vs target {ref['duration_range'][0]}-{ref['duration_range'][1]}s (3-5 min). "
                      f"Subtronics tracks are NEVER under 3 minutes.")
    elif dur > ref["duration_range"][1]:
        issues.append(f"TOO LONG: {dur:.0f}s")

    # Loudness
    lufs = analysis.get("est_lufs", -20)
    if lufs < ref["lufs_range"][0]:
        issues.append(f"TOO QUIET: ~{lufs:.1f} LUFS vs target {ref['lufs_range'][0]} to {ref['lufs_range'][1]} LUFS")

    # Peak
    peak = analysis["peak_db"]
    if peak < -2.0:
        issues.append(f"LOW PEAK: {peak:.1f} dB — not using full headroom (target: {ref['peak_db']} dB)")

    # Spectrum balance
    spec = analysis["spectrum"]
    for band, key, ref_range in [
        ("Sub 20-80Hz", "sub_pct", ref["spectrum_balance"]["sub_20_80"]),
        ("Low 80-300Hz", "low_pct", ref["spectrum_balance"]["low_80_300"]),
        ("Mid 300-3kHz", "mid_pct", ref["spectrum_balance"]["mid_300_3k"]),
        ("High 3-10kHz", "high_pct", ref["spectrum_balance"]["high_3k_10k"]),
        ("Air 10k+", "air_pct", ref["spectrum_balance"]["air_10k_plus"]),
    ]:
        val = spec[key]
        if val < ref_range[0]:
            issues.append(f"WEAK {band}: {val:.0f}% (target: {ref_range[0]}-{ref_range[1]}%)")
        elif val > ref_range[1]:
            issues.append(f"EXCESS {band}: {val:.0f}% (target: {ref_range[0]}-{ref_range[1]}%)")

    # Dynamic range
    dyn = analysis.get("dynamic_range_db", 0)
    if dyn < ref["dynamic_range_db"][0]:
        issues.append(f"NO DYNAMICS: {dyn:.1f} dB range — sounds flat/squashed (target: {ref['dynamic_range_db'][0]}-{ref['dynamic_range_db'][1]} dB)")
    elif dyn > ref["dynamic_range_db"][1]:
        issues.append(f"TOO DYNAMIC: {dyn:.1f} dB — inconsistent levels, weak drops")

    # Stereo width
    width = analysis.get("stereo_width", 0)
    if width < ref["stereo_width"][0]:
        issues.append(f"TOO NARROW: width={width:.3f} (target: {ref['stereo_width'][0]}-{ref['stereo_width'][1]})")
    elif width > ref["stereo_width"][1]:
        issues.append(f"TOO WIDE: width={width:.3f} — may cause phase issues on mono systems")

    # Section contrast
    intro_drop = analysis.get("intro_to_drop_db", 0)
    if intro_drop < 3:
        issues.append(f"NO INTRO→DROP CONTRAST: only {intro_drop:.1f} dB difference — "
                      "drops don't hit hard. Need 6-12 dB contrast.")
    drop_break = analysis.get("drop_to_breakdown_db", 0)
    if drop_break < 3:
        issues.append(f"NO DROP→BREAKDOWN CONTRAST: only {drop_break:.1f} dB — "
                      "no breathing room between drops.")

    # Silence
    silence = analysis.get("silence_pct", 0)
    if silence > 15:
        issues.append(f"TOO MUCH SILENCE: {silence:.0f}% of blocks below -60 dB — "
                      "indicates gaps or empty sections.")

    # Sidechain
    pumps = analysis.get("sidechain_pumps_detected", 0)
    if pumps < 3:
        issues.append(f"WEAK/NO SIDECHAIN: only {pumps} pump events detected in drop — "
                      "Subtronics uses aggressive sidechain compression for pumping bass.")

    return issues


def main():
    print("=" * 70)
    print("DUBFORGE vs SUBTRONICS — DEEP TRACK ANALYSIS")
    print("=" * 70)

    # Find all rendered tracks
    wav_files = sorted(glob.glob("output/*.wav"))
    # Exclude wavetables
    wav_files = [f for f in wav_files if "wavetable" not in f.lower()]

    if not wav_files:
        print("No rendered tracks found in output/")
        return

    all_issues = []

    for filepath in wav_files:
        print(f"\n{'─' * 70}")
        print(f"TRACK: {Path(filepath).name}")
        print(f"{'─' * 70}")

        analysis = analyze_wav(filepath)

        # Print stats
        print(f"  Duration:  {analysis['duration']:.0f}s ({int(analysis['duration']//60)}:{int(analysis['duration']%60):02d})")
        print(f"  Peak:      {analysis['peak_db']:.1f} dB")
        print(f"  RMS:       {analysis['rms_db']:.1f} dB")
        print(f"  Est LUFS:  {analysis.get('est_lufs', 0):.1f}")
        print(f"  Width:     {analysis.get('stereo_width', 0):.3f}")
        print(f"  Dynamics:  {analysis.get('dynamic_range_db', 0):.1f} dB range")

        spec = analysis["spectrum"]
        print(f"  Spectrum:  sub={spec['sub_pct']:.0f}% low={spec['low_pct']:.0f}% "
              f"mid={spec['mid_pct']:.0f}% high={spec['high_pct']:.0f}% air={spec['air_pct']:.0f}%")

        ec = analysis.get("energy_curve", [])
        if ec:
            labels = ["0-10%", "10-20%", "20-30%", "30-40%", "40-50%",
                       "50-60%", "60-70%", "70-80%", "80-90%", "90-100%"]
            print("  Energy curve (dB RMS):")
            max(ec)
            for i, (label, val) in enumerate(zip(labels, ec)):
                bar_len = max(0, int((val + 60) / 2))
                print(f"    {label}: {val:6.1f} dB {'█' * bar_len}")

        # Compare to Subtronics
        issues = compare_to_subtronics(analysis)
        if issues:
            print(f"\n  ISSUES vs SUBTRONICS ({len(issues)}):")
            for issue in issues:
                print(f"    ✗ {issue}")
        else:
            print("\n  ✓ Passes all Subtronics reference checks")

        all_issues.extend([(Path(filepath).name, i) for i in issues])

    # Now analyze the BACKEND code for structural issues
    print(f"\n\n{'=' * 70}")
    print("BACKEND CODE ANALYSIS — STRUCTURAL ISSUES")
    print(f"{'=' * 70}")

    backend_issues = analyze_backend()
    for issue in backend_issues:
        print(f"  ✗ {issue}")

    # Summary
    print(f"\n\n{'=' * 70}")
    print("SUMMARY — WHAT'S MISSING vs SUBTRONICS")
    print(f"{'=' * 70}")

    total_issues = len(all_issues) + len(backend_issues)
    print(f"\n  Total issues found: {total_issues}")
    print(f"  Track-level issues: {len(all_issues)}")
    print(f"  Backend issues:     {len(backend_issues)}")


def analyze_backend():
    """Analyze the forge.py and engine code for structural problems."""
    issues = []

    # Check forge.py arrangement
    try:
        with open("forge.py", "r") as f:
            forge_code = f.read()

        # Check bar counts for sections
        import re

        # Check if sections are too short
        re.findall(r'(\w+).*?(\d+)\s*(?:bars?|bar_count)', forge_code, re.IGNORECASE)

        # Check if sidechain is properly implemented
        if "sidechain" in forge_code:
            # Check if sidechain is applied to bass
            sc_calls = forge_code.count("sidechain(")
            if sc_calls < 3:
                issues.append(f"SIDECHAIN: Only {sc_calls} sidechain calls — bass + pad + atmosphere should all be sidechained")

        # Check gain staging
        gain_matches = re.findall(r'gain\s*[=:]\s*([\d.]+)', forge_code)
        if gain_matches:
            gains = [float(g) for g in gain_matches]
            if max(gains) > 1.0:
                issues.append(f"GAIN STAGING: Some gains exceed 1.0 ({max(gains):.2f}) — can cause digital clipping")

        # Check arrangement structure
        if "intro" in forge_code.lower():
            # Look for section bar counts
            section_bars = {}
            for match in re.finditer(r'"(intro|build|drop|break|outro).*?".*?bars?\s*[:=]\s*(\d+)', forge_code, re.IGNORECASE):
                section_bars[match.group(1)] = int(match.group(2))

        # Check if there's a silence/impact before drops
        if "silence" not in forge_code.lower() and "impact" not in forge_code.lower():
            if "gap" not in forge_code.lower():
                issues.append("NO IMPACT SILENCE: No silence/gap before drop hits. "
                              "Subtronics ALWAYS has 0.5-2 beat silence before the drop for maximum impact.")

        # Check if mix_into is accumulating correctly
        if "mix_into" in forge_code:
            # Check if there's any bus compression or limiting on submixes
            if "bus_comp" not in forge_code and "submix" not in forge_code:
                issues.append("NO BUS COMPRESSION: Signals are summed with mix_into() but no bus compression. "
                              "Professional tracks use bus compression on drum/bass/synth groups.")

        # Check arrangement section handling
        arrangement_sections = re.findall(r'section\s*==\s*["\'](\w+)["\']', forge_code)
        if not arrangement_sections:
            arrangement_sections = re.findall(r'["\'](\w+?)["\']\s*(?:in|==).*?arrangement', forge_code)

        # Check if sections change bass/drum patterns
        if forge_code.count("drop1") > 0 and forge_code.count("drop2") > 0:
            # Do drops use different base patterns?
            drop1_idx = forge_code.find("drop1")
            drop2_idx = forge_code.find("drop2")
            if drop1_idx > 0 and drop2_idx > 0:
                forge_code[drop1_idx:drop1_idx+500]
                drop2_section = forge_code[drop2_idx:drop2_idx+500]
                if "bass_idx" not in drop2_section and "bass_variation" not in drop2_section:
                    issues.append("DROP2 IS COPY OF DROP1: No bass variation between drops. "
                                  "Subtronics ALWAYS switches bass sound or pattern on drop 2.")

    except FileNotFoundError:
        issues.append("Could not read forge.py")

    # Check variation_engine DNA generation
    try:
        with open("engine/variation_engine.py", "r") as f:
            ve_code = f.read()

        # Check bar count assignments
        bar_matches = re.findall(r'bars?\s*[:=]\s*(\d+)', ve_code)
        if bar_matches:
            sum(int(b) for b in bar_matches[:10])

        # Check if arrangement has enough sections
        if "arrangement" in ve_code.lower():
            re.findall(r'arrangement\s*[:=]\s*\[([^\]]+)\]', ve_code)

    except FileNotFoundError:
        issues.append("Could not read variation_engine.py")

    # Check mastering chain
    try:
        with open("engine/mastering_chain.py", "r") as f:
            mc_code = f.read()

        # Check if limiter has lookahead
        if "lookahead" not in mc_code.lower():
            issues.append("LIMITER: No lookahead in limiter — causes transient distortion. "
                          "Professional limiters use 1-5ms lookahead.")

        # Check if there's proper EQ for dubstep
        if "sidechain" not in mc_code.lower():
            pass  # Sidechain at mixer level, not mastering

    except FileNotFoundError:
        issues.append("Could not read mastering_chain.py")

    # Check drum synthesis
    try:
        with open("engine/drum_generator.py", "r") as f:
            dg_code = f.read()

        # Check if kick has enough sub content
        if "noise" not in dg_code[:5000]:
            issues.append("DRUMS: Kick may lack transient noise burst (essential for punch)")

        # Check if there are drum fills
        if "fill" not in dg_code.lower():
            issues.append("DRUMS: No drum fill generation — fills are essential before drops")

        # Check if hat patterns have variation
        if "velocity" not in dg_code.lower() and "accent" not in dg_code.lower():
            issues.append("DRUMS: No velocity/accent variation in hat patterns — sounds robotic")

    except FileNotFoundError:
        issues.append("Could not read drum_generator.py")

    # Read forge.py more carefully for arrangement issues
    try:
        with open("forge.py", "r") as f:
            forge_lines = f.readlines()

        # Find the arrangement/section handling
        in_arrange = False
        for i, line in enumerate(forge_lines):
            if "Arranging" in line or "section" in line.lower():
                in_arrange = True
            if in_arrange and ("intro" in line.lower() or "drop" in line.lower()
                               or "build" in line.lower() or "break" in line.lower()):
                pass  # counting

        # Check total bar count
        bar_count_match = re.search(r'total_bars\s*=\s*(\d+)', forge_code)
        if not bar_count_match:
            bar_count_match = re.search(r'bars\s*[:=]\s*(\d+)', forge_code)

        # Check if render uses lists (inefficient) vs numpy arrays
        list_ops = forge_code.count("[0.0] *")
        if list_ops > 5:
            issues.append(f"PERFORMANCE: {list_ops} uses of '[0.0] * N' list allocation in forge.py — "
                          "Python lists are 50-100x slower than numpy arrays for audio math.")

        # Check if write function uses 16-bit
        if "int16" in forge_code or "32767" in forge_code or "32768" in forge_code:
            issues.append("FORMAT: Output is 16-bit WAV. Professional dubstep uses 24-bit or 32-bit float WAV. "
                          "16-bit has only 96 dB dynamic range.")

        # Check write function for sample rate
        if "44100" in forge_code and "48000" not in forge_code:
            issues.append("SAMPLE RATE: Only 44100 Hz. Professional dubstep is mastered at 48000 Hz "
                          "(needed for streaming platforms and better anti-aliasing).")

    except Exception:
        pass

    return issues


if __name__ == "__main__":
    main()
