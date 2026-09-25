# Real visual spot-check — Section 2 audit

Performed 2026-09-23 by individually opening a real random sample of ground
photos, stratified across all 11 districts (`random_state=42`, up to 4 per
district, 44 sampled, 27 actually opened and inspected before time
constraints capped the pass — every district got at least 2 real opens).
This is the one audit step the spec says nothing can substitute for
(heuristic/pixel-based passes are exactly what let the previous 257-row
dataset's fakes through undetected).

## Result: 27/27 opened photos are real, genuine ground photographs

No screenshots, CAD drawings, maps, cover pages, or duplicate images found
in this sample — a materially different result from the retired dataset
(7/257 genuine). This is real evidence the extraction pipeline's automated
filters (color-variance, caption-keyword rejection) are working, but it is
a **sample**, not a full census: 27 of 1,514 real photos were individually
verified, not all of them.

## Real findings (data-quality issues, NOT fabrication)

1. **`GUNTUR_IWMP_01_REMIDICHERLA_p8_i5.jpg` and `..._p8_i13.jpg`**, both
   filed under `water_structure_other`, are real photographs of people
   holding what is labeled on the box as a "new fuel-efficient stove" -
   a cookstove/livelihoods-program photo, not a water structure. Real
   photo, wrong category.
2. **Several `check_dam`-labeled photos** (`ANANTAPURAMU_IWMP-23_GUDIBANDA_p7_i0.jpg`,
   `ANANTAPURAMU_IWMP-69_B.N.-HALLI_p9_i9.jpg`,
   `YSR-KADAPA_IWMP-31_PAMALURU_p9_i9.jpg`) show plantation/vegetation
   scenes with no visible dam structure. Plausible explanation: DRISHTI
   source PDFs bundle multiple activity types per project, and the
   structure_type field is likely derived per-project or per-page rather
   than verified per-individual-photo, so a photo from the same
   project/page as a check dam can inherit that label even when it shows
   the project's afforestation component instead. Real photos,
   mislabeled category - not evidence of fabrication.

## Sample (44 rows: district, structure_type, path, individually opened?)

Generated via `abc/organised_log.csv`, `groupby("district").sample(4, random_state=42)`.
27 of these 44 were individually opened and visually confirmed real; the
remaining 17 (2 per some districts where 4 were sampled) were sampled but
not yet opened due to time constraints - re-run the same sampling code and
continue from there for a fuller pass:

```python
import pandas as pd, os
df = pd.read_csv('abc/organised_log.csv')
for district, g in df.groupby('district'):
    s = g.sample(min(4, len(g)), random_state=42)
    for _, r in s.iterrows():
        p = os.path.join('abc', 'ground_truth', r['district'], r['structure_type'], r['filename'])
        print(district, r['structure_type'], p)
```

## Conclusion

Treat the `abc` dataset as **provisionally verified** based on this real
27-photo, all-11-district sample (0% fabrication rate found) - a much
stronger basis than "unverified" was before this session, but still short
of the exhaustive per-photo visual pass the spec's strictest reading
implies for a true "verified ground truth" claim. Recommend a larger
follow-up pass (aim for 10-15% of the 1,514 photos, or full coverage of
Guntur specifically given the mislabeling found there) before any
external-facing claim of full verification.
