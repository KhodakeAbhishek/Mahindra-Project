import streamlit as st
import os
import time
import base64
from concurrent.futures import ThreadPoolExecutor, as_completed

# ============================================================
# MODULE IMPORTS
# ============================================================

import sys

sys.path.append(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)

from shared_config import LOGOS
from Sales.sales import fetch_all_sales, render_sales_tab
# from modelwise.modelwise import render_modelwise_tab

from News.news import get_market_news, render_news_tab
from News.deals import get_b2b_deals, render_deals_tab

# from News.socialmedia import fetch_social_media_news, render_social_tab

from Dealers.dealer import render_dealers_tab
from Ai.aibot import render_aibot_tab
from tender.tender import render_tenders_tab, init_tender_system


# ============================================================
# INITIALIZE TENDER SYSTEM
# ============================================================

init_tender_system()


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Mahindra Tractor Intelligence",
    layout="wide",
    initial_sidebar_state="expanded"
)


# ============================================================
# SESSION STATE
# ============================================================

if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []

if "data_loaded" not in st.session_state:
    st.session_state.data_loaded = False


# ============================================================
# IMAGE HELPER
# ============================================================

def get_base64_image(image_path, fallback_url):
    """
    Reads a local image and converts it to base64 for HTML use.
    Falls back to the provided URL if the local image is unavailable.
    """

    if os.path.exists(image_path):
        try:
            with open(image_path, "rb") as img_file:
                b64_string = base64.b64encode(
                    img_file.read()
                ).decode()

            return f"data:image/png;base64,{b64_string}"

        except Exception:
            return fallback_url

    return fallback_url


# ============================================================
# GLOBAL CSS
# ============================================================

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

*,*::before,*::after {
  box-sizing: border-box;
  margin: 0;
  padding: 0;
}

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


/* ============================================================
   SIDEBAR
   ============================================================ */

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


/* BRAND TITLE */

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


/* SIDEBAR DIVIDER */

.sidebar-divider {
  height: 3px;

  background: #B71C1C !important;

  margin: 0 0 18px 0;

  width: 100%;

  box-shadow:
    0 1px 4px rgba(183, 28, 28, 0.4);

  border-radius: 2px;
}


[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label {

  color: var(--text-gray) !important;

  font-family: var(--font-mono) !important;

  font-size: 10px !important;

  letter-spacing: 2px !important;
}


/* SIDEBAR SELECT */

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


/* FETCH BUTTON */

[data-testid="stSidebar"] button[kind="primary"],
[data-testid="stSidebar"]
[data-testid="stBaseButton-primary"] button {

  background: #0A0A0A !important;

  border: 1.5px solid #ED1C24 !important;

  border-radius: 4px !important;

  font-family: var(--font-mono) !important;

  font-size: 13px !important;

  font-weight: 800 !important;

  letter-spacing: 2px !important;

  color: #FFFFFF !important;

  height: 48px !important;

  box-shadow:
    0 2px 8px rgba(0,0,0,0.3) !important;

  transition: all .25s ease !important;

  margin-top: 15px !important;
}

[data-testid="stSidebar"] button[kind="primary"]:hover {

  background: #ED1C24 !important;

  border-color: #ED1C24 !important;

  color: #FFFFFF !important;

  box-shadow:
    0 6px 16px rgba(237,28,36,0.5) !important;

  transform: translateY(-2px) !important;
}


/* ============================================================
   SPLASH HERO
   ============================================================ */

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

    linear-gradient(
      rgba(237,28,36,0.04) 1px,
      transparent 1px
    ),

    linear-gradient(
      90deg,
      rgba(237,28,36,0.04) 1px,
      transparent 1px
    );

  background-size: 50px 50px;

  pointer-events: none;
}

