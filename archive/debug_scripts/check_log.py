"""Check Ableton log for plugin loading details after the test."""
import time, os

LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
log_start = max(0, os.path.getsize(LOG_PATH) - 20000)

time.sleep(5)

with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
    f.seek(log_start)
    new_log = f.read()

keywords = ["document", "plugin", "vst", "serum", "loaded", "error",
            "crash", "fatal", "exception", "invalid", "uuid", "exchange"]
for line in new_log.strip().split("\n"):
    line = line.strip()
    if any(k in line.lower() for k in keywords):
        print(line[:200])

os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
