"""
STEP 6: Upload Video to YouTube using YouTube Data API v3
Requires OAuth2 credentials (one-time browser auth)
"""

import os
import json
import time
import pickle
from pathlib import Path

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from googleapiclient.http import MediaFileUpload
from google.auth.transport.requests import Request


SCOPES = ["https://www.googleapis.com/auth/youtube.upload",
          "https://www.googleapis.com/auth/youtube"]

TOKEN_FILE = "youtube_token.pickle"
CREDENTIALS_FILE = "youtube_credentials.json"


def get_youtube_client():
    """Authenticate and return YouTube API client"""
    creds = None

    # Load saved token
    if Path(TOKEN_FILE).exists():
        with open(TOKEN_FILE, "rb") as f:
            creds = pickle.load(f)

    # Refresh or re-authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            if not Path(CREDENTIALS_FILE).exists():
                raise FileNotFoundError(
                    f"Missing {CREDENTIALS_FILE}. Download from Google Cloud Console:\n"
                    "https://console.cloud.google.com/apis/credentials"
                )
            flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                CREDENTIALS_FILE, SCOPES
            )
            creds = flow.run_local_server(port=0)

        # Save token for next run
        with open(TOKEN_FILE, "wb") as f:
            pickle.dump(creds, f)

    return googleapiclient.discovery.build("youtube", "v3", credentials=creds)


def upload_to_youtube(
    video_path: str,
    thumbnail_path: str,
    title: str,
    description: str,
    tags: list,
    category_id: str = "25",       # 25 = News & Politics, 22 = People & Blogs
    privacy: str = "public"        # public | unlisted | private
) -> str:
    """Upload video and thumbnail, return video_id"""

    youtube = get_youtube_client()

    # Truncate title to YouTube's 100 char limit
    title = title[:100]

    body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": tags[:15],  # YouTube max 15 tags
            "categoryId": category_id,
            "defaultLanguage": "en",
        },
        "status": {
            "privacyStatus": privacy,
            "selfDeclaredMadeForKids": False,
        }
    }

    media = MediaFileUpload(
        video_path,
        mimetype="video/mp4",
        chunksize=50 * 1024 * 1024,  # 50MB chunks
        resumable=True
    )

    print(f"   Uploading: {title}")
    request = youtube.videos().insert(
        part=",".join(body.keys()),
        body=body,
        media_body=media
    )

    # Resumable upload with progress
    response = None
    retry = 0
    while response is None:
        try:
            status, response = request.next_chunk()
            if status:
                pct = int(status.progress() * 100)
                print(f"   Upload progress: {pct}%")
        except googleapiclient.errors.HttpError as e:
            if e.resp.status in [500, 502, 503, 504] and retry < 5:
                retry += 1
                wait = 2 ** retry
                print(f"   Retrying in {wait}s...")
                time.sleep(wait)
            else:
                raise

    video_id = response["id"]
    print(f"   Video uploaded: https://youtube.com/watch?v={video_id}")

    # Set thumbnail
    if Path(thumbnail_path).exists():
        youtube.thumbnails().set(
            videoId=video_id,
            media_body=MediaFileUpload(thumbnail_path)
        ).execute()
        print(f"   Thumbnail set ✅")

    return video_id
