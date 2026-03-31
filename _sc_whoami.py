"""Get SoundCloud user info from cookies."""
import http.cookiejar
import urllib.request
import json

cj = http.cookiejar.MozillaCookieJar("cookies.txt")
cj.load(ignore_discard=True, ignore_expires=True)

token = None
for c in cj:
    if c.name == "oauth_token":
        token = c.value
        break

if not token:
    print("No oauth_token in cookies")
    raise SystemExit(1)

print(f"OAuth token: {token[:20]}...")

opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cj))
req = urllib.request.Request(
    f"https://api-v2.soundcloud.com/me?oauth_token={token}",
    headers={"User-Agent": "Mozilla/5.0"},
)
resp = opener.open(req)
data = json.loads(resp.read())

print(f"Username: {data.get('permalink')}")
print(f"Display:  {data.get('username')}")
print(f"ID:       {data.get('id')}")
print(f"Likes:    {data.get('likes_count', 'N/A')}")
print(f"URL:      {data.get('permalink_url')}")