.splash-wrap::after {

  content: '';

  position: absolute;

  top: 0;
  left: 0;
  right: 0;

  height: 3px;

  background:
    linear-gradient(
      to right,
      transparent,
      var(--mahindra-red) 30%,
      var(--mahindra-red) 70%,
      transparent
    );
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

  flex-wrap: nowrap;
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

  width: 28px;

  height: 2px;

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

  width: 380px;

  height: 380px;

  border-radius: 50%;

  background:
    radial-gradient(
      circle,
      rgba(237,28,36,0.07) 0%,
      transparent 70%
    );

  top: 50%;

  left: 50%;

  transform:
    translate(-50%, -50%);
}

.hero-image img {

  width: 480px;

  max-width: 100%;

  height: auto;

  object-fit: contain;

  position: relative;

  z-index: 1;

  filter:
    drop-shadow(
      0 20px 40px rgba(237,28,36,0.18)
    )
    drop-shadow(
      0 6px 16px rgba(0,0,0,0.12)
    );
}


/* RESPONSIVE */

@media (max-width: 1200px) {

  .title-red {
    font-size: 110px !important;
  }

  .title-black {

    font-size: 80px !important;

    white-space: normal;

    text-align: center;
  }

  .hero-container {
    gap: 15px;
  }

  .hero-image img {
    width: 360px;
  }
}


@media (max-width: 900px) {

  .hero-container {

    flex-wrap: wrap !important;

    text-align: center;

    justify-content: center;

    gap: 30px;
  }

  .hero-text {

    text-align: center;

    align-items: center;
  }

  .hero-eyebrow::before {
    display: none;
  }

  .title-red,
  .title-black {

    white-space: normal;

    text-align: center;
  }

  .title-black {
    font-size: 60px !important;
  }
}


/* ============================================================
   SPLASH STATS
   ============================================================ */

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

  box-shadow:
    0 4px 20px rgba(0,0,0,0.05);

  transition:
    transform 0.25s ease,
    box-shadow 0.25s ease;

  position: relative;

  overflow: hidden;
}

.splash-stat::after {

  content: '';

  position: absolute;

  bottom: 0;

  left: 0;

  right: 0;

  height: 0;

  background:
    linear-gradient(
      to top,
      var(--red-glow),
      transparent
    );

  transition: height 0.3s ease;
}

.splash-stat:hover {

  transform: translateY(-6px);

  box-shadow:
    0 12px 30px rgba(237,28,36,0.12);
}

.splash-stat:hover::after {
  height: 60px;
}


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


.val-red {
  color: var(--mahindra-red) !important;
}

.val-black {
  color: var(--text-dark) !important;
}

