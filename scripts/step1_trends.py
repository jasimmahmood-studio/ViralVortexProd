"""
Step 1: Fetch Trending Topics
Fixed — handles RSS errors, encoding issues, limit param, and API fallbacks
"""

import os
import json
import re
import requests
from datetime import datetime

# Optional imports
try:
    from pytrends.request import TrendReq
    PYTRENDS_AVAILABLE = True
except ImportError:
    PYTRENDS_AVAILABLE = False

import xml.etree.ElementTree as ET

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


def fetch_youtube_rss():
    trending_topics = []
    rss_urls = [
        "https://www.youtube.com/feeds/videos.xml?chart=mostPopular&hl=en&gl=US",
        "https://www.youtube.com/feeds/videos.xml?chart=mostPopular",
    ]
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/rss+xml, application/xml, text/xml, */*",
    }

    for url in rss_urls:
        try:
            response = requests.get(url, headers=headers, timeout=15)
            response.raise_for_status()
            raw = response.content

            # Remove BOM
            if raw.startswith(b'\xef\xbb\xbf'):
                raw = raw[3:]

            # Decode
            try:
                text = raw.decode('utf-8')
            except UnicodeDecodeError:
                text = raw.decode('latin-1')

            # Remove invalid XML control characters
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

            # Fix broken ampersands
            text = re.sub(r'&(?!(amp|lt|gt|quot|apos|#\d+|#x[0-9a-fA-F]+);)', '&amp;', text)

            root = ET.fromstring(text.encode('utf-8'))
            namespaces = {'atom': 'http://www.w3.org/2005/Atom'}

            entries = root.findall('.//atom:entry', namespaces)
            if not entries:
                entries = root.findall('.//entry')

            for entry in entries[:15]:
                title = None
                for tag in ['atom:title', 'title']:
                    ns = namespaces if ':' in tag else {}
                    elem = entry.find(tag, ns) if ns else entry.find(tag)
                    if elem is not None and elem.text:
                        title = elem.text.strip()
                        break
                if title and len(title) > 3:
                    trending_topics.append(title)

            if trending_topics:
                print(f"✅ YouTube RSS: {len(trending_topics)} topics")
                return trending_topics

        except ET.ParseError as e:
            print(f"⚠️  RSS parse error: {e}")
        except Exception as e:
            print(f"⚠️  RSS error: {e}")

    return []


def fetch_youtube_api():
    if not YOUTUBE_API_KEY:
        print("⚠️  No YOUTUBE_API_KEY — skipping")
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
        topics = [i["snippet"]["title"] for i in response.json().get("items", [])]
        print(f"✅ YouTube API: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  YouTube API error: {e}")
        return []


def fetch_google_trends():
    if not PYTRENDS_AVAILABLE:
        return []
    try:
        pytrends = TrendReq(hl='en-US', tz=360, timeout=(10, 25))
        df = pytrends.trending_searches(pn='united_states')
        topics = df[0].tolist()[:15]
        print(f"✅ Google Trends: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  Google Trends error: {e}")
        return []


def fetch_fallback_topics():
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
    return topics


def get_trending_topics(limit=10, **kwargs):
    """Main function — fetches trending topics from all sources."""
    print("\n🔍 Fetching trending topics...")
    print("─" * 40)

    all_topics = []
    rss_topics    = fetch_youtube_rss()
    api_topics    = fetch_youtube_api()
    trend_topics  = fetch_google_trends()

    all_topics = rss_topics + api_topics + trend_topics

    if not all_topics:
        print("⚠️  All sources failed — using fallback topics")
        all_topics = fetch_fallback_topics()

    # Deduplicate
    seen, unique_topics = set(), []
    for topic in all_topics:
        key = topic.lower().strip()
        if key not in seen and len(topic) > 3:
            seen.add(key)
            unique_topics.append(topic)

    unique_topics = unique_topics[:limit]
    selected = unique_topics[0] if unique_topics else "Top trending topics this week"

    result = {
        "topic": selected,
        "all_topics": unique_topics,
        "sources_used": {
            "youtube_rss":    len(rss_topics),
            "youtube_api":    len(api_topics),
            "google_trends":  len(trend_topics),
        },
        "timestamp": datetime.now().isoformat(),
    }

    print("─" * 40)
    print(f"✅ Selected topic: {selected}")
    print(f"📊 Total topics: {len(unique_topics)}")

    os.makedirs("output", exist_ok=True)
    with open("output/step1_trends.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


# ── Alias — keeps backward compatibility with any call signature ──
def fetch_trending_topics(limit=10, **kwargs):
    """Backward-compatible alias for get_trending_topics()."""
    return get_trending_topics(limit=limit)


if __name__ == "__main__":
    result = get_trending_topics()
    print("\n📄 Saved to output/step1_trends.json")
