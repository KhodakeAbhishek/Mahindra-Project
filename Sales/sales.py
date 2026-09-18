import streamlit as st
import pandas as pd
import requests
import json
import time
from datetime import datetime
import plotly.express as px

from Main.shared_config import (
    get_groq_client,
    get_tavily_key,
    safe_json_parse,
    style_plotly_dark,
    ACCENT_MAP,
    PLOT_COLORS,
)


# =========================================================
# HELPERS
# =========================================================

def _hex_to_rgb(hex_color: str) -> str:
    try:
        hex_color = hex_color.lstrip("#")
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r},{g},{b}"
    except Exception:
        return "255,92,10"


def _safe_float(value, default=None):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = (
                value.replace(",", "")
                .replace("₹", "")
                .replace("%", "")
                .strip()
            )

        return float(value)
    except Exception:
        return default


def _safe_int(value, default=0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = (
                value.replace(",", "")
                .replace(" ", "")
                .strip()
            )

        return int(float(value))
    except Exception:
        return default


def _normalize_growth(value):
    if value is None:
        return "N/A"

    value = str(value).strip()

    if value.lower() in ["", "n/a", "na", "none", "null", "unknown"]:
        return "N/A"

    try:
        numeric = float(value.replace("%", "").replace("+", ""))
        return f"{numeric:+.1f}%"
    except Exception:
        return "N/A"


def _empty_company_data(company):
    return {
        "company": company,

        "units_annual": 0,

        "revenue_annual_cr": None,

        "q1_cr": None,
        "q2_cr": None,
        "q3_cr": None,
        "q4_cr": None,

        "units_q1": None,
        "units_q2": None,
        "units_q3": None,
        "units_q4": None,

        "monthly_avg_cr": None,
        "monthly_avg_units": None,

        "growth_percent": "N/A",

        "scope": "Unknown",

        "source_url": "#",

        "source_urls": [],

        "source_name": "",

        "data_source_type": "No verified data",

        "confidence": "low",

        "source_description": "",
    }


# =========================================================
# TAVILY
# =========================================================

def _tavily_search(query, max_results=8):

    api_key = get_tavily_key()

    if not api_key:
        return {
            "answer": "",
            "results": []
        }

    try:

        response = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": api_key,
                "query": query,
                "search_depth": "advanced",
                "max_results": max_results,
                "include_answer": True,
                "include_raw_content": True,
            },
            timeout=30,
        )

        if response.status_code != 200:
            st.warning(
                f"Tavily HTTP error: {response.status_code}"
            )
            return {
                "answer": "",
                "results": []
            }

        return response.json()

    except requests.RequestException as e:

        st.warning(f"Tavily request failed: {e}")

        return {
            "answer": "",
            "results": []
        }

    except Exception as e:

        st.warning(f"Tavily error: {e}")

        return {
            "answer": "",
            "results": []
        }


# =========================================================
# COMPANY SEARCH
# =========================================================

def _build_company_queries(company, start_year, end_year):

    return [
        (
            f'"{company}" tractor sales '
            f'{start_year} {end_year} annual report units'
        ),

        (
            f'"{company}" tractors sold '
            f'{start_year} {end_year}'
        ),

        (
            f'"{company}" tractor volume '
            f'{start_year} {end_year}'
        ),

        (
            f'"{company}" tractor sales investor presentation '
            f'{start_year} {end_year}'
        ),

        (
            f'"{company}" agricultural tractor sales '
            f'{start_year} {end_year}'
        ),

        (
            f'"{company}" tractor wholesale retail sales '
            f'{start_year} {end_year}'
        ),
    ]


