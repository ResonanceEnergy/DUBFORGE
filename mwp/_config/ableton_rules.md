# DUBFORGE — AbletonOSC Cardinal Rules
> Layer 3 stable config. ALL phases must follow these rules without exception.

---

## Cardinal Rules (MWP v6.0.0)

1. **ALL phases use AbletonOSC** — No numpy DSP pipeline. No offline render. Ableton handles everything.
2. **Ableton Live IS the engine** — Every audio decision (EQ, comp, FX, bounce) happens in Ableton.
3. **AbletonOSC CANNOT trigger export** — Use osascript `key code 15 using {command down, shift down}` (Cmd+Shift+R) + poll.
4. **osascript app name**: `"Ableton Live 12 Suite"` — Exact string. Case-sensitive.
5. **Data flow**: `SongMandate → ArrangedTrack → MixedTrack → str(out_path)`

---

## AbletonBridge Connection

```python
from engine.ableton_bridge import AbletonBridge

DEFAULT_HOST = "127.0.0.1"
SEND_PORT    = 11000
RECV_PORT    = 11001

bridge = AbletonBridge(host=DEFAULT_HOST, send_port=SEND_PORT, recv_port=RECV_PORT)
if not bridge.connect():
    raise RuntimeError("Ableton Live not running or AbletonOSC not active")
```

**Pre-flight**: Ableton must be running. AbletonOSC M4L device on Master track.

---

## Available OSC Commands

| Category | Command | Args |
|----------|---------|------|
| Transport | `set_tempo(bpm)` | float |
| Transport | `start_playback()` / `stop_playback()` | — |
| Transport | `set_loop(start_beat, end_beat)` | float, float |
| Track | `create_audio_track(index)` → track_idx | int |
| Track | `set_track_name(idx, name)` | int, str |
| Track | `set_track_volume(idx, vol)` | int, float 0–1 |
| Track | `set_track_panning(idx, pan)` | int, float -1..1 |
| Track | `set_track_mute(idx, muted)` | int, bool |
| Device | `get_device_parameters(track, device)` | int, int |
| Device | `set_device_parameter(track, device, param, val)` | int, int, int, float |
| Clip | `create_clip(track, slot, length)` | int, int, float |
| Clip | `load_audio_clip(track, slot, path)` | int, int, str |
| Return | `set_return_volume(ret_idx, vol)` | int, float |
| Return | `set_track_send(track, send_idx, vol)` | int, int, float |
| Master | `set_master_volume(vol)` | float 0–1 |

---

## Export Trigger (MANDATORY PATTERN)

AbletonOSC cannot trigger "Export Audio/Video". Use osascript:

```python
import subprocess, time, pathlib

def _trigger_export_and_wait(output_path: str, timeout_s: float = 180.0) -> str:
    """Trigger Ableton export via Cmd+Shift+R then Enter, poll until file stabilises."""
    script = (
        'tell application "Ableton Live 12 Suite" to activate\n'
        'delay 0.5\n'
        'tell application "System Events"\n'
        '    key code 15 using {command down, shift down}\n'  # Cmd+Shift+R
        '    delay 2.0\n'
        '    key code 36\n'                                    # Enter
        'end tell\n'
    )
    subprocess.run(["osascript", "-e", script], capture_output=True)
    
    deadline = time.time() + timeout_s
    last_size = -1
    while time.time() < deadline:
        time.sleep(2.0)
        p = pathlib.Path(output_path)
        if p.exists():
            sz = p.stat().st_size
            if sz > 0 and sz == last_size:
                return output_path   # file stable = export complete
            last_size = sz
    return ""   # timed out
```

**Timeout guidance:**
- Phase 2 (arrangement bounce): 180s
- Phase 3 (mix bounce): 180s
- Phase 4 (master bounce): 300s

---

## Sidechain Limitation

`AbletonBridge.set_sidechain()` does not exist in v6.0.0. Wrap any sidechain
call in `try/except` and print a manual instruction:

```python
try:
    bridge.set_sidechain(compressor_track, kick_track)
except Exception:
    print("⚠ Sidechain config: set up kick→sub sidechain compressor manually in Ableton")
```

---

## Accessibility Pre-flight (macOS)

osascript requires Accessibility permission: **System Settings → Privacy → Accessibility → Terminal ✓**
Without this, `key code 15` does nothing silently.
