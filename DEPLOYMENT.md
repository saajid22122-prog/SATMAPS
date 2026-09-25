# Deployment Guide — PS 26015 SRISHTI-DRISHTI

Real findings and real configuration for Section 10. Read `BUILD_CHECKLIST.md`
first for full context.

## Real RAM finding (verified this session, not assumed)

Measured the actual `torch` + `transformers` + CLIP ViT-B/32 process
footprint on this machine: **~1.05 GB RSS** after loading the model and
running one real inference. This confirms the spec's own flagged risk -
free tiers (Render free: 512MB, Railway free: ~512MB-1GB, Fly.io free:
256MB) will OOM-kill the backend the first time `/api/ingest/photo` is hit
(it calls CLIP in-process via `ingest_pipeline.py` -> `ml_engine.py`).

**Decision made under this session's time constraint**: rather than
splitting live single-photo CLIP inference into a separate lightweight
microservice (the spec's suggested mitigation, a real architecture change
that needs its own design/testing pass), deploy the backend to a tier with
**at least 2 GB RAM** and document this as the real, tested requirement.
Revisit the microservice split if a stricter free-tier budget becomes a
real constraint later - this is an honest trade-off, not a shortcut being
hidden.

## What's already verified working

- Real production frontend build: `npm run build` succeeds clean, 0 errors,
  0 TypeScript errors (tested this session).
- `postinstall` script (`scripts/copy-maplibre-worker.mjs`) runs
  automatically on `npm install` and correctly populates
  `public/maplibre-worker/` - required for the map to render at all (see
  BUILD_CHECKLIST.md's MapLibre v6 bug writeup).
- Backend starts clean, real Supabase JWT verification works, real 403s
  confirmed on cross-role access.
- `psycopg2-binary` added to `requirements.txt` - `database.py` already
  reads `DATABASE_URL` from the environment and switches driver
  automatically (`postgresql://` vs `sqlite:///`), but this has **not yet
  been tested against a real Postgres instance** - no local Postgres/Docker
  available in this environment, and no production Postgres connection
  string has been provided yet. **Do this before calling Section 10 done.**

## Required environment variables

### Backend (`backend/.env` locally; set as real platform env vars in production)
```
SUPABASE_URL=https://gihuorjpaiirldxuexli.supabase.co
DATABASE_URL=<real Postgres connection string - see "What I still need" below>
ALLOWED_ORIGINS=<real production frontend URL(s), comma-separated - never a wildcard>
```
(`SUPABASE_JWT_SECRET` is NOT needed - this project uses real ES256/JWKS
verification, fetched live from `SUPABASE_URL`, not a static secret.)

### Frontend (`frontend/.env.local` locally; set as real platform env vars in production)
```
NEXT_PUBLIC_API_BASE=<real deployed backend URL>
NEXT_PUBLIC_SUPABASE_URL=https://gihuorjpaiirldxuexli.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=<the anon key already in frontend/.env.local>
```

## Backend start command
```
uvicorn main:app --host 0.0.0.0 --port $PORT
```
(`Procfile` already has this - works as-is on Railway/Render/Fly.io/Heroku-style platforms.)

## What I still need from you to actually deploy

1. **A real Postgres connection string** for `DATABASE_URL` - since we
   already have a Supabase project, the simplest real option is Supabase's
   own Postgres (Project Settings → Database → Connection string, the
   "Session pooler" or "Transaction pooler" URI, `postgresql://...`). This
   lets me actually test `DATABASE_URL` against real Postgres, migrate the
   schema, and confirm the app works against it - not just claim it does.
2. **Which hosting platforms** you want to use (see the question in chat)
   - and access to deploy: either your own login in a browser session with
     me driving it, or a CLI token/API key for that platform so I can
     deploy directly.
3. Confirmation of the **RAM tier** for the backend host (must be ≥2GB per
   the real measurement above).

## Real, honest scope note

This remains, per Section 1, a demo-ready prototype - deploying it does
not constitute an official government system and no such claim should
appear anywhere in the deployed app.
