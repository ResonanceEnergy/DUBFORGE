"""Full crash test with longer wait — check Serum 2 loads."""
import subprocess, time, os

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")

ALS = r"output\ableton\_test_vst3_fix.als"
als = os.path.abspath(ALS)

# Kill existing
os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
time.sleep(3)

# Clear crash state
for f in ("CrashDetection.cfg", "CrashRecoveryInfo.cfg"):
    p = os.path.join(PREFS, f)
    try:
        os.remove(p)
    except OSError:
        pass

log_start = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0

print(f"Launching: {os.path.basename(als)}")
proc = subprocess.Popen([ABLETON, als])
print(f"PID: {proc.pid}, waiting 45s for full load...")
time.sleep(45)

with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
    f.seek(log_start)
    new_log = f.read()

# Check crash
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

# Print relevant lines
keywords = ["document", "plugin", "vst", "serum", "loaded", "error",
            "crash", "fatal", "exception", "invalid", "uuid", "exchange",
            "Loading command"]
print("\n--- Relevant log lines ---")
for line in new_log.strip().split("\n"):
    line = line.strip()
    if any(k in line.lower() for k in keywords):
        print(f"  {line[:200]}")

os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
print("\nDone.")
