"""
Standalone diagnostic script — run this directly (not through Streamlit) to check
whether your Tavily and Groq API keys/clients actually work.

Usage:
    python test_apis.py

Make sure this is run from a location where `from Main.shared_config import ...` resolves,
same as your Streamlit app.
"""

import requests

print("=" * 60)
print("STEP 1: Importing shared_config")
print("=" * 60)
try:
    from Main.shared_config import get_groq_client, get_tavily_key, safe_json_parse
    print("✅ Import successful")
except Exception as e:
    print(f"❌ FAILED to import from Main.shared_config: {repr(e)}")
    raise SystemExit(1)

print()
print("=" * 60)
print("STEP 2: Checking Tavily API key")
print("=" * 60)
try:
    tavily_key = get_tavily_key()
    if not tavily_key:
        print("❌ get_tavily_key() returned empty/None")
    else:
        print(f"✅ Got a key (length {len(tavily_key)}, starts with '{tavily_key[:6]}...')")
except Exception as e:
    print(f"❌ get_tavily_key() raised: {repr(e)}")
    tavily_key = None

print()
print("=" * 60)
print("STEP 3: Making a real Tavily search call")
print("=" * 60)
if tavily_key:
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key": tavily_key,
                "query": "Mahindra tractor global sales units 2024",
                "search_depth": "advanced",
                "max_results": 3
            },
            timeout=15
        )
        print(f"HTTP status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("results", [])
            print(f"✅ Got {len(results)} results")
            for r in results[:2]:
                print(f"   - {r.get('url')}")
                print(f"     content snippet: {r.get('content', '')[:150]}")
        else:
            print(f"❌ Tavily error body: {resp.text[:500]}")
    except Exception as e:
        print(f"❌ Tavily request raised: {repr(e)}")
else:
    print("⏭️  Skipped — no key")

print()
print("=" * 60)
print("STEP 4: Checking Groq client")
print("=" * 60)
try:
    client = get_groq_client()
    print("✅ get_groq_client() returned a client object")
except Exception as e:
    print(f"❌ get_groq_client() raised: {repr(e)}")
    client = None

print()
print("=" * 60)
print("STEP 5: Making a real Groq completion call")
print("=" * 60)
if client:
    try:
        ai_res = client.chat.completions.create(
            messages=[{"role": "user", "content": 'Return ONLY this exact JSON: {"units_annual": 12345, "growth_percent": "+5.0%"}'}],
            model="llama-3.3-70b-versatile",
            response_format={"type": "json_object"},
            temperature=0.0
        )
        raw = ai_res.choices[0].message.content
        print(f"✅ Raw Groq response: {raw}")
        try:
            parsed = safe_json_parse(raw)
            print(f"✅ safe_json_parse() result: {parsed}")
        except Exception as e:
            print(f"❌ safe_json_parse() raised: {repr(e)}")
    except Exception as e:
        print(f"❌ Groq completion call raised: {repr(e)}")
else:
    print("⏭️  Skipped — no client")

print()
print("=" * 60)
print("DONE. Paste this entire output back for diagnosis.")
print("=" * 60)