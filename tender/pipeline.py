"""
pipeline.py  –  AI Tender Fetching Pipeline  (Tractor Edition)
===============================================================
Responsibilities:
  1. Web search for Tractor tenders (DuckDuckGo + Tavily)
  2. AI extraction via Gemini (JSON output)
  3. SQLite storage with deduplication
  4. Financial-year & month tagging

Companies tracked:
  Mahindra | Escorts Kubota | Sonalika | TAFE | Swaraj | John Deere
"""

import sqlite3
import json
import os
import time
import hashlib
import pickle
import concurrent.futures
from datetime import datetime, timedelta
from ddgs import DDGS
import requests
from Main.shared_config import get_tavily_key

# ─────────────────────────────────────────
# CONFIG  (user must set GEMINI_API_KEY)
# ─────────────────────────────────────────
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "AIzaSyCwPkqEd5p4VBGpK1cRKDGb2RiFZqO6EGk")
DB_NAME        = "tenders.db"
CACHE_DIR      = "cache"
CACHE_DURATION = 3600          # 1 hour web-search cache

# ── Tractor brands to track ──
BRANDS = [
    "Mahindra",
    "Escorts Kubota",
    "Sonalika",
    "TAFE",
    "Swaraj",
    "John Deere",
]

os.makedirs(CACHE_DIR, exist_ok=True)


# ─────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────
def calculate_financial_year(date_str: str) -> str:
    """Return 'FY YYYY-YY' for a date string YYYY-MM-DD."""
    try:
        d = datetime.strptime(str(date_str)[:10], "%Y-%m-%d")
    except Exception:
        d = datetime.now()
    if d.month >= 4:
        return f"FY {d.year}-{str(d.year + 1)[-2:]}"
    return f"FY {d.year - 1}-{str(d.year)[-2:]}"


def get_month_name(date_str: str) -> str:
    """Return full month name from date string."""
    try:
        return datetime.strptime(str(date_str)[:10], "%Y-%m-%d").strftime("%B")
    except Exception:
        return datetime.now().strftime("%B")


def _cache_path(tag: str) -> str:
    day = datetime.now().strftime("%Y-%m-%d")
    return os.path.join(CACHE_DIR, hashlib.md5(f"{tag}_{day}".encode()).hexdigest() + ".pkl")


def _load_cache(path: str):
    if os.path.exists(path):
        try:
            with open(path, "rb") as f:
                d = pickle.load(f)
            if time.time() - d["ts"] < CACHE_DURATION:
                return d["v"]
        except Exception:
            pass
    return None


def _save_cache(path: str, value) -> None:
    try:
        with open(path, "wb") as f:
            pickle.dump({"v": value, "ts": time.time()}, f)
    except Exception:
        pass


