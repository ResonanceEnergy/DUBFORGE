"""Quick test: does Apology_V4.als load in Ableton?"""
import subprocess, time, os

ABLETON = r"C:\ProgramData\Ableton\Live 12 Standard\Program\Ableton Live 12 Standard.exe"
os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
time.sleep(2)

als = os.path.join(os.path.dirname(__file__), "output", "ableton", "Apology_V4.als")
print(f"Testing: {os.path.basename(als)}")
proc = subprocess.Popen([ABLETON, als])
time.sleep(8)

poll = proc.poll()
if poll is not None:
    print(f"CRASH (exit code {poll})")
else:
    print("LOADS OK")
    os.system('taskkill /f /im "Ableton Live 12 Standard.exe" >nul 2>&1')
