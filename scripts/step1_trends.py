"""
Step 1: Fetch Trending Topics
Fixed version — handles malformed RSS, encoding issues, and API fallbacks
"""

import os
import json
import re
import requests
from datetime import datetime

# ── Optional imports (graceful fallback if not installed) ──
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

try:
    import xml.etree.ElementTree as ET
    ET_AVAILABLE = True
except ImportError:
    ET_AVAILABLE = False


YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


# ────────────────────────────────────────────────────────────
# METHOD 1: YouTube RSS Feed (Fixed)
# ────────────────────────────────────────────────────────────
def fetch_youtube_rss():
    """Fetch trending video titles via YouTube RSS — with robust XML handling."""
    trending_topics = []

    # Multiple RSS feed URLs to try
    rss_urls = [
        "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&hl=en&gl=US",
        "https://www.youtube.com/feeds/videos.xml?chart=mostPopular",
    ]

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
        "Accept-Language": "en-US,en;q=0.9",
    }

    for url in rss_urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()

            # ── FIX 1: Clean the raw XML before parsing ──
            raw = response.content

            # Remove BOM if present
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]

            # Decode safely
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')

            # Remove invalid XML characters (the main cause of your error)
            # This removes control characters except tab, newline, carriage return
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

            # Fix any broken ampersands not part of entities
            text = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', text)

            # ── FIX 2: Parse cleaned XML ──
            root = ET.fromstring(text.encode('utf-8'))

            # Handle both Atom and RSS namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'media': 'http://search.yahoo.com/mrss/',
                'yt': 'http://www.youtube.com/xml/schemas/2015',
            }

            # Try Atom feed format (YouTube uses Atom)
            entries = root.findall('.//atom:entry', namespaces)
            if not entries:
                # Fallback: no namespace
                entries = root.findall('.//entry')

            for entry in entries[:15]:
                # Try multiple ways to get the title
                title = None
                for tag in ['atom:title', 'title']:
                    elem = entry.find(tag, namespaces) if ':' in tag else entry.find(tag)
                    if elem is not None and elem.text:
                        title = elem.text.strip()
                        break

                if title and len(title) > 3:
                    trending_topics.append(title)

            if trending_topics:
                print(f"✅ YouTube RSS: fetched {len(trending_topics)} topics")
                return trending_topics

        except ET.ParseError as e:
            print(f"⚠️  YouTube RSS XML parse error: {e} — trying fallback...")
            continue
        except requests.RequestException as e:
            print(f"⚠️  YouTube RSS request error: {e} — trying fallback...")
            continue
        except Exception as e:
            print(f"⚠️  YouTube RSS unexpected error: {e} — trying fallback...")
            continue

    print("⚠️  All YouTube RSS attempts failed — moving to next source")
    return []


# ────────────────────────────────────────────────────────────
# METHOD 2: YouTube Data API v3
# ────────────────────────────────────────────────────────────
def fetch_youtube_api():
    """Fetch trending videos via official YouTube Data API."""
    if not YOUTUBE_API_KEY:
        print("⚠️  No YOUTUBE_API_KEY — skipping YouTube API")
        return []

    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet",
            "chart": "mostPopular",
            "regionCode": "US",
            "maxResults": 20,
            "key": YOUTUBE_API_KEY,
        }
        response = requests.get(url, params=params, timeout=15)
        response.raise_for_status()
        data = response.json()

        topics = []
        for item in data.get("items", []):
            title = item.get("snippet", {}).get("title", "")
            if title:
                topics.append(title)

        print(f"✅ YouTube API: fetched {len(topics)} topics")
        return topics

    except Exception as e:
        print(f"⚠️  YouTube API error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 3: Google Trends via pytrends
# ────────────────────────────────────────────────────────────
def fetch_google_trends():
    """Fetch trending searches from Google Trends."""
    if not PYTRENDS_AVAILABLE:
        print("⚠️  pytrends not installed — skipping Google Trends")
        return []

    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        trending_df = pytrends.trending_searches(pn='united_states')
        topics = trending_df[0].tolist()[:15]
        print(f"✅ Google Trends: fetched {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  Google Trends error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 4: Hardcoded evergreen fallback topics
# ────────────────────────────────────────────────────────────
def fetch_fallback_topics():
    """Always-available fallback topics when all APIs fail."""
    import random
    topics = [
        "AI tools that will blow your mind in 2025",
        "Things nobody tells you about making money online",
        "Why everyone is switching to this new technology",
        "The truth about viral social media trends",
        "Top 10 things trending on the internet right now",
        "Secret tricks big companies don't want you to know",
        "Why this video went viral overnight",
        "The most searched topics on Google this week",
        "Hidden features you never knew existed",
        "Why millennials are obsessed with this trend",
    ]
    random.shuffle(topics)
    print(f"✅ Fallback topics: using {len(topics[:5])} evergreen topics")
    return topics[:5]


# ────────────────────────────────────────────────────────────
# MAIN: Run all methods, combine results
# ────────────────────────────────────────────────────────────
def get_trending_topics():
    """Get trending topics from all available sources."""
    print("\n🔍 Fetching trending topics...")
    print("─" * 40)

    all_topics = []

    # Try each source in order of preference
    rss_topics = fetch_youtube_rss()
    all_topics.extend(rss_topics)

    api_topics = fetch_youtube_api()
    all_topics.extend(api_topics)

    trend_topics = fetch_google_trends()
    all_topics.extend(trend_topics)

    # If everything failed, use fallback
    if not all_topics:
        print("⚠️  All sources failed — using fallback topics")
        all_topics = fetch_fallback_topics()

    # Deduplicate while preserving order
    seen = set()
    unique_topics = []
    for topic in all_topics:
        key = topic.lower().strip()
        if key not in seen and len(topic) > 3:
            seen.add(key)
            unique_topics.append(topic)

    # Pick the best topic (first one = most trending)
    selected = unique_topics[0] if unique_topics else "Top trending topics this week"

    result = {
        "topic": selected,
        "all_topics": unique_topics[:20],
        "sources_used": {
            "youtube_rss": len(rss_topics),
            "youtube_api": len(api_topics),
            "google_trends": len(trend_topics),
        },
        "timestamp": datetime.now().isoformat(),
    }

    print("─" * 40)
    print(f"✅ Selected topic: {selected}")
    print(f"📊 Total topics found: {len(unique_topics)}")

    # Save result
    os.makedirs("output", exist_ok=True)
    with open("output/step1_trends.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


if __name__ == "__main__":
    result = get_trending_topics()
    print("\n📄 Result saved to output/step1_trends.json")