# =========================================================
# COLLECT WEB RESEARCH
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def collect_company_web_data(company, start_year, end_year):

    queries = _build_company_queries(
        company,
        start_year,
        end_year
    )

    all_results = []
    all_urls = []
    answers = []

    for query in queries:

        data = _tavily_search(query, max_results=6)

        answer = data.get("answer", "")

        if answer:
            answers.append(answer)

        for result in data.get("results", []):

            url = result.get("url", "")

            content = result.get("content", "")

            raw_content = result.get("raw_content", "")

            title = result.get("title", "")

            if url:
                all_urls.append(url)

            all_results.append({
                "title": title,
                "url": url,
                "content": content,
                "raw_content": raw_content,
            })

        time.sleep(0.2)

    # Remove duplicate URLs
    unique_urls = list(dict.fromkeys(all_urls))

    # Remove duplicate search results
    unique_results = []

    seen = set()

    for item in all_results:

        key = (
            item.get("url", ""),
            item.get("title", "")
        )

        if key in seen:
            continue

        seen.add(key)
        unique_results.append(item)

    # Build research text
    research_parts = []

    for answer in answers:
        research_parts.append(
            f"SEARCH ANSWER:\n{answer}"
        )

    for item in unique_results:

        research_parts.append(
            "\n".join([
                f"TITLE: {item.get('title', '')}",
                f"URL: {item.get('url', '')}",
                f"CONTENT: {item.get('content', '')}",
                f"RAW CONTENT: {item.get('raw_content', '')}",
            ])
        )

    research_text = "\n\n".join(research_parts)

    # Keep prompt manageable
    research_text = research_text[:30000]

    return {
        "research_text": research_text,
        "source_urls": unique_urls,
        "results": unique_results,
    }


# =========================================================
# GROQ EXTRACTION
# =========================================================

def _extract_company_data_with_groq(
    company,
    start_year,
    end_year,
    research
):

    client = get_groq_client()

    if client is None:
        return None

    research_text = research.get(
        "research_text",
        ""
    )

    if not research_text.strip():
        return None

    prompt = f"""
You are a strict financial data extraction engine.

COMPANY:
{company}

FINANCIAL YEAR:
{start_year}-{end_year}

Your task is to extract ONLY information explicitly supported
by the supplied research.

IMPORTANT RULES:

1. Never invent a number.

2. Never estimate a number.

3. Never use a market-share assumption.

4. Never use a proxy.

5. Never multiply tractor units by an assumed tractor price.

6. Never create quarterly numbers unless quarterly numbers are
   explicitly present in the source.

7. Never convert a country number into a worldwide number.

8. Determine the geographical scope of every number.

9. Tractor sales means agricultural/farm tractors only.

10. Ignore:
    - cars
    - SUVs
    - trucks
    - motorcycles
    - total automobiles
    - general vehicles
    - revenue unless explicitly reported as tractor/farm-equipment revenue

11. If the source reports GLOBAL/WORLDWIDE tractor units,
    return that number.

12. If the source reports INDIA tractor units only,
    return the number but set scope to "India".

13. If the source reports USA tractor units only,
    return the number but set scope to "USA".

14. If the source reports another country,
    return that country as the scope.

15. If there is no reliable tractor-unit number, return 0.

16. Revenue must only be returned if the source explicitly
    reports revenue associated with the relevant tractor/farm
    equipment business.

17. Do not calculate revenue from units.

18. Do not calculate quarterly revenue from annual revenue.

19. Do not calculate quarterly units from annual units.

20. Growth must only be returned if explicitly supported by
    the source.

21. Select the source that most directly supports the extracted
    number.

22. Give the URL of the supporting source when available.

Return ONLY valid JSON.

Required structure:

{{
    "company": "{company}",
    "units_annual": 0,
    "units_scope": "Unknown",

    "revenue_annual_cr": null,
    "revenue_currency": null,
    "revenue_scope": "Unknown",

    "q1_units": null,
    "q2_units": null,
    "q3_units": null,
    "q4_units": null,

    "q1_revenue_cr": null,
    "q2_revenue_cr": null,
    "q3_revenue_cr": null,
    "q4_revenue_cr": null,

    "growth_percent": "N/A",

    "source_name": "",
    "source_url": "",

    "confidence": "low",

    "source_description": ""
}}

WEB RESEARCH:

{research_text}
"""

    try:

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a factual financial research "
                        "extraction system. Never invent data."
                    ),
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            response_format={
                "type": "json_object"
            },
            temperature=0,
        )

        content = response.choices[0].message.content

        return safe_json_parse(content)

    except Exception as e:

        st.warning(
            f"Groq extraction failed for {company}: {e}"
        )

        return None


