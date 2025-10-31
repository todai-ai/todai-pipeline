import os, json, datetime, sys, glob
import firebase_admin
from firebase_admin import credentials, storage, firestore

# ENV expected:
#  - FIREBASE_SERVICE_ACCOUNT  (JSON string; in GH Actions)
#  - FB_BUCKET                 (e.g., "todai-alpha.firebasestorage.app")
#  - TONE_NAME                 (optional; default "Anchor Calm")

def load_tones():
    import glob, json, os, sys
    tones = {}
    for path in glob.glob(os.path.join("tones", "*.json")):
        try:
            # tolerate UTF-8 with or without BOM
            with open(path, "r", encoding="utf-8-sig") as f:
                data = json.load(f)
                name = data.get("name")
                if name:
                    tones[name] = data
                else:
                    print(f"[warn] Tone file {path} missing 'name' field", file=sys.stderr)
        except Exception as e:
            print(f"[warn] Failed to load tone file {path}: {e}", file=sys.stderr)
    return tones

def init():
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
    else:
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"storageBucket": os.environ["FB_BUCKET"]})

def run():
    init()
    db = firestore.client()
    bucket = storage.bucket()
    tones = load_tones()

    tone_name = os.environ.get("TONE_NAME", "Anchor Calm")
    tone = tones.get(tone_name) or tones.get("Anchor Calm") or {"name": "Anchor Calm"}

    now = datetime.datetime.utcnow()
    yyyy, mm, dd = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    date_key = now.strftime("%Y-%m-%d")

    try:
        # 1) placeholder MP3 (0 bytes)
        bucket.blob(f"audio/briefings/{yyyy}/{mm}/{dd}/brief.mp3").upload_from_string(
            b"", content_type="audio/mpeg"
        )

        # 2) metadata JSON (now includes tone)
        meta = {
            "date": date_key,
            "utc_timestamp": now.isoformat() + "Z",
            "tone": tone.get("name"),
            "category": "AI/Tech",
            "generator_version": "0.2",
            "status": "ok"
        }
        bucket.blob(f"audio/meta/{date_key}.json").upload_from_string(
            json.dumps(meta), content_type="application/json"
        )

        # 3) ops log
        db.collection("ops").document(date_key).set({
            "date": date_key,
            "job": "mock_generate",
            "utc": now.isoformat() + "Z",
            "status": "ok",
            "tone": tone.get("name")
        }, merge=True)

        print(f"Nightly mock brief uploaded ✅ (tone: {tone.get('name')})")
    except Exception as e:
        db.collection("ops").document(date_key).set({
            "date": date_key,
            "job": "mock_generate",
            "utc": now.isoformat() + "Z",
            "status": "error",
            "error": str(e),
            "tone": tone.get("name")
        }, merge=True)
        print("Nightly mock brief failed ❌", e, file=sys.stderr)
        raise

if __name__ == "__main__":
    run()
