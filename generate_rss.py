#!/usr/bin/env python3
"""
Polymarket Top Markets RSS Generator (日本語翻訳対応版)
"""
 
import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from xml.etree.ElementTree import Element, SubElement, tostring
from xml.dom import minidom
import os
import time
 
from deep_translator import GoogleTranslator
 
GAMMA_API = "https://gamma-api.polymarket.com/markets"
POLYMARKET_BASE = "https://polymarket.com/event"
OUTPUT_FILE = "docs/feed.xml"
FEED_TITLE = "Polymarket トレンド Top20"
FEED_LINK = "https://polymarket.com/predictions?_sort=volume"
FEED_DESC = "Polymarketの本日の取引量上位20マーケット（日本語訳付き）"
 
CATEGORY_EMOJI = {
    "politics": "🗳️",
    "crypto": "₿",
    "sports": "🏆",
    "finance": "💹",
    "geopolitics": "🌍",
    "tech": "💻",
    "ai": "🤖",
    "pop-culture": "🎬",
    "science": "🔬",
    "weather": "🌤️",
}
 
translator = GoogleTranslator(source="en", target="ja")
 
def translate(text: str) -> str:
    if not text:
        return text
    try:
        time.sleep(0.3)  # レート制限対策
        return translator.translate(text)
    except Exception as e:
        print(f"翻訳エラー: {e}")
        return text  # 失敗したら英語のままにする
 
def fetch_markets(limit: int = 20) -> list:
    params = f"?limit={limit}&order=volume24hr&ascending=false&active=true"
    url = GAMMA_API + params
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; PolymarketRSS/1.0)",
            "Accept": "application/json",
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))
 
def fmt_volume(v) -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "N/A"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"
 
def get_emoji(market: dict) -> str:
    tags = [t.get("slug", "") for t in market.get("tags", [])]
    for tag in tags:
        for key, emoji in CATEGORY_EMOJI.items():
            if key in tag:
                return emoji
    return "📊"
 
def build_description(market: dict, title_ja: str) -> str:
    vol24 = fmt_volume(market.get("volume24hr"))
    vol_total = fmt_volume(market.get("volume"))
    liquidity = fmt_volume(market.get("liquidity"))
    outcomes = market.get("outcomes", "[]")
    prices = market.get("outcomePrices", "[]")
    try:
        outcomes = json.loads(outcomes) if isinstance(outcomes, str) else outcomes
        prices = json.loads(prices) if isinstance(prices, str) else prices
    except Exception:
        outcomes, prices = [], []
 
    odds_lines = []
    for o, p in zip(outcomes, prices):
        try:
            pct = round(float(p) * 100)
            odds_lines.append(f"  • {o}: {pct}%")
        except Exception:
            pass
 
    end_date = market.get("endDate", "")
    if end_date:
        try:
            dt = datetime.fromisoformat(end_date.replace("Z", "+00:00"))
            end_date = dt.strftime("%Y-%m-%d")
        except Exception:
            pass
 
    parts = [
        f"<b>🇯🇵 {title_ja}</b>",
        "",
        f"<b>本日の取引量:</b> {vol24}",
        f"<b>累計取引量:</b> {vol_total}",
        f"<b>流動性:</b> {liquidity}",
        f"<b>終了日:</b> {end_date}" if end_date else "",
        "<b>現在の確率:</b>",
        *odds_lines,
    ]
    return "<br/>".join(p for p in parts if p != "" or True)
 
def build_rss(markets: list) -> str:
    now_rfc = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
 
    rss = Element("rss", version="2.0")
    rss.set("xmlns:content", "http://purl.org/rss/1.0/modules/content/")
    channel = SubElement(rss, "channel")
 
    SubElement(channel, "title").text = f"{FEED_TITLE}（{today}）"
    SubElement(channel, "link").text = FEED_LINK
    SubElement(channel, "description").text = FEED_DESC
    SubElement(channel, "language").text = "ja"
    SubElement(channel, "lastBuildDate").text = now_rfc
 
    for rank, market in enumerate(markets, 1):
        question_en = market.get("question", "Unknown")
        slug = market.get("slug", "")
        emoji = get_emoji(market)
        vol24 = fmt_volume(market.get("volume24hr"))
 
        print(f"  翻訳中 #{rank}: {question_en[:50]}...")
        question_ja = translate(question_en)
 
        item = SubElement(channel, "item")
        SubElement(item, "title").text = f"#{rank} {emoji} {question_ja}（{vol24}）"
        SubElement(item, "link").text = f"{POLYMARKET_BASE}/{slug}" if slug else FEED_LINK
        SubElement(item, "guid").text = f"polymarket-{slug}-{today}"
        SubElement(item, "pubDate").text = now_rfc
 
        desc_html = build_description(market, question_ja)
        content = SubElement(item, "content:encoded")
        content.text = f"<![CDATA[{desc_html}]]>"
        SubElement(item, "description").text = desc_html
 
    xml_str = tostring(rss, encoding="unicode")
    return minidom.parseString(xml_str).toprettyxml(indent="  ", encoding=None)
 
def main():
    print("Polymarket APIからデータ取得中...")
    markets = fetch_markets(20)
    print(f"{len(markets)}件取得完了\n日本語に翻訳中...")
 
    os.makedirs("docs", exist_ok=True)
    rss_content = build_rss(markets)
 
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(rss_content)
    print(f"\nRSSフィード生成完了: {OUTPUT_FILE}")
 
if __name__ == "__main__":
    main()
 
