"""Crash-test Fix 9 ALS files against Ableton Live."""
import subprocess, time, os, glob

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")
LOG = os.path.join(PREFS, "Log.txt")
CRASH_FILES = [
    os.path.join(PREFS, "CrashDetection.cfg"),
    os.path.join(PREFS, "CrashRecoveryInfo.cfg"),
]
CRASH_DIR = os.path.join(PREFS, "Crash")
BASE_DIR = os.path.join(PREFS, "BaseFiles")
WAIT = 40  # seconds

def clean():
    for f in CRASH_FILES:
        if os.path.exists(f):
            os.remove(f)
    for d in [CRASH_DIR, BASE_DIR]:
        if os.path.isdir(d):
            for ff in glob.glob(os.path.join(d, "*")):
                os.remove(ff)

def test_file(als_path, label):
    clean()
    abs_path = os.path.abspath(als_path)
    print(f"\n{'='*60}")
    print(f"Testing: {label}")
    print(f"File: {abs_path}")
    print(f"Wait: {WAIT}s")
    print(f"{'='*60}")

    proc = subprocess.Popen([ABLETON, abs_path])
    time.sleep(WAIT)

    # Check if process is still running
    poll = proc.poll()
    if poll is not None:
        print(f"RESULT: PROCESS EXITED (code {poll})")
    else:
        proc.terminate()
        try:
            proc.wait(timeout=10)
        except subprocess.TimeoutExpired:
            proc.kill()
        print("RESULT: Process terminated normally")

    # Check log for crash
    crashed = False
    if os.path.exists(LOG):
        with open(LOG, "r", encoding="utf-8", errors="replace") as f:
            log = f.read()
        # Check last 3000 chars for crash indicators
        tail = log[-3000:]
        if "EXCEPTION_ACCESS_VIOLATION" in tail:
            print("LOG: EXCEPTION_ACCESS_VIOLATION detected!")
            crashed = True
        elif "invalid uuid string" in tail:
            print("LOG: 'invalid uuid string' detected!")
            crashed = True
        elif "Crash" in tail and "CrashRecovery" not in tail:
            print("LOG: Other crash indicator found")
            crashed = True

        # Check for successful VST3 load
        if "VST3: Restored:" in tail:
            # Find all restored lines
            for line in tail.split("\n"):
                if "VST3: Restored:" in line:
                    print(f"LOG: {line.strip()}")

        if "Loading command-line document: done" in tail:
            print("LOG: Document loaded successfully")

    # Check crash detection file
    for cf in CRASH_FILES:
        if os.path.exists(cf):
            print(f"CRASH FILE EXISTS: {cf}")
            crashed = True

    if crashed:
        print(f">>> {label}: CRASH <<<")
    else:
        print(f">>> {label}: LOADS OK <<<")

    time.sleep(5)  # cooldown
    return not crashed


results = {}
for als, label in [
    ("_test_fix9_noserum.als", "Fix9 No VST3"),
    ("_test_fix9_serum.als", "Fix9 With Serum 2"),
]:
    results[label] = test_file(als, label)

print("\n" + "="*60)
print("SUMMARY")
print("="*60)
for label, ok in results.items():
    status = "LOADS OK" if ok else "CRASH"
    print(f"  {label}: {status}")
