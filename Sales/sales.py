import streamlit as st
import pandas as pd
import requests
import re
import json
import time
from datetime import datetime
import plotly.express as px

# Import from your shared_config
from Main.shared_config import (
    get_groq_client, get_tavily_key, safe_json_parse, style_plotly_dark, ACCENT_MAP, PLOT_COLORS
)

def _hex_to_rgb(hex_color: str) -> str:
    try:
        hex_color = hex_color.lstrip('#')
        r, g, b = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        return f"{r},{g},{b}"
    except:
        return "255,92,10"

# =========================================================
# 🌍 COUNTRY NAME NORMALIZER (handles native names, abbreviations, spelling variants)
# =========================================================
COUNTRY_ALIASES = {
    "brasil": "Brazil", "brazil": "Brazil",
    "usa": "United States", "us": "United States", "u.s.": "United States",
    "u.s.a.": "United States", "united states of america": "United States",
    "america": "United States", "united states": "United States",
    "uk": "United Kingdom", "u.k.": "United Kingdom", "britain": "United Kingdom",
    "great britain": "United Kingdom", "england": "United Kingdom",
    "deutschland": "Germany", "germany": "Germany",
    "bharat": "India", "india": "India",
    "zhongguo": "China", "china": "China", "prc": "China",
    "nippon": "Japan", "nihon": "Japan", "japan": "Japan",
    "russia": "Russia", "rossiya": "Russia",
    "espana": "Spain", "españa": "Spain", "spain": "Spain",
    "italia": "Italy", "italy": "Italy",
    "france": "France", "francia": "France",
    "mexico": "Mexico", "méxico": "Mexico",
    "turkiye": "Turkey", "türkiye": "Turkey", "turkey": "Turkey",
    "south africa": "South Africa", "rsa": "South Africa",
    "aotearoa": "New Zealand", "new zealand": "New Zealand",
    "canada": "Canada",
    "australia": "Australia",
    "indonesia": "Indonesia",
    "argentina": "Argentina",
    "poland": "Poland", "polska": "Poland",
    "global": "Global", "all": "Global", "worldwide": "Global", "world": "Global",
}

def normalize_country(raw: str) -> str:
    """Map user-typed country names (native spelling, abbreviation, etc.) to one canonical form."""
    if not raw or raw.strip().lower() in ("all", "", "global", "worldwide", "world"):
        return "Global"
    key = raw.strip().lower()
    if key in COUNTRY_ALIASES:
        return COUNTRY_ALIASES[key]
    for alias, canonical in COUNTRY_ALIASES.items():
        if key in alias or alias in key:
            return canonical
    return raw.strip().title()

