import streamlit as st
import os
import time
import datetime
import base64

# ── Module imports ──
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared_config import LOGOS
from Sales.sales import fetch_all_sales, render_sales_tab
# from modelwise.modelwise import render_modelwise_tab
from News.news import get_market_news, render_news_tab
from News.deals import get_b2b_deals, render_deals_tab
# from News.socialmedia import fetch_social_media_news, render_social_tab
from Dealers.dealer import render_dealers_tab
from Ai.aibot import render_aibot_tab
from tender.tender import render_tenders_tab, init_tender_system

# Initialize tender system
init_tender_system()

def get_base64_image(image_path, fallback_url):
    """Reads a local image and converts it to base64 for HTML use."""
    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                b64_string = base64.b64encode(img_file.read()).decode()
            return f"data:image/png;base64,{b64_string}"
        except Exception:
            return fallback_url
    return fallback_url

st.set_page_config(
    page_title="Mahindra Tractor Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

# ==========================================
# GLOBAL CSS – FIXED LAYOUT & RED DIVIDER
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=JetBrains+Mono:wght@300;400;500;600;700&family=Barlow+Condensed:wght@400;600;700;800;900&display=swap');

:root {
  --mahindra-red: #ED1C24;
  --red-dark: #B71C1C;
  --red-glow: rgba(237,28,36,0.15);
  --bg-light: #FAFAFA;
  --bg-white: #FFFFFF;
  --bg-alt: #F4F4F4;
  --sidebar-dark: #0A0A0A;
  --text-dark: #0D0D0D;
  --text-mid: #444444;
  --text-gray: #999999;
  --border-light: #E5E5E5;
  --font-display: 'Bebas Neue', sans-serif;
  --font-cond: 'Barlow Condensed', sans-serif;
  --font-mono: 'JetBrains Mono', monospace;
}

*,*::before,*::after { box-sizing: border-box; margin:0; padding:0; }

.stApp {
  background-color: var(--bg-light);
  color: var(--text-dark);
  font-family: var(--font-cond);
}

[data-testid="stHeader"] {
  background: rgba(250,250,250,0.95) !important;
  border-bottom: 1px solid var(--border-light) !important;
  backdrop-filter: blur(8px);
}

/* ── SIDEBAR STYLES ── */
[data-testid="stSidebar"] {
  background-color: var(--sidebar-dark) !important;
  border-right: 1px solid #1a1a1a !important;
  min-width: 270px !important;
  max-width: 270px !important;
}

[data-testid="stSidebar"] [data-testid="stVerticalBlock"] {
    padding-left: 0.8rem !important;
    padding-right: 0.8rem !important;
}

.sidebar-logo-box {
    background-color: #FFFFFF;
    padding: 4px 12px;
    border-radius: 6px;
    margin: 8px 0px 10px 0px;
    display: flex;
    justify-content: center;
    align-items: center;
    border: 1px solid #222;
    width: 100%;
}
.sidebar-logo-box img { 
    max-width: 100%; 
    max-height: 55px;
    object-fit: contain; 
    display: block; 
    margin: 0 auto; 
}

/* BRAND TITLE – reduced gap */
.brand-title {
    margin-bottom: 6px !important;
    margin-left: 2px;
}
.brand-title h1 {
  font-family: var(--font-display) !important;
  font-size: 26px !important;
  letter-spacing: 2px !important;
  color: var(--mahindra-red) !important;
  margin: 0 0 3px 0 !important;
  line-height: 1 !important;
}
.brand-title p {
  font-family: var(--font-display) !important;
  font-size: 16px !important;
  letter-spacing: 6px !important;
  color: #FFFFFF !important;
  margin: 0 !important;
  line-height: 1.1 !important;
}

/* SIDEBAR DIVIDER – NOW SOLID RED */
.sidebar-divider {
    height: 3px;
    background: #B71C1C !important;
    margin: 0 0 18px 0;
    width: 100%;
    box-shadow: 0 1px 4px rgba(183, 28, 28, 0.4);
    border-radius: 2px;
}

[data-testid="stSidebar"] p, [data-testid="stSidebar"] label {
  color: var(--text-gray) !important;
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 2px !important;
}

/* SIDEBAR INPUTS */
[data-testid="stSidebar"] [data-baseweb="select"]>div {
  background-color: #FFFFFF !important;
  border: 1px solid #CCCCCC !important;
  border-radius: 4px !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] span {
  color: #000000 !important;
  font-family: var(--font-cond) !important;
  font-size: 15px !important;
  font-weight: 600 !important;
}
[data-testid="stSidebar"] [data-baseweb="select"] svg {
  fill: #000000 !important;
  color: #000000 !important;
}

/* FETCH BUTTON – high contrast */
[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] button {
  background: #0A0A0A !important;
  border: 1.5px solid #ED1C24 !important;
  border-radius: 4px !important;
  font-family: var(--font-mono) !important;
  font-size: 13px !important;
  font-weight: 800 !important;
  letter-spacing: 2px !important;
  color: #FFFFFF !important;
  height: 48px !important;
  box-shadow: 0 2px 8px rgba(0,0,0,0.3) !important;
  transition: all .25s ease !important;
  margin-top: 15px !important;
}
[data-testid="stSidebar"] button[kind="primary"]:hover {
  background: #ED1C24 !important;
  border-color: #ED1C24 !important;
  color: #FFFFFF !important;
  box-shadow: 0 6px 16px rgba(237,28,36,0.5) !important;
  transform: translateY(-2px) !important;
}

/* ── SPLASH HERO – SIDE BY SIDE (NO WRAP) ── */
.splash-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 86vh;
  padding: 40px 20px 20px;
  position: relative;
  overflow: hidden;
}

