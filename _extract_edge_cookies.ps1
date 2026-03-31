# Extract Edge cookies for yt-dlp (SoundCloud likes)
# This kills Edge, copies the cookies DB, exports to cookies.txt, then you can reopen Edge.

Write-Host "Closing Edge..." -ForegroundColor Yellow
Stop-Process -Name msedge -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

$src = "$env:LOCALAPPDATA\Microsoft\Edge\User Data\Default\Network\Cookies"
$dst = "$env:TEMP\edge_cookies_copy.db"
$cookiesTxt = "C:\dev\SuperAgency-Shared\repos\DUBFORGE\cookies.txt"

if (-not (Test-Path $src)) {
    Write-Host "Edge cookies DB not found at $src" -ForegroundColor Red
    exit 1
}

Copy-Item $src $dst -Force
Write-Host "Copied cookies DB ($((Get-Item $dst).Length) bytes)" -ForegroundColor Green

# Export SoundCloud cookies to Netscape cookies.txt format
python -c @"
import sqlite3, os, time
db = os.path.join(os.environ['TEMP'], 'edge_cookies_copy.db')
out = r'$cookiesTxt'
conn = sqlite3.connect(db)
c = conn.cursor()
c.execute('SELECT host_key, path, is_secure, expires_utc, name, value FROM cookies WHERE host_key LIKE ''%soundcloud%''')
rows = c.fetchall()
conn.close()
with open(out, 'w') as f:
    f.write('# Netscape HTTP Cookie File\n')
    for host, path, secure, expires, name, value in rows:
        httponly = 'TRUE' if host.startswith('.') else 'FALSE'
        sec = 'TRUE' if secure else 'FALSE'
        # Chromium stores expires as microseconds since 1601-01-01
        if expires > 0:
            exp_unix = int((expires / 1000000) - 11644473600)
        else:
            exp_unix = 0
        f.write(f'{host}\t{httponly}\t{path}\t{sec}\t{exp_unix}\t{name}\t{value}\n')
print(f'Exported {len(rows)} SoundCloud cookies to {out}')
"@

if (Test-Path $cookiesTxt) {
    $lines = (Get-Content $cookiesTxt | Measure-Object).Count
    Write-Host "cookies.txt ready: $lines lines" -ForegroundColor Green
    Write-Host "You can now reopen Edge and run the analyzer!" -ForegroundColor Cyan
} else {
    Write-Host "Failed to create cookies.txt" -ForegroundColor Red
}
