# SAS Internet Access — Setup Guide

SAS (the dashboard) now runs as a secure, installable web app reachable from
anywhere. Two ways to expose it:

- **Quick tunnel** — instant, zero setup, but the URL changes each restart.
- **Permanent tunnel** — `sas.cybernetic67.com`, stable forever (uses your domain).

Both keep Ollama + the GPU on your PC (free, fast, private). Cloudflare only
forwards traffic; no model ever leaves your machine.

---

## Security model (read this first)

- SAS is protected by a **login token** stored in `secrets/secrets.env`
  as `SAS_ACCESS_TOKEN`. Auth turns on automatically when that's set.
- Your current token is in the vault. To see/change it:
  ```
  notepad secrets\secrets.env
  ```
- The token gates the dashboard **and** every `/api/*` route. `/health` and the
  app icons are the only open endpoints.
- Sessions last 30 days per device (so your phone stays logged in).
- **Never share the token.** Anyone with it + the URL can drive your AI.

---

## Option A — Quick tunnel (instant, recommended to start)

Just double-click:

```
Start_SAS_Public.cmd
```

It will:
1. Start Ollama (if not already running)
2. Start the SAS server (waitress, production-grade)
3. Open a Cloudflare tunnel and print a public URL like
   `https://random-words.trycloudflare.com`

The URL is also written to `CURRENT_PUBLIC_URL.txt`.

**On your phone:**
1. Open that URL (works on cellular or any WiFi — anywhere)
2. Log in with your token
3. Tap the browser menu → **Add to Home Screen** (or tap the "Install app"
   button in the header). Now SAS is an icon on your phone like a real app.

> The quick-tunnel URL changes every time you restart it. Fine for testing or
> occasional use. For a URL that never changes, do Option B once.

---

## Option B — Permanent tunnel: sas.cybernetic67.com

One-time setup (~10 min). After this, the same URL works forever and starts
automatically with Windows.

### Step 1 — Log cloudflared into your Cloudflare account
```
bin\cloudflared.exe tunnel login
```
A browser opens → pick the **cybernetic67.com** zone → Authorize.

### Step 2 — Create the named tunnel
```
bin\cloudflared.exe tunnel create sas
```
This prints a tunnel ID and saves a credentials file in
`C:\Users\93jes\.cloudflared\<TUNNEL_ID>.json`.

### Step 3 — Route the subdomain to the tunnel
```
bin\cloudflared.exe tunnel route dns sas sas.cybernetic67.com
```
This creates the DNS record automatically (no manual DNS editing).

### Step 4 — Create the config file
Save as `C:\Users\93jes\.cloudflared\config.yml`:

```yaml
tunnel: sas
credentials-file: C:\Users\93jes\.cloudflared\<TUNNEL_ID>.json

ingress:
  - hostname: sas.cybernetic67.com
    service: http://localhost:5000
  - service: http_status:404
```
(Replace `<TUNNEL_ID>` with the ID from Step 2.)

### Step 5 — Test it
Start the SAS server first:
```
python serve.py
```
Then in another terminal:
```
bin\cloudflared.exe tunnel run sas
```
Visit **https://sas.cybernetic67.com/dashboard** on your phone. Log in. Install.

### Step 6 (optional) — Run as a Windows service (auto-start on boot)
From an **Administrator** terminal:
```
bin\cloudflared.exe service install
```
Now the tunnel runs in the background on every boot. You only need to keep the
SAS server (`python serve.py`) running — add it to Task Scheduler or your
existing Jacky launcher.

---

## Daily use

- **Quick way:** double-click `Start_SAS_Public.cmd`, read the URL, go.
- **Permanent way:** SAS server + `cloudflared service` both run on boot →
  `sas.cybernetic67.com` is always live.

To take SAS offline: close the launcher window (quick tunnel), or stop the
`python serve.py` process.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Phone shows "wrong access token" | Token is in `secrets\secrets.env` → `SAS_ACCESS_TOKEN`. Copy it exactly. |
| Phone can't reach the URL | Make sure the launcher window is still open (quick tunnel) or `cloudflared` service is running (permanent). |
| Dashboard loads but no data | The SAS server or Ollama isn't running. Check `sas_serve.log`. |
| "auth: disabled" in /health | `SAS_ACCESS_TOKEN` isn't set in the vault — SAS is OPEN. Set it before exposing. |
| Port 5000 already in use | An old Flask debug server is stuck. The launcher auto-kills it; or run `python serve.py` after closing stale windows. |
| Want to rotate the token | Edit `SAS_ACCESS_TOKEN` in `secrets\secrets.env`, restart `serve.py`. All devices must log in again. |

---

## Files

| File | Role |
|---|---|
| `serve.py` | Production server (waitress) — run this, not jacky_api.py, for internet |
| `Start_SAS_Public.cmd` | One-click: Ollama + server + quick tunnel |
| `Start_SAS_Public.ps1` | The actual launcher logic |
| `bin\cloudflared.exe` | The tunnel binary (Cloudflare) |
| `secrets\secrets.env` | Holds `SAS_ACCESS_TOKEN` + `SAS_SECRET_KEY` (gitignored) |
| `sas_ui/manifest` + `sw.js` + icons | PWA app shell (served by jacky_api.py routes) |
| `CURRENT_PUBLIC_URL.txt` | Last quick-tunnel URL (auto-written) |
