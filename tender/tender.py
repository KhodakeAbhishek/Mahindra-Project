"""
tender.py  –  Tender Manager + Streamlit Dashboard Tab  (Tractor Edition)
Companies: Mahindra | Escorts Kubota | Sonalika | TAFE | Swaraj | John Deere
"""

import sqlite3
import json
import os
import re
import time
import hashlib
import pickle
import streamlit as st
from datetime import datetime, timedelta

from tender.pipeline import run_ai_tender_pipeline, setup_database

# ─────────────────────────────────────────
# CONFIG
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCwPkqEd5p4VBGpK1cRKDGb2RiFZqO6EGk")
DB_NAME        = "tenders.db"
CACHE_DIR      = "cache"
CACHE_DURATION = 1800

MONTHS_LIST = [
    "All Months",
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]
MONTHS_ONLY = [
    "January","February","March","April","May","June",
    "July","August","September","October","November","December",
]

# ── Brand colours (Tractor Edition) ──
BRAND_COLORS = {
    "Mahindra":       "#E8002D",   # Mahindra Red
    "Escorts Kubota": "#F97316",   # Escorts Orange
    "Sonalika":       "#22C55E",   # Sonalika Green
    "TAFE":           "#F5C842",   # TAFE Yellow
    "Swaraj":         "#3B82F6",   # Swaraj Blue
    "John Deere":     "#84CC16",   # John Deere Lime
}

# ── Company display name → DB brand key mapping ──
COMPANY_TO_BRAND = {
    "All (Competitors)":    "",
    "Mahindra":             "Mahindra",
    "Escorts Kubota":       "Escorts Kubota",
    "Sonalika":             "Sonalika",
    "TAFE":                 "TAFE",
    "Swaraj":               "Swaraj",
    "John Deere":           "John Deere",
}

os.makedirs(CACHE_DIR, exist_ok=True)

_GEMINI_OK = False
def _init_gemini():
    global _GEMINI_OK
    if _GEMINI_OK:
        return True
    try:
        import google.genai as genai
        client = genai.Client(api_key=GEMINI_API_KEY)
        _GEMINI_OK = True
        return True
    except Exception as e:
        print(f"Gemini init error: {e}")
    return _GEMINI_OK


# ─────────────────────────────────────────
# CACHE
# ─────────────────────────────────────────
def _ck(tag):
    h = datetime.now().strftime("%Y-%m-%d_%H")
    return os.path.join(CACHE_DIR, hashlib.md5(f"{tag}_{h}".encode()).hexdigest() + ".pkl")

def _lc(path):
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                d = pickle.load(f)
            if time.time() - d["ts"] < CACHE_DURATION:
                return d["v"]
        except Exception:
            pass
    return None

def _sc(path, value):
    try:
        with open(path, "wb") as f:
            pickle.dump({"v": value, "ts": time.time()}, f)
    except Exception:
        pass


# ─────────────────────────────────────────
# UTILITY
# ─────────────────────────────────────────
def get_brand_color(brand):
    brand = brand or ""
    for k, v in BRAND_COLORS.items():
        if k.lower() in brand.lower():
            return v
    return "#9D6FFF"


def get_days_until_deadline(dl):
    if not dl or dl in ("Not Specified", "", None):
        return None
    try:
        d    = datetime.strptime(str(dl)[:10], "%Y-%m-%d")
        days = (d - datetime.now()).days
        if days < 0:  return "Expired"
        if days == 0: return "Today"
        if days == 1: return "Tomorrow"
        return f"{days}d left"
    except Exception:
        return None


def _fy_date_bounds(fy_str):
    try:
        parts      = fy_str.replace("FY ", "").split("-")
        start_year = int(parts[0])
        end_year   = start_year + 1
        return f"{start_year}-04-01", f"{end_year}-03-31"
    except Exception:
        return None, None


def _month_in_fy(fy_str, month_name):
    try:
        parts      = fy_str.replace("FY ", "").split("-")
        start_year = int(parts[0])
        end_year   = start_year + 1
        month_num  = datetime.strptime(month_name, "%B").month
        year       = start_year if month_num >= 4 else end_year
        return year, month_num
    except Exception:
        return None, None