.splash-wrap::before {
  content: '';
  position: absolute;
  inset: 0;
  background-image:
    linear-gradient(rgba(237,28,36,0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(237,28,36,0.04) 1px, transparent 1px);
  background-size: 50px 50px;
  pointer-events: none;
}

.splash-wrap::after {
  content: '';
  position: absolute;
  top: 0; left: 0; right: 0;
  height: 3px;
  background: linear-gradient(to right, transparent, var(--mahindra-red) 30%, var(--mahindra-red) 70%, transparent);
}

.hero-container {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 20px;
  width: 100%;
  max-width: 1300px;
  margin-bottom: 50px;
  position: relative;
  flex-wrap: nowrap;        /* PREVENTS STACKING */
}

.hero-text {
  text-align: left;
  padding-right: 0px;
  display: flex;
  flex-direction: column;
  z-index: 2;
  flex-shrink: 1;
  min-width: 0;
}

.hero-eyebrow {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 4px !important;
  color: var(--mahindra-red) !important;
  text-transform: uppercase !important;
  margin-bottom: 12px !important;
  display: flex;
  align-items: center;
  gap: 8px;
}
.hero-eyebrow::before {
  content: '';
  display: inline-block;
  width: 28px; height: 2px;
  background: var(--mahindra-red);
}

.title-red {
  font-family: var(--font-display) !important;
  color: var(--mahindra-red) !important;
  font-size: 150px !important;
  line-height: 0.85 !important;
  margin-bottom: 0px !important;
}
.title-black {
  font-family: var(--font-display) !important;
  color: var(--text-dark) !important;
  font-size: 110px !important;
  line-height: 0.85 !important;
  white-space: nowrap;
}

.title-sub {
  font-family: var(--font-cond) !important;
  font-size: 16px !important;
  font-weight: 600 !important;
  color: var(--text-mid) !important;
  letter-spacing: 6px !important;
  text-transform: uppercase !important;
  margin-top: 18px !important;
  padding-left: 4px;
}

.hero-image {
  position: relative;
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1;
  flex-shrink: 0;
}

.hero-image::before {
  content: '';
  position: absolute;
  width: 380px; height: 380px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(237,28,36,0.07) 0%, transparent 70%);
  top: 50%; left: 50%;
  transform: translate(-50%, -50%);
}

