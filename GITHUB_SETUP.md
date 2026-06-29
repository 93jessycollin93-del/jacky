# Pushing Jacky to GitHub

The repository is initialized locally and ready to push. Here's what to do:

## Step 1: Create a real GitHub token

Go to https://github.com/settings/tokens/new and create a **Personal Access Token (classic)**:
- Name: `jacky-repo`
- Expiration: 90 days or longer
- Scopes: `repo` (full control of private repositories)
- Copy the token (it starts with `ghp_`)

## Step 2: Replace the placeholder in .env

Edit `.env` and replace:
```
GITHUB_TOKEN=ghp_PAS... (fake)
```
With the real token:
```
GITHUB_TOKEN=ghp_YOUR_REAL_TOKEN_HERE
```

## Step 3: Create the remote repository

**Option A: Via GitHub web UI**
1. Go to https://github.com/new
2. Create a repo named `jacky`
3. Leave it empty (no README, .gitignore, or license)
4. Click Create

**Option B: Via gh CLI** (if installed)
```bash
gh repo create jacky --public
```

## Step 4: Add remote and push

GitHub username: **93jessycollin93-del**

```bash
cd /e/AI/Jacky
git remote add origin https://github.com/93jessycollin93-del/jacky.git
git branch -M main
git push -u origin main
```

When git asks for a password, paste your Personal Access Token (not your
account password).

## Step 5: Verify

Visit https://github.com/93jessycollin93-del/jacky in your browser.

---

**Current state:**
- Commit: `34d4d3c` (v1.1 initial)
- Files staged: 26 (4570 lines)
- .gitignore: Secrets + data logs excluded
- .env template: Present (safe to commit)
- Vault: Not tracked (never pushed)

Ready to go once you have a real token!