# ─────────────────────────────────────────
# TENDER MANAGER
# ─────────────────────────────────────────
class TenderManager:
    def __init__(self):
        self.db = DB_NAME

    def _conn(self):
        return sqlite3.connect(self.db)

    def _to_dicts(self, cur):
        cols = [d[0] for d in cur.description]
        return [dict(zip(cols, row)) for row in cur.fetchall()]

    def get_latest_tenders(self, days=7, limit=20):
        key    = _ck(f"latest_{days}_{limit}")
        cached = _lc(key)
        if cached is not None:
            return cached
        conn   = self._conn()
        cur    = conn.cursor()
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        cur.execute(
            "SELECT * FROM tractor_tenders WHERE publish_date>=? ORDER BY publish_date DESC, created_at DESC LIMIT ?",
            (cutoff, limit),
        )
        result = self._to_dicts(cur)
        conn.close()
        _sc(key, result)
        return result

    def get_tenders_by_fy(self, fy_str, brand_kw=""):
        key    = _ck(f"fy_{fy_str}_{brand_kw}")
        cached = _lc(key)
        if cached is not None:
            return cached
        start, end = _fy_date_bounds(fy_str)
        if not start:
            return []
        conn = self._conn()
        cur  = conn.cursor()
        if brand_kw:
            cur.execute(
                "SELECT * FROM tractor_tenders WHERE publish_date BETWEEN ? AND ? AND brand LIKE ? ORDER BY publish_date DESC",
                (start, end, f"%{brand_kw}%"),
            )
        else:
            cur.execute(
                "SELECT * FROM tractor_tenders WHERE publish_date BETWEEN ? AND ? ORDER BY publish_date DESC",
                (start, end),
            )
        result = self._to_dicts(cur)
        conn.close()
        _sc(key, result)
        return result

    def get_tenders_by_fy_month(self, fy_str, month_name, brand_kw=""):
        year, month_num = _month_in_fy(fy_str, month_name)
        if not year:
            return []
        key    = _ck(f"fym_{year}_{month_num}_{brand_kw}")
        cached = _lc(key)
        if cached is not None:
            return cached
        conn = self._conn()
        cur  = conn.cursor()
        if brand_kw:
            cur.execute(
                "SELECT * FROM tractor_tenders WHERE strftime('%Y',publish_date)=? AND strftime('%m',publish_date)=? AND brand LIKE ? ORDER BY publish_date DESC",
                (str(year), f"{month_num:02d}", f"%{brand_kw}%"),
            )
        else:
            cur.execute(
                "SELECT * FROM tractor_tenders WHERE strftime('%Y',publish_date)=? AND strftime('%m',publish_date)=? ORDER BY publish_date DESC",
                (str(year), f"{month_num:02d}"),
            )
        result = self._to_dicts(cur)
        conn.close()
        _sc(key, result)
        return result

    def get_tenders_by_date_range(self, start_date, end_date, brand_kw=""):
        conn = self._conn()
        cur  = conn.cursor()
        if brand_kw:
            cur.execute(
                "SELECT * FROM tractor_tenders WHERE publish_date BETWEEN ? AND ? AND brand LIKE ? ORDER BY publish_date DESC",
                (str(start_date), str(end_date), f"%{brand_kw}%"),
            )
        else:
            cur.execute(
                "SELECT * FROM tractor_tenders WHERE publish_date BETWEEN ? AND ? ORDER BY publish_date DESC",
                (str(start_date), str(end_date)),
            )
        result = self._to_dicts(cur)
        conn.close()
        return result

    def get_tender_by_id(self, tender_id):
        conn = self._conn()
        cur  = conn.cursor()
        cur.execute("SELECT * FROM tractor_tenders WHERE id=?", (tender_id,))
        cols = [d[0] for d in cur.description]
        row  = cur.fetchone()
        conn.close()
        return dict(zip(cols, row)) if row else None

    def _store_summary(self, tender_id, summary):
        conn = self._conn()
        cur  = conn.cursor()
        try:
            cur.execute(
                "UPDATE tractor_tenders SET ai_summary=? WHERE id=?",
                (json.dumps(summary), tender_id),
            )
            conn.commit()
        except Exception as e:
            print(f"[Tender] summary store error: {e}")
        conn.close()

    def analyze_tender(self, tender_id):
        tender = self.get_tender_by_id(tender_id)
        if not tender:
            return None
        if tender.get("ai_summary"):
            try:
                return json.loads(tender["ai_summary"])
            except Exception:
                pass
        if not _init_gemini():
            return {"error": "Gemini API not available. Check GEMINI_API_KEY."}

        import google.genai as genai

        prompt = f"""
Analyze this tractor / farm equipment tender for a sales intelligence dashboard.

Tender Details:
  Brand        : {tender.get('brand','N/A')}
  Title        : {tender.get('tender_title','N/A')}
  Authority    : {tender.get('company_name','N/A')}
  Location     : {tender.get('location','N/A')}
  Value        : {tender.get('value','N/A')}
  Type         : {tender.get('tender_type','N/A')}
  Deadline     : {tender.get('deadline_date','N/A')}
  Description  : {(tender.get('description') or '')[:400]}

Return a single JSON object with EXACTLY these keys (no markdown fences):
  key_highlights     : array of 3 strings
  opportunity_score  : integer 1–10
  requirements       : string (one sentence)
  competition_level  : "Low" | "Medium" | "High"
  recommendations    : array of 3 strings
  risk_factors       : array of 2 strings
  next_steps         : array of 2 strings
  budget_estimate    : string
  deadline_summary   : string
"""
        try:
            client = genai.Client(api_key=GEMINI_API_KEY)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text.strip()
            text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
            text = re.sub(r"\s*```$", "", text)
            analysis = json.loads(text.strip())
            self._store_summary(tender_id, analysis)
            return analysis
        except Exception as e:
            print(f"[Tender] AI analysis error: {e}")
            return None


