"""
Step 7: Send Pipeline Report
- Slack webhook (if SLACK_WEBHOOK_URL set)
- Gmail (if GMAIL_USER + GMAIL_APP_PASSWORD set)
- Logs to file (always works, no config needed)
"""

import os
import json
import smtplib
import requests
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart


SLACK_WEBHOOK  = os.environ.get("SLACK_WEBHOOK_URL", "").strip()
GMAIL_USER     = os.environ.get("GMAIL_USER", "").strip()
GMAIL_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "").strip()


def send_report(topic=None, upload_result=None, state=None, **kwargs):
    """Send pipeline completion report. Accepts any keyword arguments."""
    print(f"\n📊 Sending pipeline report...")

    # ── Build report data from whatever was passed ───────────
    # Support both new style (topic, upload_result, state)
    # and old style (just state dict)
    if state is None:
        state = {}

    if topic is None:
        topic = state.get("topic", "Unknown topic")

    if upload_result is None:
        upload_result = state.get("upload_result")

    video_id  = None
    video_url = None
    if isinstance(upload_result, dict):
        video_id  = upload_result.get("video_id")
        video_url = upload_result.get("url", f"https://youtube.com/watch?v={video_id}" if video_id else None)

    status = "✅ SUCCESS" if upload_result else "⚠️  PARTIAL"

    report = {
        "status":       status,
        "topic":        topic,
        "video_id":     video_id,
        "video_url":    video_url,
        "audio_path":   state.get("audio_path"),
        "video_path":   state.get("video_path"),
        "thumbnail":    state.get("thumbnail_path"),
        "timestamp":    datetime.now().isoformat(),
    }

    print(f"   Status  : {status}")
    print(f"   Topic   : {topic}")
    print(f"   Video   : {video_url or 'Not uploaded'}")

    # ── Always save to log file ──────────────────────────────
    _save_log(report)

    # ── Send Slack notification ──────────────────────────────
    if SLACK_WEBHOOK:
        _send_slack(report)

    # ── Send Gmail notification ──────────────────────────────
    if GMAIL_USER and GMAIL_PASSWORD:
        _send_gmail(report)

    print("✅ Report complete")
    return report


def _save_log(report):
    """Always save report to local log file."""
    try:
        os.makedirs("output", exist_ok=True)
        log_path = "output/pipeline_report.json"

        # Append to history
        history = []
        if os.path.exists(log_path):
            try:
                with open(log_path) as f:
                    existing = json.load(f)
                    history = existing if isinstance(existing, list) else [existing]
            except Exception:
                history = []

        history.append(report)

        with open(log_path, "w") as f:
            json.dump(history[-30:], f, indent=2)  # Keep last 30 runs

        print(f"✅ Report saved to {log_path}")
    except Exception as e:
        print(f"⚠️  Log save error: {e}")


def _send_slack(report):
    """Send Slack webhook notification."""
    try:
        status   = report.get("status", "unknown")
        topic    = report.get("topic", "unknown")
        url      = report.get("video_url", "Not uploaded")
        ts       = report.get("timestamp", "")

        message = {
            "text": f"{status} ViralVortex Pipeline",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": f"{status} ViralVortex Pipeline"}
                },
                {
                    "type": "section",
                    "fields": [
                        {"type": "mrkdwn", "text": f"*Topic:*\n{topic}"},
                        {"type": "mrkdwn", "text": f"*Video:*\n{url}"},
                        {"type": "mrkdwn", "text": f"*Time:*\n{ts}"},
                    ]
                }
            ]
        }

        r = requests.post(SLACK_WEBHOOK, json=message, timeout=10)
        r.raise_for_status()
        print("✅ Slack notification sent")

    except Exception as e:
        print(f"⚠️  Slack error (non-fatal): {e}")


def _send_gmail(report):
    """Send Gmail notification."""
    try:
        status = report.get("status", "unknown")
        topic  = report.get("topic", "unknown")
        url    = report.get("video_url", "Not uploaded")
        ts     = report.get("timestamp", "")

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"ViralVortex {status} — {topic[:50]}"
        msg["From"]    = GMAIL_USER
        msg["To"]      = GMAIL_USER

        body = f"""
ViralVortex Pipeline Report
============================
Status    : {status}
Topic     : {topic}
Video URL : {url}
Time      : {ts}

Audio     : {report.get('audio_path', 'N/A')}
Video     : {report.get('video_path', 'N/A')}
Thumbnail : {report.get('thumbnail', 'N/A')}
        """

        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_PASSWORD)
            server.sendmail(GMAIL_USER, GMAIL_USER, msg.as_string())

        print(f"✅ Gmail notification sent to {GMAIL_USER}")

    except Exception as e:
        print(f"⚠️  Gmail error (non-fatal): {e}")


# Aliases
def generate_report(**kwargs): return send_report(**kwargs)
def create_report(**kwargs):   return send_report(**kwargs)
def report(**kwargs):          return send_report(**kwargs)


if __name__ == "__main__":
    send_report(
        topic="Test topic",
        upload_result={"video_id": "test123", "url": "https://youtube.com/watch?v=test123"},
        state={"audio_path": "output/audio.mp3", "video_path": "output/video.mp4"},
    )
