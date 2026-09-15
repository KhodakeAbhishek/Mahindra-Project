import streamlit as st
import requests
import urllib.parse
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from shared_config import get_groq_client, get_tavily_key, safe_json_parse, flatten_ai_val

try:
    from duckduckgo_search import DDGS
except ImportError:
    DDGS = None

ALL_COMPANIES = ["Mahindra", "Sonalika", "Escorts Kubota", "Swaraj", "Tafe", "John Deere"]

COMPANY_QUERIES = {
    "Mahindra": ['"Mahindra tractor" news', '"Mahindra" agricultural machinery'],
    "Sonalika": ['"Sonalika tractor" news', '"Sonalika" farm equipment'],
    "Escorts Kubota": ['"Escorts Kubota" news', '"Escorts Kubota" tractor'],
    "Swaraj": ['"Swaraj tractor" news', '"Swaraj" farm machinery'],
    "Tafe": ['"TAFE tractor" news', '"TAFE" agricultural news'],
    "John Deere": ['"John Deere India" news', '"John Deere" tractor launch']
}

def parse_smart_date(text_to_parse):
    if not text_to_parse:
        return None
    text = str(text_to_parse).lower().strip()
    now = datetime.now()
    m_rel = re.search(r'\b(\d+)\s*(s|sec|m|min|h|hr|hour|d|day|w|wk|week|mo|month|y|yr|year)s?(?:\s*ago|\s*•|\s*[-|])?', text)
    if m_rel:
        val = int(m_rel.group(1))
        unit = m_rel.group(2)
        if unit.startswith('h'):
            return now - timedelta(hours=val)
        if unit.startswith('d'):
            return now - timedelta(days=val)
        if unit.startswith('w'):
            return now - timedelta(weeks=val)
        if unit.startswith('mo') or unit == 'month':
            return now - timedelta(days=val*30)
    formats = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%d", "%d %b %Y", "%B %d, %Y"]
    for f in formats:
        try:
            return datetime.strptime(text[:30].strip(), f).replace(tzinfo=None)
        except:
            pass
    m_date = re.search(r'\b(\d{1,2}\s(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s\d{4})\b', text, re.IGNORECASE)
    if m_date:
        try:
            return datetime.strptime(m_date.group(1), "%d %b %Y")
        except:
            pass
    return None

@st.cache_data(ttl=300, show_spinner=False)
def get_market_news(company_name, period):
    target_companies = ALL_COMPANIES if company_name == "All (Competitors)" else [company_name]
    all_results = []
    sixty_days_ago = datetime.now() - timedelta(days=60)

    for comp in target_companies:
        queries = COMPANY_QUERIES.get(comp, [f'"{comp}" news'])
        comp_results = fetch_news_sources(comp, queries)

        for item in comp_results:
            dt_obj = parse_smart_date(item.get('published_date', ''))
            if not dt_obj:
                dt_obj = parse_smart_date(item['date'])
            if dt_obj:
                if dt_obj < sixty_days_ago:
                    continue
                item['date'] = dt_obj.strftime("%d %b %Y")
            else:
                continue
            all_results.append(item)

    unique_results = list({v['url']: v for v in all_results if v.get('url')}.values())
    unique_results.sort(key=lambda x: 0 if x['tag'] == "Mahindra" else 1)
    return unique_results

def fetch_news_sources(company, queries):
    results = []

    # 1. Google News RSS
    for q in queries:
        try:
            rss_url = f"https://news.google.com/rss/search?q={urllib.parse.quote(q + ' India')}&hl=en-IN&gl=IN&ceid=IN:en"
            res = requests.get(rss_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if res.status_code == 200:
                soup = BeautifulSoup(res.text, "xml")
                for item in soup.find_all('item')[:20]:
                    pub_raw = item.pubDate.text if item.pubDate else ""
                    results.append({
                        "title": item.title.text if item.title else "",
                        "url": item.link.text if item.link else "",
                        "source": "Google News",
                        "tag": company,
                        "content": item.title.text if item.title else "",
                        "date": pub_raw,
                        "published_date": pub_raw
                    })
        except:
            pass

    # 2. Tavily API
    api_key = get_tavily_key()
    if api_key:
        for q in queries:
            try:
                payload = {
                    "api_key": api_key,
                    "query": f"{q} India recent market updates",
                    "search_depth": "advanced",
                    "topic": "news",
                    "days": 60,
                    "max_results": 20
                }
                res = requests.post("https://api.tavily.com/search", json=payload, timeout=12)
                if res.status_code == 200:
                    for item in res.json().get("results", []):
                        results.append({
                            "title": item.get('title', ''),
                            "url": item.get('url', ''),
                            "source": "Tavily Intelligence",
                            "tag": company,
                            "content": item.get('content', ''),
                            "date": item.get("published_date", ""),
                            "published_date": item.get("published_date", "")
                        })
            except:
                pass

    # 3. DuckDuckGo News
    if DDGS:
        try:
            with DDGS() as ddgs:
                for q in queries:
                    for r in ddgs.news(f"{q} India", timelimit="m", max_results=20):
                        results.append({
                            "title": r.get("title", ""),
                            "url": r.get("url", ""),
                            "source": r.get("source", "DDG News"),
                            "tag": company,
                            "content": r.get("body", ""),
                            "date": r.get("date", ""),
                            "published_date": r.get("date", "")
                        })
        except:
            pass

    return results

def analyze_news(title, snippet):
    prompt = f"Analyze this tractor/agricultural market news: '{title} - {snippet}'. Return strict JSON with keys: Event_Overview, Market_or_Product_Impact, Industry_Context, Strategic_Intent."
    try:
        client = get_groq_client()
        res = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.1-8b-instant",
            response_format={"type": "json_object"},
            temperature=0.1
        )
        return {k: flatten_ai_val(v) for k, v in safe_json_parse(res.choices[0].message.content).items()}
    except:
        return {"Error": "Analysis failed"}

