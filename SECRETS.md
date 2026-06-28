# Jacky Secrets — How Keys Are Handled (future-proof pattern)

**The problem this solves:** real API keys kept leaking into `.env` inside the
project, where they get backed up, read at process boot, and flagged. This
pattern keeps secrets in one gitignored vault, read lazily, never at boot.

**Status:** ✅ All legacy keys (Anthropic, OpenAI, Telegram) have been migrated
to the vault per this pattern. Real secrets live ONLY in `secrets/secrets.env`.

## The rules
1. **Real secrets live ONLY in `secrets/secrets.env`** — the vault. It is
   gitignored (`.gitignore`: `secrets/`, `*.secret`, `.env`).
2. **`.env` holds placeholders only.** Safe to back up. Never paste a real
   cloud key here. (Legacy pre-existing keys — Anthropic, Telegram — still live
   in `.env`; migrate them into the vault over time.)
3. **All key reads go through `secrets_loader.py`** with precedence:
   `os.environ` → `secrets/secrets.env` → `.env`.
4. **Nothing reads a secret at import/boot.** Keys are fetched lazily only when
   a provider is actually called — so launching the app surfaces no credentials.

## How to add a free cloud key
Paste it into **`secrets/secrets.env`** (not `.env`):
```
GROQ_API_KEY_1=gsk_...
GEMINI_API_KEY=AIza...
OPENROUTER_API_KEY=sk-or-...
```
Then the router (`cloud_router.py`) picks it up automatically — no code change.

## Provider order & cost (config.json → integrations.cloud_bots.providers)
`groq` (free) → `gemini` (free) → `openrouter` (free) → **local fallback**.
`xai` (Grok) is **paid + disabled**; its 4 keys sit archived in the vault. Flip
`xai.enabled: true` in `config.json` only on purpose (saves the $5).

## TLS / Avast
`cloud_client.py` uses `truststore` (trusts the Windows cert store where Avast's
interception root lives). Verification stays **ON** — no `CERT_NONE`, Avast
untouched.

## Files
- `secrets/secrets.env` — the vault (gitignored)
- `secrets_loader.py` — the one loader
- `cloud_client.py` — generic OpenAI-compatible client (truststore TLS)
- `cloud_router.py` — free-first failover
- `.env` — placeholders only
- `.gitignore` — excludes the vault + `.env`