# =========================================================
# COMPANY DATA
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_company_data_dynamic(company, period):

    data = _empty_company_data(company)

    # -----------------------------------------------------
    # YEAR
    # -----------------------------------------------------

    try:

        clean_period = (
            period
            .replace("FY ", "")
            .strip()
        )

        start_year = int(
            clean_period.split("-")[0]
        )

        end_year = start_year + 1

    except Exception:

        data["data_source_type"] = (
            "Invalid financial year"
        )

        return data

    # -----------------------------------------------------
    # FUTURE YEAR
    # -----------------------------------------------------

    if start_year > datetime.now().year:

        data["data_source_type"] = (
            "Financial year not yet available"
        )

        return data

    # -----------------------------------------------------
    # TAVILY
    # -----------------------------------------------------

    research = collect_company_web_data(
        company,
        start_year,
        end_year
    )

    if not research["research_text"]:

        data["data_source_type"] = (
            "Tavily returned no usable research"
        )

        return data

    # -----------------------------------------------------
    # GROQ
    # -----------------------------------------------------

    extracted = _extract_company_data_with_groq(
        company,
        start_year,
        end_year,
        research
    )

    if not extracted:

        data["data_source_type"] = (
            "Groq could not extract verified data"
        )

        return data

    # -----------------------------------------------------
    # UNITS
    # -----------------------------------------------------

    units = _safe_int(
        extracted.get("units_annual"),
        0
    )

    units_scope = str(
        extracted.get(
            "units_scope",
            "Unknown"
        )
    )

    # -----------------------------------------------------
    # REVENUE
    # -----------------------------------------------------

    revenue = _safe_float(
        extracted.get("revenue_annual_cr"),
        None
    )

    revenue_scope = str(
        extracted.get(
            "revenue_scope",
            "Unknown"
        )
    )

    # -----------------------------------------------------
    # QUARTERLY UNITS
    # -----------------------------------------------------

    q_units = [
        _safe_int(
            extracted.get("q1_units"),
            None
        ),
        _safe_int(
            extracted.get("q2_units"),
            None
        ),
        _safe_int(
            extracted.get("q3_units"),
            None
        ),
        _safe_int(
            extracted.get("q4_units"),
            None
        ),
    ]

    # -----------------------------------------------------
    # QUARTERLY REVENUE
    # -----------------------------------------------------

    q_revenue = [
        _safe_float(
            extracted.get("q1_revenue_cr"),
            None
        ),
        _safe_float(
            extracted.get("q2_revenue_cr"),
            None
        ),
        _safe_float(
            extracted.get("q3_revenue_cr"),
            None
        ),
        _safe_float(
            extracted.get("q4_revenue_cr"),
            None
        ),
    ]

    # -----------------------------------------------------
    # GROWTH
    # -----------------------------------------------------

    growth = _normalize_growth(
        extracted.get(
            "growth_percent",
            "N/A"
        )
    )

    # -----------------------------------------------------
    # SOURCE
    # -----------------------------------------------------

    source_url = str(
        extracted.get(
            "source_url",
            ""
        )
    ).strip()

    if not source_url:
        urls = research.get(
            "source_urls",
            []
        )

        if urls:
            source_url = urls[0]

    # -----------------------------------------------------
    # STORE VALUES
    # -----------------------------------------------------

    data["units_annual"] = units

    data["scope"] = units_scope

    data["revenue_annual_cr"] = revenue

    data["growth_percent"] = growth

    data["q1_cr"] = q_revenue[0]
    data["q2_cr"] = q_revenue[1]
    data["q3_cr"] = q_revenue[2]
    data["q4_cr"] = q_revenue[3]

    data["units_q1"] = q_units[0]
    data["units_q2"] = q_units[1]
    data["units_q3"] = q_units[2]
    data["units_q4"] = q_units[3]

    data["monthly_avg_cr"] = (
        revenue / 12
        if revenue is not None
        else None
    )

    data["monthly_avg_units"] = (
        units / 12
        if units > 0
        else None
    )

    data["source_url"] = (
        source_url
        if source_url
        else "#"
    )

    data["source_urls"] = (
        research.get("source_urls", [])
    )

    data["source_name"] = str(
        extracted.get(
            "source_name",
            ""
        )
    )

    data["confidence"] = str(
        extracted.get(
            "confidence",
            "low"
        )
    )

    data["source_description"] = str(
        extracted.get(
            "source_description",
            ""
        )
    )

    # -----------------------------------------------------
    # DATA STATUS
    # -----------------------------------------------------

    if units > 0 and revenue is not None:

        data["data_source_type"] = (
            f"Live Web + Groq | "
            f"{units_scope} | "
            f"{data['confidence']} confidence"
        )

    elif units > 0:

        data["data_source_type"] = (
            f"Live Tractor Units | "
            f"{units_scope} | "
            f"{data['confidence']} confidence"
        )

    elif revenue is not None:

        data["data_source_type"] = (
            f"Live Revenue | "
            f"{revenue_scope} | "
            f"{data['confidence']} confidence"
        )

    else:

        data["data_source_type"] = (
            "No verified tractor sales data"
        )

    return data


