"""
Step 6: Upload Video to YouTube
- Uses OAuth2 token (YOUTUBE_TOKEN_B64 env var)
- Full error logging to diagnose issues
"""

import os
import json
import base64
import pickle
import tempfile
from datetime import datetime


def upload_video(video_path, title, description, thumbnail_path=None, **kwargs):
    print(f"\n🚀 Uploading to YouTube...")
    print(f"   Video     : {video_path}")
    print(f"   Title     : {title}")
    print(f"   Thumbnail : {thumbnail_path}")

    # ── Check video file ─────────────────────────────────────
    if not video_path or not os.path.exists(video_path):
        raise ValueError(f"Video file not found: {video_path}")

    size = os.path.getsize(video_path)
    print(f"   File size : {size:,} bytes ({size/1024/1024:.1f} MB)")

    if size < 1000:
        raise ValueError(f"Video file too small ({size} bytes) — probably corrupted")

    # ── Load OAuth token ─────────────────────────────────────
    creds = _load_credentials()
    if not creds:
        raise ValueError(
            "No YouTube OAuth token found.\n"
            "Set YOUTUBE_TOKEN_B64 in Railway Variables.\n"
            "Generate it locally with: python step6_upload.py --auth"
        )

    # ── Build YouTube client ─────────────────────────────────
    try:
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import google.auth.transport.requests

        # Refresh token if expired
        if creds.expired and creds.refresh_token:
            print("🔄 Refreshing OAuth token...")
            creds.refresh(google.auth.transport.requests.Request())
            _save_credentials(creds)

        youtube = build("youtube", "v3", credentials=creds)
        print("✅ YouTube client built")

    except ImportError as e:
        raise ImportError(f"Missing Google API packages: {e}\nRun: pip install google-api-python-client google-auth-oauthlib")
    except Exception as e:
        raise RuntimeError(f"Failed to build YouTube client: {e}")

    # ── Upload video ─────────────────────────────────────────
    try:
        print("📤 Starting upload...")

        body = {
            "snippet": {
                "title":       title[:100],
                "description": description[:5000],
                "tags":        ["ViralVortex", "Trending", "Viral", "News"],
                "categoryId":  "25",  # News & Politics
            },
            "status": {
                "privacyStatus":           "public",
                "selfDeclaredMadeForKids": False,
            },
        }

        media = MediaFileUpload(
            video_path,
            mimetype="video/mp4",
            resumable=True,
            chunksize=1024*1024*5  # 5MB chunks
        )

        request = youtube.videos().insert(
            part="snippet,status",
            body=body,
            media_body=media,
        )

        response = None
        last_progress = 0
        while response is None:
            status, response = request.next_chunk()
            if status:
                progress = int(status.progress() * 100)
                if progress >= last_progress + 10:
                    print(f"   Upload progress: {progress}%")
                    last_progress = progress

        video_id = response.get("id", "")
        print(f"✅ Uploaded! Video ID: {video_id}")
        print(f"🔗 URL: https://www.youtube.com/watch?v={video_id}")

    except Exception as e:
        err = str(e)
        if "uploadLimitExceeded" in err:
            raise RuntimeError(
                "UPLOAD_LIMIT_EXCEEDED: YouTube daily upload limit reached.\n"
                "Solutions:\n"
                "  1. Verify your phone at youtube.com/verify\n"
                "  2. Set VIDEOS_PER_RUN=3 in Railway Variables\n"
                "  3. Wait 24 hours for limit to reset"
            )
        raise RuntimeError(f"Video upload failed: {e}")

    # ── Upload thumbnail ─────────────────────────────────────
    if thumbnail_path and os.path.exists(thumbnail_path) and video_id:
        try:
            youtube.thumbnails().set(
                videoId=video_id,
                media_body=MediaFileUpload(thumbnail_path, mimetype="image/jpeg")
            ).execute()
            print(f"✅ Thumbnail uploaded")
        except Exception as e:
            print(f"⚠️  Thumbnail upload failed (non-fatal): {e}")

    result = {
        "video_id":  video_id,
        "url":       f"https://www.youtube.com/watch?v={video_id}",
        "title":     title,
        "timestamp": datetime.now().isoformat(),
    }

    os.makedirs("output", exist_ok=True)
    with open("output/step6_upload.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


def _load_credentials():
    """Load OAuth credentials from env var or local file."""
    # Try env var first (Railway)
    token_b64 = os.environ.get("YOUTUBE_TOKEN_B64", "").strip()
    if token_b64:
        try:
            token_bytes = base64.b64decode(token_b64)
            creds = pickle.loads(token_bytes)
            print("✅ OAuth token loaded from YOUTUBE_TOKEN_B64")
            return creds
        except Exception as e:
            print(f"⚠️  Failed to decode YOUTUBE_TOKEN_B64: {e}")
            print(f"   Token preview: {token_b64[:30]}...")

    # Try local pickle file
    local_paths = ["youtube_token.pickle", "token.pickle", "credentials.pickle"]
    for path in local_paths:
        if os.path.exists(path):
            try:
                with open(path, "rb") as f:
                    creds = pickle.load(f)
                print(f"✅ OAuth token loaded from {path}")
                return creds
            except Exception as e:
                print(f"⚠️  Failed to load {path}: {e}")

    print("❌ No OAuth token found")
    print("   Set YOUTUBE_TOKEN_B64 in Railway Variables")
    return None


def _save_credentials(creds):
    """Save refreshed credentials back to env-compatible format."""
    try:
        token_bytes = pickle.dumps(creds)
        token_b64 = base64.b64encode(token_bytes).decode()
        # Save locally for reference
        with open("output/token_refreshed.txt", "w") as f:
            f.write(token_b64)
        print("✅ Refreshed token saved to output/token_refreshed.txt")
        print("   Update YOUTUBE_TOKEN_B64 in Railway with this new value")
    except Exception as e:
        print(f"⚠️  Could not save refreshed token: {e}")


def _run_auth_flow():
    """Run OAuth flow locally to generate token. Run with: python step6_upload.py --auth"""
    print("\n🔑 Running YouTube OAuth flow...")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        SCOPES = [
            "https://www.googleapis.com/auth/youtube.upload",
            "https://www.googleapis.com/auth/youtube",
        ]
        secrets_files = ["client_secrets.json", "client_secret.json", "credentials.json"]
        secrets_file  = next((f for f in secrets_files if os.path.exists(f)), None)

        if not secrets_file:
            print("❌ client_secrets.json not found!")
            print("   Download it from Google Cloud Console → Credentials → OAuth Client → Download JSON")
            return

        flow  = InstalledAppFlow.from_client_secrets_file(secrets_file, SCOPES)
        creds = flow.run_local_server(port=0)

        # Save pickle
        with open("youtube_token.pickle", "wb") as f:
            pickle.dump(creds, f)
        print("✅ Token saved to youtube_token.pickle")

        # Print base64 for Railway
        token_b64 = base64.b64encode(pickle.dumps(creds)).decode()
        print("\n" + "=" * 60)
        print("Copy this value to Railway as YOUTUBE_TOKEN_B64:")
        print("=" * 60)
        print(token_b64)
        print("=" * 60)

    except Exception as e:
        print(f"❌ Auth flow failed: {e}")


# Aliases
def upload(video_path, title, description, thumbnail_path=None, **kwargs):
    return upload_video(video_path, title, description, thumbnail_path, **kwargs)

def youtube_upload(video_path, title, description, thumbnail_path=None, **kwargs):
    return upload_video(video_path, title, description, thumbnail_path, **kwargs)


if __name__ == "__main__":
    import sys
    if "--auth" in sys.argv:
        _run_auth_flow()
    else:
        print("Run with --auth to generate OAuth token")
        print("Example: python step6_upload.py --auth")
