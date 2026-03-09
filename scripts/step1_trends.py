"""
STEP 1: Fetch Trending Topics
Sources: YouTube Trending (RSS) + Google Trends + RapidAPI
"""

import os
import re
import json
import requests
import xml.etree.ElementTree as ET
from pytrends.request import TrendReq


def fetch_youtube_trending_rss():
    """Fetch trending from YouTube RSS (no API key needed)"""
    url = "https://www.youtube.com/feeds/videos.xml?chart=mostpopular&hl=en&regionCode=US"
    try:
        res = requests.get(url, timeout=10)
        root = ET.fromstring(res.content)
        ns = {'atom': 'http://www.w3.org/2005/Atom', 'yt': 'http://www.youtube.com/xml/schemas/2015'}
        topics = []
        for entry in root.findall('atom:entry', ns)[:10]:
            title = entry.find('atom:title', ns).text
            video_id = entry.find('yt:videoId', ns).text
            topics.append({
                'title': title,
                'source': 'YouTube RSS',
                'url': f'https://youtube.com/watch?v={video_id}',
                'traffic': 'Trending'
            })
        return topics
    except Exception as e:
        print(f"YouTube RSS failed: {e}")
        return []


def fetch_google_trends():
    """Fetch real-time Google Trends (no API key)"""
    try:
        pytrends = TrendReq(hl='en-US', tz=360)
        df = pytrends.trending_searches(pn='united_states')
        topics = []
        for term in df[0].tolist()[:10]:
            topics.append({
                'title': term,
                'source': 'Google Trends',
                'traffic': 'Trending Now'
            })
        return topics
    except Exception as e:
        print(f"Google Trends failed: {e}")
        return []


def fetch_youtube_trending_api():
    """Fetch via YouTube Data API v3 (requires API key)"""
    api_key = os.environ.get("YOUTUBE_API_KEY", "")
    if not api_key:
        return []
    try:
        url = "https://www.googleapis.com/youtube/v3/videos"
        params = {
            "part": "snippet,statistics",
            "chart": "mostPopular",
            "regionCode": "US",
            "maxResults": 10,
            "key": api_key
        }
        res = requests.get(url, params=params, timeout=10)
        data = res.json()
        topics = []
        for item in data.get("items", []):
            topics.append({
                'title': item['snippet']['title'],
                'source': 'YouTube API',
                'traffic': f"{int(item['statistics'].get('viewCount', 0)):,} views",
                'video_id': item['id']
            })
        return topics
    except Exception as e:
        print(f"YouTube API failed: {e}")
        return []


def score_topic(topic):
    """Score topics by viral potential keywords"""
    viral_keywords = [
        'breaking', 'viral', 'shocking', 'secret', 'exposed', 'caught',
        'never seen', 'world record', 'first ever', 'leaked', 'banned',
        'react', 'try not to', 'impossible', 'unbelievable', 'insane'
    ]
    title_lower = topic['title'].lower()
    score = 0
    for kw in viral_keywords:
        if kw in title_lower:
            score += 2
    # Prefer shorter, punchier titles
    if len(topic['title']) < 60:
        score += 1
    return score


def fetch_trending_topics(limit=10):
    """Main function: fetch from all sources, deduplicate, rank"""
    print("   Fetching from YouTube API...")
    yt_api = fetch_youtube_trending_api()

    print("   Fetching from YouTube RSS...")
    yt_rss = fetch_youtube_trending_rss()

    print("   Fetching from Google Trends...")
    g_trends = fetch_google_trends()

    # Combine all sources
    all_topics = yt_api + g_trends + yt_rss

    # Deduplicate by title similarity
    seen = []
    unique = []
    for t in all_topics:
        title_clean = re.sub(r'[^a-z0-9 ]', '', t['title'].lower())
        if not any(title_clean in s or s in title_clean for s in seen):
            seen.append(title_clean)
            unique.append(t)

    # Score and sort
    unique.sort(key=score_topic, reverse=True)

    return unique[:limit]