.hero-image img {
  width: 480px;
  max-width: 100%;
  height: auto;
  object-fit: contain;
  position: relative;
  z-index: 1;
  filter: drop-shadow(0 20px 40px rgba(237,28,36,0.18)) drop-shadow(0 6px 16px rgba(0,0,0,0.12));
}

/* Responsive: if screen too narrow, scale down fonts and image */
@media (max-width: 1200px) {
  .title-red { font-size: 110px !important; }
  .title-black { font-size: 80px !important; white-space: normal; text-align: center; }
  .hero-container { gap: 15px; }
  .hero-image img { width: 360px; }
}
@media (max-width: 900px) {
  .hero-container { flex-wrap: wrap !important; text-align: center; justify-content: center; gap: 30px; }
  .hero-text { text-align: center; align-items: center; }
  .hero-eyebrow::before { display: none; }
  .title-red, .title-black { white-space: normal; text-align: center; }
  .title-black { font-size: 60px !important; }
}

.splash-stats {
  display: flex;
  gap: 16px;
  justify-content: center;
  flex-wrap: wrap;
  margin-bottom: 40px;
}

.splash-stat {
  background: var(--bg-white);
  border: 1px solid var(--border-light);
  border-top: 3px solid var(--mahindra-red);
  border-radius: 6px;
  padding: 22px 32px;
  min-width: 155px;
  text-align: center;
  box-shadow: 0 4px 20px rgba(0,0,0,0.05);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
  position: relative;
  overflow: hidden;
}
.splash-stat::after {
  content: '';
  position: absolute;
  bottom: 0; left: 0; right: 0;
  height: 0;
  background: linear-gradient(to top, var(--red-glow), transparent);
  transition: height 0.3s ease;
}
.splash-stat:hover {
  transform: translateY(-6px);
  box-shadow: 0 12px 30px rgba(237,28,36,0.12);
}
.splash-stat:hover::after { height: 60px; }

.splash-stat-label {
  font-family: var(--font-mono) !important;
  font-size: 9px !important;
  letter-spacing: 2.5px !important;
  color: var(--text-gray) !important;
  text-transform: uppercase !important;
  margin-bottom: 12px;
}
.splash-stat-val {
  font-family: var(--font-display) !important;
  font-size: 52px !important;
  letter-spacing: 2px !important;
  line-height: 1 !important;
}

.val-red   { color: var(--mahindra-red) !important; }
.val-black { color: var(--text-dark) !important; }
.val-green {
  color: #1B8A42 !important;
  font-family: var(--font-cond) !important;
  font-weight: 700 !important;
  font-size: 30px !important;
  letter-spacing: 1px !important;
  display: flex; align-items: center; justify-content: center; gap: 6px;
}
.val-blue {
  color: #1565C0 !important;
  font-family: var(--font-cond) !important;
  font-weight: 700 !important;
  font-size: 30px !important;
  letter-spacing: 2px !important;
}

.instruction {
  font-family: var(--font-mono) !important;
  font-size: 10px !important;
  letter-spacing: 3.5px !important;
  color: var(--text-gray) !important;
  text-transform: uppercase !important;
  margin-top: 16px;
}

