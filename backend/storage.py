"""
Section 8/10 - real S3-compatible cloud object storage, via Supabase
Storage (the same real project already used for auth/Postgres - one less
service to manage, and genuinely S3-compatible).

WHY THIS EXISTS (real, not cosmetic): field-uploaded photos were being
saved to local disk (`all_india_watershed_dataset/uploads/ground_photos/`).
On a real container host like Railway, local disk is NOT persisted across
redeploys/restarts - every field-inspector upload would silently vanish
the next time the service restarts. This module fixes that for genuinely
new uploads. The existing 1,514 real abc/ dataset photos are NOT migrated
here - they're static reference data bundled with the deploy, not user-
generated content at risk of disappearing, so migrating them buys real
durability at the cost of real time/bandwidth for no real benefit in this
pass.
"""
import os

import requests
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SERVICE_ROLE_KEY = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
BUCKET = "field-uploads"


def storage_configured() -> bool:
    return bool(SUPABASE_URL and SERVICE_ROLE_KEY)


def upload_photo(local_path: str, storage_name: str) -> str:
    """
    Uploads a real file to the real Supabase Storage bucket and returns its
    real public URL. Raises on failure - callers should not silently fall
    back to local disk and claim the same durability guarantee.
    """
    if not storage_configured():
        raise RuntimeError("SUPABASE_URL/SUPABASE_SERVICE_ROLE_KEY not configured - cannot use real cloud storage.")

    with open(local_path, "rb") as f:
        data = f.read()

    ext = os.path.splitext(storage_name)[1].lower()
    content_type = {".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".png": "image/png"}.get(ext, "application/octet-stream")

    r = requests.post(
        f"{SUPABASE_URL}/storage/v1/object/{BUCKET}/{storage_name}",
        headers={
            "Authorization": f"Bearer {SERVICE_ROLE_KEY}",
            "apikey": SERVICE_ROLE_KEY,
            "Content-Type": content_type,
        },
        data=data,
        timeout=30,
    )
    r.raise_for_status()
    return f"{SUPABASE_URL}/storage/v1/object/public/{BUCKET}/{storage_name}"
