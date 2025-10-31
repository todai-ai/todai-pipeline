import os, json, datetime, sys
import firebase_admin
from firebase_admin import credentials, storage, firestore

# ENV expected:
#  - FIREBASE_SERVICE_ACCOUNT  (JSON string; in local tests you can use GOOGLE_APPLICATION_CREDENTIALS instead)
#  - FB_BUCKET                 (e.g., 'todai-alpha.firebasestorage.app')

def init():
    sa_json = os.environ.get("FIREBASE_SERVICE_ACCOUNT")
    cred = None
    if sa_json:
        cred = credentials.Certificate(json.loads(sa_json))
    else:
        # fallback for local runs if you prefer the file path env
        cred = credentials.ApplicationDefault()
    firebase_admin.initialize_app(cred, {"storageBucket": os.environ["FB_BUCKET"]})

def run():
    init()
    db = firestore.client()
    bucket = storage.bucket()

    now = datetime.datetime.utcnow()
    yyyy, mm, dd = now.strftime("%Y"), now.strftime("%m"), now.strftime("%d")
    date_key = now.strftime("%Y-%m-%d")

    try:
        # 1) meta JSON
        meta = {
            "date": date_key,
            "title": f"TODAi daily mock {date_key}",
            "tone": "Anchor Calm",
            "sources": ["Mock Source A", "Mock Source B"],
            "status": "mock-generated"
        }
        bucket.blob(f"audio/meta/{date_key}.json").upload_from_string(
            json.dumps(meta), content_type="application/json"
        )

        # 2) placeholder MP3 (0 bytes just to prove pathing)
        bucket.blob(f"audio/briefings/{yyyy}/{mm}/{dd}/brief.mp3").upload_from_string(
            b"", content_type="audio/mpeg"
        )

        # 3) ops log
        db.collection("ops").document(date_key).set({
            "date": date_key,
            "job": "mock_generate",
            "utc": now.isoformat() + "Z",
            "status": "ok"
        }, merge=True)

        print("Nightly mock brief uploaded ✅")
    except Exception as e:
        db.collection("ops").document(date_key).set({
            "date": date_key,
            "job": "mock_generate",
            "utc": now.isoformat() + "Z",
            "status": "error",
            "error": str(e)
        }, merge=True)
        print("Nightly mock brief failed ❌", e, file=sys.stderr)
        raise

if __name__ == "__main__":
    run()
