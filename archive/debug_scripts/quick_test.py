"""Quick single-file Ableton crash test."""
import subprocess, time, os, sys

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
PREFS = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")

als = sys.argv[1] if len(sys.argv) > 1 else r"output\ableton\_test_mini.als"
als = os.path.abspath(als)

# Kill any existing
os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
time.sleep(2)

# Clear crash state
for f in ("CrashDetection.cfg", "CrashRecoveryInfo.cfg"):
    p = os.path.join(PREFS, f)
    try:
        os.remove(p)
    except OSError:
        pass
    print(f"  {f}: exists={os.path.exists(p)}")

# Get log position
log_start = os.path.getsize(LOG_PATH) if os.path.exists(LOG_PATH) else 0

print(f"Launching: {os.path.basename(als)}")
proc = subprocess.Popen([ABLETON, als])
print(f"PID: {proc.pid}, waiting 20s...")
time.sleep(20)

# Read new log
with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
    f.seek(log_start)
    new_log = f.read()

# Check
crashed = False
for kw in ["Fatal Error", "EXCEPTION_ACCESS_VIOLATION", "Unhandled exception",
           "Message Box: Live unexpectedly quit"]:
    if kw in new_log:
        crashed = True
        print(f"CRASH: found '{kw}'")

poll = proc.poll()
print(f"Process poll: {poll}")

if not crashed and poll is None:
    print(f"RESULT: {os.path.basename(als)} LOADS OK")
elif not crashed and poll is not None:
    print(f"RESULT: {os.path.basename(als)} PROCESS EXITED (code {poll})")
else:
    print(f"RESULT: {os.path.basename(als)} CRASHED")

# Print relevant log lines
for line in new_log.split("\n"):
    line = line.strip()
    if any(k in line for k in ["Fatal", "EXCEPTION", "Message Box", "Opening Log",
                                "Command-line", "document", "Error", "Loading",
                                "Loaded document"]):
        print(f"  LOG: {line[:150]}")

# Kill
os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
print("Done")