# ─────────────────────────────────────────
# MODULE INIT
# ─────────────────────────────────────────
def init_tender_system():
    setup_database()
    return TenderManager()


# ─────────────────────────────────────────
# GLOBAL RENDER COUNTER
# ensures every button key is unique per Streamlit run
# ─────────────────────────────────────────
_CARD_CTR = 0


# ─────────────────────────────────────────
# CARD RENDERER
# ─────────────────────────────────────────
def _render_card(tender, manager):
    global _CARD_CTR
    _CARD_CTR += 1
    uniq = _CARD_CTR

    tid         = tender.get("id", 0)
    brand       = tender.get("brand")         or "Unknown"
    title       = tender.get("tender_title")  or "No Title"
    pub_date    = tender.get("publish_date")  or ""
    value       = tender.get("value")         or ""
    location    = tender.get("location")      or ""
    authority   = tender.get("company_name")  or ""
    deadline    = tender.get("deadline_date") or ""
    source_url  = tender.get("source_url")    or ""
    description = tender.get("description")   or ""
    t_type      = tender.get("tender_type")   or ""

    color        = get_brand_color(brand)
    deadline_lbl = get_days_until_deadline(deadline)

    try:
        date_display = datetime.strptime(pub_date[:10], "%Y-%m-%d").strftime("%d %b %Y")
    except Exception:
        date_display = pub_date or "N/A"

    # ── badges ──
    if deadline_lbl == "Expired":
        dl_badge = '<span style="background:rgba(150,150,150,0.15);color:#888;padding:3px 10px;border-radius:10px;font-size:11px;font-family:monospace;">✗ Expired</span>'
    elif deadline_lbl:
        dl_badge = f'<span style="background:rgba(255,92,10,0.15);color:#FF5C0A;padding:3px 10px;border-radius:10px;font-size:11px;font-weight:600;font-family:monospace;">⏰ {deadline_lbl}</span>'
    else:
        dl_badge = ""

    if value and value not in ("Not Specified", "Value TBD", ""):
        val_html = f'<div style="color:#F5C842;font-weight:600;font-size:13px;margin-top:6px;font-family:sans-serif;">💰 {value}</div>'
    else:
        val_html = '<div style="color:#64748b;font-size:12px;margin-top:6px;font-family:sans-serif;">💰 Value Not Specified</div>'

    type_html = ""
    if t_type and t_type not in ("Not Specified", ""):
        type_html = f'<span style="background:rgba(31,216,240,0.12);color:#1FD8F0;padding:2px 9px;border-radius:8px;font-size:10px;margin-left:8px;font-family:monospace;">{t_type}</span>'

    meta_parts = []
    if location and location not in ("Not Specified", ""):
        meta_parts.append(f"📍 {location}")
    if authority and authority not in ("Not Specified", ""):
        meta_parts.append(f"🏢 {authority}")
    meta_line = "&nbsp;&nbsp;·&nbsp;&nbsp;".join(meta_parts)

    # ── card HTML ──
    st.markdown(f"""
<div style="background:linear-gradient(145deg,#0f1520,#141b28); border:1px solid #1c2540; border-left:4px solid {color}; border-radius:14px; padding:25px 28px; margin-bottom:25px; margin-top:25px; box-shadow:0 4px 16px rgba(0,0,0,0.3); position:relative; overflow:hidden; clear:both; min-height:180px;">
<div style="display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:18px;">
<div style="flex:1;margin-right:20px;">
<div style="display:inline-block; background:{color}22; color:{color}; border-radius:20px; padding:5px 16px; font-family:monospace; font-size:10px; letter-spacing:2px; font-weight:700; text-transform:uppercase; margin-bottom:10px;">{brand.upper()}</div>
{type_html}
</div>
<div style="display:flex;gap:10px;align-items:center;flex-shrink:0;white-space:nowrap;">
{dl_badge}
<span style="font-family:monospace;font-size:11px;color:#ffffff;">📅 {date_display}</span>
</div>
</div>
<div style="font-family:'Barlow Condensed',sans-serif; font-size:18px; font-weight:600; color:#ffffff; line-height:1.5; margin-bottom:18px; word-wrap:break-word; overflow-wrap:break-word; clear:both; padding-right:10px;">{title}</div>
{val_html}
<div style="font-family:monospace;font-size:11px;color:#94a3b8;margin-top:18px;line-height:1.4;clear:both;">{meta_line}</div>
</div>
""", unsafe_allow_html=True)

    # ── action buttons ──
    bc1, bc2, bc3 = st.columns([2, 2, 4])
    with bc1:
        if source_url and source_url.startswith("http"):
            st.link_button("🔗 View Source", source_url)
        else:
            st.button("🔗 No URL", key=f"nosrc_{uniq}", disabled=True)
    with bc2:
        analyze_clicked = st.button("🧠 Analyze", key=f"analyze_{tid}_{uniq}")

    # ── description expander ──
    if description and description not in ("Not Specified", "No description available", ""):
        clean_desc = description
        clean_desc = re.sub(r'<[^>]+>', '', clean_desc)
        clean_desc = re.sub(r'```.*?```', '', clean_desc, flags=re.DOTALL)
        clean_desc = re.sub(r'def\s+\w+.*', '', clean_desc)
        clean_desc = re.sub(r'import\s+\w+.*', '', clean_desc)
        clean_desc = re.sub(r'from\s+\w+.*', '', clean_desc)
        clean_desc = re.sub(r'#.*', '', clean_desc)
        clean_desc = re.sub(r'style=.*?;', '', clean_desc)
        clean_desc = re.sub(r'color:.*?;', '', clean_desc)
        clean_desc = re.sub(r'background:.*?;', '', clean_desc)
        clean_desc = re.sub(r'padding:.*?;', '', clean_desc)
        clean_desc = re.sub(r'margin:.*?;', '', clean_desc)
        clean_desc = re.sub(r'display:.*?;', '', clean_desc)
        clean_desc = re.sub(r'font-family:.*?;', '', clean_desc)
        clean_desc = re.sub(r'font-size:.*?;', '', clean_desc)
        clean_desc = re.sub(r'border:.*?;', '', clean_desc)
        clean_desc = ' '.join(clean_desc.split())[:300]
        if clean_desc:
            with st.expander("📄 Description", expanded=False):
                st.markdown(
                    f"<div style='padding:15px; background:#0a0d17; border-radius:8px; color:#ffffff;"
                    f"font-size:13px; line-height:1.5; border:1px solid #1c2540; margin:10px 0;'>"
                    f"{clean_desc}</div>",
                    unsafe_allow_html=True,
                )

    # ── analysis panel ──
    if analyze_clicked:
        with st.spinner("Gemini is analyzing the tender…"):
            analysis = manager.analyze_tender(tid)
        if not analysis:
            st.error("Analysis failed. Please check your GEMINI_API_KEY.")
        elif "error" in analysis:
            st.warning(analysis["error"])
        else:
            score       = analysis.get("opportunity_score", 0)
            score_color = "#0FE88A" if score >= 7 else "#F5C842" if score >= 4 else "#FF5C0A"
            comp        = analysis.get("competition_level", "N/A")

            def _row(label, val_html_inner):
                return (
                    f'<div style="display:flex;align-items:flex-start;padding:12px 20px;'
                    f'border-bottom:1px solid #1c2540;gap:20px;">'
                    f'<div style="font-family:monospace;font-size:9px;font-weight:700;color:#1FD8F0;'
                    f'text-transform:uppercase;letter-spacing:1.5px;min-width:200px;flex-shrink:0;padding-top:2px;">'
                    f'{label}</div>'
                    f'<div style="font-family:sans-serif;font-size:13px;color:#e2e8f0;line-height:1.6;flex:1;">'
                    f'{val_html_inner}</div></div>'
                )

            def _bullets(items):
                return "".join(f'<div style="padding:2px 0;">• {i}</div>' for i in (items or []))

            body = (
                _row("OPPORTUNITY SCORE", f'<span style="font-size:22px;font-weight:700;color:{score_color};">{score}/10</span>')
                + _row("COMPETITION", comp)
                + _row("BUDGET ESTIMATE", analysis.get("budget_estimate", "N/A"))
                + _row("DEADLINE", analysis.get("deadline_summary", "N/A"))
            )
            if analysis.get("key_highlights"):
                body += _row("KEY HIGHLIGHTS", _bullets(analysis["key_highlights"]))
            if analysis.get("requirements"):
                body += _row("REQUIREMENTS", analysis["requirements"])
            if analysis.get("recommendations"):
                body += _row("RECOMMENDATIONS", _bullets(analysis["recommendations"]))
            if analysis.get("risk_factors"):
                rf = "".join(
                    f'<div style="color:#FF5C0A;padding:2px 0;">⚠ {r}</div>'
                    for r in analysis["risk_factors"]
                )
                body += _row("RISK FACTORS", rf)
            if analysis.get("next_steps"):
                ns = "".join(
                    f'<div style="color:#0FE88A;padding:2px 0;">✓ {s}</div>'
                    for s in analysis["next_steps"]
                )
                body += _row("NEXT STEPS", ns)

            st.markdown(f"""
<div style="background:linear-gradient(145deg,#0a0d17,#060911); border:1px solid #1c2540; border-left:4px solid #0FE88A; border-radius:12px; margin-top:30px; margin-bottom:40px; overflow:hidden; clear:both; min-height:200px;">
    <div style="background:rgba(15,232,138,0.07); padding:15px 25px; border-bottom:1px solid #1c2540; font-family:monospace; font-size:14px; letter-spacing:3px; color:#0FE88A; font-weight:700;">📊 AI TENDER ANALYSIS — GEMINI</div>
    {body}
</div>
""", unsafe_allow_html=True)

    st.markdown("<div style='height:8px;clear:both;'></div>", unsafe_allow_html=True)