# =========================================================
# 🌐 1. DYNAMIC COMPANY DATA FETCH (WORLDWIDE OR COUNTRY-SPECIFIC)
# =========================================================
@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_data_dynamic(company: str, period: str, country: str = "Global"):
    start_year = int(period.split("-")[0].replace("FY ", "").strip())
    target_year = start_year + 1
    current_year = datetime.now().year
    short_fy = f"FY{str(target_year)[-2:]}"

    is_global = (country == "Global")

    default_data = {
        "company": company, "estimated_annual_cr": 0.0, "q1_cr": 0.0, "q2_cr": 0.0, "q3_cr": 0.0, "q4_cr": 0.0,
        "units_annual": 0, "units_q1": 0, "units_q2": 0, "units_q3": 0, "units_q4": 0,
        "growth_percent": "N/A", "source_url": "#",
        "data_source_type": "Global Industry Report / Live Web Fetch" if is_global else f"{country} Market Report / Live Web Fetch"
    }

    if start_year > current_year:
        default_data["data_source_type"] = "Awaiting Data"
        return default_data

    search_term = company
    if company == "Swaraj": search_term = "Swaraj Tractors"
    elif company == "John Deere": search_term = "John Deere tractor"
    elif company == "TAFE": search_term = "TAFE Tractors"
    elif company == "Mahindra": search_term = "Mahindra farm equipment tractor"
    elif company == "Escorts Kubota": search_term = "Escorts Kubota agri machinery"
    elif company == "Sonalika": search_term = "Sonalika International Tractors ITL"

    if is_global:
        query = f"{search_term} tractor global worldwide retail sales units {start_year} {target_year} {short_fy} annual report"
    else:
        query = f"{search_term} tractor {country} retail sales units {start_year} {target_year} {short_fy} market report"
    tavily_text = ""

    for attempt in range(4):
        try:
            tavily_resp = requests.post(
                "https://api.tavily.com/search",
                json={"api_key": get_tavily_key(), "query": query, "search_depth": "advanced", "max_results": 6},
                timeout=15
            )
            if tavily_resp.status_code == 200:
                data = tavily_resp.json()
                for res in data.get("results", []):
                    tavily_text += res['content'] + " "
                    if "sales" in res['url'].lower() or "report" in res['url'].lower() or "auto" in res['url'].lower():
                        default_data["source_url"] = res['url']
                if len(tavily_text) > 100:
                    break
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)

    if is_global:
        prompt = f"""
        Extract ONLY the TOTAL WORLDWIDE (global, all countries combined) tractor retail sales units for '{company}' in the financial year {start_year}-{target_year} ({short_fy}).
        Use only official company annual reports, investor presentations, or credible industry sources. DO NOT include car/auto sales.
        If the source only gives a single country's number (e.g. only India or only USA), do NOT treat it as the global total — set units_annual to 0 instead.
        Text: {tavily_text[:6000]}
        Return ONLY JSON: {{"units_annual": 0, "growth_percent": "+0.0%"}}
        If no clear global number is found, set units_annual to 0. Do not invent data.
        """
    else:
        prompt = f"""
        Extract ONLY the tractor retail sales units for '{company}' specifically WITHIN {country} for the financial year {start_year}-{target_year} ({short_fy}).
        Use only official company reports, dealer association data (e.g. FADA for India), government registration data, or credible industry sources for {country}. DO NOT include car/auto sales.
        If the source gives a global/worldwide number instead of a {country}-specific number, do NOT use it — set units_annual to 0 instead.
        Text: {tavily_text[:6000]}
        Return ONLY JSON: {{"units_annual": 0, "growth_percent": "+0.0%"}}
        If no clear {country}-specific number is found, set units_annual to 0. Do not invent data.
        """

    u_annual = 0
    growth_val = "N/A"

    for attempt in range(4):
        try:
            client = get_groq_client()
            ai_res = client.chat.completions.create(
                messages=[{"role": "user", "content": prompt}],
                model="openai/gpt-oss-120b",
                response_format={"type": "json_object"},
                temperature=0.0
            )

            ai_data = safe_json_parse(ai_res.choices[0].message.content)
            u_annual = int(ai_data.get("units_annual", 0))
            growth_val = str(ai_data.get("growth_percent", "N/A"))

            if u_annual > 0:
                if growth_val != "N/A" and not growth_val.startswith(("+", "-")) and growth_val[0].isdigit():
                    growth_val = "+" + growth_val
                break
            time.sleep(0.1)
        except Exception:
            time.sleep(0.1)

    if u_annual == 0 and tavily_text:
        patterns = [r'(\d{1,3}(?:,\d{3})+|\d{4,7})\s*(?:tractors|units)', r'(\d+(?:\.\d+)?)\s*(?:million|lakh)\s*(?:tractors|units)']
        for pat in patterns:
            match = re.search(pat, tavily_text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(',', '')
                if 'million' in pat:
                    u_annual = int(float(val_str) * 1000000)
                elif 'lakh' in pat:
                    u_annual = int(float(val_str) * 100000)
                else:
                    u_annual = int(val_str)
                break

    # Sanity cap: global totals can run much higher than any single country's totals
    cap = 5000000 if is_global else 1500000
    if u_annual > cap: u_annual = 0

    default_data["units_annual"] = u_annual
    default_data["growth_percent"] = growth_val if growth_val != "N/A" else "N/A"
    default_data["estimated_annual_cr"] = u_annual * 0.065

    ann_rev = default_data["estimated_annual_cr"]
    ann_u = default_data["units_annual"]

    default_data["q1_cr"], default_data["q2_cr"], default_data["q3_cr"], default_data["q4_cr"] = ann_rev*0.20, ann_rev*0.25, ann_rev*0.35, ann_rev*0.20
    default_data["q4_is_est"] = True

    default_data["units_q1"], default_data["units_q2"], default_data["units_q3"], default_data["units_q4"] = int(ann_u*0.20), int(ann_u*0.25), int(ann_u*0.35), int(ann_u*0.20)

    default_data["monthly_avg_cr"] = ann_rev / 12 if ann_rev else 0
    default_data["monthly_avg_units"] = ann_u / 12 if ann_u else 0

    return default_data

# =========================================================
# 🔄 MASTER FETCH FUNCTION (worldwide by default, or a specific country)
# =========================================================
ALL_COMPANIES = ["Mahindra", "Escorts Kubota", "Sonalika", "TAFE", "Swaraj", "John Deere"]

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_sales(period: str, country: str = "Global"):
    results = []
    for co in ALL_COMPANIES:
        results.append(fetch_company_data_dynamic(co, period, country))
    return results

# =========================================================
# 🖥️ UI RENDERER (DASHBOARD)
# =========================================================
def render_sales_tab(market_data, period, selected_company):
    clean_fy = period.replace("FY ", "")

    if "sales_spotlight" not in st.session_state:
        st.session_state.sales_spotlight = "Mahindra"
    if "sales_country_sel" not in st.session_state:
        st.session_state.sales_country_sel = "Global"

    # =====================================================
    # 🌍 COUNTRY FILTER — drives Table 1, Table 2, and all 3 charts
    # =====================================================
    col_country, col_apply = st.columns([4, 1])
    with col_country:
        country_input_raw = st.text_input(
            "Country filter (type 'Global' for worldwide totals)",
            value=st.session_state.sales_country_sel,
            placeholder="e.g. India, USA, Brazil, Germany"
        )
    with col_apply:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        apply_country = st.button("Apply", use_container_width=True)

    if apply_country:
        st.session_state.sales_country_sel = normalize_country(country_input_raw)
        st.rerun()

    active_country = st.session_state.sales_country_sel

    if active_country == "Global":
        display_data = market_data
        scope_label = "GLOBAL"
    else:
        with st.spinner(f"Fetching {active_country} sales data for all companies..."):
            display_data = fetch_all_sales(period, active_country)
        scope_label = active_country.upper()

    st.markdown(f"""
    <div class="sec-head">
      <div class="sec-head-bar" style="background:#FF5C0A;"></div>
      <div class="sec-head-title">{scope_label} TRACTOR SALES DATA — {clean_fy}</div>
      <div class="sec-head-badge">100% DYNAMIC SALES ENGINE</div>
    </div>""", unsafe_allow_html=True)

    spotlight_company = st.session_state.sales_spotlight
    if spotlight_company not in [d['company'] for d in display_data]:
        spotlight_company = display_data[0]['company'] if display_data else "Mahindra"

    spot = next((x for x in display_data if x['company'] == spotlight_company), display_data[0])
    accent, glow = ACCENT_MAP.get(spot['company'], ("#FF5C0A", "rgba(255,92,10,.18)"))
    g_sp = str(spot['growth_percent'])

    if "+" in g_sp:
        g_arrow, g_color = f"▲ {g_sp}", "#0FE88A"
    elif "-" in g_sp:
        g_arrow, g_color = f"▼ {g_sp}", "#FF2D55"
    else:
        g_arrow, g_color = g_sp, "#7b8db5"

    st.markdown(f"""
    <div style="background:linear-gradient(135deg,rgba({_hex_to_rgb(accent)},.13) 0%,rgba({_hex_to_rgb(accent)},.04) 100%);
         border:1.5px solid rgba({_hex_to_rgb(accent)},.45);border-radius:12px;padding:18px 26px;margin-bottom:22px;
         display:flex;align-items:center;gap:28px;">
      <div style="flex-shrink:0;">
        <div style="font-family:'Bebas Neue',sans-serif;font-size:28px;letter-spacing:4px;color:{accent};">{spot['company'].upper()}</div>
        <div style="margin-top:6px;">
            <a href="{spot['source_url']}" target="_blank" style="font-family:'JetBrains Mono',monospace;font-size:9px;color:{accent};border:1px solid {accent}55;padding:2px 6px;border-radius:4px;text-decoration:none;">🔗 SOURCE</a>
        </div>
      </div>
      <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
      <div>
        <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">Annual Revenue (Est, {scope_label})</div>
        <div style="font-size:34px;font-family:'Bebas Neue';color:#fff;">₹{spot['estimated_annual_cr']:,.2f} <span style="font-size:18px;">Cr</span></div>
      </div>
      <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
      <div>
        <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">Tractors Sold ({scope_label} Retail)</div>
        <div style="font-size:34px;font-family:'Bebas Neue';color:#fff;">{spot['units_annual']:,.0f} <span style="font-size:18px;">Units</span></div>
      </div>
      <div style="width:1px;height:50px;background:rgba({_hex_to_rgb(accent)},.25);"></div>
      <div>
        <div style="font-size:8px;color:#6a7fa8;text-transform:uppercase;">YoY Growth</div>
        <div style="font-size:28px;font-family:'Bebas Neue';color:{g_color};">{g_arrow}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    kpi_cols = st.columns(len(display_data))
    for i, res in enumerate(display_data):
        with kpi_cols[i]:
            card_accent, card_glow = ACCENT_MAP.get(res['company'], ("#FF5C0A","rgba(255,92,10,.18)"))
            mp_class = 'kpi-mahindra' if res['company'] == spotlight_company else ''

            if st.button("", key=f"kpi_card_{i}_{res['company']}", help=f"Click to focus on {res['company']}"):
                st.session_state.sales_spotlight = res['company']
                st.rerun()

            st.markdown(f"""
            <div class="kpi-card {mp_class}" style="--_accent:{card_accent};--_glow:{card_glow};cursor:pointer;" onclick="document.querySelector('[data-testid=\"stButton\"]:has([key=\"kpi_card_{i}_{res['company']}\"])').click()">
              <div>
                <div class="kpi-lbl">{scope_label} Revenue & Units &#183; {period}</div>
                <div class="kpi-company-name">{res['company']}</div>
                <div class="kpi-val">₹{res['estimated_annual_cr']:,.2f}<span> Cr</span></div>
              </div>
              <div style="margin-top:8px; display:flex; flex-direction:column; gap:2px;">
                 <span style="font-size:8px;color:{'#FF2D55' if res['units_annual']==0 else '#0FE88A'};font-weight:bold;">{res['data_source_type']}</span>
              </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<div style='height:28px'></div>", unsafe_allow_html=True)

    # TABLES
    st.markdown(f"""<div class="sec-head"><div class="sec-head-bar" style="background:#1FD8F0;"></div>
      <div class="sec-head-title">TABLE 1: ESTIMATED {scope_label} TRACTOR REVENUE (₹ CRORES)</div></div>""", unsafe_allow_html=True)

    rev_dict = [{
        "Company": item["company"],
        "Monthly Avg": f"₹ {item['monthly_avg_cr']:,.2f}",
        "Q1": f"₹ {item['q1_cr']:,.2f}",
        "Q2": f"₹ {item['q2_cr']:,.2f}",
        "Q3": f"₹ {item['q3_cr']:,.2f}",
        "Q4": f"₹ {item['q4_cr']:,.2f}",
        "Annual Total": f"₹ {item['estimated_annual_cr']:,.2f}"
    } for item in display_data]
    rev_df = pd.DataFrame(rev_dict)
    st.dataframe(rev_df, use_container_width=True, hide_index=True)
    total_rev = sum(item['estimated_annual_cr'] for item in display_data)
    st.markdown(f"<p style='color:#0FE88A;font-weight:bold;'>🌍 Total {scope_label} Revenue (All Companies): ₹ {total_rev:,.2f} Cr</p>", unsafe_allow_html=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    st.markdown(f"""<div class="sec-head"><div class="sec-head-bar" style="background:#9D6FFF;"></div>
      <div class="sec-head-title">TABLE 2: TRACTOR UNITS SOLD ({scope_label} RETAIL)</div></div>""", unsafe_allow_html=True)

    units_dict = [{
        "Company": item["company"],
        "Monthly Avg": f"{item['monthly_avg_units']:,.0f}",
        "Q1": f"{item['units_q1']:,.0f}",
        "Q2": f"{item['units_q2']:,.0f}",
        "Q3": f"{item['units_q3']:,.0f}",
        "Q4": f"{item['units_q4']:,.0f}",
        "Annual Total": f"{item['units_annual']:,.0f}",
        "YoY Growth": item["growth_percent"]
    } for item in display_data]
    st.dataframe(pd.DataFrame(units_dict), use_container_width=True, hide_index=True)
    total_units = sum(item['units_annual'] for item in display_data)
    st.markdown(f"<p style='color:#0FE88A;font-weight:bold;'>🌍 Total {scope_label} Units Sold (All Companies): {total_units:,.0f} Units</p>", unsafe_allow_html=True)

    st.markdown("<div style='height:36px'></div>", unsafe_allow_html=True)

    # CHARTS (ALL 3 RESTORED, driven by display_data)
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#0FE88A;"></div>
      <div class="sec-head-title">1. QUARTERLY REVENUE TRAJECTORY (LINE CHART)</div></div>""", unsafe_allow_html=True)

    line_data = []
    for item in display_data:
        line_data.extend([
            {"Company": item["company"], "Quarter": "Q1", "Revenue (₹ Cr)": item["q1_cr"]},
            {"Company": item["company"], "Quarter": "Q2", "Revenue (₹ Cr)": item["q2_cr"]},
            {"Company": item["company"], "Quarter": "Q3", "Revenue (₹ Cr)": item["q3_cr"]},
            {"Company": item["company"], "Quarter": "Q4", "Revenue (₹ Cr)": item["q4_cr"]},
        ])
    df_line = pd.DataFrame(line_data)
    if not df_line.empty and df_line["Revenue (₹ Cr)"].sum() > 0:
        fig_line = px.line(df_line, x="Quarter", y="Revenue (₹ Cr)", color="Company", color_discrete_map=PLOT_COLORS, markers=True)
        st.plotly_chart(style_plotly_dark(fig_line), use_container_width=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # DONUT CHART
    st.markdown(f"""<div class="sec-head"><div class="sec-head-bar" style="background:#FF2D55;"></div>
      <div class="sec-head-title">2. {scope_label} REVENUE MARKET SHARE (DONUT CHART)</div></div>""", unsafe_allow_html=True)

    pie_df = pd.DataFrame(display_data)
    if pie_df["estimated_annual_cr"].sum() > 0:
        fig_pie = px.pie(pie_df, values="estimated_annual_cr", names="company", hole=0.55, color="company", color_discrete_map=PLOT_COLORS)
        fig_pie.update_traces(textinfo='percent+label', textposition='inside', hovertemplate="<b>%{label}</b><br>₹%{value:,.2f} Cr<br>%{percent:.1%}")
        fig_pie.update_layout(height=400, showlegend=True, margin=dict(t=20, b=20))
        st.plotly_chart(style_plotly_dark(fig_pie), use_container_width=True)

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)

    # BAR CHART
    st.markdown("""<div class="sec-head"><div class="sec-head-bar" style="background:#3B82F6;"></div>
      <div class="sec-head-title">3. TOTAL UNITS SOLD COMPARISON (BAR CHART)</div></div>""", unsafe_allow_html=True)

    if pie_df["units_annual"].sum() > 0:
        fig_units = px.bar(pie_df, x="company", y="units_annual", color="company", color_discrete_map=PLOT_COLORS, text="units_annual")
        fig_units.update_traces(texttemplate='%{text:,.0f}', textposition='outside')
        fig_units.update_layout(height=400, showlegend=False, yaxis_title="Total Units Sold", xaxis_title="Company", margin=dict(t=20, b=20))
        st.plotly_chart(style_plotly_dark(fig_units), use_container_width=True)