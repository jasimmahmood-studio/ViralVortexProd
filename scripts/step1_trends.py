"""
Step 1: Fetch Trending Topics
Sources: YouTube API, YouTube scrape, BBC RSS, HackerNews, Wikipedia, fallback
Reddit and Google Trends removed (both blocked)
"""

import os
import json
import re
import requests
import xml.etree.ElementTree as ET
from datetime import datetime
import random

YOUTUBE_API_KEY = os.environ.get("YOUTUBE_API_KEY", "").strip()


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
            timeout=15
        )
        r.raise_for_status()
        topics = [i["snippet"]["title"] for i in r.json().get("items", []) if i.get("snippet", {}).get("title")]
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
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        }
        r = requests.get("https://www.youtube.com/feed/trending", headers=headers, timeout=20)
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
# METHOD 3: BBC News RSS (always works)
# ────────────────────────────────────────────────────────────
def fetch_bbc_rss():
    feeds = [
        "http://feeds.bbci.co.uk/news/rss.xml",
        "http://feeds.bbci.co.uk/news/world/rss.xml",
        "http://feeds.bbci.co.uk/news/technology/rss.xml",
    ]
    topics = []
    for url in feeds:
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            # Clean XML
            text = r.text
            text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
            root = ET.fromstring(text.encode('utf-8'))
            titles = [item.findtext("title") for item in root.findall(".//item")]
            titles = [t.strip() for t in titles if t and len(t.strip()) > 10]
            topics.extend(titles[:5])
        except Exception as e:
            print(f"⚠️  BBC RSS {url} error: {e}")
    if topics:
        print(f"✅ BBC RSS: {len(topics)} topics")
    return topics


# ────────────────────────────────────────────────────────────
# METHOD 4: HackerNews Top Stories (always works, no auth)
# ────────────────────────────────────────────────────────────
def fetch_hackernews():
    try:
        r = requests.get(
            "https://hacker-news.firebaseio.com/v0/topstories.json",
            timeout=10
        )
        r.raise_for_status()
        ids = r.json()[:10]
        topics = []
        for story_id in ids:
            try:
                story = requests.get(
                    f"https://hacker-news.firebaseio.com/v0/item/{story_id}.json",
                    timeout=5
                ).json()
                title = story.get("title", "")
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
# METHOD 5: Wikipedia Current Events (always works, no auth)
# ────────────────────────────────────────────────────────────
def fetch_wikipedia_trending():
    try:
        from datetime import date
        today = date.today()
        url = f"https://en.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "list": "mostviewed",
            "pvimoffset": 0,
            "pvimtop": 20,
            "pvimlimit": 20,
            "format": "json",
        }
        r = requests.get(url, params=params, timeout=15)
        r.raise_for_status()
        pages = r.json().get("query", {}).get("mostviewed", [])
        topics = []
        skip = {"Main_Page", "Special:Search", "-", "Wikipedia", ""}
        for p in pages:
            title = p.get("title", "").replace("_", " ").strip()
            if title and title not in skip and len(title) > 3:
                topics.append(title)
        print(f"✅ Wikipedia Trending: {len(topics)} topics")
        return topics[:10]
    except Exception as e:
        print(f"⚠️  Wikipedia error: {e}")
        return []


# ────────────────────────────────────────────────────────────
# METHOD 6: Evergreen fallback
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

    api_topics   = fetch_youtube_api()
    scrape_topics = fetch_youtube_scrape()
    bbc_topics   = fetch_bbc_rss()
    hn_topics    = fetch_hackernews()
    wiki_topics  = fetch_wikipedia_trending()

    all_topics = api_topics + scrape_topics + bbc_topics + hn_topics + wiki_topics

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

    unique = unique[:limit]
    selected = unique[0] if unique else "Top trending topics this week"

    result = {
        "topic": selected,
        "all_topics": unique,
        "sources_used": {
            "youtube_api":    len(api_topics),
            "youtube_scrape": len(scrape_topics),
            "bbc_rss":        len(bbc_topics),
            "hackernews":     len(hn_topics),
            "wikipedia":      len(wiki_topics),
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
