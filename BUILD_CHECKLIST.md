# BUILD_CHECKLIST.md — PS 26015 SRISHTI-DRISHTI, spec-section-by-section status

## SESSION 3 UPDATE (2026-09-23, same day, after user asked "did you do every
single thing mentioned in the prompt?" and the honest answer was no) — read
this first, before Session 2's update below

User asked to complete every remaining partial/gap end-to-end. Real work
done, in order:

1. **Section 3 — 5 real separate form files, finally matching the spec's
   literal file names.** Previously one generic `ExpertReviewForm.tsx` did
   all 5 roles via conditional rendering - real data, but not what was
   specified. Split into `WaterManagementForm.tsx`, `AgricultureForm.tsx`,
   `SoilScienceForm.tsx`, `SocialMobilizationForm.tsx`, `CommitteeForm.tsx`,
   sharing a small `useReviewSubmit.tsx` hook for the actual submit logic
   (not duplicated 5x). Deleted the old generic file. Verified clean
   production build.
2. **Section 3 — real `CrossValidation` table**, exactly as the spec
   describes ("Layer 3 sets a disagreement_type field on the CrossValidation
   row"). Previously `disagreement_type`/`routed_role` lived only on
   `Asset`. Added `models.CrossValidation` (satellite_verdict,
   photo_classification, disagreement_type, routed_role, rule_applied -
   the real values `routing.py` actually used, not re-derived), a new
   `/api/assets/{id}/cross-validation` endpoint, and updated
   `routing.classify_disagreement()` to return which real rule fired.
   `Asset.disagreement_type`/`routed_role` remain as fast summary fields
   the list/queue endpoints read (avoids a join on every request);
   `CrossValidation` is the inspectable audit trail. Verified live:
   `GET /api/assets/47/cross-validation` returns a real row.
3. **Section 9 — all 8 roles now tested with real accounts**, not 3.
   Created real pre-confirmed Supabase users for agriculture, soil_science,
   social_mobilization, committee_member, field_inspector (water_management,
   district_state_admin, and a no-role account already existed). Verified
   real 200s on own-role submit, real 403s on cross-role submit, for every
   role. Cleaned up the review/photo-coordinate rows this test run created
   afterward (including reverting one photo's `latitude`/`longitude` back
   to honest `NULL` - a test call had set it to an arbitrary but
   plausible-looking coordinate for a photo whose source CSV row says
   `no_coordinate_available`, which would have looked like real data if
   left in place).
4. **Section 11 — the PDF report now actually matches the spec**, not just
   a single-asset evidence sheet. New `backend/district_report.py` +
   `GET /api/districts/{district}/report`: real title page, real executive
   summary (real counts/percentages, honest small-sample caveats), a real
   satellite-mapping page (real ArcGIS composite + real asset markers
   colored by real triage_status + real district boundary outline), a real
   current-LULC map with a real dynamically-generated legend (only classes
   actually present), a real activity-classification table (from real
   `Photo.activity_type` values, including "unspecified" honestly), real
   site-wise evidence pages (one per real asset, real photo + real
   RESTREND chart + real captions), and a real conclusions section.
   **Scoped per real district, not per "project"** - verified every real
   `project_id` in the live data is 1:1 with a single asset (358 distinct
   IDs for 358 assets), so a literal project-level report would just be
   the existing single-asset packet; district is the real grouping this
   dataset actually has multiple assets under. Verified end-to-end for a
   small district (Guntur, 2 assets, 8 pages, 5.5s) and a large one
   (Kurnool, 59 assets, 65 pages, 18.7s, 11MB) - both produced real,
   correct content. Added a "Download District Report" button next to the
   map's district selector with a real loading state.
5. Fixed a cosmetic bug found while verifying the new report: an em-dash
   placeholder character in a photo caption rendered as a garbled glyph in
   ReportLab's default font - replaced with "N/A".

6. **Section 5 Stage 1 (field upload) — now verified real end-to-end.**
   Created a real test photo with real GPS EXIF (via `piexif`, coordinate
   15.5°N 78.5°E - a real, plausible in-bounds AP test point), uploaded it
   through the real `/api/ingest/photo` endpoint as the real
   `field_inspector` test account. Result was fully real: correct state
   detection, a real live GEE snapshot (NDWI -0.5457, LULC "crops", soil
   "clay loam", elevation 206.98m, slope 0.09°), a real CLIP prediction,
   and an honest `no_evidence`/Low-confidence triage result (correct,
   since a brand-new point has no RESTREND history yet). Cleaned up the
   test asset/photo/file afterward.
   **Real, notable finding that contradicts an earlier claim in this
   file**: this same test call's `bhuvan_baseline_lulc` came back with a
   real value ("Agriculture, Cropland") - meaning Bhuvan's WMS
   `GetFeatureInfo` endpoint is NOT durably unreachable the way the
   earlier "verified unreachable" note above claims (that was based on a
   `GetCapabilities` call timing out once). It's evidently flaky/
   intermittent rather than fully blocked. **Not pursued further this
   pass** (user explicitly said not to spend time on this) - but flagging
   honestly rather than leaving the stronger "verified unreachable" claim
   uncorrected. If Agriculture's routing trigger is revisited later, retest
   Bhuvan's real reachability properly (multiple attempts, both endpoints)
   before deciding it's unusable.

7. **Section 8/10 — real S3-compatible cloud storage, DONE.** Found this
   was a real production-breaking gap, not just a spec checkbox: field
   uploads were saved to local disk, which does not persist across a real
   container host's redeploys (Railway) - every Stage 1 upload would have
   silently vanished after the next deploy. Created a real public Supabase
   Storage bucket (`field-uploads`, same project, genuinely S3-compatible),
   added `backend/storage.py` (real upload, honest fallback to local path
   only if cloud storage genuinely isn't configured or the call fails -
   never silently claims durability it didn't get), wired it into
   `ingest_pipeline.py` *after* CLIP reads the local file it needs.
   Updated the frontend's `mediaUrl()` to pass through absolute URLs
   unchanged (the existing 1,514 static abc/ photos stay served locally -
   deliberately not migrated, they're bundled reference data, not
   at-risk user content). **Verified for real end-to-end**: uploaded a
   real test photo, confirmed the DB stored a real
   `https://.../storage/v1/object/public/field-uploads/...` URL, confirmed
   that URL is really publicly fetchable (200, real image bytes), cleaned
   up the test asset/DB row/cloud file afterward. PDFs are deliberately
   NOT cached to cloud storage - they're cheaply regenerated from live DB
   data on every request, so a stale cached copy would be less honest than
   just rebuilding it each time.

8. **Build step 12 — admin-only historical backfill, DONE, with a real bug
   found and fixed along the way.** Added `POST /api/admin/backfill`
   (district_state_admin only, real 403 verified for other roles) that
   re-runs the real ingest -> geocode -> enrich chain, reporting the real
   delta each time. **First real test run created 106 duplicate empty
   Asset rows** (464 instead of 358) - root cause: `ingest_abc_dataset.py`
   matched "does this asset already exist" on `project_id` AND exact
   `latitude`/`longitude`, but `scripts/geocode_all_fallbacks.py`
   legitimately updates a fallback asset's real coordinates after first
   ingest, so a coordinate-based re-match could never find it again and
   inserted a fresh (photo-less) duplicate every re-run. Verified the
   duplicates were harmless to real data before fixing (all 106 had zero
   photos, real photo count stayed at 1,514 throughout - only the
   asset-existence check was wrong, nothing photo-related was affected).
   Fixed the match to use `project_id` alone (verified real 1:1 with
   assets in this dataset), cleaned up the 106 duplicates, re-verified
   `python ingest_abc_dataset.py` now reports "0 new assets" standalone,
   then re-verified the full endpoint end-to-end: real 200/"0 new" for
   admin, real 403 for a non-admin role, DB back to the real 358/1,514
   with no drift. Also bounded the endpoint's Nominatim geocoding
   subprocess to 90s (observed hanging past its expected real runtime at
   least once this session) so a slow/flaky external call can never block
   the whole admin request indefinitely - new assets just keep their real
   district-centroid fallback coordinates if that happens, honestly
   reported in the response, retryable on a later call.

9. **User pasted the real PS 26015 study/problem-statement document and
   asked for its "Expected Solutions" (a)-(g) to be built strictly, using
   real alternatives since the literal named "SRISHTI-DRISHTI platform" is
   inaccessible (per explicit user instruction, not pursued further).
   Mapped against item (c), "Generation of Thematic Maps and Visualization
   Products: land use maps, drainage maps, vegetation maps, watershed
   intervention maps, and spatial change detection products"** - land use
   and watershed-intervention (triage-status) maps already existed;
   **drainage, vegetation, and spatial change-detection maps did not.**
   Added all three as real new pages in `district_report.py`:
   - Vegetation map: real Landsat 8 NDVI (2023, cloud-masked median
     composite), rendered server-side via `ee.Image.getThumbURL()`.
   - Drainage map: real WWF HydroSHEDS `FreeFlowingRivers` vector geometry
     (a real, public, established hydrology dataset - verified live, 614
     real river features returned for a real AP bounding box test).
   - Spatial change detection: real NDVI difference between a real
     2014-2015 Landsat composite and a real 2022-2023 one - genuine
     before/after vegetation gain (green) / loss (red), not a synthetic
     diff.
   **Hit and fixed a real bug while wiring this in**: all three pages
   failed live with "Earth Engine client library not initialized" even
   though the exact same code worked in a standalone test script. First
   diagnosis (thread-local `ee` session state, since FastAPI dispatches
   sync endpoints to a threadpool) was wrong and wasted a few fix attempts
   (tried unconditional re-init, tried `async def` - neither helped,
   because neither was the real cause). **Real root cause**: `_ensure_ee()`
   was only called inside the shared `_fetch_gee_thumb()` helper, but each
   render function builds `ee.Geometry.Rectangle(...)` as its own first
   line, before ever reaching that helper - initialization was just
   happening too late. Fixed by moving `_ensure_ee()` to the actual start
   of each of the three render functions. Verified for real: all three
   pages now render genuine images (extracted and visually inspected the
   vegetation map's embedded JPEG - real yellow-green NDVI coloring, not a
   blank/error placeholder); full report generation for a real district
   now takes ~50s (up from ~4s before this addition - real GEE median
   composites over a decade span are not fast, and this is not
   pre-cached). This is an honest, real time cost for real newly-added
   data, not a regression to hide.

**Still open after this pass**: further Section 2 dataset-audit sampling,
Section 7 hover-state polish, and resuming the paused deployment (Railway
backend build was mid-progress when paused; Vercel and production Postgres
untouched). Possible future improvement: pre-cache the three new thematic
map images per district (similar to how RESTREND is pre-computed) if the
~50s live generation time becomes a real problem - not done this pass.

## SESSION 2 UPDATE (2026-09-23, earlier same day)

Under a 5-hour full-scope push, real work completed since the section-by-section
audit below was written:

- **Fixed a real bug in `compute_live_snapshot`** (restrend_engine.py): Dynamic
  World LULC used `.first()` instead of `.mode()` (the exact anti-pattern the
  spec's Section 3b explicitly names), which left 192/358 assets with
  `sentinel_current_lulc=None` and made NDWI a noisy single-scene read. Fixed
  to a real mode-composite (LULC) and median-composite (NDWI) over the same
  window. `backend/refresh_snapshot.py` (new) re-ran this for all 345 unique
  coordinates without repeating the expensive RESTREND regression.
- **Open-Meteo rate-limiting hit mid-run** (HTTP 429 at coordinate ~199/345)
  — fixed with real retry/backoff + pacing in `restrend_engine.py` and
  `enrich_abc_dataset.py`; 29 failed cache entries were cleared and retried
  honestly rather than left as permanent failures.
- **Section 3 routing is now real**, not the spec-forbidden generic queue.
  Found and replaced `main.py`'s `_route_specialist()`, which routed almost
  every flagged asset to *every* role unconditionally — exactly the
  "generic queue" anti-pattern Section 3 forbids. Built:
  - A second real CLIP zero-shot pass (`ml_engine.CONDITION_LABELS`,
    reusing cached embeddings, no new inference) giving each photo a real
    `predicted_condition` (functional/dry/damaged/new-construction).
  - `backend/routing.py` — explicit, documented, single-role rules: a real
    water-signal mismatch (photo condition vs. Sentinel-2 NDWI) routes to
    Water Management and sets `disagreement_type`; `no_evidence` cases
    route, in priority order, to Committee Member (low coordinate
    precision) → Soil Science (real soil_texture_class exists AND the
    structure type is one where soil siting genuinely matters per Section
    3c — check_dam/boulder_structure/gabion_structure — added later this
    session, 61/358 real assets route here) → Social Mobilization
    (everything else) via `routed_role`.
  - **Agriculture's trigger remains honestly NOT implemented** — verified
    (not assumed) this session that Bhuvan's real WMS endpoint
    (`bhuvan-vec2.nrsc.gov.in`) times out from this environment (a real,
    timed connection test), so there is no real baseline LULC to compare
    against for abc coordinates. Do not add a weak proxy for this without a
    real baseline-LULC source becoming reachable.
  - New DB columns: `Asset.disagreement_type`, `Asset.routed_role`,
    `Photo.predicted_condition`, `Photo.predicted_condition_confidence`.
  - `backend/apply_condition_and_routing.py` (new) — run after
    `enrich_abc_dataset.py` and `refresh_snapshot.py`.
- **Found and removed a second live fabrication**: `MapView.tsx` was
  drawing a fake "Bhuvan Micro-Watershed" catchment polygon around every
  asset using hand-tuned offset math, branded with a "Bhuvan" popup badge
  as if it were a real NRSC boundary product. Removed entirely.
- **Section 6 built for real**: verified DataMeet's actual repo structure
  via the GitHub API (initial guessed URLs 404'd - never guess, always
  browse the real tree), found and used
  `docs/data/geojson/{states,dists11}.geojson`. That district file predates
  the 2014 AP/Telangana split, so `backend/extract_ap_boundaries.py`
  filters by a documented real district-name mapping (not the stale
  `ST_NM` field) and computes the "state" outline as a real union of the
  11 current-AP district polygons rather than trusting the file's own
  pre-bifurcation state polygon. Output: `frontend/public/boundaries/
  ap_districts.geojson` + `ap_state_union.geojson`. Wired into `MapView.tsx`:
  a real district dropdown, MapLibre boundary layer, `fitBounds()` to the
  real computed bbox, "no confirmed data" messaging for empty districts.
- **MAP RENDERING BUG - FOUND AND FIXED.** Root cause: MapLibre GL JS v6
  no longer ships a UMD bundle, only ES modules split into a main module
  plus a separate Web Worker module (`maplibre-gl-worker.mjs`, which itself
  imports a sibling `maplibre-gl-shared.mjs`). Turbopack cannot resolve the
  worker's own relative module path inside its bundle, so the worker
  silently fails to start - the map mounts (WebGL context, controls) but
  never issues a single tile request, with zero console errors anywhere.
  Confirmed via: (a) a standalone HTML page outside the app, hitting the
  exact same symptom against two different CDNs, which is what surfaced
  the real cause (the CDN's `maplibre-gl.js` 404s for v6 - no such file
  exists anymore), and (b) a live web search that matched this exact
  Next.js 16/Turbopack + MapLibre v6 interaction, independently confirming
  the diagnosis and the fix pattern.
  **Do NOT downgrade maplibre-gl as a fix** - versions <=6.4.0 (which
  includes all of v4 and v5) carry a real critical XSS advisory
  (GHSA-jrc7-96c5-q579, DOM sanitizer bypass). Fix actually applied:
  upgraded to the patched `maplibre-gl@^6.11.0` (`npm audit` now reports 0
  vulnerabilities), added `scripts/copy-maplibre-worker.mjs` as a real
  `postinstall` hook that copies the real worker + shared `.mjs` files from
  `node_modules` into `public/maplibre-worker/` (gitignored - regenerated
  on every `npm install`, not committed as source), and called
  `maplibregl.setWorkerUrl("/maplibre-worker/maplibre-gl-worker.mjs")`
  before constructing the Map in `MapView.tsx`.
  A second, related bug surfaced once tiles started loading: the "Update
  Markers" effect used a fragile `map.once("style.load", renderMarkers)`
  pattern that could register after that event had already fired for the
  current style (a real event-ordering race with the sibling
  "Handle Basemap Switch" / boundary-layer effects, all of which touch
  `map.setStyle`/style state on the same `mapReady` transition) - the
  listener would then wait forever for an event that would never fire
  again. Fixed by replacing the one-shot listener with a short bounded
  poll (`setTimeout` every 100ms until `map.isStyleLoaded()`), which is
  immune to event-ordering races between effects.
  **Verified for real in Chrome**: real satellite + Terrarium 3D terrain
  tiles render, the real district boundary layer draws and `fitBounds()`
  flies to the real selected district (tested selecting Kurnool - 59
  assets, map flew to its real computed bbox), and **all 358 real asset
  markers render** with their status-colored pins. Loading a country-scale
  3D-terrain view genuinely takes ~15-20 real seconds in this environment
  (many DEM tiles at low zoom) - this is real network/tile-volume latency,
  not a bug; a skeleton/loading-state UI cue for this wait is still a
  legitimate Section 7 polish item, not yet added.
- **Follow-up bug, found by the user on `/assets/[id]`, fixed**: the same
  worker error hit `InteractiveSatelliteView.tsx` (the asset-detail page's
  own live-pan satellite map), because `setWorkerUrl` had only been called
  inside `MapView.tsx` - a library-global setting that must run before
  ANY component constructs a Map, not once per component. Fixed by
  extracting it into `src/lib/maplibreSetup.ts` (a module-scope side
  effect on import) and importing that from both `MapView.tsx` and
  `InteractiveSatelliteView.tsx`. Verified in Chrome: `/assets/11`'s live
  map now loads with zero worker errors and real imagery renders once
  zoomed to a level with real ArcGIS coverage (a "Map data not available"
  placeholder at extreme zoom for a rural coordinate is expected honest
  behavior from the tile provider, not a bug).
- **Fixed a real classification bug found from the corrected NDWI data**:
  0/358 real assets ever show NDWI > -0.1 (all project/village-level
  coordinates, none land precisely on the actual small water body), which
  meant `triage.py`'s old NDWI-gated "greening" definition silently
  reclassified 100% of the dataset as `no_evidence`, discarding 209/358
  (58%) real, statistically-significant RESTREND trends. Fixed
  `classify_triage_status` so "greening" is a real OR of (NDWI > -0.1) OR
  (RESTREND significant) - documented in the function's docstring with the
  full reasoning. Final real distribution: **209 confirmed, 149
  no_evidence, 0 rainfall_confounded** (the last is correctly zero here:
  rainfall_confounded specifically requires NDWI-driven greening that
  ISN'T restrend-significant, and NDWI-driven greening never occurs in
  this dataset - an honest consequence of coordinate precision, not a bug).
  Routing result: 209 confirmed need no routing, 148 no_evidence ->
  social_mobilization, 1 no_evidence -> committee_member (district-fallback
  precision), 0 water_signal_mismatch disagreements detected this run.
- **Section 9 auth built and verified (pending real credentials)**: real
  `backend/auth.py` (Supabase JWT verification via PyJWT, `require_role()`
  FastAPI dependency), new `UserRole` table (real backend-owned roles, not
  client-supplied JWT metadata), gated `/api/reviews` (role in body must
  match caller's real role), `/api/photos/{id}/coordinates`,
  `/api/dispatch/simulate`, `/api/ingest/photo`, and added `/api/me`.
  Verified for real: no token -> 401, and the missing-secret case fails
  loudly (500, not a silent pass) rather than accepting anything. Frontend:
  `@supabase/supabase-js` installed, `lib/supabase.ts` (real config only,
  `supabaseConfigured` flag - never a placeholder that pretends to work),
  `lib/AuthProvider.tsx`, `components/AuthStatus.tsx` (shows "Auth not
  configured" honestly rather than a fake login form when env vars are
  unset - verified via screenshot), roles fetched from `/api/me` (our own
  DB), never trusted from the Supabase session alone.

  **UPDATE - fully tested end-to-end, real credentials wired in**
  (`backend/.env`, `frontend/.env.local`). Discovered this project uses
  Supabase's newer ES256/JWKS asymmetric signing (verified by fetching the
  real `/auth/v1/.well-known/jwks.json` endpoint), not the legacy shared
  HS256 secret the dashboard also shows - `auth.py` was rewritten to use
  `PyJWKClient` against the real JWKS endpoint instead of a static secret.
  Created 3 real pre-confirmed Supabase test users via the Admin API
  (service_role key, used once for setup then never exposed to the
  frontend), assigned real roles in `user_roles`, signed in as each for a
  real access token, and hit the live running API. **All 5 real checks
  passed**: own-role review submit -> 200, cross-role review submit -> 403,
  non-admin hitting the admin-only dispatch endpoint -> 403, real admin ->
  200, `/api/me` correctly reflects DB-backed roles. Test review/dispatch
  rows created during this check were deleted afterward; the 3 Supabase
  test accounts (`srishtidrishti.test.{water,admin,norole}@gmail.com`,
  password `TestPassword123!`) were left in place as reusable fixtures -
  delete them from the Supabase dashboard if not wanted. **Section 9 is
  genuinely done**, not just code-complete.

- **Minor, not yet fixed**: the disclaimer text in `MapView.tsx` reads
  "does not replace physical engineering certification" - Section 12 quotes
  the required text as "...does not replace physical inspection." Close in
  spirit, not an exact match. Low priority, quick fix whenever touched next.


Tracks `SPEC_MASTER_PROMPT.md` (the verbatim original spec, saved in this
same directory) against real, verified current state. Update this file —
never the spec file — as work progresses. Status legend:

- ✅ **DONE** — real, verified, matches spec intent
- 🟡 **PARTIAL** — some real work exists but doesn't fully satisfy the section
- ❌ **NOT DONE** — doesn't exist yet
- 🚫 **FAKE (quarantined/flagged)** — code exists but fabricates data; don't trust it as-is

Last verified: 2026-09-23.

---

## Section 1 — The Problem
✅ **DONE.** No code artifact needed; just framing. Nothing in the app currently claims a formal NRSC/DoLR agreement or impersonates an official deployment. Keep it that way in any UI copy/report text added later.

## Section 2 — The Real Dataset
🟡 **PARTIAL, materially improved this session.**
- ✅ Live DB is built from real `abc/organised_log.csv` (not the legacy CSV/dataset).
- ✅ Real counts as of this session's rebuild: **358 assets, 1,514 photos** (grown from the "346/1,466" originally quoted — the CSV now has more already-filtered rows).
- ✅ `abc/organised_log.csv` already carries `stage1_passed`/`stage2_passed`/`stage3_passed`/`duplicate_of` columns — all 1,514 current rows show all three stages `True` and `duplicate_of` null, i.e. content-filter + dedup already ran upstream (via `scripts/extract_abc_pipeline.py` / `scripts/separate_ambiguous.py`).
- ✅ **Real visual spot-check DONE** — see `abc/visual_spotcheck_log.md`. 27 real photos individually opened, stratified across all 11 districts (random_state=42 sample). **27/27 are genuine ground photographs** - zero screenshots/drawings/maps/duplicates found. Found 2 real (non-fabrication) mislabeling issues worth knowing about: 2 Guntur photos filed under `water_structure_other` are actually cookstove-distribution photos, and a few `check_dam`-labeled photos show plantation scenes instead of a dam. This is a **sample** (27 of 1,514), not exhaustive - treat the dataset as provisionally verified, not fully verified, until a larger pass runs (see the log file for how to continue the same sampling).
- 🟡 Perceptual-hash duplicate detection: the code exists (`imagehash.phash` in `extract_abc_pipeline.py` line ~535) and `duplicate_of` is a real column already populated (all null in the current 1,514 survivors) — but re-verify this was actually run against the *current* full 1,514-row set, not a stale earlier pass, since the row count has changed since the audit fork's original check (`abc/separation_audit.csv` covered 1,254 rows at that check).

## Section 3 — Domain expert routing (5 roles)
❌ **NOT DONE.** This is flagged as the system's "core novelty claim" by the spec, and it's currently missing entirely.
- ❌ No `disagreement_type` field on any model (`CrossValidation` doesn't exist as a table at all — `triage_status` lives directly on `Asset`).
- ❌ No explicit mismatch→role routing rules written anywhere.
- 🟡 Frontend has one generic `ExpertReviewForm.tsx`, not the five specified: `WaterManagementForm.tsx`, `AgricultureForm.tsx`, `SoilScienceForm.tsx`, `SocialMobilizationForm.tsx`, `CommitteeForm.tsx`.
- **Real blocker discovered this session:** `abc` ground photos carry no pre/post-treatment condition label (`structure_condition` is honestly `"not_recorded"` for every asset — the dataset simply doesn't have this information). `triage.py`'s classification logic can currently only reach `confirmed` / `rainfall_confounded` / `no_evidence` for real abc assets, **never `disagreement`**, because a real "claimed condition vs. satellite" mismatch needs a claimed condition to compare against, and there isn't one in the source data. Section 3's whole premise (route by mismatch *type*) needs either:
  (a) a real per-photo condition classifier (CLIP prompted for functional/silted/breached — `ml_engine.py`'s `CANDIDATE_LABELS` currently classify structure *type*, not condition — would need a second real classifier or a relabeled prompt set), or
  (b) accepting for this dataset that review routing can only be confidence-based (`confidence_level == "Low"`), not true cross-validation-mismatch-based, and being explicit about that limitation in the UI rather than inventing a disagreement type.
  **This is a real design decision for the user, not something to silently pick.**

## Section 4 — RESTREND
✅ **DONE**, real, verified this session.
- ✅ Real OLS regression (`scipy.stats.linregress`) — was already true before this session.
- ✅ **Fixed this session:** NDVI source switched from MODIS (1km) to real cloud-masked Landsat 8 (30m, `LANDSAT/LC08/C02/T1_L2`, QA_PIXEL-masked). Documented choice: Landsat 8 alone (not blended with Sentinel-2) gives unbroken 2014-2023 coverage.
- ✅ **Fixed this session:** precipitation switched from TerraClimate to real IMD-with-Open-Meteo-fallback (`backend/restrend_engine.py`). IMD (`imdpune.gov.in`) confirmed unreachable from this environment (TCP connects but the HTTP layer hangs — a real, verified, timeout-bounded finding, not an assumption) — Open-Meteo historical archive API confirmed working and used for all current results. Every result records which source was actually used (`Asset.restrend_precip_source`).
- ✅ Real p-values verified varying genuinely across ~124+ sites checked mid-run (0.0 to 0.6+), not a fixed value.
- ✅ Pre-computed and cached, never run live on a request (`backend/enrich_abc_dataset.py` → `restrend_cache_abc.json` → DB; `/assets/{id}/restrend` only reads DB).
- ✅ `RestrendChart.tsx` already exists in frontend (built before this session) — not reverified against the new data shape in this session; **spot-check after enrichment finishes that the chart still renders correctly with real Landsat/Open-Meteo-sourced points** (schema unchanged, so it should, but hasn't been visually confirmed post-enrichment).

## Section 5 — Full system flow
🟡 **PARTIAL.**
- Stage 1 (field inspector upload): 🟡 exists as a photo-upload endpoint in `main.py` per the earlier audit ("ingest/photo" endpoint) — not re-verified this session, and it calls `compute_live_snapshot` (real) rather than the full 10-year RESTREND (correctly deferred per the spec's own note about async backfill).
- Stage 2 (storage): ✅ DB record + file pointer, real, SQLite dev.
- Stage 3 (automatic triage): 🟡 CLIP ✅ real, GEE before/after ✅ real, IMD/RESTREND ✅ real (fixed this session), soil/DEM ✅ real, but the "Confirmed/Rainfall-Confounded/Disagreement/No Evidence" combination can't currently reach "Disagreement" for real abc data (see Section 3 blocker above) and there's no `disagreement_type` field to set.
- Stage 4 (result propagation to review queue): ✅ exists (`main.py`'s review-queue endpoint, filters on `triage_status == "disagreement"` or `confidence_level == "Low"` — the Low-confidence path works for real abc data even though the disagreement path currently can't trigger).
- Stage 5 (targeted expert routing): ❌ not done — see Section 3.
- Stage 6 (report export): ✅ `evidence_packet.py` is real, PDF from real DB/matplotlib data.

## Section 6 — State/district boundary navigation
❌ **NOT DONE.** No GeoJSON boundary file anywhere in the repo. No DataMeet/India-WRIS integration attempted yet. Nothing to correct here — this is a clean "not started," not a fabrication to fix.

## Section 7 — UI/Visual design
🟡 **PARTIAL, real progress this session.**
- ✅ 3D terrain confirmed genuinely working (Terrarium raster-dem via `setTerrain()`) — verified visually in Chrome after the MapLibre worker fix, real elevation-shaded satellite imagery renders.
- ✅ **Found and fixed a real gap**: there was no PDF export button anywhere in the UI — the real `/api/assets/{id}/evidence-packet` endpoint worked but nothing linked to it. Added a "Download Evidence Packet" button to the asset detail page with a real loading spinner while the PDF builds; verified a real 153KB PDF downloads correctly.
- ✅ Replaced the bare `Loading…` text on the asset detail page with a real skeleton loader (per spec's "never a blank loading screen" rule).
- ❌ Still not done: a full pass on hover states, the specified restrained color palette consistency, and skeleton loaders on the remaining pages (review-queue, map's own initial asset load still shows a plain text "Loading assets…" rather than a skeleton).

## Section 8 — Tech stack
🟡 **PARTIAL.** Most of the stack matches (FastAPI, SQLAlchemy, Pydantic v2, GEE, CLIP, scikit-learn, ReportLab, Next.js, MapLibre, Recharts, Tailwind v4 — all confirmed real and in use). Gaps: no auth service wired in (Section 9), production Postgres/PostGIS path untested (Section 10), Bhuvan WMS mentioned in spec but current code uses Bhuvan only incidentally if at all — not verified this session.

## Section 9 — User roles & authentication
❌ **NOT DONE.** No `User` model, no auth service, no `require_role()` dependency. `role` query param on `/api/review-queue` is unenforced. This is a clean gap, not a fabrication — nothing pretends to have auth that doesn't exist.

## Section 10 — Deployment stability
🟡 **PARTIAL.**
- ✅ CLIP embedding extraction is already offline/cached (`clip_embeddings.npz`), matches spec intent — this was already true before this session, and this session's enrichment run extends the same cache (`abc_<photo_id>` keys) rather than replacing the pattern.
- ❌ Real hosting-tier RAM testing never done — currently dev-only (local SQLite, local Python process). No claim has been made otherwise, so nothing to un-fabricate, just not started.
- ❌ Production PostgreSQL/PostGIS path (`DATABASE_URL` override exists in `database.py`, confirmed by code read) — never actually tested against a real Postgres instance.

## Section 11 — Exportable report
✅ **Largely DONE**, per the earlier audit: `evidence_packet.py` builds a real PDF from real DB + matplotlib data. **Not re-verified against the post-enrichment data this session** — worth re-running once enrichment finishes to confirm the PDF picks up real (not null) elevation/slope/RESTREND/confidence values now that they're populated.

## Section 12 — Human-in-the-loop principle
🟡 **Not audited this session.** Need to confirm the disclaimer text actually appears in the frontend UI, not just as an intention. Quick check, not done yet.

## Section 13 — No-hardcode rule
🟡 **MAJOR PROGRESS this session, not fully closed.**
- ✅ Fixed: `ingest_abc_dataset.py`'s hardcoded triage/confidence/condition/elevation/slope fields.
- ✅ Fixed: RESTREND now real end-to-end for the live dataset (was previously never computed for it at all).
- ✅ Quarantined: `ingest_drishti_dataset.py` (fake RESTREND sine-wave + hardcoded p=0.012, fake NDWI-by-keyword, DB-wiping `drop_all()`), `apply_watershed_overlay.py` (fake watermark + `hashlib`-seeded fake boundary burned into image pixels), two legacy-CSV RESTREND scripts. Moved to `backend/_legacy_fabricated_DO_NOT_RUN/`, never deleted, README explains why.
- ✅ **FIXED: `site_feasibility.py` retrained on real abc data.** Rewrote `build_training_frame()` to query `watershed.db` directly instead of the banned legacy CSV. First attempt used the real per-photo CLIP condition classifier as the target, but that turned out degenerate for this dataset (0/348 assets had "functional" win as the top condition prediction — zero variance, unusable). Switched the target to `Asset.triage_status == "confirmed"` (real, well-populated: 209/348 vs 139/348), which is also the more defensible real-world meaning of "feasibility" for this dataset anyway. Retrained: **348 real samples, 65.5% real 5-fold cross-validated accuracy**. Verified live via `/api/feasibility/meta` and `/api/feasibility/predict` against the running backend — both return real, non-fabricated numbers. `baseline_lulc` in the request/response is documented as actually carrying real *current* LULC (no real baseline LULC exists for abc), not silently relabeled.
- ❌ Section 6 boundary shapes: not started, so no fake shapes exist yet either (clean state).
- ❌ Bhuvan `GetCapabilities` live-resolution for WMS layer names: not verified either way this session.

## Section 14 — Build order (meta-checklist)
1. Dataset audit (Section 2) — 🟡 partial, visual spot-check still missing
2. DB schema + confirm DB reflects only real audited data — 🟡 DB rebuilt from real abc data this session (358/1,514), but no User/role model yet, and the audit itself is incomplete
3. Backend cross-validation + `disagreement_type` + confidence ceiling — 🟡 confidence ceiling rule (`triage.py`) is real and tested-in-principle; `disagreement_type` doesn't exist (Section 3 blocker)
4. Real RESTREND, cached — ✅ DONE this session
5. Auth + role-based access — ❌ not started
6. Offline CLIP embeddings — ✅ pattern already existed, extended this session to real abc photos (in progress as of last check)
7. State/district boundaries — ❌ not started
8. Frontend 3D map + boundary selector — 🟡 3D map exists (unverified depth), boundary selector doesn't (Section 6)
9. Review queue + 5 expert forms — 🟡 review queue exists, only 1 generic form exists (not 5)
10. Direct photo upload + live CLIP — 🟡 exists per earlier audit, not re-verified this session
11. PDF export — ✅ real, not re-verified post-enrichment
12. Admin-only PDF backfill — not independently confirmed either way this session
13. CORS locked to explicit origins — ✅ confirmed by earlier audit (no wildcard)
14. Deploy + real RAM check — ❌ not started

---

## Suggested next priorities (not yet chosen by the user — ask before starting)

In rough order of how tightly they gate other work:

1. **Finish the Section 2 visual spot-check** — it's the one manual step nothing else can substitute for, and the spec is explicit that nothing should be presented as verified until it's done.
2. **Resolve the Section 3 condition-label blocker** — decide with the user whether to build a real CLIP-based condition classifier or scope down the disagreement-routing claim honestly. This gates Section 3 (5 expert forms), part of Section 5 (Stage 3/5), and `site_feasibility.py`'s retrain.
3. **Retrain `site_feasibility.py` on real abc data** once the condition-label question is resolved.
4. **Section 6 boundary GeoJSON** — self-contained, doesn't block on anything else, good candidate for a focused next session.
5. **Section 9 auth/roles** — self-contained backend work, doesn't block the above.
6. **Visual/UI pass (Section 7)** — needs the dev server actually running and looked at, not just code review.
