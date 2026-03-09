# 🌀 ViralVortex — Daily YouTube Automation Engine

Automatically fetches trending topics, generates a video script with Claude AI,
creates a voiceover, renders a video, and uploads it to your YouTube channel — every day.

---

## 🗂️ Project Structure

```
viralvortex/
├── main.py                  ← Orchestrator (runs all 7 steps)
├── scheduler.py             ← Daily cron scheduler
├── requirements.txt         ← Python dependencies
├── .env.example             ← API keys template
├── youtube_credentials.json ← (you create this)
├── scripts/
│   ├── step1_trends.py      ← Fetch YouTube + Google trends
│   ├── step2_script.py      ← Claude AI script generation
│   ├── step3_voice.py       ← ElevenLabs / gTTS voiceover
│   ├── step4_video.py       ← FFmpeg video rendering
│   ├── step5_thumbnail.py   ← Pillow / DALL-E thumbnail
│   ├── step6_upload.py      ← YouTube Data API upload
│   └── step7_report.py      ← Slack + Email reporting
└── output/                  ← Generated files (auto-created)
```

---

## ⚡ Quick Start (5 Steps)

### 1. Install dependencies

```bash
# Install FFmpeg (required for video rendering)
sudo apt install ffmpeg          # Ubuntu/Debian
brew install ffmpeg              # macOS

# Install Python packages
pip install -r requirements.txt
```

### 2. Configure API keys

```bash
cp .env.example .env
nano .env   # Fill in your API keys
```

**Required keys:**
| Key | Where to get |
|-----|-------------|
| `ANTHROPIC_API_KEY` | https://console.anthropic.com |
| `YOUTUBE_API_KEY` | https://console.cloud.google.com |

**Optional (recommended):**
| Key | Where to get |
|-----|-------------|
| `ELEVENLABS_API_KEY` | https://elevenlabs.io |
| `PEXELS_API_KEY` | https://www.pexels.com/api |
| `OPENAI_API_KEY` | https://platform.openai.com (for DALL-E thumbnails) |
| `SLACK_WEBHOOK_URL` | https://api.slack.com/apps |

### 3. Set up YouTube OAuth (one-time)

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project → Enable **YouTube Data API v3**
3. Go to **Credentials** → Create **OAuth 2.0 Client ID** (Desktop app)
4. Download the JSON → Save as `youtube_credentials.json` in the project folder
5. Run once to authorize: `python main.py` → browser will open for permission

### 4. Test the pipeline

```bash
source .env
python scheduler.py --now
```

This runs the full pipeline immediately. Check the `output/` folder for generated files.

### 5. Start the daily scheduler

```bash
# Run in background on a VPS
nohup python scheduler.py &

# Or set up a system cron job
crontab -e
# Add: 0 6 * * * cd /path/to/viralvortex && python main.py >> viralvortex.log 2>&1
```

---

## 🚀 Deploy on a VPS (Recommended)

For reliable 24/7 automation, deploy on a cheap VPS:

**Option A: Railway (easiest, ~$5/month)**
```bash
railway login
railway init
railway up
```

**Option B: DigitalOcean / Hetzner ($4–6/month)**
```bash
# On your VPS:
git clone your-repo
cd viralvortex
pip install -r requirements.txt
cp .env.example .env && nano .env
# Run as systemd service (see below)
```

**Systemd service (auto-restart on crash):**
```ini
# /etc/systemd/system/viralvortex.service
[Unit]
Description=ViralVortex YouTube Automation
After=network.target

[Service]
WorkingDirectory=/home/ubuntu/viralvortex
EnvironmentFile=/home/ubuntu/viralvortex/.env
ExecStart=/usr/bin/python3 scheduler.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
```bash
sudo systemctl enable viralvortex
sudo systemctl start viralvortex
sudo systemctl status viralvortex
```

---

## 💡 No-Code Alternative: n8n

If you prefer a visual workflow, use **n8n** instead of running Python:

```bash
npx n8n   # starts n8n at http://localhost:5678
```

Then build this flow visually:
```
[Cron 6AM] → [HTTP: Google Trends] → [Claude AI Node] 
           → [ElevenLabs Node] → [Code: FFmpeg] 
           → [YouTube Upload] → [Slack Notification]
```

---

## 📊 Expected Performance

| Metric | Estimate |
|--------|----------|
| Pipeline duration | ~35–45 min |
| Video length | 7–9 minutes |
| Monthly cost | $19–57 |
| Break-even views | ~5,000–15,000/month |
| RPM (ad revenue) | $3–8 per 1,000 views |

---

## 🔧 Troubleshooting

**FFmpeg not found:** `sudo apt install ffmpeg`

**YouTube auth error:** Delete `youtube_token.pickle` and re-run to re-authorize

**ElevenLabs quota exceeded:** Script auto-falls back to gTTS (free, lower quality)

**Pexels returns no clips:** Video uses animated background fallback

**Rate limits:** Add `time.sleep(2)` between API calls if hitting limits