.val-green {

  color: #1B8A42 !important;

  font-family: var(--font-cond) !important;

  font-weight: 700 !important;

  font-size: 30px !important;

  letter-spacing: 1px !important;

  display: flex;

  align-items: center;

  justify-content: center;

  gap: 6px;
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


/* ============================================================
   DATA / TAB STYLES
   ============================================================ */

.stTabs [data-baseweb="tab-list"] {

  background: var(--bg-alt) !important;

  border: 1px solid var(--border-light) !important;

  border-radius: 6px;
}

.stTabs [data-baseweb="tab"] {

  color: var(--text-gray) !important;

  font-family: var(--font-cond) !important;

  font-weight: 600 !important;

  letter-spacing: 1px !important;
}

.stTabs [aria-selected="true"] {

  background: var(--mahindra-red) !important;

  color: #fff !important;

  box-shadow:
    0 4px 12px rgba(237,28,36,0.3) !important;

  border-radius: 4px !important;
}


.kpi-card {

  background: #FFFFFF !important;

  border: 1px solid var(--border-light) !important;

  box-shadow:
    0 4px 15px rgba(0,0,0,0.03) !important;
}

.kpi-card:hover {

  border-color: var(--mahindra-red) !important;

  box-shadow:
    0 8px 25px rgba(237,28,36,0.1) !important;
}

.kpi-val {

  color: var(--text-dark) !important;

  text-shadow: none !important;
}

.kpi-company-name {

  color: var(--mahindra-red) !important;
}

.kpi-lbl {

  color: var(--text-gray) !important;
}

.sec-head-title {

  color: var(--text-dark) !important;

  text-shadow: none !important;
}

.sec-head-badge {

  background: var(--bg-alt) !important;

  color: var(--text-gray) !important;

  border-color: var(--border-light) !important;
}


[data-testid="stDataFrame"] table {

  background: #FFFFFF !important;
}

[data-testid="stDataFrame"] thead tr th {

  background: var(--bg-alt) !important;

  color: var(--text-dark) !important;

  border-bottom:
    2px solid var(--border-light) !important;
}

[data-testid="stDataFrame"] tbody tr td {

  color: var(--text-dark) !important;

  border-bottom:
    1px solid var(--border-light) !important;
}

[data-testid="stDataFrame"] tbody tr:hover td {

  background:
    rgba(237,28,36,0.04) !important;
}


.status-bar {

  background: #FFFFFF !important;

  border: 1px solid var(--border-light) !important;

  box-shadow:
    0 2px 8px rgba(0,0,0,0.02);

  border-left:
    3px solid var(--mahindra-red) !important;

  padding: 10px 15px;

  display: flex;

  align-items: center;

  gap: 10px;

  margin-bottom: 15px;

  border-radius: 4px;
}

.status-bar-dot {

  width: 8px;

  height: 8px;

  border-radius: 50%;

  flex-shrink: 0;
}

.status-item {

  color: var(--text-gray) !important;

  font-family: var(--font-mono);

  font-size: 10px;

  letter-spacing: 1px;
}

.status-item span {

  color: var(--text-dark) !important;

  font-weight: bold;
}

.status-sep {
  color: #ddd;
}

</style>
""", unsafe_allow_html=True)


# ============================================================
# CACHED DATA FUNCTIONS
# ============================================================

@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def load_sales_data(period):
    """
    Fetch sales data.

    Cached for 1 hour.
    """
    return fetch_all_sales(period)


@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def load_deals_data(company, period):
    """
    Fetch B2B deals.

    Cached for 1 hour.
    """
    return get_b2b_deals(company, period)


@st.cache_data(
    ttl=3600,
    show_spinner=False
)
def load_news_data(company, period):
    """
    Fetch market news.

    Cached for 1 hour.
    """
    return get_market_news(company, period)


# ============================================================
# PARALLEL DATA FETCH
# ============================================================

def fetch_intelligence(company, period):
    """
    Fetch Sales, Deals and News concurrently.

    Instead of:

        Sales -> Deals -> News

    we do:

        Sales
        Deals
        News

    at the same time.
    """

    results = {}

    errors = {}

    with ThreadPoolExecutor(max_workers=3) as executor:

        futures = {

            executor.submit(
                load_sales_data,
                period
            ): "sales",

            executor.submit(
                load_deals_data,
                company,
                period
            ): "deals",

            executor.submit(
                load_news_data,
                company,
                period
            ): "news",
        }

        for future in as_completed(futures):

            source = futures[future]

            try:

                results[source] = future.result()

            except Exception as e:

                errors[source] = str(e)

                # Don't allow one source to kill the
                # entire dashboard.

                if source == "sales":
                    results[source] = []

                elif source == "deals":
                    results[source] = []

                elif source == "news":
                    results[source] = []


    return (
        results.get("sales", []),
        results.get("deals", []),
        results.get("news", []),
        errors
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:

    # --------------------------------------------------------
    # LOGO
    # --------------------------------------------------------

    logo_fallback_url = (
        "https://upload.wikimedia.org/wikipedia/commons/"
        "thumb/6/68/Mahindra_logo.svg/"
        "512px-Mahindra_logo.svg.png"
    )

    local_logo_path = os.path.join(
        os.path.dirname(
            os.path.dirname(__file__)
        ),
        "Images",
        "mahindrat.png"
    )

    logo_src = get_base64_image(
        local_logo_path,
        logo_fallback_url
    )

    st.markdown(
        f"""
        <div class="sidebar-logo-box">
            <img
                src="{logo_src}"
                alt="Mahindra Logo"
            >
        </div>
        """,
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # BRAND
    # --------------------------------------------------------

    st.markdown(
        """
        <div class="brand-title">
            <h1>MAHINDRA</h1>
            <p>TRACTORS</p>
        </div>

        <div class="sidebar-divider"></div>
        """,
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # COMPANY
    # --------------------------------------------------------

    st.markdown(
        "<label>TARGET ENTITY</label>",
        unsafe_allow_html=True
    )

    company = st.selectbox(
        "",
        [
            "All (Competitors)",
            "Mahindra",
            "John Deere",
            "TAFE",
            "Sonalika",
            "Escorts Kubota",
            "Swaraj"
        ],
        label_visibility="collapsed"
    )


    st.markdown(
        "<div style='height:15px'></div>",
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # FINANCIAL YEAR
    # --------------------------------------------------------

    st.markdown(
        "<label>FINANCIAL YEAR</label>",
        unsafe_allow_html=True
    )

    period = st.selectbox(
        "",
        [
            "FY 2025-26",
            "FY 2024-25",
            "FY 2023-24",
            "FY 2022-23",
            "FY 2021-22",
            "FY 2020-21"
        ],
        label_visibility="collapsed"
    )


    st.markdown(
        "<div style='height:25px'></div>",
        unsafe_allow_html=True
    )


    # --------------------------------------------------------
    # FETCH BUTTON
    # --------------------------------------------------------

    fetch_btn = st.button(
        "✦ FETCH INTELLIGENCE",
        use_container_width=True,
        type="primary"
    )


# ============================================================
# FETCH ACTION
# ============================================================

if fetch_btn:

    st.session_state["data_loaded"] = True


# ============================================================
# MAIN DASHBOARD
# ============================================================

if st.session_state.get("data_loaded", False):

    # --------------------------------------------------------
    # TARGET COMPANIES
    # --------------------------------------------------------

    target_companies = (
        [
            "Mahindra",
            "John Deere",
            "TAFE",
            "Sonalika",
            "Escorts Kubota",
            "Swaraj"
        ]
        if company == "All (Competitors)"
        else [company]
    )


    # --------------------------------------------------------
    # FETCH DATA
    # --------------------------------------------------------

    start_time = time.time()

    with st.spinner(
        "Fetching intelligence from all sources..."
    ):

        (
            market_data,
            target_deals,
            target_news,
            fetch_errors
        ) = fetch_intelligence(
            company,
            period
        )


    elapsed_time = time.time() - start_time


    # --------------------------------------------------------
    # FILTER SALES
    # --------------------------------------------------------

    if company != "All (Competitors)":

        market_data = [
            d
            for d in market_data
            if d.get("company") == company
        ]


    # --------------------------------------------------------
    # SORT DATA
    # --------------------------------------------------------

    market_data = sorted(
        market_data,
        key=lambda x:
            0 if x.get("company") == "Mahindra" else 1
    )


    def mahindra_first(items):

        return sorted(
            items,
            key=lambda x:
                0 if x.get("tag") == "Mahindra" else 1
        )


    target_deals = mahindra_first(
        target_deals
    )

    target_news = mahindra_first(
        target_news
    )


    # --------------------------------------------------------
    # STATUS TIME
    # --------------------------------------------------------

    ts = time.strftime(
        "%d %b %Y · %H:%M IST"
    )


    # --------------------------------------------------------
    # STATUS BAR
    # --------------------------------------------------------

    st.markdown(
        f"""
        <div class="status-bar">

            <div
                class="status-bar-dot"
                style="
                    background:#2E7D32;
                    box-shadow:0 0 8px #2E7D32;
                "
            ></div>

            <span class="status-item">
                STATUS
