"""Reliable Ableton crash tester — uses Log.txt to detect crashes.

The process-alive check DOESN'T WORK because Ableton's crash dialog keeps
the process running. Instead, we check the log for "Fatal Error" after loading.
"""
import subprocess
import time
import os
import sys

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
LOG_PATH = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences\Log.txt")
PREFS_DIR = os.path.expandvars(r"%APPDATA%\Ableton\Live 12.3.6\Preferences")
CRASH_DIR = os.path.join(PREFS_DIR, "Crash")
BASE_FILES_DIR = os.path.join(PREFS_DIR, "BaseFiles")
CRASH_DETECTION_CFG = os.path.join(PREFS_DIR, "CrashDetection.cfg")
CRASH_RECOVERY_CFG = os.path.join(PREFS_DIR, "CrashRecoveryInfo.cfg")


def kill_ableton():
    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
    os.system('taskkill /f /im "AbletonAudioCpl.exe" >nul 2>&1')
    time.sleep(3)


def clear_crash_recovery():
    """Remove ALL crash recovery state so Ableton doesn't show recovery dialog."""
    import shutil
    # Delete crash detection flag ("Running" state)
    for cfg in (CRASH_DETECTION_CFG, CRASH_RECOVERY_CFG):
        try:
            os.remove(cfg)
        except OSError:
            pass
    # Clear crash and base file directories
    for d in (CRASH_DIR, BASE_FILES_DIR):
        if os.path.exists(d):
            for item in os.listdir(d):
                path = os.path.join(d, item)
                if os.path.isdir(path):
                    shutil.rmtree(path, ignore_errors=True)
                else:
                    try:
                        os.remove(path)
                    except OSError:
                        pass


def get_log_size():
    try:
        return os.path.getsize(LOG_PATH)
    except OSError:
        return 0


def read_new_log(start_pos):
    """Read log content written after start_pos."""
    try:
        with open(LOG_PATH, "r", encoding="utf-8", errors="replace") as f:
            f.seek(start_pos)
            return f.read()
    except OSError:
        return ""


def test_file(als_path, wait_secs=15):
    """Launch Ableton with ALS file and check log for crash."""
    kill_ableton()
    clear_crash_recovery()
    time.sleep(1)

    log_start = get_log_size()
    print(f"\n  Testing: {os.path.basename(als_path)}")
    print(f"  Waiting {wait_secs}s...", end="", flush=True)

    proc = subprocess.Popen([ABLETON, os.path.abspath(als_path)])
    time.sleep(wait_secs)

    # Read new log entries
    new_log = read_new_log(log_start)

    # Check for crash indicators
    crashed = False
    crash_reason = ""
    if "Fatal Error" in new_log:
        crashed = True
        crash_reason = "Fatal Error in log"
    elif "EXCEPTION_ACCESS_VIOLATION" in new_log:
        crashed = True
        crash_reason = "ACCESS_VIOLATION in log"
    elif "Unhandled exception" in new_log:
        crashed = True
        crash_reason = "Unhandled exception in log"
    elif "Message Box: Live unexpectedly quit" in new_log:
        crashed = True
        crash_reason = "Recovery dialog triggered"

    # Also check if process actually terminated
    poll = proc.poll()
    if poll is not None and not crashed:
        # Process exited cleanly? Or crashed without log entry?
        crash_reason = f"Process exited (code {poll})"
        crashed = True

    if crashed:
        print(f" CRASH ({crash_reason})")
    else:
        print(" LOADS OK")

    # Print relevant log lines
    for line in new_log.split("\n"):
        line = line.strip()
        if any(kw in line for kw in ["Fatal", "EXCEPTION", "Message Box", "Opening Log",
                                      "Command-line", "document", "error:", "Error"]):
            print(f"    LOG: {line[:120]}")

    kill_ableton()
    return not crashed


def main():
    if not os.path.exists(ABLETON):
        print(f"ERROR: Ableton not found at {ABLETON}")
        sys.exit(1)

    base = os.path.dirname(__file__)

    # Files to test (simplest first for binary search)
    test_files = [
        (os.path.join(base, "output", "ableton", "_test_mini.als"), "Mini (2 tracks, 3 notes)"),
        (os.path.join(base, "output", "ableton", "Wild_Ones_V12.als"), "V12 (15 tracks, 4946 notes)"),
    ]

    # Also test stripped variants if they exist
    strip_dir = os.path.join(base, "output", "ableton", "test_v12strip")
    if os.path.exists(strip_dir):
        strip_files = [
            ("s9_bare_skeleton.als", "Bare skeleton"),
            ("s6_no_notes.als", "No notes"),
            ("s7_simple_notes.als", "Simple 4-note clips"),
            ("s1_plain_names.als", "Plain track names"),
            ("s2_no_automation.als", "No automation"),
            ("s4_2tracks_only.als", "DRUMS+BASS only"),
        ]
        for fname, desc in strip_files:
            path = os.path.join(strip_dir, fname)
            if os.path.exists(path):
                test_files.append((path, f"STRIP: {desc}"))

    print(f"Ableton: {ABLETON}")
    print(f"Log: {LOG_PATH}")
    print(f"Testing {len(test_files)} files")

    results = []
    for path, desc in test_files:
        ok = test_file(path)
        results.append((os.path.basename(path), desc, ok))

    print("\n" + "=" * 70)
    print("RESULTS")
    print("=" * 70)
    for name, desc, ok in results:
        status = "OK" if ok else "CRASH"
        print(f"  {'pass' if ok else 'FAIL':5s}  {name:35s}  {desc}")


if __name__ == "__main__":
    main()
