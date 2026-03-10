"""
Step 1: Fetch Trending Topics
Sources: YouTube API, YouTube scrape, BBC RSS, HackerNews, Guardian RSS,
         AP News RSS, NPR RSS, fallback
Removed: Reuters (dead domain), Reddit (403), Wikipedia (403), Google Trends (404)
"""

import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import random

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()
NEWS_API_KEY    = os.environ.get("NEWS_API_KEY", "").strip()

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
    "Accept": "application/rss+xml, application/xml, text/xml, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


def _parse_rss(url, limit=5):
    """Generic RSS parser — returns list of titles."""
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', r.text)
        root = ET.fromstring(text.encode('utf-8'))
        titles = [item.findtext("title") for item in root.findall(".//item")]
        titles = [t.strip() for t in titles if t and len(t.strip()) > 10]
        return titles[:limit]
    except Exception as e:
        print(f"⚠️  RSS error {url}: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 1: YouTube Data API v3
# ────────────────────────────────────────────────────────────
def fetch_youtube_api():
    if not YOUTUBE_API_KEY:
        print("⚠️  No YOUTUBE_API_KEY — skipping")
        return []
    try:
        r = requests.get(
            "https://www.googleapis.com/youtube/v3/videos",
            params={"part": "snippet", "chart": "mostPopular",
                    "regionCode": "US", "maxResults": 20, "key": YOUTUBE_API_KEY},
            headers=HEADERS, timeout=15
        )
        r.raise_for_status()
        topics = [i["snippet"]["title"] for i in r.json().get("items", [])
                  if i.get("snippet", {}).get("title")]
        print(f"✅ YouTube API: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  YouTube API error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 2: YouTube Trending page scrape
# ────────────────────────────────────────────────────────────
def fetch_youtube_scrape():
    try:
        r = requests.get("https://www.youtube.com/feed/trending",
                         headers=HEADERS, timeout=20)
        r.raise_for_status()
        titles = re.findall(r'"title":\{"runs":\[\{"text":"([^"]{10,100})"\}', r.text)
        seen, unique = set(), []
        for t in titles:
            if t.lower() not in seen:
                seen.add(t.lower())
                unique.append(t)
        print(f"✅ YouTube Scrape: {len(unique[:15])} topics")
        return unique[:15]
    except Exception as e:
        print(f"⚠️  YouTube Scrape error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 3: BBC News RSS
# ────────────────────────────────────────────────────────────
def fetch_bbc_rss():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/technology/rss.xml",
    ]
    topics = []
    for url in feeds:
        topics.extend(_parse_rss(url, limit=5))
    if topics:
        print(f"✅ BBC RSS: {len(topics)} topics")
    return topics


# ────────────────────────────────────────────────────────────
# METHOD 4: HackerNews
# ────────────────────────────────────────────────────────────
def fetch_hackernews():
    try:
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            headers=HEADERS, timeout=10
        )
        r.raise_for_status()
        topics = []
        for story_id in r.json()[:8]:
            try:
                s = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    headers=HEADERS, timeout=5
                ).json()
                title = s.get("title", "")
                if title and len(title) > 10:
                    topics.append(title)
            except Exception:
                pass
        print(f"✅ HackerNews: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  HackerNews error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 5: The Guardian RSS
# ────────────────────────────────────────────────────────────
def fetch_guardian_rss():
    feeds = [
        "https://www.theguardian.com/world/rss",
        "https://www.theguardian.com/technology/rss",
    ]
    topics = []
    for url in feeds:
        topics.extend(_parse_rss(url, limit=5))
    if topics:
        print(f"✅ Guardian RSS: {len(topics)} topics")
    return topics


# ────────────────────────────────────────────────────────────
# METHOD 6: AP News RSS
# ────────────────────────────────────────────────────────────
def fetch_ap_news():
    feeds = [
        "https://feeds.apnews.com/rss/apf-topnews",
        "https://feeds.apnews.com/rss/apf-technology",
        "https://feeds.apnews.com/rss/apf-entertainment",
    ]
    topics = []
    for url in feeds:
        topics.extend(_parse_rss(url, limit=4))
    if topics:
        print(f"✅ AP News RSS: {len(topics)} topics")
    return topics


# ────────────────────────────────────────────────────────────
# METHOD 7: NPR News RSS
# ────────────────────────────────────────────────────────────
def fetch_npr_rss():
    feeds = [
        "https://feeds.npr.org/1001/rss.xml",   # News
        "https://feeds.npr.org/1019/rss.xml",   # Technology
    ]
    topics = []
    for url in feeds:
        topics.extend(_parse_rss(url, limit=4))
    if topics:
        print(f"✅ NPR RSS: {len(topics)} topics")
    return topics


# ────────────────────────────────────────────────────────────
# METHOD 8: NewsAPI (optional key)
# ────────────────────────────────────────────────────────────
def fetch_newsapi():
    if not NEWS_API_KEY:
        return []
    try:
        r = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"country": "us", "pageSize": 20, "apiKey": NEWS_API_KEY},
            headers=HEADERS, timeout=15
        )
        r.raise_for_status()
        topics = [a["title"] for a in r.json().get("articles", []) if a.get("title")][:15]
        print(f"✅ NewsAPI: {len(topics)} topics")
        return topics
    except Exception as e:
        print(f"⚠️  NewsAPI error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 9: Evergreen fallback
# ────────────────────────────────────────────────────────────
def fetch_fallback_topics():
    topics = [
        "AI tools that are changing everything in 2025",
        "The biggest news story nobody is talking about",
        "Top 10 viral moments everyone is watching right now",
        "Why this trend is taking over social media",
        "Secret tricks that will blow your mind",
        "Why millions of people are searching for this right now",
        "The shocking truth behind the latest viral trend",
        "How to go viral on social media in 2025",
        "Things nobody tells you about making money online",
        "The most watched videos on the internet this week",
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

    api_topics      = fetch_youtube_api()
    scrape_topics   = fetch_youtube_scrape()
    bbc_topics      = fetch_bbc_rss()
    hn_topics       = fetch_hackernews()
    guardian_topics = fetch_guardian_rss()
    ap_topics       = fetch_ap_news()
    npr_topics      = fetch_npr_rss()
    news_topics     = fetch_newsapi()

    all_topics = (api_topics + scrape_topics + bbc_topics + hn_topics +
                  guardian_topics + ap_topics + npr_topics + news_topics)

    if not all_topics:
        print("⚠️  All sources failed — using fallback")
        all_topics = fetch_fallback_topics()

    # Deduplicate
    seen, unique = set(), []
    for t in all_topics:
        key = t.lower().strip()
        if key not in seen and len(t) > 5:
            seen.add(key)
            unique.append(t)

    unique   = unique[:limit]
    selected = unique[0] if unique else "Top trending topics this week"

    result = {
        "topic": selected,
        "all_topics": unique,
        "sources_used": {
            "youtube_api":    len(api_topics),
            "youtube_scrape": len(scrape_topics),
            "bbc_rss":        len(bbc_topics),
            "hackernews":     len(hn_topics),
            "guardian_rss":   len(guardian_topics),
            "ap_news":        len(ap_topics),
            "npr_rss":        len(npr_topics),
            "newsapi":        len(news_topics),
        },
        "timestamp": datetime.now().isoformat(),
    }

    print("─" * 40)
    print(f"✅ Selected: {selected}")
    print(f"📊 Total unique: {len(unique)}")

    os.makedirs("output", exist_ok=True)
    with open("output/step1_trends.json", "w") as f:
        json.dump(result, f, indent=2)

    return result


# Aliases
def fetch_trending_topics(limit=10, **kwargs):
    return get_trending_topics(limit=limit)


if __name__ == "__main__":
    result = get_trending_topics()
    print(f"\n📄 Saved to output/step1_trends.json")