def render_news_tab(target_news, period):
    st.markdown(f'''
        <div class="sec-head">
            <div class="sec-head-bar" style="background:#0FE88A;box-shadow:0 0 14px rgba(15,232,138,.4);"></div>
            <div class="sec-head-title">OFFICIAL MARKET EVENTS & ANNOUNCEMENTS</div>
            <div class="sec-head-badge">LAST 60 DAYS (LIVE)</div>
        </div>
    ''', unsafe_allow_html=True)

    if not target_news:
        st.markdown('''
            <div style="border:1px dashed #1c2540;border-radius:10px;padding:48px 20px;text-align:center;">
                <div style="font-size:32px;margin-bottom:12px;">📰</div>
                <div style="font-size:10px;letter-spacing:3px;color:#6a7fa8;">No recent (last 60 days) tractor industry news found. APIs are scanning.</div>
            </div>
        ''', unsafe_allow_html=True)
        return

    ACCENT_MAP = {
        "Mahindra": "#FF5C0A",
        "Sonalika": "#E1306C",
        "Escorts Kubota": "#3B82F6",
        "Swaraj": "#1FD8F0",
        "Tafe": "#FF2D55",
        "John Deere": "#10B981"
    }

    st.markdown(f'''
        <div style="background:rgba(15,232,138,.06);border:1px solid rgba(15,232,138,.2);border-radius:8px;padding:11px 18px;margin-bottom:16px;font-family:JetBrains Mono,monospace;font-size:9px;letter-spacing:2px;text-transform:uppercase;color:#0FE88A;">
            ✅ {len(target_news)} LATEST TRACTOR NEWS (EXACTLY WITHIN 60 DAYS)
        </div>
    ''', unsafe_allow_html=True)

    for i, n in enumerate(target_news):
        bg_color = ACCENT_MAP.get(n['tag'], "#0FE88A")
        st.markdown(f'''
            <div class="news-card" style="border-left-color:{bg_color};">
                <div style="display:flex;justify-content:space-between;">
                    <div style="flex:1;">
                        <div style="margin-bottom:8px;">
                            <span class="company-tag" style="color:{bg_color};border:1px solid {bg_color}35;">● {n["tag"].upper()}</span>
                            <span class="company-tag">📅 {n.get("date", "Recent")}</span>
                        </div>
                        <div class="news-title">{n["title"]}</div>
                        <div style="font-size:9px;color:#6a7fa8;margin-top:6px;">SOURCE: {n["source"]}</div>
                    </div>
                    <div>
                        <a href="{n["url"]}" target="_blank" style="color:#0FE88A;border:1px solid rgba(15,232,138,.25);padding:5px 10px;border-radius:6px;text-decoration:none;">📖 READ</a>
                    </div>
                </div>
            </div>
        ''', unsafe_allow_html=True)

        col_btn, _ = st.columns([1, 3])
        if col_btn.button(f"💡 Highlight Impacts", key=f"n_btn_{i}", use_container_width=True):
            with st.spinner("Extracting Impacts..."):
                ans = analyze_news(n['title'], n.get('content', ''))
                rows = "".join([
                    f'<div style="margin-bottom:12px; border-bottom:1px solid #1c2540; padding-bottom:8px;">'
                    f'<strong style="color:{bg_color}; font-size:14px; display:block;">{k.replace("_"," ").upper()}</strong> '
                    f'<span style="color:#e2e8f0; font-size:15px;">{v}</span></div>'
                    for k, v in ans.items()
                ])
                st.markdown(f'<div style="background:#0b1120; border-left:4px solid {bg_color}; border-radius:8px; padding:20px; margin-top:5px; margin-bottom:20px;">{rows}</div>', unsafe_allow_html=True)