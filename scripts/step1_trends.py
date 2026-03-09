"""
Step 1: Fetch Trending Topics
- Removed broken YouTube RSS (400 error)
- Uses YouTube Data API v3, Google Trends, scraping fallback, evergreen fallback
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

YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY", "")


# ────────────────────────────────────────────────────────────
# METHOD 1: YouTube Data API v3 (most reliable)
# ────────────────────────────────────────────────────────────
def fetch_youtube_api():
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
        topics = [
            item["snippet"]["title"]
            for item in response.json().get("items", [])
            if item.get("snippet", {}).get("title")
        ]
        print(f"✅ YouTube API: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  YouTube API error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 2: Google Trends via pytrends
# ────────────────────────────────────────────────────────────
def fetch_google_trends():
    if not PYTRENDS_AVAILABLE:
        print("⚠️  pytrends not installed — skipping")
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


# ────────────────────────────────────────────────────────────
# METHOD 3: YouTube Trending page scrape (no API key needed)
# ────────────────────────────────────────────────────────────
def fetch_youtube_scrape():
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        response = requests.get(
            "https://www.youtube.com/feed/trending",
            headers=headers,
            timeout=20
        )
        response.raise_for_status()

        # Extract video titles from the page HTML
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]{10,100})"\}', response.text)

        # Deduplicate
        seen, unique = set(), []
        for t in titles:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique.append(t)

        topics = unique[:15]
        if topics:
            print(f"✅ YouTube Scrape: {len(topics)} topics")
        else:
            print("⚠️  YouTube Scrape: no titles found in page")
        return topics
    except Exception as e:
        print(f"⚠️  YouTube Scrape error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 4: Reddit trending (r/trending, r/popular)
# ────────────────────────────────────────────────────────────
def fetch_reddit_trending():
    try:
        headers = {"User-Agent": "ViralVortex/1.0 trending-bot"}
        response = requests.get(
            "https://www.reddit.com/r/popular.json?limit=20",
            headers=headers,
            timeout=15
        )
        response.raise_for_status()
        posts = response.json().get("data", {}).get("children", [])
        topics = [
            p["data"]["title"]
            for p in posts
            if p.get("data", {}).get("title")
        ][:15]
        print(f"✅ Reddit Trending: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  Reddit error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 5: Evergreen fallback (always works)
# ────────────────────────────────────────────────────────────
def fetch_fallback_topics():
    import random
    topics = [
        "AI tools that will change everything in 2025",
        "Things nobody tells you about making money online",
        "Why everyone is switching to this new technology",
        "The truth about viral social media trends",
        "Top 10 things trending on the internet right now",
        "Secret tricks big companies don't want you to know",
        "Why this video went viral overnight",
        "The most searched topics on Google this week",
        "Hidden features you never knew existed",
        "Why this trend is taking over the internet",
        "The biggest news story nobody is talking about",
        "How to go viral on social media in 2025",
        "The shocking truth behind this viral trend",
        "Why millions are watching this right now",
        "What everyone is searching for this week",
    ]
    random.shuffle(topics)
    print(f"✅ Fallback: using evergreen topics")
    return topics


# ────────────────────────────────────────────────────────────
# MAIN
# ────────────────────────────────────────────────────────────
def get_trending_topics(limit=10, **kwargs):
    print("\n🔍 Fetching trending topics...")
    print("─" * 40)

    all_topics    = []
    api_topics    = fetch_youtube_api()
    trend_topics  = fetch_google_trends()
    scrape_topics = fetch_youtube_scrape()
    reddit_topics = fetch_reddit_trending()

    all_topics = api_topics + trend_topics + scrape_topics + reddit_topics

    if not all_topics:
        print("⚠️  All sources failed — using fallback topics")
        all_topics = fetch_fallback_topics()

    # Deduplicate
    seen, unique_topics = set(), []
    for topic in all_topics:
        key = topic.lower().strip()
        if key not in seen and len(topic) > 5:
            seen.add(key)
            unique_topics.append(topic)

    unique_topics = unique_topics[:limit]
    selected = unique_topics[0] if unique_topics else "Top trending topics this week"

    result = {
        "topic": selected,
        "all_topics": unique_topics,
        "sources_used": {
            "youtube_api":   len(api_topics),
            "google_trends": len(trend_topics),
            "youtube_scrape": len(scrape_topics),
            "reddit":        len(reddit_topics),
        },
        "timestamp": datetime.now().isoformat(),
    }

    print("─" * 40)
    print(f"✅ Selected topic: {selected}")
    print(f"📊 Total unique topics: {len(unique_topics)}")

    os.makedirs("output", exist_ok=True)
    with open("output/step1_trends.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


# Backward-compatible alias
def fetch_trending_topics(limit=10, **kwargs):
    return get_trending_topics(limit=limit)


if __name__ == "__main__":
    result = get_trending_topics()
    print("\n📄 Saved to output/step1_trends.json")
