"""Single-file crash test for Fix 9 with Serum 2 — check log thoroughly."""
import subprocess, time, os, glob

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")
LOG = os.path.join(PREFS, "Log.txt")
WAIT = 45

# Clean crash files
for f in ["CrashDetection.cfg", "CrashRecoveryInfo.cfg"]:
    p = os.path.join(PREFS, f)
    if os.path.exists(p):
        os.remove(p)
for d in ["Crash", "BaseFiles"]:
    dp = os.path.join(PREFS, d)
    if os.path.isdir(dp):
        for ff in glob.glob(os.path.join(dp, "*")):
            os.remove(ff)

# Record log size before launch
log_size_before = os.path.getsize(LOG) if os.path.exists(LOG) else 0

als = os.path.abspath("_test_fix9_serum.als")
print(f"Testing: {als}")
print(f"Wait: {WAIT}s")

proc = subprocess.Popen([ABLETON, als])
time.sleep(WAIT)

poll = proc.poll()
if poll is not None:
    print(f"PROCESS EXITED (code {poll})")
else:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
    print("Process terminated by us (clean)")

# Read only the NEW portion of the log
with open(LOG, "r", encoding="utf-8", errors="replace") as f:
    f.seek(log_size_before)
    new_log = f.read()

print(f"\n--- New log entries ({len(new_log)} chars) ---")

# Check for crash indicators
crash = False
for kw in ["EXCEPTION_ACCESS_VIOLATION", "invalid uuid string", "unhandled exception"]:
    if kw in new_log:
        print(f"CRASH INDICATOR: {kw}")
        crash = True

if not crash:
    print("No crash indicators found")

# Check for VST3 loading
serum_lines = [l.strip() for l in new_log.split("\n")
               if "Serum" in l or "VST3: Restored" in l or "VST3: plugin processor" in l]
print(f"\nVST3 lines ({len(serum_lines)}):")
for l in serum_lines:
    print(f"  {l}")

# Check for document load
if "Loading command-line document: done" in new_log:
    print("\nDocument loaded successfully")

# Print last 20 interesting lines
print("\n--- Last 20 log lines ---")
lines = new_log.strip().split("\n")
for l in lines[-20:]:
    print(l.strip())