# =========================================================
# COMPANIES
# =========================================================

ALL_COMPANIES = [
    "Mahindra",
    "Escorts Kubota",
    "Sonalika",
    "TAFE",
    "Swaraj",
    "John Deere",
]


# =========================================================
# FETCH ALL
# =========================================================

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_all_sales(period):

    results = []

    for company in ALL_COMPANIES:

        result = fetch_company_data_dynamic(
            company,
            period
        )

        results.append(result)

    return results


# =========================================================
# FORMAT VALUE
# =========================================================

def fmt_number(value, decimals=0):

    if value is None:
        return "N/A"

    try:
        return f"{value:,.{decimals}f}"
    except Exception:
        return "N/A"


def fmt_currency(value):

    if value is None:
        return "N/A"

    return f"₹ {value:,.2f}"


# =========================================================
# RENDER SALES TAB
# =========================================================

def render_sales_tab(
    market_data,
    period,
    selected_company
):

    clean_fy = period.replace(
        "FY ",
        ""
    )

    if not market_data:

        st.warning(
            "No company data was returned."
        )

        return

    # -----------------------------------------------------
    # SPOTLIGHT
    # -----------------------------------------------------

    if "sales_spotlight" not in st.session_state:

        st.session_state.sales_spotlight = (
            selected_company
            if selected_company in ALL_COMPANIES
            else ALL_COMPANIES[0]
        )

    spotlight_company = (
        st.session_state.sales_spotlight
    )

    available_companies = [
        x["company"]
        for x in market_data
    ]

    if spotlight_company not in available_companies:

        spotlight_company = (
            available_companies[0]
        )

    spot = next(
        (
            x for x in market_data
            if x["company"] == spotlight_company
        ),
        market_data[0]
    )

    # -----------------------------------------------------
    # HEADER
    # -----------------------------------------------------

    st.markdown(
        f"""
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#FF5C0A;"></div>

            <div class="sec-head-title">
                TRACTOR SALES DATA — {clean_fy}
            </div>

            <div class="sec-head-badge">
                LIVE WEB + GROQ EXTRACTION
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    accent, glow = ACCENT_MAP.get(
        spot["company"],
        (
            "#FF5C0A",
            "rgba(255,92,10,.18)"
        )
    )

    growth = spot["growth_percent"]

    if growth.startswith("+"):

        growth_color = "#0FE88A"
        growth_display = f"▲ {growth}"

    elif growth.startswith("-"):

        growth_color = "#FF2D55"
        growth_display = f"▼ {growth}"

    else:

        growth_color = "#7b8db5"
        growth_display = "N/A"

    # -----------------------------------------------------
    # SPOTLIGHT CARD
    # -----------------------------------------------------

    revenue_display = (
        f"₹{spot['revenue_annual_cr']:,.2f} Cr"
        if spot["revenue_annual_cr"] is not None
        else "N/A"
    )

    units_display = (
        f"{spot['units_annual']:,.0f} Units"
        if spot["units_annual"] > 0
        else "N/A"
    )

    st.markdown(
        f"""
        <div style="
            background:
            linear-gradient(
                135deg,
                rgba({_hex_to_rgb(accent)},.13),
                rgba({_hex_to_rgb(accent)},.04)
            );
            border:1.5px solid
            rgba({_hex_to_rgb(accent)},.45);
            border-radius:12px;
            padding:18px 26px;
            margin-bottom:22px;
            display:flex;
            align-items:center;
            gap:28px;
        ">

            <div style="flex-shrink:0;">

                <div style="
                    font-family:'Bebas Neue';
                    font-size:28px;
                    letter-spacing:4px;
                    color:{accent};
                ">
                    {spot['company'].upper()}
                </div>

                <div style="
                    margin-top:6px;
                    font-size:9px;
                    color:#7b8db5;
                ">
                    Scope: {spot['scope']}
                </div>

                <div style="
                    margin-top:5px;
                    font-size:9px;
                    color:#7b8db5;
                ">
                    Confidence: {spot['confidence']}
                </div>

            </div>

            <div style="
                width:1px;
                height:50px;
                background:
                rgba({_hex_to_rgb(accent)},.25);
            "></div>

            <div>

                <div style="
                    font-size:8px;
                    color:#6a7fa8;
                    text-transform:uppercase;
                ">
                    Verified Revenue
                </div>

                <div style="
                    font-size:30px;
                    font-family:'Bebas Neue';
                    color:#fff;
                ">
                    {revenue_display}
                </div>

            </div>

            <div style="
                width:1px;
                height:50px;
                background:
                rgba({_hex_to_rgb(accent)},.25);
            "></div>

            <div>

                <div style="
                    font-size:8px;
                    color:#6a7fa8;
                    text-transform:uppercase;
                ">
                    Tractor Units
                </div>

                <div style="
                    font-size:30px;
                    font-family:'Bebas Neue';
                    color:#fff;
                ">
                    {units_display}
                </div>

            </div>

            <div style="
                width:1px;
                height:50px;
                background:
                rgba({_hex_to_rgb(accent)},.25);
            "></div>

            <div>

                <div style="
                    font-size:8px;
                    color:#6a7fa8;
                    text-transform:uppercase;
                ">
                    YoY Growth
                </div>

                <div style="
                    font-size:28px;
                    font-family:'Bebas Neue';
                    color:{growth_color};
                ">
                    {growth_display}
                </div>

            </div>

        </div>
        """,
        unsafe_allow_html=True
    )

    # -----------------------------------------------------
    # COMPANY CARDS
    # -----------------------------------------------------

    kpi_cols = st.columns(
        len(market_data)
    )

    for i, item in enumerate(market_data):

        with kpi_cols[i]:

            card_accent, card_glow = ACCENT_MAP.get(
                item["company"],
                (
                    "#FF5C0A",
                    "rgba(255,92,10,.18)"
                )
            )

            if st.button(
                f"Focus {item['company']}",
                key=f"sales_focus_{i}_{item['company']}",
                use_container_width=True
            ):

                st.session_state.sales_spotlight = (
                    item["company"]
                )

                st.rerun()

            revenue = (
                fmt_currency(
                    item["revenue_annual_cr"]
                )
                if item["revenue_annual_cr"] is not None
                else "N/A"
            )

            units = (
                fmt_number(
                    item["units_annual"]
                )
                if item["units_annual"] > 0
                else "N/A"
            )

            st.markdown(
                f"""
                <div class="kpi-card"
                     style="
                     --_accent:{card_accent};
                     --_glow:{card_glow};
                     ">

                    <div class="kpi-lbl">
                        {period}
                    </div>

                    <div class="kpi-company-name">
                        {item['company']}
                    </div>

                    <div class="kpi-val">
                        {revenue}
                    </div>

                    <div style="
                        margin-top:8px;
                        font-size:10px;
                        color:#7b8db5;
                    ">
                        Tractor Units:
                        <b style="color:#fff;">
                            {units}
                        </b>
                    </div>

                    <div style="
                        margin-top:8px;
                        font-size:8px;
                        color:#0FE88A;
                    ">
                        {item['data_source_type']}
                    </div>

                </div>
                """,
                unsafe_allow_html=True
            )

    # =====================================================
    # TABLE 1
    # =====================================================

    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#1FD8F0;"></div>
            <div class="sec-head-title">
                TABLE 1: VERIFIED TRACTOR REVENUE
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    revenue_rows = []

    for item in market_data:

        revenue_rows.append({
            "Company": item["company"],
            "Monthly Avg": fmt_currency(
                item["monthly_avg_cr"]
            ),
            "Q1": fmt_currency(item["q1_cr"]),
            "Q2": fmt_currency(item["q2_cr"]),
            "Q3": fmt_currency(item["q3_cr"]),
            "Q4": fmt_currency(item["q4_cr"]),
            "Annual Total": fmt_currency(
                item["revenue_annual_cr"]
            ),
            "Scope": item["scope"],
        })

    st.dataframe(
        pd.DataFrame(revenue_rows),
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # TABLE 2
    # =====================================================

    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#9D6FFF;"></div>
            <div class="sec-head-title">
                TABLE 2: VERIFIED TRACTOR UNITS
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    unit_rows = []

    for item in market_data:

        unit_rows.append({
            "Company": item["company"],

            "Monthly Avg": fmt_number(
                item["monthly_avg_units"]
            ),

            "Q1": fmt_number(
                item["units_q1"]
            ),

            "Q2": fmt_number(
                item["units_q2"]
            ),

            "Q3": fmt_number(
                item["units_q3"]
            ),

            "Q4": fmt_number(
                item["units_q4"]
            ),

            "Annual Total": fmt_number(
                item["units_annual"]
            ),

            "YoY Growth": item["growth_percent"],

            "Scope": item["scope"],
        })

    st.dataframe(
        pd.DataFrame(unit_rows),
        use_container_width=True,
        hide_index=True
    )

    # =====================================================
    # CHART 1 — QUARTERLY REVENUE
    # =====================================================

    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#0FE88A;"></div>
            <div class="sec-head-title">
                1. QUARTERLY REVENUE TRAJECTORY
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    line_data = []

    for item in market_data:

        quarters = [
            ("Q1", item["q1_cr"]),
            ("Q2", item["q2_cr"]),
            ("Q3", item["q3_cr"]),
            ("Q4", item["q4_cr"]),
        ]

        for quarter, value in quarters:

            if value is not None:

                line_data.append({
                    "Company": item["company"],
                    "Quarter": quarter,
                    "Revenue (₹ Cr)": value,
                })

    df_line = pd.DataFrame(line_data)

    if not df_line.empty:

        fig_line = px.line(
            df_line,
            x="Quarter",
            y="Revenue (₹ Cr)",
            color="Company",
            color_discrete_map=PLOT_COLORS,
            markers=True,
        )

        st.plotly_chart(
            style_plotly_dark(fig_line),
            use_container_width=True
        )

    else:

        st.info(
            "No verified quarterly revenue data was found."
        )

    # =====================================================
    # CHART 2 — REVENUE SHARE
    # =====================================================

    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#FF2D55;"></div>
            <div class="sec-head-title">
                2. REVENUE DISTRIBUTION
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    revenue_chart_data = [
        item
        for item in market_data
        if item["revenue_annual_cr"] is not None
        and item["revenue_annual_cr"] > 0
    ]

    if revenue_chart_data:

        pie_df = pd.DataFrame(
            revenue_chart_data
        )

        fig_pie = px.pie(
            pie_df,
            values="revenue_annual_cr",
            names="company",
            hole=0.55,
            color="company",
            color_discrete_map=PLOT_COLORS,
        )

        fig_pie.update_traces(
            textinfo="percent+label",
            textposition="inside",
            hovertemplate=(
                "<b>%{label}</b><br>"
                "₹%{value:,.2f} Cr<br>"
                "%{percent:.1%}"
            ),
        )

        fig_pie.update_layout(
            height=400,
            showlegend=True,
            margin=dict(
                t=20,
                b=20
            ),
        )

        st.plotly_chart(
            style_plotly_dark(fig_pie),
            use_container_width=True
        )

    else:

        st.info(
            "No verified revenue data available for distribution chart."
        )

    # =====================================================
    # CHART 3 — UNITS
    # =====================================================

    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#3B82F6;"></div>
            <div class="sec-head-title">
                3. VERIFIED TRACTOR UNITS COMPARISON
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    unit_chart_data = [
        item
        for item in market_data
        if item["units_annual"] > 0
    ]

    if unit_chart_data:

        units_df = pd.DataFrame(
            unit_chart_data
        )

        fig_units = px.bar(
            units_df,
            x="company",
            y="units_annual",
            color="company",
            color_discrete_map=PLOT_COLORS,
            text="units_annual",
        )

        fig_units.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
        )

        fig_units.update_layout(
            height=400,
            showlegend=False,
            yaxis_title="Verified Tractor Units",
            xaxis_title="Company",
            margin=dict(
                t=20,
                b=20
            ),
        )

        st.plotly_chart(
            style_plotly_dark(fig_units),
            use_container_width=True
        )

    else:

        st.info(
            "No verified tractor-unit data available."
        )

    # =====================================================
    # SOURCE DETAILS
    # =====================================================

    st.markdown("---")

    st.markdown(
        """
        <div class="sec-head">
            <div class="sec-head-bar"
                 style="background:#64748B;"></div>
            <div class="sec-head-title">
                DATA SOURCES & VERIFICATION
            </div>
        </div>
        """,
        unsafe_allow_html=True
    )

    for item in market_data:

        with st.expander(
            f"{item['company']} — {item['data_source_type']}"
        ):

            st.write(
                f"**Scope:** {item['scope']}"
            )

            st.write(
                f"**Confidence:** {item['confidence']}"
            )

            if item["source_name"]:
                st.write(
                    f"**Source:** {item['source_name']}"
                )

            if item["source_description"]:
                st.write(
                    item["source_description"]
                )

            if item["source_url"] != "#":

                st.markdown(
                    f"[Open source]({item['source_url']})"
                )

            if item["source_urls"]:

                st.write("Additional Tavily sources:")

                for url in item["source_urls"][:10]:

                    st.markdown(
                        f"- [{url}]({url})"
                    )


# =========================================================
# OPTIONAL DEBUG FUNCTION
# =========================================================

def render_sales_debug(market_data):

    st.markdown("---")

    st.subheader("Sales Data Debug")

    debug_rows = []

    for item in market_data:

        debug_rows.append({
            "Company": item["company"],
            "Units": item["units_annual"],
            "Revenue": item["revenue_annual_cr"],
            "Scope": item["scope"],
            "Growth": item["growth_percent"],
            "Confidence": item["confidence"],
            "Source": item["source_url"],
            "Status": item["data_source_type"],
        })

    st.dataframe(
        pd.DataFrame(debug_rows),
        use_container_width=True,
        hide_index=True
    )
