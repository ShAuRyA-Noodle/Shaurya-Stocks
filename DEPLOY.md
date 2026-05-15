# Deploy — World-Class 5-Layer LLM Pipeline

## What you get

- **Frontend on Vercel** (free Hobby tier) — `/recommendations`, `/results`, `/paper`, `/`
- **5-layer LLM pipeline** running daily via GitHub Actions cron (free 2000 min/mo)
- **Static-rebuild architecture** — no always-on backend, $0/month hosting
- **Phone access** — bookmark Vercel URL, add to home screen

## One-time setup (run these once)

### 1. Push current branch to GitHub

```bash
cd /Users/shauryapunj/Desktop/ShAuRyA_Side_Projects/Finance_Project
git push origin main
```

### 2. Add GitHub repository secrets

Repo → Settings → Secrets and variables → Actions → **Secrets**:

| Secret | Value |
|---|---|
| `ALPACA_API_KEY_ID` | paper account |
| `ALPACA_API_SECRET_KEY` | paper account |
| `JWT_SECRET_KEY` | any 32+ char random string |
| `OPENROUTER_API_KEY` | `sk-or-v1-...` (your key) |
| `MARKETAUX_API_KEY` | for news |
| `NEWSAPI_KEY` | for news (optional) |
| `FINNHUB_API_KEY` | for news (optional) |
| `GROQ_API_KEY` | fallback when OpenRouter rate-limits |
| `SLACK_WEBHOOK_URL` | order alerts (optional) |

### 3. Add GitHub repository variables

Repo → Settings → Secrets and variables → Actions → **Variables**:

| Variable | Value |
|---|---|
| `TRADING_ENABLED` | `true` (after you're satisfied with plan-only runs) |
| `UNIVERSE_TIER` | `TOP100` (or `DEV` / `TOP50` / `SP500`) |

### 4. Deploy frontend to Vercel

```bash
cd apps/web
npx vercel login        # one-time
npx vercel link         # link this folder to a Vercel project
npx vercel --prod       # deploy
```

Output: `https://your-project-name.vercel.app` — bookmark on phone.

### 5. (Optional) Enable Vercel auto-deploy on push

Vercel dashboard → Project → Settings → Git → Connect to `Silky-Blade` repo, branch `main`.
Now every cron commit triggers auto-rebuild.

## Daily workflow (runs automatically)

```
21:30 UTC weekday (5:30 PM ET)
  ↓
GitHub Actions cron fires
  ↓
Layer 3: Classify macro regime          (1 LLM call, ~$0.001/day)
Layer 1: Fetch + score sentiment        (~120 articles × Flash, ~$0.005/day)
Layer 2: Tag catalysts                  (~120 articles × K2.5, ~$0.010/day)
Snapshot Alpaca paper account           (free)
Compute orders (momentum signal)        (free, Alpaca bars)
Layer 5: Generate daily briefing        (1 LLM call, ~$0.001/day)
  ↓
Commit all artifacts to repo
  ↓
Vercel detects push → rebuilds frontend
  ↓
Phone shows fresh data within 60sec
```

Daily LLM cost: ~$0.02. **3-month total: ~$2.40.**

## Monitoring

- **Phone**: open Vercel URL, check `/recommendations` daily
- **GitHub Actions** tab: see cron run history, click any run to view logs
- **Slack** (if `SLACK_WEBHOOK_URL` set): order submission alerts

## Safety gates (cron is paper-only by design)

The cron CANNOT submit live orders. All four gates are required:

1. `ALPACA_PAPER=true` — hardcoded in workflow YAML (immutable)
2. `TRADING_ENABLED=true` — GitHub variable (opt-in)
3. `--confirm` flag — passed explicitly in workflow
4. `LIVE_TRADING_CONFIRMED` — set to `"false"` in workflow (immutable)

To ever switch to live broker, all four would need to flip — three of which are immutable in the YAML.

## Cost summary (3 months)

| Item | Cost |
|---|---|
| LLM (5-layer pipeline, top-100) | ~$2.40 |
| Vercel Hobby tier | $0 |
| GitHub Actions cron (under 2000 min/mo) | $0 |
| Alpaca paper account | $0 |
| News APIs (free tiers cover top-100) | $0 |
| **GRAND TOTAL** | **~$2.40** |