# ─────────────────────────────────────────
# MAIN DASHBOARD TAB
# ─────────────────────────────────────────
def render_tenders_tab(selected_company, selected_period):
    global _CARD_CTR
    _CARD_CTR = 0

    manager  = TenderManager()
    brand_kw = "" if selected_company == "All (Competitors)" else COMPANY_TO_BRAND.get(selected_company, selected_company.split()[0])

    # ── section header ──
    st.markdown("""
<div style="display:flex;align-items:center;gap:12px;margin-bottom:22px;padding-bottom:14px;border-bottom:1px solid #1c2540;">
    <div style="width:4px;height:26px;background:#E8002D;border-radius:2px;flex-shrink:0;"></div>
    <div style="font-family:'Bebas Neue',sans-serif;font-size:21px;letter-spacing:3px;color:#f8fafc;">TRACTOR TENDERS INTELLIGENCE</div>
    <div style="margin-left:auto;font-family:monospace;font-size:8px;letter-spacing:2px;color:#8a9fc0;background:#0f1520;border:1px solid #1c2540;padding:3px 10px;border-radius:4px;text-transform:uppercase;">
        MAHINDRA · ESCORTS KUBOTA · SONALIKA · TAFE · SWARAJ · JOHN DEERE
    </div>
</div>
""", unsafe_allow_html=True)

    # ══════════════════════════════════════
    # BLOCK 1 — LATEST 7-DAY STRIP
    # ══════════════════════════════════════
    with st.expander("🔴  LATEST TENDERS — Last 7 Days", expanded=True):
        latest = manager.get_latest_tenders(days=7, limit=15)
        if latest:
            st.markdown(
                f"<p style='font-family:monospace;font-size:10px;color:#94a3b8;'>"
                f"Showing {len(latest)} most recent tenders across all companies</p>",
                unsafe_allow_html=True,
            )
            for t in latest:
                _render_card(t, manager)
        else:
            st.info("No tenders in the last 7 days. Use the pipeline below to fetch fresh data.")

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)

    # ══════════════════════════════════════
    # BLOCK 2 — PIPELINE TRIGGER
    # ══════════════════════════════════════
    with st.expander("🌐  FETCH NEW LIVE DATA FROM THE WEB  (RUN PIPELINE)", expanded=False):
        st.caption("The dashboard loads instantly from the database. Use this to scrape fresh data from the internet.")

        tab_month, tab_range = st.tabs(["📅 By Month & Year", "📆 Custom Date Range"])

        with tab_month:
            mc1, mc2, mc3 = st.columns([1, 1, 2])
            with mc1:
                cur_month   = datetime.now().strftime("%B")
                fetch_month = st.selectbox(
                    "Target Month", MONTHS_ONLY,
                    index=MONTHS_ONLY.index(cur_month) if cur_month in MONTHS_ONLY else 0,
                    key="pipeline_month",
                )
            with mc2:
                cur_yr     = datetime.now().year
                fetch_year = st.selectbox(
                    "Target Year",
                    [cur_yr + 1, cur_yr, cur_yr - 1, cur_yr - 2],
                    index=1, key="pipeline_year",
                )
            with mc3:
                st.markdown("<br>", unsafe_allow_html=True)
                force_refetch = st.checkbox("Force re-fetch (overwrite existing)", key="pipeline_force")
                if st.button(
                    f"⚡ RUN AI SCRAPER FOR {fetch_month[:3].upper()} {fetch_year}",
                    key="pipeline_run", use_container_width=True, type="primary",
                ):
                    with st.spinner(
                        f"🔍 Searching web for {fetch_month} {fetch_year} tenders "
                        f"(Mahindra, Escorts Kubota, Sonalika, TAFE, Swaraj, John Deere)…"
                    ):
                        ok = run_ai_tender_pipeline(
                            target_year=fetch_year,
                            target_month=fetch_month,
                            force=force_refetch,
                        )
                    if ok:
                        st.success(f"✅ Pipeline complete for {fetch_month} {fetch_year}! Database updated.")
                        st.cache_data.clear()
                        if os.path.exists(CACHE_DIR):
                            for file in os.listdir(CACHE_DIR):
                                os.remove(os.path.join(CACHE_DIR, file))
                        st.rerun()
                    else:
                        st.error("Pipeline failed. Check logs / API key.")

        with tab_range:
            rc1, rc2, rc3 = st.columns([1, 1, 2])
            with rc1:
                start_dt = st.date_input("Start Date", value=datetime.now().replace(day=1), key="range_start")
            with rc2:
                end_dt   = st.date_input("End Date",   value=datetime.now(),                key="range_end")
            with rc3:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("⚡ FETCH DATE RANGE", key="range_run", use_container_width=True, type="primary"):
                    if start_dt > end_dt:
                        st.error("Start date must be before end date.")
                    else:
                        months_to_fetch = []
                        cur_date = datetime(start_dt.year, start_dt.month, 1)
                        end_date = datetime(end_dt.year,   end_dt.month,   1)
                        while cur_date <= end_date:
                            months_to_fetch.append((cur_date.year, cur_date.strftime("%B")))
                            cur_date = (
                                cur_date.replace(month=1, year=cur_date.year + 1)
                                if cur_date.month == 12
                                else cur_date.replace(month=cur_date.month + 1)
                            )
                        prog = st.progress(0, text="Starting…")
                        for i, (yr, mn) in enumerate(months_to_fetch):
                            prog.progress(i / len(months_to_fetch), text=f"Fetching {mn} {yr}…")
                            run_ai_tender_pipeline(target_year=yr, target_month=mn)
                        prog.progress(1.0, text="Done!")
                        st.success(f"✅ Fetched {len(months_to_fetch)} month(s) of tender data!")
                        st.cache_data.clear()
                        st.rerun()

    st.markdown("---")

    # ══════════════════════════════════════
    # BLOCK 3 — MAIN FILTERED LIST
    # ══════════════════════════════════════
    st.markdown(
        f"<div style='font-family:\"Bebas Neue\",sans-serif;font-size:18px;letter-spacing:3px;"
        f"color:#f8fafc;margin-bottom:14px;'>TENDERS FOR {selected_period} · {selected_company.upper()}</div>",
        unsafe_allow_html=True,
    )

    month_filter = st.selectbox(
        "Filter by Month", MONTHS_LIST, index=0,
        key="tender_month_filter",
        help="Select 'All Months' to see all tenders for this financial year",
    )

    # ── DB fetch ──
    if month_filter == "All Months":
        tenders      = manager.get_tenders_by_fy(selected_period, brand_kw)
        period_label = f"All Months · {selected_period}"
    else:
        tenders      = manager.get_tenders_by_fy_month(selected_period, month_filter, brand_kw)
        period_label = f"{month_filter} · {selected_period}"

    # ── stats strip ──
    if tenders:
        brands_found = sorted({t.get("brand", "Unknown") for t in tenders})

        stats_html = '<div style="display:flex;gap:10px;flex-wrap:wrap;margin-bottom:18px;">'
        stats_html += (
            f'<div style="background:#0f1520;border:1px solid #1c2540;border-radius:8px;padding:10px 18px;">'
            f'<div style="font-family:monospace;font-size:8px;color:#64748b;letter-spacing:2px;text-transform:uppercase;">Total</div>'
            f'<div style="font-size:24px;font-family:\'Bebas Neue\',sans-serif;color:#1FD8F0;letter-spacing:2px;">{len(tenders)}</div>'
            f'</div>'
        )
        for b in brands_found:
            cnt   = sum(1 for t in tenders if (t.get("brand") or "") == b)
            color = get_brand_color(b)
            stats_html += (
                f'<div style="background:#0f1520;border:1px solid #1c2540;border-radius:8px;padding:10px 18px;">'
                f'<div style="font-family:monospace;font-size:8px;color:#64748b;letter-spacing:2px;text-transform:uppercase;">{b}</div>'
                f'<div style="font-size:24px;font-family:\'Bebas Neue\',sans-serif;color:{color};letter-spacing:2px;">{cnt}</div>'
                f'</div>'
            )
        stats_html += "</div>"
        st.markdown(stats_html, unsafe_allow_html=True)

        st.markdown(
            f"<p style='font-size:11px;color:#94a3b8;font-family:monospace;'>"
            f"Showing <b>{len(tenders)}</b> instant records for <b>{selected_period}</b></p>",
            unsafe_allow_html=True,
        )

        for t in sorted(tenders, key=lambda x: x.get("publish_date", ""), reverse=True):
            _render_card(t, manager)

    else:
        st.info(
            f"No records found in the database for **{selected_company}** in **{period_label}**. "
            "You may need to fetch new data from the web using the menu above."
        )