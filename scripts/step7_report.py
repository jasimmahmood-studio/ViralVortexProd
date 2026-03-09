"""
STEP 7: Send Daily Report via Slack Webhook and/or Email
"""

import os
import json
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime


def send_slack_report(results: dict):
    """Send summary to Slack channel"""
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL", "")
    if not webhook_url:
        print("   Slack webhook not configured, skipping.")
        return

    upload = results.get("steps", {}).get("upload", {})
    video_url = upload.get("url", "N/A")
    topic = results.get("steps", {}).get("trends", {}).get("topic", "Unknown")
    run_id = results.get("run_id", "")
    status = "✅ SUCCESS" if "error" not in results else f"❌ FAILED: {results['error']}"

    message = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": "🌀 ViralVortex Daily Upload Report"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Status:*\n{status}"},
                    {"type": "mrkdwn", "text": f"*Run ID:*\n`{run_id}`"},
                    {"type": "mrkdwn", "text": f"*Topic:*\n{topic}"},
                    {"type": "mrkdwn", "text": f"*Video URL:*\n{video_url}"},
                    {"type": "mrkdwn", "text": f"*Time:*\n{datetime.now().strftime('%Y-%m-%d %H:%M')}"},
                ]
            },
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "▶ Watch on YouTube"},
                        "url": video_url,
                        "style": "primary"
                    }
                ]
            }
        ]
    }

    res = requests.post(webhook_url, json=message, timeout=10)
    if res.status_code == 200:
        print("   ✅ Slack report sent")
    else:
        print(f"   Slack failed: {res.status_code}")


def send_email_report(results: dict):
    """Send summary via email (Gmail SMTP)"""
    smtp_user = os.environ.get("GMAIL_USER", "")
    smtp_pass = os.environ.get("GMAIL_APP_PASSWORD", "")
    to_email  = os.environ.get("REPORT_EMAIL", smtp_user)

    if not smtp_user or not smtp_pass:
        print("   Gmail not configured, skipping email.")
        return

    upload = results.get("steps", {}).get("upload", {})
    video_url = upload.get("url", "N/A")
    topic = results.get("steps", {}).get("trends", {}).get("topic", "Unknown")
    status = "SUCCESS" if "error" not in results else f"FAILED"

    subject = f"[ViralVortex] Daily Upload {status} — {datetime.now().strftime('%Y-%m-%d')}"

    html = f"""
    <html><body style="font-family:monospace;background:#00040f;color:#e8f4ff;padding:20px;">
    <h1 style="color:#00f5ff;">🌀 ViralVortex Daily Report</h1>
    <table style="border-collapse:collapse;width:100%;">
      <tr><td style="padding:8px;color:#3a5a7a;">Status</td>
          <td style="padding:8px;color:{'#00ff88' if status == 'SUCCESS' else '#ff3366'}">
            {'✅ ' + status}
          </td></tr>
      <tr><td style="padding:8px;color:#3a5a7a;">Topic</td>
          <td style="padding:8px;">{topic}</td></tr>
      <tr><td style="padding:8px;color:#3a5a7a;">Video URL</td>
          <td style="padding:8px;"><a href="{video_url}" style="color:#00f5ff;">{video_url}</a></td></tr>
      <tr><td style="padding:8px;color:#3a5a7a;">Time</td>
          <td style="padding:8px;">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</td></tr>
    </table>
    <p style="margin-top:20px;">
      <a href="{video_url}" style="background:#00f5ff;color:#00040f;padding:12px 24px;
         text-decoration:none;border-radius:6px;font-weight:bold;">
        ▶ Watch on YouTube
      </a>
    </p>
    </body></html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_user
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(smtp_user, smtp_pass)
            server.sendmail(smtp_user, to_email, msg.as_string())
        print(f"   ✅ Email report sent to {to_email}")
    except Exception as e:
        print(f"   Email failed: {e}")


def send_report(results: dict):
    """Send reports via all configured channels"""
    send_slack_report(results)
    send_email_report(results)
