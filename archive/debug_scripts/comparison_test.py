"""Test both ALS files: with and without Serum 2."""
import subprocess, time, os

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")


def test_als(label, als_path, wait_secs=35):
    als_path = os.path.abspath(als_path)
    print(f"\n{'='*60}")
    print(f"TEST: {label}")
    print(f"File: {os.path.basename(als_path)}")
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
               "Message Box: Live unexpectedly quit", "invalid uuid"]:
        if kw in new_log:
            crashed = True
            print(f"  CRASH: found '{kw}'")

    poll = proc.poll()
    if not crashed and poll is None:
        print("RESULT: LOADS OK (still running)")
    elif not crashed and poll is not None:
        print(f"RESULT: EXITED (code {poll})")
    else:
        print("RESULT: CRASHED")

    keywords = ["document", "plugin", "vst", "serum", "loaded", "error",
                "crash", "fatal", "exception", "invalid", "uuid", "exchange",
                "loading command", "restored"]
    for line in new_log.strip().split("\n"):
        line = line.strip()
        if any(k in line.lower() for k in keywords):
            print(f"  LOG: {line[:200]}")

    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
    time.sleep(2)
    return crashed


# Test 1: Without Serum 2 (control)
c1 = test_als("No VST3 (control)", r"output\ableton\_test_no_serum.als")

# Test 2: With Serum 2
c2 = test_als("With Serum 2 VST3", r"output\ableton\_test_with_serum.als")

print(f"\n{'='*60}")
print(f"SUMMARY: Control={'CRASH' if c1 else 'OK'}, Serum2={'CRASH' if c2 else 'OK'}")