# ─────────────────────────────────────────
# DATABASE
# ─────────────────────────────────────────
def setup_database() -> None:
    """Create / migrate the tractor_tenders table."""
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS tractor_tenders (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        brand          TEXT,
        tender_title   TEXT,
        publish_date   DATE,
        financial_year TEXT,
        month          TEXT,
        value          TEXT,
        source_url     TEXT,
        description    TEXT,
        location       TEXT,
        company_name   TEXT,
        tender_type    TEXT,
        deadline_date  DATE,
        ai_summary     TEXT,
        created_at     TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(brand, tender_title, publish_date)
    )
    """)

    # Backward-compat: add any missing columns
    cur.execute("PRAGMA table_info(tractor_tenders)")
    existing = {row[1] for row in cur.fetchall()}
    add_cols = {
        "financial_year": "TEXT",
        "month":          "TEXT",
        "ai_summary":     "TEXT",
        "source_url":     "TEXT",
        "description":    "TEXT",
        "location":       "TEXT",
        "company_name":   "TEXT",
        "tender_type":    "TEXT",
        "deadline_date":  "DATE",
        "created_at":     "TIMESTAMP DEFAULT CURRENT_TIMESTAMP",
    }
    for col, col_type in add_cols.items():
        if col not in existing:
            try:
                cur.execute(f"ALTER TABLE tractor_tenders ADD COLUMN {col} {col_type}")
            except Exception:
                pass

    # Backfill financial_year & month where missing
    cur.execute("""
        SELECT id, publish_date FROM tractor_tenders
        WHERE (financial_year IS NULL OR financial_year = '') AND publish_date IS NOT NULL
    """)
    rows = cur.fetchall()
    for row_id, pub_date in rows:
        cur.execute(
            "UPDATE tractor_tenders SET financial_year=?, month=? WHERE id=?",
            (calculate_financial_year(pub_date), get_month_name(pub_date), row_id),
        )

    # Indexes
    for col in ("brand", "publish_date", "financial_year", "month"):
        try:
            cur.execute(f"CREATE INDEX IF NOT EXISTS idx_tr_{col} ON tractor_tenders({col})")
        except Exception:
            pass

    conn.commit()
    conn.close()


def data_exists(year: int, month: str) -> bool:
    """Return True if tenders for this month/year are already in DB."""
    try:
        month_num = datetime.strptime(month, "%B").month
    except Exception:
        return False
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    cur.execute(
        "SELECT COUNT(*) FROM tractor_tenders WHERE strftime('%Y', publish_date)=? AND strftime('%m', publish_date)=?",
        (str(year), f"{month_num:02d}"),
    )
    count = cur.fetchone()[0]
    conn.close()
    return count > 0


# ─────────────────────────────────────────
# WEB SEARCH
# ─────────────────────────────────────────
def _fetch_ddgs(query: str) -> list[str]:
    """Fetch using DuckDuckGo."""
    try:
        from ddgs import DDGS
        results = DDGS().text(query, max_results=10)
        if results:
            return [
                f"Title: {r.get('title','')}\nDetails: {r.get('body','')}\nURL: {r.get('href','')}\n\n"
                for r in results
            ]
    except Exception as e:
        print(f"[Pipeline] DDGS search error: {e}")
    return []


def _fetch_tavily(query: str) -> list[str]:
    """Fetch using Tavily API for deep AI parsing."""
    try:
        tavily_key = get_tavily_key()
        if not tavily_key:
            return []
        headers = {"Content-Type": "application/json"}
        data = {
            "api_key": tavily_key,
            "query": query,
            "search_depth": "advanced",
            "include_answer": False,
            "max_results": 5,
        }
        resp = requests.post("https://api.tavily.com/search", json=data, headers=headers)
        if resp.status_code == 200:
            results = resp.json().get("results", [])
            return [
                f"Title: {r.get('title','')}\nDetails: {r.get('content','')}\nURL: {r.get('url','')}\n\n"
                for r in results
            ]
    except Exception as e:
        print(f"[Pipeline] Tavily search error: {e}")
    return []


def _web_search(year: int, month: str, force: bool = False) -> list[str]:
    """Deep, anti-blocking search across Govt portals, tender aggregators."""
    cache_path = _cache_path(f"tractor_{year}_{month}")
    if not force:
        cached = _load_cache(cache_path)
        if cached:
            print(f"[Pipeline] Loaded {len(cached)} results from cache.")
            return cached

    all_content: list[str] = []

    for brand in BRANDS:
        queries = [
            # 1. GeM / Govt portal tenders
            f'"{brand}" tractor tender site:gem.gov.in OR site:eprocure.gov.in India {month} {year}',

            # 2. General tractor tender search
            f'"{brand}" tractor tender procurement India {month} {year}',

            # 3. Tender aggregator sites
            f'"{brand}" tractor tender (tendertiger OR tendernews OR tenderdetail OR bidassist) India {year}',

            # 4. State agriculture / govt departments
            f'"{brand}" tractor supply tender agriculture department India {year}',

            # 5. Competitor comparison tenders (helps cross-capture)
            f'tractor tender India {month} {year} Mahindra "Escorts Kubota" OR Sonalika OR TAFE OR Swaraj OR "John Deere"',
        ]

        for q in queries:
            # Tavily — deep scanning, no bot-block
            tavily_results = _fetch_tavily(q)
            if tavily_results:
                all_content.extend(tavily_results)

            # DuckDuckGo
            ddgs_results = _fetch_ddgs(q)
            if ddgs_results:
                all_content.extend(ddgs_results)

            # Anti-blocking delay
            time.sleep(2.5)

    if all_content:
        _save_cache(cache_path, all_content)

    return all_content


# ─────────────────────────────────────────
# AI EXTRACTION
# ─────────────────────────────────────────
def _ai_extract(raw_text: str, year: int, month: str) -> list[dict]:
    """Send raw web text to Gemini and get structured tender JSON."""
    import google.genai as genai
    client = genai.Client(api_key=GEMINI_API_KEY)

    month_num = datetime.strptime(month, "%B").month

    prompt = f"""
You are a tender data extraction expert for the Indian agricultural tractor industry.
Extract tractor-related tenders from the web content below.

Focus ONLY on these brands / companies:
  Mahindra | Escorts Kubota | Sonalika | TAFE | Swaraj | John Deere

Target period: {month} {year}.

Return a JSON ARRAY. Each object must contain EXACTLY these fields:
  brand          – one of: Mahindra / Escorts Kubota / Sonalika / TAFE / Swaraj / John Deere
  tender_title   – full tender title/description
  publish_date   – YYYY-MM-DD (estimate {year}-{month_num:02d}-01 if unknown)
  value          – tender value/amount as text, "Not Specified" if unknown
  source_url     – EXACT URL from the "URL:" line in the search result (do not fabricate)
  description    – brief description ≤120 words
  location       – city / state, "Not Specified" if unknown
  company_name   – name of the procuring organisation (e.g., state govt, PSU, etc.)
  tender_type    – Supply / AMC / Hire / Lease / Other
  deadline_date  – YYYY-MM-DD, "Not Specified" if unknown

