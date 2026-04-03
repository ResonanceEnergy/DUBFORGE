"""Test V12 roundtrip (known-good) vs our generated ALS with longer wait."""
import subprocess, time, os

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")


def test_als(label, als_path, wait_secs=35):
    als_path = os.path.abspath(als_path)
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"{'='*60}")

    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
    time.sleep(3)

    for f in ("CrashDetection.cfg", "CrashRecoveryInfo.cfg"):
        p = os.path.join(PREFS, f)
        try:
            os.remove(p)
        except OSError:
            pass

    log_start = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0
    proc = subprocess.Popen([ABLETON, als_path])
    print(f"PID: {proc.pid}, waiting {wait_secs}s...")
    time.sleep(wait_secs)

    with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
        f.seek(log_start)
        new_log = f.read()

    crashed = False
    for kw in ["Fatal Error", "EXCEPTION_ACCESS_VIOLATION", "Unhandled exception",
               "Message Box: Live unexpectedly quit"]:
        if kw in new_log:
            crashed = True

    poll = proc.poll()
    status = "LOADS OK" if (not crashed and poll is None) else ("CRASHED" if crashed else f"EXITED({poll})")
    print(f"RESULT: {status}")

    # Show key log lines
    for line in new_log.strip().split("\n"):
        l = line.strip()
        if any(k in l.lower() for k in ["document", "loaded", "exchange", "error", "fatal", "exception", "vst3", "serum"]):
            print(f"  {l[:180]}")

    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
    time.sleep(2)
    return crashed


c1 = test_als("V12 roundtrip (known-good)", r"output\ableton\test_bisect\v12_roundtrip.als")
c2 = test_als("Apology V4", r"output\ableton\Apology_V4.als")
c3 = test_als("Generated: no VST3", r"output\ableton\_test_no_serum.als")

print(f"\nSUMMARY: V12={'CRASH' if c1 else 'OK'}, Apology={'CRASH' if c2 else 'OK'}, Generated={'CRASH' if c3 else 'OK'}")