/* rest of original tab/data styles */
.stTabs [data-baseweb="tab-list"] { background: var(--bg-alt) !important; border: 1px solid var(--border-light) !important; border-radius: 6px; }
.stTabs [data-baseweb="tab"] { color: var(--text-gray) !important; font-family: var(--font-cond) !important; font-weight: 600 !important; letter-spacing: 1px !important; }
.stTabs [aria-selected="true"] { background: var(--mahindra-red) !important; color: #fff !important; box-shadow: 0 4px 12px rgba(237,28,36,0.3) !important; border-radius: 4px !important; }
.kpi-card { background: #FFFFFF !important; border: 1px solid var(--border-light) !important; box-shadow: 0 4px 15px rgba(0,0,0,0.03) !important; }
.kpi-card:hover { border-color: var(--mahindra-red) !important; box-shadow: 0 8px 25px rgba(237,28,36,0.1) !important; }
.kpi-val { color: var(--text-dark) !important; text-shadow: none !important; }
.kpi-company-name { color: var(--mahindra-red) !important; }
.kpi-lbl { color: var(--text-gray) !important; }
.sec-head-title { color: var(--text-dark) !important; text-shadow: none !important; }
.sec-head-badge { background: var(--bg-alt) !important; color: var(--text-gray) !important; border-color: var(--border-light) !important; }
[data-testid="stDataFrame"] table { background: #FFFFFF !important; }
[data-testid="stDataFrame"] thead tr th { background: var(--bg-alt) !important; color: var(--text-dark) !important; border-bottom: 2px solid var(--border-light) !important; }
[data-testid="stDataFrame"] tbody tr td { color: var(--text-dark) !important; border-bottom: 1px solid var(--border-light) !important; }
[data-testid="stDataFrame"] tbody tr:hover td { background: rgba(237,28,36,0.04) !important; }
.status-bar { background: #FFFFFF !important; border: 1px solid var(--border-light) !important; box-shadow: 0 2px 8px rgba(0,0,0,0.02); border-left: 3px solid var(--mahindra-red) !important; }
.status-item { color: var(--text-gray) !important; }
.status-item span { color: var(--text-dark) !important; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# SIDEBAR
# ==========================================
with st.sidebar:
    logo_fallback_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/6/68/Mahindra_logo.svg/512px-Mahindra_logo.svg.png"
    local_logo_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Images", "mahindrat.png")
    logo_src = get_base64_image(local_logo_path, logo_fallback_url)

    st.markdown(f"""
<div class="sidebar-logo-box">
<img src="{logo_src}" alt="Mahindra Logo">
</div>
    """, unsafe_allow_html=True)

    st.markdown("""
<div class="brand-title">
<h1>MAHINDRA</h1>
<p>TRACTORS</p>
</div>
<div class="sidebar-divider"></div>
    """, unsafe_allow_html=True)

    st.markdown("<label>TARGET ENTITY</label>", unsafe_allow_html=True)
    company = st.selectbox("", ["All (Competitors)", "Mahindra", "John Deere", "TAFE", "Sonalika", "Escorts Kubota","Swaraj"], label_visibility="collapsed")
 
    st.markdown("<div style='height:15px'></div>", unsafe_allow_html=True)
    
    st.markdown("<label>FINANCIAL YEAR</label>", unsafe_allow_html=True)
    period = st.selectbox("", [ "FY 2025-26", "FY 2024-25", "FY 2023-24", "FY 2022-23", "FY 2021-22", "FY 2020-21"], label_visibility="collapsed")

    st.markdown("<div style='height:25px'></div>", unsafe_allow_html=True)
    fetch_btn = st.button("✦ Loading...", use_container_width=True, type="primary")

# ==========================================
# MAIN DASHBOARD
# ==========================================
if fetch_btn:
    st.cache_data.clear()

if fetch_btn or 'data_loaded' in st.session_state:
    st.session_state['data_loaded'] = True
    target_companies = (
        ["Mahindra", "John Deere", "TAFE", "Sonalika", "Escorts Kubota","Swaraj"]
        if company == "All (Competitors)" else [company]
    )

    with st.spinner("Fetching intelligence..."):
        market_data   = fetch_all_sales(period)
        # Filter if specific company selected
        if company != "All (Competitors)":
            market_data = [d for d in market_data if d['company'] == company]
        target_deals  = get_b2b_deals(company, period)
        target_news   = get_market_news(company, period)
    #    target_social = fetch_social_media_news(company, period)

    market_data = sorted(market_data, key=lambda x: 0 if x.get('company') == 'Mahindra' else 1)

    def mahindra_first(items):
        return sorted(items, key=lambda x: 0 if x.get('tag') == 'Mahindra' else 1)
        
    target_deals  = mahindra_first(target_deals)
    target_news   = mahindra_first(target_news)
 #   target_social = mahindra_first(target_social)

    ts = time.strftime("%d %b %Y · %H:%M IST")
    st.markdown(f"""
<div class="status-bar">
<div class="status-bar-dot" style="background:#2E7D32; box-shadow:0 0 8px #2E7D32;"></div>
<span class="status-item">STATUS <span>LIVE</span></span>
<span class="status-sep" style="color:#ddd;">│</span>
<span class="status-item">ENTITY <span>{company.upper()}</span></span>
<span class="status-sep" style="color:#ddd;">│</span>
<span class="status-item">PERIOD <span>{period}</span></span>
<span class="status-sep" style="color:#ddd;">│</span>
<span class="status-item">FETCHED <span>{ts}</span></span>
<span class="status-sep" style="color:#ddd;">│</span>
<span class="status-item">RECORDS <span>{len(market_data)} co · {len(target_deals)} deals · {len(target_news)} news</span></span>
</div>
    """, unsafe_allow_html=True)

    t_sales, t_deals, t_news, t_social, t_dealers, t_tenders, t_chat = st.tabs([
        "💰 SALES", "🤝 DEALS",
        "📰 NEWS", "📱 SOCIAL MEDIA", "🏢 DEALERS", "📋 TENDERS", "🤖 AI ANALYST"
    ])

    with t_sales:
        render_sales_tab(market_data, period, company)
    # with t_models:
    #     render_modelwise_tab(market_data, period)
    with t_deals:
        render_deals_tab(target_deals, period)
    with t_news:
        render_news_tab(target_news, period)
#    with t_social:
#        render_social_tab(target_social, period)
    with t_dealers:
        render_dealers_tab(company)
    with t_chat:
        render_aibot_tab(market_data, period)
    with t_tenders:
        render_tenders_tab(selected_company=company, selected_period=period)

# ==========================================
# SPLASH STATE
# ==========================================
else:
    tractor_fallback_url = "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e0/Tractor_red.svg/1024px-Tractor_red.svg.png"
    local_tractor_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "Images", "tractor.png")
    tractor_src = get_base64_image(local_tractor_path, tractor_fallback_url)

    st.markdown(f"""
<div class="splash-wrap">
<div class="hero-container">
<div class="hero-text">
<div class="hero-eyebrow">Sales Intelligence Platform · India</div>
<div class="title-red">INDIAN</div>
<div class="title-black">TRACTOR MARKET</div>
<div class="title-sub">Competitive Intelligence · FY Data</div>
</div>
<div class="hero-image">
<img src="{tractor_src}" alt="Tractor Illustration">
</div>
</div>
<div class="splash-stats">
<div class="splash-stat">
<div class="splash-stat-label">Competitors</div>
<div class="splash-stat-val val-red">6</div>
</div>
<div class="splash-stat">
<div class="splash-stat-label">Data Tabs</div>
<div class="splash-stat-val val-black">7</div>
</div>
<div class="splash-stat">
<div class="splash-stat-label">FY Coverage</div>
<div class="splash-stat-val val-green">● LIVE</div>
</div>
<div class="splash-stat">
<div class="splash-stat-label">Source</div>
<div class="splash-stat-val val-blue">WEB</div>
</div>
</div>
<div class="instruction">← Configure parameters in sidebar &nbsp;·&nbsp; Click fetch intelligence</div>
</div>
    """, unsafe_allow_html=True)