Rules:
• Only include genuine tenders — NOT news articles about tenders.
• Pick only tractor / farm-equipment related tenders (not genset, not DG-set).
• Use the literal URL provided in the content for source_url.
• If no valid tenders found, return [].
• Return ONLY the raw JSON array, no markdown fences, no explanation.
• STRICTLY assign 'brand' to one of the 6 targets above if their name appears ANYWHERE in the tender.

WEB CONTENT:
{raw_text}
"""

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            text = response.text.strip()

            # Strip markdown fences if present
            for fence in ("```json", "```"):
                if text.startswith(fence):
                    text = text[len(fence):]
            if text.endswith("```"):
                text = text[:-3]

            extracted_data = json.loads(text.strip())
            print(f"[AI Engine] Successfully extracted {len(extracted_data)} items.")
            return extracted_data

        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "UNAVAILABLE" in error_msg or "quota" in error_msg.lower():
                print(
                    f"[Pipeline] Gemini API busy (503). Retrying in 5s… "
                    f"(Attempt {attempt + 1}/{max_retries})"
                )
                time.sleep(5)
                continue
            else:
                print(f"[Pipeline] Gemini error: {error_msg}")
                break

    return []


# ─────────────────────────────────────────
# DATABASE WRITE
# ─────────────────────────────────────────
def _store_tenders(tenders: list[dict], year: int, month: str) -> tuple[int, int]:
    """Insert / update tenders in DB. Returns (inserted, updated)."""
    conn = sqlite3.connect(DB_NAME)
    cur  = conn.cursor()
    inserted = updated = 0

    for item in tenders:
        pub_date = item.get("publish_date") or f"{year}-{datetime.strptime(month,'%B').month:02d}-01"
        fy       = calculate_financial_year(pub_date)
        mon_name = get_month_name(pub_date)

        # Sanitise
        brand   = (item.get("brand") or "Other").strip()
        title   = (item.get("tender_title") or "Untitled").strip()
        src_url = (item.get("source_url") or "").strip()

        # Skip obviously fabricated URLs
        if "example.com" in src_url or "yoursite" in src_url:
            src_url = ""

        try:
            cur.execute(
                "SELECT id FROM tractor_tenders WHERE brand=? AND tender_title=? AND publish_date=?",
                (brand, title, pub_date),
            )
            row = cur.fetchone()

            if row:
                cur.execute(
                    """UPDATE tractor_tenders SET
                         value=?, source_url=?, description=?, location=?,
                         company_name=?, tender_type=?, deadline_date=?,
                         financial_year=?, month=?
                       WHERE id=?""",
                    (
                        item.get("value", "Not Specified"),
                        src_url,
                        item.get("description", ""),
                        item.get("location", "Not Specified"),
                        item.get("company_name", "Not Specified"),
                        item.get("tender_type", "Not Specified"),
                        item.get("deadline_date", ""),
                        fy, mon_name, row[0],
                    ),
                )
                updated += 1
            else:
                cur.execute(
                    """INSERT INTO tractor_tenders
                         (brand, tender_title, publish_date, financial_year, month,
                          value, source_url, description, location,
                          company_name, tender_type, deadline_date)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        brand, title, pub_date, fy, mon_name,
                        item.get("value", "Not Specified"),
                        src_url,
                        item.get("description", ""),
                        item.get("location", "Not Specified"),
                        item.get("company_name", "Not Specified"),
                        item.get("tender_type", "Not Specified"),
                        item.get("deadline_date", ""),
                    ),
                )
                inserted += 1

        except sqlite3.IntegrityError:
            pass
        except Exception as e:
            print(f"[Pipeline] DB error: {e}")

    conn.commit()
    conn.close()
    return inserted, updated


# ─────────────────────────────────────────
# PUBLIC ENTRY POINT
# ─────────────────────────────────────────
def run_ai_tender_pipeline(
    target_year:  int  | None = None,
    target_month: str  | None = None,
    force:        bool        = False,
) -> bool:
    year  = target_year  or datetime.now().year
    month = target_month or datetime.now().strftime("%B")

    print(f"\n[Pipeline] ── Starting for {month} {year} ──")

    # ── STEP 1: web search ──
    all_content = _web_search(year, month, force=force)
    if not all_content:
        print("[Pipeline] No web content found.")
        return False
    print(f"[Pipeline] {len(all_content)} search result snippets retrieved.")

    # ── STEP 2: AI extraction ──
    raw_text = "\n".join(all_content)
    tenders  = _ai_extract(raw_text, year, month)
    print(f"[Pipeline] AI extracted {len(tenders)} tender records.")
    if not tenders:
        return True

    # ── STEP 3: store ──
    inserted, updated = _store_tenders(tenders, year, month)
    print(f"[Pipeline] Done. {inserted} inserted, {updated} updated.")
    return True


# ─────────────────────────────────────────
if __name__ == "__main__":
    setup_database()
    run_ai_tender_pipeline()