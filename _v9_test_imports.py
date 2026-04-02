#!/usr/bin/env python3
"""Quick test to verify _v9_fast_init bypass works."""
import time
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
t0 = time.time()

print(f"[{time.time()-t0:.1f}s] Starting...", flush=True)

import _v9_fast_init  # noqa
print(f"[{time.time()-t0:.1f}s] Stub installed", flush=True)

try:
    from make_apology import build_apology_dna
    print(f"[{time.time()-t0:.1f}s] make_apology imported", flush=True)
except Exception as e:
    print(f"[{time.time()-t0:.1f}s] make_apology FAILED: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

try:
    from make_full_track import SAMPLE_RATE
    print(f"[{time.time()-t0:.1f}s] make_full_track imported (SR={SAMPLE_RATE})", flush=True)
except Exception as e:
    print(f"[{time.time()-t0:.1f}s] make_full_track FAILED: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)

dna = build_apology_dna()
print(f"[{time.time()-t0:.1f}s] DNA: {dna.title} | {dna.bpm} BPM | {dna.key}", flush=True)
print("SUCCESS", flush=True)
